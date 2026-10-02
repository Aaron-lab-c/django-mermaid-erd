import os
import shutil
import subprocess
import sys

import pytest

from django_mermaid_erd import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def mermaid_erd(*args, env=None, cwd=ROOT):
    exe = shutil.which("mermaid-erd", path=os.path.dirname(sys.executable))
    command = [exe] if exe else [sys.executable, "-m", "django_mermaid_erd"]
    environ = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    environ.update(env or {})
    return subprocess.run(command + list(args), cwd=cwd, env=environ, capture_output=True)


def test_works_without_installed_app():
    result = mermaid_erd("--settings", "tests.settings_cli", "--no-banner", "shop")
    assert result.returncode == 0, result.stderr
    out = result.stdout.decode("utf-8")
    assert out.startswith("erDiagram\n    %% app: shop\n")


def test_same_output_as_management_command():
    import io

    from django.core.management import call_command

    buf = io.StringIO()
    call_command("mermaid_erd", "--comments", "--verbose-names", stdout=buf)
    result = mermaid_erd("--settings", "tests.settings_cli", "--comments", "--verbose-names")
    assert result.stdout.decode("utf-8") == buf.getvalue()


def test_piped_output_is_utf8_with_lf():
    result = mermaid_erd("--settings", "tests.settings", "shop", "--verbose-names")
    assert result.returncode == 0, result.stderr
    assert b"\r\n" not in result.stdout
    assert "名稱" in result.stdout.decode("utf-8")


def test_manage_py_style_piped_output_is_utf8_with_lf():
    code = "from django.core.management import execute_from_command_line; execute_from_command_line()"
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="tests.settings")
    result = subprocess.run(
        [sys.executable, "-c", code, "mermaid_erd", "shop", "--verbose-names"],
        cwd=ROOT,
        env=env,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert b"\r\n" not in result.stdout and "名稱" in result.stdout.decode("utf-8")


def test_settings_from_environment():
    result = mermaid_erd("blog", env={"DJANGO_SETTINGS_MODULE": "tests.settings_cli"})
    assert result.returncode == 0 and b"Post" in result.stdout


def test_pythonpath(tmp_path):
    result = mermaid_erd("--settings", "tests.settings_cli", "--pythonpath", ROOT, "blog", cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr


def test_missing_settings_is_usage_error():
    result = mermaid_erd("blog")
    assert result.returncode == 2
    assert b"no Django settings" in result.stderr


@pytest.mark.parametrize(
    "args, message",
    [
        (("--settings", "does.not.exist"), b"could not set up Django"),
        (("--settings", "tests.settings_cli", "nope"), b"Unknown app label 'nope'"),
        (("--settings", "tests.settings_cli", "--check"), b"--check needs a target"),
    ],
)
def test_errors_are_one_line(args, message):
    result = mermaid_erd(*args)
    assert result.returncode == 1
    lines = result.stderr.decode("utf-8").strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("mermaid-erd: error:"), lines
    assert message in result.stderr


def test_manage_py_errors_have_no_traceback():
    code = "from django.core.management import execute_from_command_line; execute_from_command_line()"
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="tests.settings")
    result = subprocess.run(
        [sys.executable, "-c", code, "mermaid_erd", "--focus", "Nope"], cwd=ROOT, env=env, capture_output=True
    )
    assert result.returncode == 1
    assert result.stderr.decode().strip() == "CommandError: No model named 'Nope'."


def test_check_exit_code(tmp_path):
    target = tmp_path / "erd.md"
    ok = mermaid_erd("--settings", "tests.settings_cli", "blog", "-o", str(target))
    assert ok.returncode == 0 and target.exists()
    assert mermaid_erd("--settings", "tests.settings_cli", "blog", "-o", str(target), "--check").returncode == 0
    stale = mermaid_erd("--settings", "tests.settings_cli", "shop", "-o", str(target), "--check")
    assert stale.returncode == 1 and b"+++" in stale.stdout


def test_bad_choice_exits_2():
    result = mermaid_erd("--settings", "tests.settings_cli", "--diagram", "uml")
    assert result.returncode == 2


def test_version():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
