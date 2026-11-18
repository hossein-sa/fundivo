from importlib import import_module

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        # Register drf-spectacular's custom JWT authentication schema.
        import_module("apps.accounts.schema")
