"""Read-only support tooling. Never expose bearer codes or fingerprints."""

from django.contrib import admin

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "fund", "status", "created_at", "expires_at")
    list_filter = ("status",)
    readonly_fields = (
        "id", "fund", "created_by", "status", "created_at",
        "expires_at", "responded_at", "responded_by",
    )
    # No target_fingerprint or token_digest in admin forms.
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
