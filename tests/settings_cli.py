# Same project, but django_mermaid_erd is NOT in INSTALLED_APPS.
from tests.settings import *  # noqa: F401,F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django_mermaid_erd"]  # noqa: F405
