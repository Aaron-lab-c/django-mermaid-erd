import io
import os

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from django_mermaid_erd.output import END_MARKER, START_MARKER


def run(*args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    call_command("mermaid_erd", *args, stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


def test_stdout_default():
    out, err = run()
    assert out.startswith("erDiagram\n") and "Customer ||--o{ Order" in out
    assert err == ""


def test_targets_and_options():
    out, _ = run("shop.Order", "shop.Customer", "--fields", "keys", "--no-banner")
    assert out.splitlines()[1] == "    %% app: shop"
    assert "Customer ||--o{ Order" in out and "Coupon {" not in out
    out, _ = run("-d", "class", "blog")
    assert out.startswith("classDiagram\n") and "namespace blog {" in out


def test_md_flag():
    out, _ = run("blog", "--md")
    assert out.startswith("```mermaid\nerDiagram\n") and out.endswith("```\n")


def test_output_file_and_md_autodetect(tmp_path):
    mmd, md = tmp_path / "erd.mmd", tmp_path / "docs" / "erd.md"
    out, err = run("blog", "-o", str(mmd))
    assert out == "" and "Wrote" in err
    assert mmd.read_bytes().startswith(b"erDiagram\n")
    assert b"\r\n" not in mmd.read_bytes()
    run("blog", "-o", str(md))
    assert md.read_text(encoding="utf-8").startswith("```mermaid\n")
    _, err = run("blog", "-o", str(md))
    assert "Unchanged" in err


def test_inject(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\n%s\nold\n%s\n\nFooter\n" % (START_MARKER, END_MARKER), encoding="utf-8")
    run("blog", "--inject", str(readme))
    first = readme.read_text(encoding="utf-8")
    assert "old" not in first and "```mermaid\nerDiagram" in first and first.endswith("\nFooter\n")
    run("blog", "--inject", str(readme))
    assert readme.read_text(encoding="utf-8") == first  # idempotent


def test_inject_without_markers_appends(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n", encoding="utf-8")
    run("blog", "--inject", str(readme))
    text = readme.read_text(encoding="utf-8")
    assert text.startswith("# Project\n\n" + START_MARKER) and text.rstrip().endswith(END_MARKER)


def test_check_up_to_date(tmp_path):
    target = tmp_path / "erd.md"
    run("blog", "-o", str(target))
    out, err = run("blog", "-o", str(target), "--check")
    assert out == "" and "up to date" in err


def test_check_tolerates_crlf_checkout(tmp_path):
    target = tmp_path / "erd.md"
    run("blog", "-o", str(target))
    target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    run("blog", "-o", str(target), "--check")


def test_check_out_of_date_prints_diff_and_fails(tmp_path):
    target = tmp_path / "erd.md"
    run("blog", "-o", str(target))
    before = target.read_text(encoding="utf-8")
    out = io.StringIO()
    with pytest.raises(CommandError, match="out of date") as exc:
        call_command("mermaid_erd", "blog", "shop", "-o", str(target), "--check", stdout=out, stderr=io.StringIO())
    assert exc.value.returncode == 1
    assert "--- %s (current)" % target in out.getvalue() and "+    %% app: shop" in out.getvalue()
    assert target.read_text(encoding="utf-8") == before  # --check never writes


def test_check_missing_file(tmp_path):
    with pytest.raises(CommandError, match="missing"):
        run("blog", "-o", str(tmp_path / "nope.md"), "--check")
    assert not (tmp_path / "nope.md").exists()


def test_check_inject(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# P\n", encoding="utf-8")
    with pytest.raises(CommandError):
        run("blog", "--inject", str(readme), "--check")
    run("blog", "--inject", str(readme))
    run("blog", "--inject", str(readme), "--check")


@pytest.mark.parametrize(
    "args, message",
    [
        (("nope",), "Unknown app label 'nope'"),
        (("shop.Nope",), "has no model named 'Nope'"),
        (("--focus", "Nope"), "No model named 'Nope'"),
        (("--focus", "Tag"), "ambiguous"),
        (("--focus", "auth.User"), "not among the selected models"),
        (("--check",), "--check needs a target"),
        (("--exclude", "*"), "no models selected"),
    ],
)
def test_friendly_errors(args, message):
    with pytest.raises(CommandError, match=message):
        run(*args)


def test_focus():
    out, _ = run("--focus", "shop.Order", "--depth", "0")
    assert "    Order {" in out and "Customer {" not in out and "-> shop.Customer" in out


def test_settings_defaults_and_cli_precedence():
    with override_settings(MERMAID_ERD={"DIAGRAM": "class", "BANNER": False, "EXCLUDE": ["shop"]}):
        out, _ = run()
        assert out.startswith("classDiagram\n    namespace blog")
        assert "namespace shop" not in out
        out, _ = run("-d", "er", "--exclude", "inventory")
        assert out.startswith("erDiagram\n    %% app: blog")
        assert "inventory" not in out and "%% app: shop" not in out  # excludes add up


@pytest.mark.parametrize(
    "value, message",
    [
        ({"DIAGRAM": "uml"}, "invalid diagram"),
        ({"NOPE": 1}, "unknown key 'NOPE'"),
        ({"BANNER": "yes"}, "must be True or False"),
        ({"MAX_FIELDS": -1}, "non-negative"),
        ({"EXCLUDE": "shop"}, "list of strings"),
        ("er", "must be a dict"),
    ],
)
def test_bad_settings(value, message):
    with override_settings(MERMAID_ERD=value):
        with pytest.raises(CommandError, match=message):
            run()


def test_generate_api():
    from django_mermaid_erd import generate

    assert generate("blog", diagram="class", banner=False).startswith("classDiagram\n    namespace blog")
    assert generate() == run()[0]


def test_never_queries_the_database():
    # tests.settings uses the dummy backend, which raises on any query; this
    # double-checks against a real sqlite connection with CaptureQueriesContext.
    import subprocess
    import sys

    code = (
        "import django, io\n"
        "django.setup()\n"
        "from django.db import connection\n"
        "from django.test.utils import CaptureQueriesContext\n"
        "from django.core.management import call_command\n"
        "with CaptureQueriesContext(connection) as ctx:\n"
        "    call_command('mermaid_erd', '--include-builtin', '--generic-edges', stdout=io.StringIO())\n"
        "    call_command('mermaid_erd', '-d', 'class', stdout=io.StringIO())\n"
        "print(len(ctx.captured_queries))\n"
    )
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="tests.settings_sqlite")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["0"]


def test_readme_example_is_up_to_date():
    readme = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")
    run("shop", "--no-banner", "--inject", readme, "--check")
