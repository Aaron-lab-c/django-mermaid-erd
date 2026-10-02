from ..schema import Schema
from .class_ import render_class
from .er import render_er

DIAGRAMS = ("er", "class")


def render(schema: Schema, diagram: str = "er", **options) -> str:
    """Render ``schema`` as Mermaid text.

    ``diagram`` is ``"er"`` (erDiagram) or ``"class"`` (classDiagram). Options:
    ``fields``, ``types``, ``field_names``, ``sort_fields``, ``max_fields``,
    ``comments``, ``verbose_names``, ``direction``, ``banner`` and, for class
    diagrams, ``group_by_app``.
    """
    if diagram == "er":
        options.pop("group_by_app", None)
        return render_er(schema, **options)
    if diagram == "class":
        if options.get("group_by_app") is None:
            options.pop("group_by_app", None)
        return render_class(schema, **options)
    raise ValueError("diagram must be one of %s, not %r" % (", ".join(DIAGRAMS), diagram))


__all__ = ["render", "render_er", "render_class", "DIAGRAMS"]
