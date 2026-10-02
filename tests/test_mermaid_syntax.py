"""Validate output with the real Mermaid parser via mermaid-cli (``mmdc``).

Skipped when ``mmdc`` isn't installed, unless ``REQUIRE_MMDC=1`` (set in CI),
in which case a missing ``mmdc`` is a failure. In sandboxed CI, point
``MERMAID_ERD_PUPPETEER_CONFIG`` at a file containing ``{"args": ["--no-sandbox"]}``.
"""

import os

import pytest

from django_mermaid_erd import image
from django_mermaid_erd.render import render

from .helpers import SNAPSHOTS, mini_schema, reserved_schema
from .test_snapshots import command_output

HAND_BUILT = {
    "mini_er": lambda: render(mini_schema(), "er", comments=True, verbose_names=True),
    "mini_er_full": lambda: render(mini_schema(), "er", types="full", direction="RL"),
    "mini_er_none": lambda: render(mini_schema(), "er", types="none", max_fields=1),
    "mini_class": lambda: render(mini_schema(), "class", comments=True),
    "mini_class_flat": lambda: render(mini_schema(), "class", group_by_app=False, types="none", direction="BT"),
    "reserved_er": lambda: render(reserved_schema(), "er"),
    "reserved_class": lambda: render(reserved_schema(), "class"),
    "reserved_class_flat": lambda: render(reserved_schema(), "class", group_by_app=False),
}


@pytest.fixture(scope="module")
def mmdc():
    if image.mmdc_command() is None:
        if os.environ.get("REQUIRE_MMDC") == "1":
            pytest.fail("REQUIRE_MMDC=1 but mmdc is not on PATH")
        pytest.skip("mmdc (@mermaid-js/mermaid-cli) not installed")


def assert_renders(text, tmp_path):
    out = tmp_path / "diagram.svg"
    image.render_with_mmdc(text, str(out), "svg")
    svg = out.read_text(encoding="utf-8")
    assert "Syntax error" not in svg


def test_validator_rejects_invalid_input(mmdc, tmp_path):
    with pytest.raises(image.ImageError, match="mmdc failed"):
        assert_renders("erDiagram\n    A ||--o{ : \"x\"\n", tmp_path)


@pytest.mark.parametrize("name", sorted(SNAPSHOTS))
def test_project_outputs_render(mmdc, tmp_path, name):
    targets, options = SNAPSHOTS[name]
    assert_renders(command_output(targets, options), tmp_path)


@pytest.mark.parametrize("name", sorted(HAND_BUILT))
def test_edge_case_outputs_render(mmdc, tmp_path, name):
    assert_renders(HAND_BUILT[name](), tmp_path)
