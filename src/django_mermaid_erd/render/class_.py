"""Mermaid ``classDiagram`` renderer (namespaces per app, inheritance arrows)."""

from typing import Optional

from ..naming import CLASS_RESERVED, class_ident
from ..schema import Relation, Schema
from ._common import (
    attribute_name,
    attribute_type,
    banner_text,
    entities_by_app,
    more_fields_note,
    visible_attributes,
)

INDENT = "    "


def render_class(
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
    group_by_app: bool = True,
) -> str:
    # verbose_names has no place to go in classDiagram members; accepted for API symmetry.
    del verbose_names
    if types == "full":
        types = "short"  # "decimal(10,2)" would be parsed as a method signature
    schema = schema.normalized()
    ident = {e.key: class_ident(e.key) for e in schema.entities}
    class_ids = set(ident.values())

    lines = ["classDiagram"]
    if banner:
        lines.append(INDENT + "%% " + banner_text())
    if direction:
        lines.append(INDENT + "direction " + direction)

    for app, entities in entities_by_app(schema):
        if group_by_app:
            lines.append(INDENT + "namespace %s {" % _namespace(app, class_ids))
            pad = INDENT * 2
        else:
            lines.append(INDENT + "%% app: " + app)
            pad = INDENT
        for entity in entities:
            name = ident[entity.key]
            decl = "class " + name
            if name != entity.model_name:
                shown = entity.model_name if entity.key == entity.model_name else entity.label
                decl += '["%s"]' % shown
            body = []
            if comments:
                if entity.proxy:
                    body.append("<<proxy>>")
                if not entity.managed:
                    body.append("<<unmanaged>>")
            attrs, hidden = visible_attributes(entity, fields, field_names, sort_fields, max_fields)
            for attr in attrs:
                member_type = "" if types == "none" else attribute_type(attr, types) + " "
                body.append("+%s%s" % (member_type, attribute_name(attr, field_names)))
            if body:
                lines.append(pad + decl + " {")
                lines.extend(pad + INDENT + item for item in body)
                lines.append(pad + "}")
            else:
                lines.append(pad + decl)
            if hidden:
                lines.append(pad + more_fields_note(hidden))
        if group_by_app:
            lines.append(INDENT + "}")

    if schema.relations:
        lines.append("")
        for rel in schema.relations:
            lines.append(INDENT + _relation(rel, ident))
    return "\n".join(lines) + "\n"


def _namespace(app: str, class_ids) -> str:
    # A namespace sharing an id with a class can hang Mermaid's layout.
    name = app
    while name in CLASS_RESERVED or name in class_ids:
        name += "_"
    return name


def _label(text: str) -> str:
    # Relation labels run to end of line and may not contain ':' or ';'.
    return text.replace(":", " ").replace(";", " ")


def _relation(rel: Relation, ident) -> str:
    src, tgt = ident[rel.source], ident[rel.target]
    one = '"0..1"' if rel.nullable else '"1"'
    if rel.kind == "fk":
        return '%s %s --> "*" %s : %s' % (tgt, one, src, _label(rel.label))
    if rel.kind == "o2o":
        return '%s %s --> "1" %s : %s' % (tgt, one, src, _label(rel.label))
    if rel.kind == "m2m":
        label = rel.label + (" via " + rel.through if rel.through else "")
        return '%s "*" -- "*" %s : %s' % (src, tgt, _label(label))
    if rel.kind == "inherit":
        return "%s <|-- %s" % (tgt, src)
    if rel.kind == "proxy":
        return "%s <|.. %s : proxy" % (tgt, src)
    if rel.kind == "generic":
        return '%s "0..1" ..> "*" %s : %s' % (tgt, src, _label(rel.label))
    raise ValueError("unknown relation kind %r" % rel.kind)
