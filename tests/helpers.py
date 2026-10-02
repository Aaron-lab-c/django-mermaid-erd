"""Shared fixtures: hand-built schemas and the list of snapshot configurations."""

from django_mermaid_erd.schema import Attribute, Entity, Relation, Schema


def attr(name, type="int", **kw):
    kw.setdefault("django_type", "Field")
    return Attribute(name=name, type=type, **kw)


def entity(key, app="app", model=None, attrs=(), **kw):
    model = model or key
    return Entity(
        key=key, label="%s.%s" % (app, model), app_label=app, model_name=model, attributes=list(attrs), **kw
    )


def mini_schema():
    """A small schema exercising every relation kind."""
    entities = [
        entity("Parent", attrs=[attr("id", pk=True)]),
        entity(
            "Child",
            attrs=[
                attr("id", pk=True),
                attr("parent", attname="parent_id", fk=True, references="app.Parent"),
                attr("maybe", attname="maybe_id", fk=True, nullable=True, references="app.Parent"),
                attr("ext", attname="ext_id", fk=True, references="other.Gone"),
                attr("note", "string", type_params="20", comment='say "hi"'),
                attr("price", "decimal", type_params="10,2", choices=True, verbose_name="價格"),
            ],
        ),
        entity("Twin", attrs=[attr("child", attname="child_id", fk=True, unique=True)]),
        entity("Sub"),
        entity("Alias", managed=False, proxy=True),
        entity("Tagged", attrs=[attr("content_object", "generic", comment="GenericForeignKey")]),
    ]
    relations = [
        Relation("Child", "Parent", "fk", "parent"),
        Relation("Child", "Parent", "fk", "maybe", nullable=True),
        Relation("Twin", "Child", "o2o", "child"),
        Relation("Twin", "Parent", "o2o", "opt", nullable=True),
        Relation("Child", "Twin", "m2m", "friends"),
        Relation("Child", "Twin", "m2m", "others", through="app.Link"),
        Relation("Sub", "Parent", "inherit", "inherits"),
        Relation("Alias", "Parent", "proxy", "proxy"),
        Relation("Tagged", "Parent", "generic", "content_object", nullable=True),
        Relation("Parent", "Parent", "fk", "up", nullable=True, self_ref=True),
    ]
    return Schema(entities, relations, ["app"]).normalized()


def reserved_schema():
    """Entity, app and attribute names that collide with Mermaid keywords."""
    names = ["Class", "Style", "To", "One", "Many", "End", "Note", "Link", "Click"]
    entities = [
        entity(n, app="note", attrs=[attr("id", pk=True), attr("fk"), attr("uk", unique=True)]) for n in names
    ]
    entities.append(entity("o", app="link", attrs=[attr("id", pk=True)]))
    entities.append(entity("call", app="click", attrs=[attr("id", pk=True)]))
    relations = [Relation(n, "o", "fk", "class") for n in names] + [Relation("call", "Class", "m2m", "style")]
    return Schema(entities, relations, []).normalized()


# name -> (targets, options) rendered against the test project
SNAPSHOTS = {
    "er_default": ((), {}),
    "er_keys": ((), {"fields": "keys"}),
    "er_no_fields": ((), {"fields": "none"}),
    "er_full_types": ((), {"types": "full"}),
    "er_no_types": (("shop",), {"types": "none"}),
    "er_qualified": ((), {"qualified": True}),
    "er_comments": ((), {"comments": True, "verbose_names": True}),
    "er_names_sorted": (("shop",), {"field_names": "name", "sort_fields": True}),
    "er_max_fields": ((), {"max_fields": 2}),
    "er_builtin_generic": ((), {"include_builtin": True, "generic_edges": True}),
    "er_direction_lr": (("inventory",), {"direction": "LR", "banner": False}),
    "focus_order_depth1": ((), {"focus": "shop.Order", "depth": 1}),
    "focus_order_depth2": ((), {"focus": "Order", "depth": 2}),
    "class_default": ((), {"diagram": "class"}),
    "class_flat": ((), {"diagram": "class", "group_by_app": False, "comments": True, "direction": "LR"}),
    "class_keys_builtin": (
        (),
        {"diagram": "class", "fields": "keys", "include_builtin": True, "generic_edges": True},
    ),
}
