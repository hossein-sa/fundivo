"""Read-only internal administration; business updates must use services."""

from django.contrib import admin

from .models import AuditLog, Fund, FundMembership


class ReadOnlyFundAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Fund)
class FundAdmin(ReadOnlyFundAdmin):
    list_display = ("name", "status", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("status",)


@admin.register(FundMembership)
class FundMembershipAdmin(ReadOnlyFundAdmin):
    list_display = ("fund", "user", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active")


@admin.register(AuditLog)
class AuditLogAdmin(ReadOnlyFundAdmin):
    list_display = ("action", "fund", "actor", "created_at")
    list_filter = ("action",)
