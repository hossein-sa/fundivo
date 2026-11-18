
"""
URL configuration for Fundivo.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/funds/", include("apps.funds.urls")),
    path("api/v1/invitations/", include("apps.invitations.urls")),
    path("admin/", admin.site.urls),
]

# API documentation is publicly accessible only
# in the local development environment.
if getattr(settings, "API_DOCS_ENABLED", False):
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns += [
        path(
            "api/v1/schema/",
            SpectacularAPIView.as_view(),
            name="schema",
        ),
        path(
            "api/v1/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/v1/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
