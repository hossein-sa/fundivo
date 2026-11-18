"""Expose the verified JWT authenticator to drf-spectacular."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class VerifiedJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.auth_tokens.VerifiedJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
