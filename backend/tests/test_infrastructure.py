import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse


def test_database_engine_is_postgresql():
    assert (
        settings.DATABASES["default"]["ENGINE"]
        == "django.db.backends.postgresql"
    )


def test_rest_framework_is_installed():
    assert "rest_framework" in settings.INSTALLED_APPS


def test_openapi_schema_is_valid():
    client = Client()
    response = client.get(
        reverse("schema"),
        HTTP_ACCEPT="application/json",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["openapi"].startswith("3.")
    assert data["info"]["title"] == "Fundivo API"


@pytest.mark.parametrize(
    "url_name",
    ["swagger-ui", "redoc"],
)
def test_api_documentation_is_available(url_name):
    client = Client()
    response = client.get(reverse(url_name))

    assert response.status_code == 200
