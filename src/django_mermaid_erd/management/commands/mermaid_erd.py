import sys

from django.core.management.base import BaseCommand, CommandError

from django_mermaid_erd.conf import resolve_options
from django_mermaid_erd.exceptions import MermaidErdError
from django_mermaid_erd.runner import add_arguments, ensure_utf8_stdout, run


class _Plain:
    """Adapt Django's OutputWrapper to a file-like ``write`` without styling or added newlines."""

    def __init__(self, wrapper):
        self.wrapper = wrapper

    def write(self, text):
        self.wrapper.write(text, style_func=lambda s: s, ending="")


class Command(BaseCommand):
    help = "Render your models as a Mermaid ER (or class) diagram."
    requires_system_checks = []

    def add_arguments(self, parser):
        add_arguments(parser)

    def handle(self, *args, **options):
        if getattr(self.stdout, "_out", None) is sys.stdout:
            ensure_utf8_stdout(sys.stdout)
        try:
            opts = resolve_options(options)
            run(opts, _Plain(self.stdout), _Plain(self.stderr))
        except MermaidErdError as exc:
            raise CommandError(str(exc)) from None
