"""Identifier sanitizing, reserved-word escaping and the Django -> Mermaid type table.

The reserved-word lists come from the lexers of Mermaid 12's erDiagram and
classDiagram grammars and were confirmed by rendering with mermaid-cli.
"""

import re
from typing import Tuple

# Django field class name -> Mermaid type. Looked up along the field's MRO,
# so subclasses of known fields (e.g. a custom ``MoneyField(DecimalField)``)
# inherit the mapping of their closest known ancestor.
TYPE_MAP = {
    "AutoField": "int",
    "BigAutoField": "int",
    "SmallAutoField": "int",
    "IntegerField": "int",
    "SmallIntegerField": "int",
    "BigIntegerField": "int",
    "PositiveIntegerField": "int",
    "PositiveSmallIntegerField": "int",
    "PositiveBigIntegerField": "int",
    "FloatField": "float",
    "DecimalField": "decimal",
    "BooleanField": "bool",
    "NullBooleanField": "bool",
    "CharField": "string",
    "SlugField": "string",
    "EmailField": "string",
    "URLField": "string",
    "TextField": "text",
    "DateField": "date",
    "DateTimeField": "datetime",
    "TimeField": "time",
    "DurationField": "duration",
    "UUIDField": "uuid",
    "JSONField": "json",
    "BinaryField": "binary",
    "FileField": "file",
    "ImageField": "image",
    "IPAddressField": "ip",
    "GenericIPAddressField": "ip",
}

# Placeholder type used with ``types="none"``: erDiagram requires a type token.
NO_TYPE = "field"

# Whole-word, case-insensitive keywords of the erDiagram lexer that would be
# mis-read when used as an entity name.
ER_RESERVED = frozenset(
    {"erdiagram", "style", "classdef", "class", "subgraph", "end", "one", "many", "to"}
)
# Inside an entity block these are key markers, so attributes can't be named so.
ER_RESERVED_ATTRIBUTES = frozenset({"pk", "fk", "uk"})
# Case-sensitive keywords of the classDiagram lexer.
CLASS_RESERVED = frozenset(
    {
        "classDiagram",
        "classDiagram-v2",
        "class",
        "classDef",
        "namespace",
        "style",
        "cssClass",
        "callback",
        "call",
        "link",
        "click",
        "note",
        "href",
        "o",
        "_self",
        "_blank",
        "_parent",
        "_top",
        "direction",
    }
)

_IDENT_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")
_TYPE_ILLEGAL = re.compile(r"[^A-Za-z0-9_\-]")


def sanitize_identifier(value: str) -> str:
    """Make ``value`` a plain ASCII identifier usable as a Mermaid node id."""
    ident = _IDENT_ILLEGAL.sub("_", value)
    if not ident or not ident[0].isalpha():
        ident = "M" + ident
    return ident


def er_ident(key: str) -> str:
    return key + "_" if key.lower() in ER_RESERVED else key


def class_ident(key: str) -> str:
    return key + "_" if key in CLASS_RESERVED else key


def er_attribute_name(name: str) -> str:
    return "`%s`" % name if name.lower() in ER_RESERVED_ATTRIBUTES else name


def quote_label(text: str) -> str:
    """Double-quote a relationship label, escaping embedded quotes."""
    return '"%s"' % text.replace('"', "#quot;")


def quote_comment(text: str) -> str:
    """Double-quote an erDiagram attribute comment (entity codes aren't decoded there)."""
    return '"%s"' % text.replace('"', "'").replace("\n", " ").replace("\r", " ")


def _fallback_type(class_name: str) -> str:
    name = class_name[:-5] if class_name.endswith("Field") and len(class_name) > 5 else class_name
    name = _TYPE_ILLEGAL.sub("_", name.lower())
    if not name or not name[0].isalpha():
        name = "t" + name
    return name


def field_type(field) -> Tuple[str, str]:
    """Return ``(mermaid_type, params)`` for a concrete Django field.

    Relational fields take the type of the primary key they point at.
    """
    seen = 0
    while getattr(field, "is_relation", False) and getattr(field, "concrete", False):
        target = getattr(field, "target_field", None)
        if target is None or seen > 20:
            break
        field, seen = target, seen + 1

    # Django 5.0+ GeneratedField: describe the value it produces.
    output_field = getattr(field, "output_field", None)
    if type(field).__name__ == "GeneratedField" and output_field is not None:
        field = output_field

    mermaid_type = None
    for klass in type(field).__mro__:
        if klass.__name__ in TYPE_MAP:
            mermaid_type = TYPE_MAP[klass.__name__]
            break
        if klass.__name__ == "Field":
            break
    if mermaid_type is None:
        return _fallback_type(type(field).__name__), ""

    params = ""
    if mermaid_type == "string" and getattr(field, "max_length", None):
        params = str(field.max_length)
    elif mermaid_type == "decimal":
        digits = getattr(field, "max_digits", None)
        places = getattr(field, "decimal_places", None)
        if digits is not None and places is not None:
            params = "%s,%s" % (digits, places)
    return mermaid_type, params
