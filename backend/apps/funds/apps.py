"""Fund domain application."""

from django.apps import AppConfig


class FundsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.funds"
    label = "funds"
    verbose_name = "Funds"
