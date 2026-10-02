SECRET_KEY = "test"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "tests.apps.shop",
    "tests.apps.blog",
    "tests.apps.inventory",
    "django_mermaid_erd",
]
# The dummy backend raises on any query: the whole suite proves we never touch the DB.
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
