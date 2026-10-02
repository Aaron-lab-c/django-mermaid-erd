"""Golden files: ``pytest --update-snapshots`` rewrites tests/snapshots/*.mmd."""

import io

import pytest
from django.core.management import call_command

from .helpers import SNAPSHOTS


def command_output(targets, options):
    out = io.StringIO()
    call_command("mermaid_erd", *targets, stdout=out, **options)
    return out.getvalue()


@pytest.mark.parametrize("name", sorted(SNAPSHOTS))
def test_snapshot(name, snapshot):
    targets, options = SNAPSHOTS[name]
    snapshot(name, command_output(targets, options))


def test_repeated_runs_are_identical():
    first = command_output((), {})
    for _ in range(10):
        assert command_output((), {}) == first
