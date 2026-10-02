"""Mermaid ``erDiagram`` renderer."""

from typing import Optional

from ..naming import er_attribute_name, er_ident, quote_comment, quote_label
from ..schema import Relation, Schema
from ._common import (
    attribute_name,
    attribute_type,
    banner_text,
    comment_parts,
    entities_by_app,
    more_fields_note,
    visible_attributes,
)

INDENT = "    "


def render_er(
    schema: Schema,
    *,
    fields: str = "all",
    types: str = "short",
    field_names: str = "attname",
    sort_fields: bool = False,
    max_fields: Optional[int] = None,
    comments: bool = False,
    verbose_names: bool = False,
    direction: Optional[str] = None,
    banner: bool = True,
) -> str:
    schema = schema.normalized()
    ident = {e.key: er_ident(e.key) for e in schema.entities}
    present = {e.label for e in schema.entities}

    lines = ["erDiagram"]
    if banner:
        lines.append(INDENT + "%% " + banner_text())
    if direction:
        lines.append(INDENT + "direction " + direction)

    for app, entities in entities_by_app(schema):
        lines.append(INDENT + "%% app: " + app)
        for entity in entities:
            if comments and not entity.managed:
                lines.append(INDENT + "%%%% %s: unmanaged" % entity.label)
            name = ident[entity.key]
            decl = name if name == entity.model_name else '%s["%s"]' % (name, _display(entity))
            attrs, hidden = visible_attributes(entity, fields, field_names, sort_fields, max_fields)
            if attrs:
                lines.append(INDENT + decl + " {")
                for attr in attrs:
                    line = "%s %s" % (attribute_type(attr, types), er_attribute_name(attribute_name(attr, field_names)))
                    keys = [k for k, on in (("PK", attr.pk), ("FK", attr.fk), ("UK", attr.unique)) if on]
                    if keys:
                        line += " " + ", ".join(keys)
                    parts = comment_parts(attr, present, comments, verbose_names)
                    if parts:
                        line += " " + quote_comment(", ".join(parts))
                    lines.append(INDENT * 2 + line)
                lines.append(INDENT + "}")
            else:
                lines.append(INDENT + decl)
            if hidden:
                lines.append(INDENT + more_fields_note(hidden))

    if schema.relations:
        lines.append("")
        for rel in schema.relations:
            lines.append(INDENT + _relation(rel, ident))
    return "\n".join(lines) + "\n"


def _display(entity) -> str:
    # Plain model name when the id only differs because of reserved-word escaping.
    return entity.model_name if entity.key == entity.model_name else entity.label


def _relation(rel: Relation, ident) -> str:
    src, tgt = ident[rel.source], ident[rel.target]
    one = "|o" if rel.nullable else "||"
    if rel.kind == "fk":
        return "%s %s--o{ %s : %s" % (tgt, one, src, quote_label(rel.label))
    if rel.kind == "o2o":
        return "%s %s--|| %s : %s" % (tgt, one, src, quote_label(rel.label))
    if rel.kind == "m2m":
        label = rel.label + (" via " + rel.through if rel.through else "")
        return "%s }o--o{ %s : %s" % (src, tgt, quote_label(label))
    if rel.kind == "inherit":
        return "%s ||--|| %s : %s" % (tgt, src, quote_label(rel.label))
    if rel.kind == "proxy":
        return "%s ||..|| %s : %s" % (tgt, src, quote_label(rel.label))
    if rel.kind == "generic":
        return "%s |o..o{ %s : %s" % (tgt, src, quote_label(rel.label))
    raise ValueError("unknown relation kind %r" % rel.kind)
