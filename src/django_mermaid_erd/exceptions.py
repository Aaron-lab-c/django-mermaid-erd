class MermaidErdError(Exception):
    """A user-facing error: reported as a single line, never as a traceback."""


class CheckFailed(MermaidErdError):
    """``--check`` found an out-of-date target."""
