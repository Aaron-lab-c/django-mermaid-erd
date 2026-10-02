"""Choosing which models end up in the diagram."""

from collections import deque
from fnmatch import fnmatchcase
from typing import Iterable, List, Optional, Sequence

from .exceptions import MermaidErdError
from .schema import Schema

BUILTIN_PREFIX = "django.contrib."


def is_builtin(app_config) -> bool:
    return app_config.name.startswith(BUILTIN_PREFIX)


def matches(model, pattern: str) -> bool:
    """Case-insensitive glob match against ``app_label`` or ``app_label.ModelName``."""
    opts = model._meta
    pattern = pattern.lower()
    if "." in pattern:
        subject = "%s.%s" % (opts.app_label, opts.object_name)
    else:
        subject = opts.app_label
    return fnmatchcase(subject.lower(), pattern)


def _app_config(app_label: str, registry):
    try:
        return registry.get_app_config(app_label)
    except LookupError:
        available = ", ".join(sorted(c.label for c in registry.get_app_configs() if c.models_module))
        raise MermaidErdError(
            "Unknown app label '%s'. Installed apps with models: %s" % (app_label, available or "none")
        ) from None


def find_model(spec: str, registry=None):
    """Resolve ``app.Model`` (or a bare, unambiguous ``Model``) to a model class."""
    if registry is None:
        from django.apps import apps as registry
    if "." in spec:
        app_label, model_name = spec.split(".", 1)
        config = _app_config(app_label, registry)
        try:
            return config.get_model(model_name)
        except LookupError:
            raise MermaidErdError("App '%s' has no model named '%s'." % (app_label, model_name)) from None
    candidates = [
        m for m in registry.get_models(include_swapped=True) if m._meta.object_name.lower() == spec.lower()
    ]
    if not candidates:
        raise MermaidErdError("No model named '%s'." % spec)
    if len(candidates) > 1:
        labels = ", ".join(sorted("%s.%s" % (m._meta.app_label, m._meta.object_name) for m in candidates))
        raise MermaidErdError("Model name '%s' is ambiguous: %s. Use app.Model." % (spec, labels))
    return candidates[0]


def select_models(
    targets: Sequence[str] = (),
    exclude: Iterable[str] = (),
    include_builtin: bool = False,
    include_proxy: bool = True,
    registry=None,
) -> List[type]:
    """Return the models to draw.

    ``targets`` are app labels or ``app.Model`` strings; empty means every
    installed app except ``django.contrib.*`` (unless ``include_builtin``).
    Apps named explicitly are always included, built-in or not.
    """
    if registry is None:
        from django.apps import apps as registry

    chosen: List[type] = []
    if targets:
        for target in targets:
            if "." in target:
                model = find_model(target, registry)
                if model._meta.swapped:
                    raise MermaidErdError("Model '%s' is swapped out by '%s'." % (target, model._meta.swapped))
                chosen.append(model)
            else:
                chosen.extend(_app_config(target, registry).get_models())
    else:
        for model in registry.get_models():
            if include_builtin or not is_builtin(registry.get_app_config(model._meta.app_label)):
                chosen.append(model)

    patterns = list(exclude)
    result: List[type] = []
    seen = set()
    for model in chosen:
        if model in seen:
            continue
        seen.add(model)
        if not include_proxy and model._meta.proxy:
            continue
        if any(matches(model, p) for p in patterns):
            continue
        result.append(model)
    return result


def focus_schema(schema: Schema, key: str, depth: int = 1) -> Schema:
    """Keep only ``key`` and entities within ``depth`` relation hops of it."""
    neighbours = {e.key: set() for e in schema.entities}
    for rel in schema.relations:
        if rel.source in neighbours and rel.target in neighbours:
            neighbours[rel.source].add(rel.target)
            neighbours[rel.target].add(rel.source)
    distance = {key: 0}
    queue = deque([key])
    while queue:
        current = queue.popleft()
        if distance[current] >= depth:
            continue
        for other in sorted(neighbours[current]):
            if other not in distance:
                distance[other] = distance[current] + 1
                queue.append(other)
    entities = [e for e in schema.entities if e.key in distance]
    relations = [r for r in schema.relations if r.source in distance and r.target in distance]
    return Schema(entities=entities, relations=relations, apps=[]).normalized()


def entity_key_for(schema: Schema, label: str) -> Optional[str]:
    """Return the key of the entity whose label is ``app.Model``, or ``None``."""
    for entity in schema.entities:
        if entity.label == label:
            return entity.key
    return None
