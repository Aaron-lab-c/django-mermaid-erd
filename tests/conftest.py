import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
django.setup()

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")


def pytest_addoption(parser):
    parser.addoption(
        "--update-snapshots", action="store_true", default=False, help="rewrite tests/snapshots/*.mmd"
    )


@pytest.fixture
def snapshot(request):
    update = request.config.getoption("--update-snapshots")

    def check(name, text):
        path = os.path.join(SNAPSHOT_DIR, name + ".mmd")
        if update or not os.path.exists(path):
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            if not update:
                pytest.fail("snapshot %s did not exist and was created; re-run" % name)
            return
        with open(path, encoding="utf-8", newline="") as fh:
            expected = fh.read()
        assert text == expected, "output differs from snapshots/%s.mmd (run pytest --update-snapshots)" % name

    return check
