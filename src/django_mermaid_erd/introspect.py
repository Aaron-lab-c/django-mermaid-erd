"""Django models -> :class:`~django_mermaid_erd.schema.Schema`.

Pure ``_meta`` inspection: nothing here ever touches the database. Django's
contenttypes module is deliberately not imported (it can't be imported when
the app isn't installed); generic foreign keys are recognised by duck typing.
"""

from collections import Counter
from typing import Dict, Iterable, List

from .naming import field_type, sanitize_identifier
from .schema import Attribute, Entity, Relation, Schema


def model_label(model) -> str:
    return "%s.%s" % (model._meta.app_label, model._meta.object_name)


def _assign_keys(models, qualified: bool) -> Dict[type, str]:
    counts = Counter(m._meta.object_name for m in models)
    keys: Dict[type, str] = {}
    used = set()
    for model in models:
        opts = model._meta
        if qualified or counts[opts.object_name] > 1:
            key = sanitize_identifier("%s_%s" % (opts.app_label, opts.object_name))
        else:
            key = sanitize_identifier(opts.object_name)
        base, n = key, 2
        while key in used:
            key, n = "%s_%d" % (base, n), n + 1
        used.add(key)
        keys[model] = key
    return keys


def _is_generic_fk(field) -> bool:
    return hasattr(field, "ct_field") and hasattr(field, "fk_field")


def _is_composite_pk(field) -> bool:
    return type(field).__name__ == "CompositePrimaryKey"


def _pk_names(opts) -> set:
    pk = opts.pk
    if pk is None:
        return set()
    if _is_composite_pk(pk):
        return set(getattr(pk, "field_names", ()) or ())
    return {pk.name}


def _verbose_name(field) -> str:
    verbose = getattr(field, "verbose_name", None)
    if not verbose:
        return ""
    verbose = str(verbose)
    return "" if verbose == field.name.replace("_", " ") else verbose


def _local_fields(opts) -> List:
    fields = list(opts.local_fields) + list(opts.local_many_to_many)
    return sorted(fields, key=lambda f: (getattr(f, "creation_counter", 0), f.name))


def build_schema(
    models: Iterable,
    *,
    qualified: bool = False,
    generic_edges: bool = False,
) -> Schema:
    """Describe ``models`` (Django model classes) as a :class:`Schema`.

    Relations are only created between models in ``models``; foreign keys to
    anything else keep their attribute (with ``references`` set) but get no edge.
    """
    models = sorted(set(models), key=lambda m: (m._meta.app_label, m._meta.object_name))
    in_scope = set(models)
    keys = _assign_keys(models, qualified)

    entities: List[Entity] = []
    relations: List[Relation] = []

    for model in models:
        opts = model._meta
        key = keys[model]
        pk_names = _pk_names(opts)
        attributes: List[Attribute] = []
        parents: List[str] = []

        for f in _local_fields(opts):
            if _is_composite_pk(f):
                continue
            if f.many_to_many:
                _add_m2m(f, key, keys, in_scope, relations)
                continue
            if not getattr(f, "concrete", False):
                continue
            if f.is_relation and f.remote_field is not None:
                remote = f.remote_field
                if f.one_to_one and getattr(remote, "parent_link", False):
                    continue  # MTI pointer; drawn as an "inherits" edge below
                target = f.related_model
                kind = "o2o" if f.one_to_one else "fk"
                if target in in_scope:
                    relations.append(
                        Relation(
                            source=key,
                            target=keys[target],
                            kind=kind,
                            label=f.name,
                            nullable=bool(f.null),
                            self_ref=target is model,
                        )
                    )
            attributes.append(_attribute(f, pk_names))

        # Generic foreign keys sit right after their object-id column, which
        # keeps the order identical across Django versions.
        for f in opts.private_fields:
            if not _is_generic_fk(f) or getattr(f, "mti_inherited", False):
                continue
            attr = Attribute(
                name=f.name,
                attname=f.name,
                type="generic",
                django_type=type(f).__name__,
                comment="GenericForeignKey",
            )
            index = next(
                (i + 1 for i, a in enumerate(attributes) if a.name == f.fk_field),
                len(attributes),
            )
            attributes.insert(index, attr)
            if generic_edges:
                ct_model = _content_type_model(opts, f)
                if ct_model in in_scope:
                    relations.append(
                        Relation(
                            source=key,
                            target=keys[ct_model],
                            kind="generic",
                            label=f.name,
                            nullable=True,
                        )
                    )

        if opts.proxy:
            parent = opts.proxy_for_model
            if parent not in in_scope:
                parent = opts.concrete_model
            if parent in in_scope and parent is not model:
                parents.append(keys[parent])
                relations.append(
                    Relation(source=key, target=keys[parent], kind="proxy", label="proxy")
                )
        else:
            for parent, ptr in opts.parents.items():
                if ptr is None or parent not in in_scope:
                    continue
                parents.append(keys[parent])
                relations.append(
                    Relation(source=key, target=keys[parent], kind="inherit", label="inherits")
                )

        entities.append(
            Entity(
                key=key,
                label=model_label(model),
                app_label=opts.app_label,
                model_name=opts.object_name,
                attributes=attributes,
                abstract=bool(opts.abstract),
                proxy=bool(opts.proxy),
                managed=bool(opts.managed),
                parents=parents,
            )
        )

    return Schema(entities=entities, relations=relations, apps=[]).normalized()


def _attribute(f, pk_names) -> Attribute:
    mermaid_type, params = field_type(f)
    is_pk = f.name in pk_names or bool(getattr(f, "primary_key", False))
    is_fk = bool(f.is_relation and f.remote_field is not None)
    return Attribute(
        name=f.name,
        attname=getattr(f, "attname", None) or f.name,
        type=mermaid_type,
        type_params=params,
        django_type=type(f).__name__,
        pk=is_pk,
        fk=is_fk,
        unique=bool(getattr(f, "unique", False)) and not is_pk,
        nullable=bool(getattr(f, "null", False)),
        choices=bool(getattr(f, "choices", None)),
        verbose_name=_verbose_name(f),
        references=model_label(f.related_model) if is_fk else None,
    )


def _add_m2m(f, key, keys, in_scope, relations) -> None:
    target = f.related_model
    if target not in in_scope:
        return
    through = f.remote_field.through
    through_label = None
    if not through._meta.auto_created:
        if through in in_scope:
            return  # the through model's own two FKs already draw this link
        through_label = model_label(through)
    relations.append(
        Relation(
            source=key,
            target=keys[target],
            kind="m2m",
            label=f.name,
            self_ref=keys[target] == key,
            through=through_label,
        )
    )


def _content_type_model(opts, gfk):
    try:
        return opts.get_field(gfk.ct_field).remote_field.model
    except Exception:  # misconfigured GFK: just don't draw the edge
        return None
