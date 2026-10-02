"""Graphviz-free Django ER diagrams as Mermaid text."""

__version__ = "0.1.0"

from .introspect import build_schema  # noqa: E402
from .render import render  # noqa: E402


def generate(*targets: str, **options) -> str:
    """Return Mermaid text for the installed models, like ``manage.py mermaid_erd``.

    ``targets`` are app labels / ``app.Model`` strings; ``options`` use the
    command's option names (``diagram="class"``, ``fields="keys"``,
    ``exclude=["shop.*Log"]``, ``focus="shop.Order"``, ...) and are merged
    with ``settings.MERMAID_ERD``. Requires ``django.setup()`` to have run.
    """
    from .conf import resolve_options
    from .runner import generate_text

    options["targets"] = targets
    return generate_text(resolve_options(options))


__all__ = ["__version__", "build_schema", "render", "generate"]
