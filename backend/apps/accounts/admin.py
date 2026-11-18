"""Read-only account inspection; identity changes require audited workflows."""

from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "is_phone_verified",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("is_phone_verified", "is_active", "is_staff")
    search_fields = ("phone_number",)
    ordering = ("-date_joined",)
    fields = (
        "id",
        "phone_number",
        "is_phone_verified",
        "is_active",
        "is_staff",
        "last_login",
        "date_joined",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
