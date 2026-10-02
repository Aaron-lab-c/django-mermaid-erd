"""Writing files, Markdown fences, marker-block injection and ``--check`` diffs."""

import difflib
import os
from typing import List, Optional

from .exceptions import MermaidErdError

START_MARKER = "<!-- mermaid-erd:start -->"
END_MARKER = "<!-- mermaid-erd:end -->"


def wrap_markdown(text: str) -> str:
    return "```mermaid\n" + text + "```\n"


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text(path: str) -> Optional[str]:
    """Return the file's text with newlines left untouched, or ``None`` if missing."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        raise MermaidErdError("%s is not valid UTF-8" % path) from None
    except OSError as exc:
        raise MermaidErdError("cannot read %s: %s" % (path, exc.strerror or exc)) from None


def write_text(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    except OSError as exc:
        raise MermaidErdError("cannot write %s: %s" % (path, exc.strerror or exc)) from None


def inject(existing: Optional[str], diagram: str) -> str:
    """Put ``diagram`` (fenced) between the markers in ``existing``.

    Without markers the block is appended at the end of the document. The
    result is idempotent and keeps the document's CRLF/LF convention.
    """
    existing = existing or ""
    crlf = "\r\n" in existing
    doc = normalize_newlines(existing)
    block = START_MARKER + "\n" + wrap_markdown(diagram) + END_MARKER

    start = doc.find(START_MARKER)
    end = doc.find(END_MARKER)
    if start == -1 and end == -1:
        if doc and not doc.endswith("\n"):
            doc += "\n"
        if doc:
            doc += "\n"
        result = doc + block + "\n"
    elif start == -1 or end == -1 or end < start:
        raise MermaidErdError(
            "found only one of %s / %s (or they are out of order); fix the markers first"
            % (START_MARKER, END_MARKER)
        )
    else:
        result = doc[:start] + block + doc[end + len(END_MARKER):]
    return result.replace("\n", "\r\n") if crlf else result


def diff(current: Optional[str], expected: str, path: str) -> List[str]:
    """Unified diff (newline-insensitive) from ``current`` to ``expected``; empty if equal."""
    old = normalize_newlines(current or "").splitlines(keepends=True)
    new = normalize_newlines(expected).splitlines(keepends=True)
    lines = list(
        difflib.unified_diff(old, new, fromfile="%s (current)" % path, tofile="%s (expected)" % path)
    )
    return [line if line.endswith("\n") else line + "\n" for line in lines]
