"""``mermaid-erd``: the same as ``manage.py mermaid_erd`` without touching INSTALLED_APPS."""

import argparse
import os
import sys
from typing import Optional, Sequence

from . import __version__
from .exceptions import MermaidErdError


def build_parser() -> argparse.ArgumentParser:
    from .runner import add_arguments

    parser = argparse.ArgumentParser(
        prog="mermaid-erd",
        description="Render Django models as a Mermaid ER (or class) diagram.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    django_group = parser.add_argument_group("django")
    django_group.add_argument(
        "--settings", metavar="MODULE", help="settings module (default: $DJANGO_SETTINGS_MODULE)"
    )
    django_group.add_argument(
        "--pythonpath", metavar="DIR", help="directory to add to sys.path (the current directory always is)"
    )
    add_arguments(parser)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    if args.pythonpath:
        sys.path.insert(0, os.path.abspath(args.pythonpath))
    if args.settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = args.settings
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        parser.error("no Django settings: pass --settings or set DJANGO_SETTINGS_MODULE")

    def fail(message: str) -> int:
        sys.stderr.write("mermaid-erd: error: %s\n" % message)
        return 1

    try:
        import django

        django.setup()
    except Exception as exc:  # any import/config problem in the user's project
        return fail(
            "could not set up Django with settings %r: %s: %s"
            % (os.environ["DJANGO_SETTINGS_MODULE"], type(exc).__name__, exc)
        )

    from .conf import resolve_options
    from .runner import ensure_utf8_stdout, run

    ensure_utf8_stdout(sys.stdout)
    options = vars(args)
    options.pop("settings", None)
    options.pop("pythonpath", None)
    try:
        return run(resolve_options(options), sys.stdout, sys.stderr)
    except MermaidErdError as exc:
        return fail(str(exc))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
