import base64
import io
import json
import sys
import urllib.error
import zlib

import pytest

from django_mermaid_erd import image
from django_mermaid_erd.image import ImageError, ink_url, render_image

FAKE_MMDC = """
import sys
args = sys.argv[1:]
src, out = args[args.index("-i") + 1], args[args.index("-o") + 1]
text = open(src, encoding="utf-8").read()
if "BROKEN" in text:
    sys.stderr.write("Error: Parse error on line 2\\n")
    sys.exit(1)
with open(out, "w", encoding="utf-8") as fh:
    fh.write("<svg>" + str("-p" in args) + "</svg>")
"""


@pytest.fixture
def fake_mmdc(tmp_path, monkeypatch):
    script = tmp_path / "fake_mmdc.py"
    script.write_text(FAKE_MMDC, encoding="utf-8")
    monkeypatch.setattr(image, "mmdc_command", lambda: [sys.executable, str(script)])
    return script


@pytest.fixture
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("tests must not hit the network")

    monkeypatch.setattr(image.urllib.request, "urlopen", fail)


def test_mmdc_success(fake_mmdc, tmp_path, monkeypatch):
    monkeypatch.delenv(image.PUPPETEER_CONFIG_ENV, raising=False)
    out = tmp_path / "sub" / "erd.svg"
    assert render_image("erDiagram\n    A\n", str(out), "svg", "mmdc") == "mmdc"
    assert out.read_text() == "<svg>False</svg>"
    monkeypatch.setenv(image.PUPPETEER_CONFIG_ENV, "cfg.json")
    render_image("erDiagram\n    A\n", str(out), "svg", "mmdc")
    assert out.read_text() == "<svg>True</svg>"


def test_mmdc_failure_is_reported(fake_mmdc, tmp_path):
    with pytest.raises(ImageError, match="mmdc failed .*Parse error"):
        render_image("BROKEN", str(tmp_path / "x.svg"), "svg", "mmdc")


def test_mmdc_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(image, "mmdc_command", lambda: None)
    with pytest.raises(ImageError, match="npm install -g @mermaid-js/mermaid-cli"):
        render_image("x", str(tmp_path / "x.svg"), "svg", "mmdc")


def test_auto_prefers_mmdc(fake_mmdc, no_network, tmp_path):
    assert render_image("erDiagram\n", str(tmp_path / "a.svg"), "svg", "auto") == "mmdc"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_ink_url_roundtrip():
    url = ink_url("erDiagram\n    A\n", "svg")
    assert url.startswith("https://mermaid.ink/svg/pako:")
    payload = url.split("pako:", 1)[1]
    payload += "=" * (-len(payload) % 4)
    state = json.loads(zlib.decompress(base64.urlsafe_b64decode(payload)))
    assert state["code"] == "erDiagram\n    A\n"
    assert ink_url("x", "png").startswith("https://mermaid.ink/img/pako:")
    assert ink_url("x", "png").endswith("?type=png")


def test_ink_success_and_warning(monkeypatch, tmp_path):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"], seen["timeout"] = request.full_url, timeout
        return FakeResponse(b"PNGDATA")

    monkeypatch.setattr(image, "mmdc_command", lambda: None)
    monkeypatch.setattr(image.urllib.request, "urlopen", fake_urlopen)
    warnings = []
    out = tmp_path / "erd.png"
    assert render_image("erDiagram\n", str(out), "png", "auto", warn=warnings.append) == "ink"
    assert out.read_bytes() == b"PNGDATA"
    assert seen["timeout"] == 30 and "/img/" in seen["url"]
    assert warnings and "third-party" in warnings[0]


def http_error(code):
    return urllib.error.HTTPError("https://mermaid.ink/x", code, "error", {}, io.BytesIO(b""))


@pytest.mark.parametrize(
    "error, message",
    [
        (lambda: urllib.error.URLError("no network"), "could not reach mermaid.ink: no network"),
        (lambda: http_error(414), "HTTP 414 .*too large"),
        (lambda: http_error(503), "HTTP 503"),
    ],
)
def test_ink_errors(monkeypatch, tmp_path, error, message):
    def fake_urlopen(request, timeout):
        raise error()

    monkeypatch.setattr(image.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ImageError, match=message):
        render_image("x", str(tmp_path / "x.svg"), "svg", "ink")


def test_command_svg_option(fake_mmdc, no_network, tmp_path):
    from django.core.management import call_command

    out, err = io.StringIO(), io.StringIO()
    call_command("mermaid_erd", "blog", "--svg", str(tmp_path / "erd.svg"), stdout=out, stderr=err)
    assert (tmp_path / "erd.svg").exists()
    assert out.getvalue() == "" and "via mmdc" in err.getvalue()


def test_command_image_error_is_command_error(monkeypatch, tmp_path):
    from django.core.management import CommandError, call_command

    monkeypatch.setattr(image, "mmdc_command", lambda: None)
    with pytest.raises(CommandError, match="mmdc not found"):
        call_command("mermaid_erd", "blog", "--png", str(tmp_path / "x.png"), "--renderer", "mmdc")
