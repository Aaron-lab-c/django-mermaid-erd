import pytest

from django_mermaid_erd.exceptions import MermaidErdError
from django_mermaid_erd.output import END_MARKER, START_MARKER, diff, inject, wrap_markdown

DIAGRAM = "erDiagram\n    A\n"


def test_wrap_markdown():
    assert wrap_markdown(DIAGRAM) == "```mermaid\nerDiagram\n    A\n```\n"


def test_inject_appends_when_no_markers():
    result = inject("# Title\n\nText", DIAGRAM)
    assert result == "# Title\n\nText\n\n%s\n```mermaid\nerDiagram\n    A\n```\n%s\n" % (START_MARKER, END_MARKER)


def test_inject_into_empty_or_missing():
    assert inject(None, DIAGRAM).startswith(START_MARKER)
    assert inject("", DIAGRAM).startswith(START_MARKER)


def test_inject_replaces_between_markers_and_is_idempotent():
    doc = "before\n%s\nold stuff\n%s\nafter\n" % (START_MARKER, END_MARKER)
    once = inject(doc, DIAGRAM)
    assert "old stuff" not in once
    assert once.startswith("before\n") and once.endswith("\nafter\n")
    assert inject(once, DIAGRAM) == once
    appended = inject("x\n", DIAGRAM)
    assert inject(appended, DIAGRAM) == appended


def test_inject_keeps_crlf():
    doc = "a\r\n%s\r\n%s\r\nb\r\n" % (START_MARKER, END_MARKER)
    result = inject(doc, DIAGRAM)
    assert "\r\n" in result and "\n" not in result.replace("\r\n", "")
    assert inject(result, DIAGRAM) == result


def test_inject_rejects_broken_markers():
    with pytest.raises(MermaidErdError, match="markers"):
        inject("x\n%s\n" % START_MARKER, DIAGRAM)
    with pytest.raises(MermaidErdError):
        inject("%s\n%s\n" % (END_MARKER, START_MARKER), DIAGRAM)


def test_diff_ignores_newline_style():
    assert diff("a\r\nb\r\n", "a\nb\n", "f") == []
    lines = diff("a\n", "b\n", "f")
    assert lines[0] == "--- f (current)\n" and "-a\n" in lines and "+b\n" in lines
    assert diff(None, "x\n", "f")
