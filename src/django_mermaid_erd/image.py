"""Optional SVG/PNG rendering — standard library only.

* ``mmdc``: a locally installed ``@mermaid-js/mermaid-cli``.
* ``ink``: the public https://mermaid.ink service. This sends the diagram,
  i.e. your model schema, to a third party.
* ``auto``: ``mmdc`` when it is on PATH, otherwise ``ink``.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import zlib
from typing import List, Optional

from .exceptions import MermaidErdError

INK_URL = "https://mermaid.ink"
INK_TIMEOUT = 30
PUPPETEER_CONFIG_ENV = "MERMAID_ERD_PUPPETEER_CONFIG"
INK_WARNING = (
    "warning: rendering with mermaid.ink sends the diagram (your model schema) "
    "to a third-party service (%s)." % INK_URL
)


class ImageError(MermaidErdError):
    pass


def mmdc_command() -> Optional[List[str]]:
    exe = shutil.which("mmdc")
    return [exe] if exe else None


def render_image(text: str, path: str, fmt: str, renderer: str = "auto", warn=None) -> str:
    """Render Mermaid ``text`` to ``path`` as ``fmt`` ("svg" or "png"); return the renderer used."""
    if fmt not in ("svg", "png"):
        raise ValueError("fmt must be 'svg' or 'png'")
    if renderer == "auto":
        renderer = "mmdc" if mmdc_command() else "ink"
    if renderer == "mmdc":
        render_with_mmdc(text, path, fmt)
    elif renderer == "ink":
        if warn is not None:
            warn(INK_WARNING)
        render_with_ink(text, path, fmt)
    else:
        raise ValueError("unknown renderer %r" % renderer)
    return renderer


def render_with_mmdc(text: str, path: str, fmt: str) -> None:
    command = mmdc_command()
    if not command:
        raise ImageError(
            "mmdc not found on PATH. Install it with `npm install -g @mermaid-js/mermaid-cli` "
            "or use --renderer ink."
        )
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "diagram.mmd")
        target = os.path.join(tmp, "diagram." + fmt)
        with open(source, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        args = command + ["-i", source, "-o", target, "-q"]
        config = os.environ.get(PUPPETEER_CONFIG_ENV)
        if config:
            args += ["-p", config]
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        except OSError as exc:
            raise ImageError("could not run mmdc: %s" % exc) from None
        if proc.returncode != 0 or not os.path.exists(target):
            detail = _first_error_line(proc.stderr or proc.stdout)
            raise ImageError("mmdc failed (exit %s)%s" % (proc.returncode, ": " + detail if detail else ""))
        _copy(target, path)


def ink_url(text: str, fmt: str) -> str:
    """Build a mermaid.ink URL using the compact ``pako:`` (zlib + base64url) encoding."""
    state = json.dumps({"code": text, "mermaid": {"theme": "default"}}, separators=(",", ":"))
    payload = base64.urlsafe_b64encode(zlib.compress(state.encode("utf-8"), 9)).decode("ascii")
    payload = "pako:" + payload.rstrip("=")
    if fmt == "svg":
        return "%s/svg/%s" % (INK_URL, payload)
    return "%s/img/%s?type=png" % (INK_URL, payload)


def render_with_ink(text: str, path: str, fmt: str, timeout: float = INK_TIMEOUT) -> None:
    from . import __version__

    request = urllib.request.Request(
        ink_url(text, fmt), headers={"User-Agent": "django-mermaid-erd/%s" % __version__}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        hint = " (the diagram may be too large for a URL; try --fields keys or install mmdc)" if exc.code in (
            400,
            414,
        ) else ""
        raise ImageError("mermaid.ink returned HTTP %s%s" % (exc.code, hint)) from None
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ImageError("could not reach mermaid.ink: %s" % reason) from None
    if not data:
        raise ImageError("mermaid.ink returned an empty response")
    directory = os.path.dirname(path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
    except OSError as exc:
        raise ImageError("cannot write %s: %s" % (path, exc.strerror or exc)) from None


def _copy(source: str, path: str) -> None:
    directory = os.path.dirname(path)
    try:
        if directory:
            os.makedirs(directory, exist_ok=True)
        shutil.copyfile(source, path)
    except OSError as exc:
        raise ImageError("cannot write %s: %s" % (path, exc.strerror or exc)) from None


def _first_error_line(output: str) -> str:
    lines = [line.strip() for line in (output or "").splitlines() if line.strip()]
    for line in lines:
        if "error" in line.lower():
            return line
    return lines[0] if lines else ""
