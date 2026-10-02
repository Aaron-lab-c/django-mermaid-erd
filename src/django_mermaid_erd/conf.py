"""Option defaults, ``settings.MERMAID_ERD`` and CLI-argument merging.

Precedence: command-line argument > ``settings.MERMAID_ERD`` > built-in default.
``EXCLUDE`` is the exception: patterns from settings and ``--exclude`` add up.
"""

from dataclasses import dataclass, fields, replace
from typing import Optional, Tuple

from .exceptions import MermaidErdError
from .render import DIAGRAMS
from .render._common import DIRECTION_CHOICES, FIELD_NAMES_CHOICES, FIELDS_CHOICES, TYPES_CHOICES

RENDERER_CHOICES = ("auto", "mmdc", "ink")


@dataclass(frozen=True)
class Options:
    # selection
    targets: Tuple[str, ...] = ()
    exclude: Tuple[str, ...] = ()
    include_builtin: bool = False
    proxy: bool = True
    focus: Optional[str] = None
    depth: int = 1
    # content
    diagram: str = "er"
    fields: str = "all"
    types: str = "short"
    field_names: str = "attname"
    sort_fields: bool = False
    max_fields: Optional[int] = None
    comments: bool = False
    verbose_names: bool = False
    generic_edges: bool = False
    qualified: bool = False
    direction: Optional[str] = None
    banner: bool = True
    group_by_app: Optional[bool] = None
    # output
    output: Optional[str] = None
    md: Optional[bool] = None
    inject: Optional[str] = None
    check: bool = False
    svg: Optional[str] = None
    png: Optional[str] = None
    renderer: str = "auto"

    def render_options(self) -> dict:
        return {
            "fields": self.fields,
            "types": self.types,
            "field_names": self.field_names,
            "sort_fields": self.sort_fields,
            "max_fields": self.max_fields,
            "comments": self.comments,
            "verbose_names": self.verbose_names,
            "direction": self.direction,
            "banner": self.banner,
            "group_by_app": self.group_by_app,
        }


# settings key -> (Options attribute, validator)
_CHOICES = {
    "diagram": DIAGRAMS,
    "fields": FIELDS_CHOICES,
    "types": TYPES_CHOICES,
    "field_names": FIELD_NAMES_CHOICES,
    "direction": DIRECTION_CHOICES,
    "renderer": RENDERER_CHOICES,
}
_BOOLS = {
    "include_builtin",
    "proxy",
    "sort_fields",
    "comments",
    "verbose_names",
    "generic_edges",
    "qualified",
    "banner",
    "group_by_app",
}
_INTS = {"max_fields", "depth"}
SETTINGS_KEYS = {
    name.upper(): name
    for name in sorted(_BOOLS | _INTS | set(_CHOICES) | {"exclude"})
}


def _validate(name: str, value, source: str):
    if name in _CHOICES:
        if value is not None and value not in _CHOICES[name]:
            raise MermaidErdError(
                "%s: invalid %s %r (choose from %s)" % (source, name, value, ", ".join(_CHOICES[name]))
            )
    elif name in _BOOLS:
        if not isinstance(value, bool) and not (name == "group_by_app" and value is None):
            raise MermaidErdError("%s: %s must be True or False, not %r" % (source, name, value))
    elif name in _INTS:
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise MermaidErdError("%s: %s must be a non-negative integer, not %r" % (source, name, value))
    elif name == "exclude":
        if isinstance(value, str) or not all(isinstance(v, str) for v in value):
            raise MermaidErdError("%s: EXCLUDE must be a list of strings" % source)
        value = tuple(value)
    return value


def settings_overrides() -> dict:
    from django.conf import settings

    raw = getattr(settings, "MERMAID_ERD", None) or {}
    if not isinstance(raw, dict):
        raise MermaidErdError("settings.MERMAID_ERD must be a dict")
    result = {}
    for key, value in raw.items():
        if key not in SETTINGS_KEYS:
            raise MermaidErdError(
                "settings.MERMAID_ERD: unknown key %r (valid keys: %s)" % (key, ", ".join(sorted(SETTINGS_KEYS)))
            )
        name = SETTINGS_KEYS[key]
        result[name] = _validate(name, value, "settings.MERMAID_ERD")
    return result


def resolve_options(cli: Optional[dict] = None, use_settings: bool = True) -> Options:
    """Merge built-in defaults, settings and ``cli`` (``None`` values = not given)."""
    known = {f.name for f in fields(Options)}
    opts = Options()
    if use_settings:
        opts = replace(opts, **settings_overrides())
    given = {}
    for name, value in (cli or {}).items():
        if name not in known or value is None:
            continue
        if name in ("targets", "exclude"):
            value = tuple(value)
        given[name] = _validate(name, value, "option")
    if "exclude" in given:
        given["exclude"] = tuple(opts.exclude) + given["exclude"]
    return replace(opts, **given)


__all__ = ["Options", "resolve_options", "settings_overrides", "SETTINGS_KEYS", "RENDERER_CHOICES"]
