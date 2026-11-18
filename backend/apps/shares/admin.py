"""Read-only administrative view; allocations must go through service layer."""

from django.contrib import admin

from .models import Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("id", "fund", "membership", "number", "created_at")
    list_filter = ("fund",)
    readonly_fields = ("id", "fund", "membership", "number", "allocation_id", "created_at")
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
