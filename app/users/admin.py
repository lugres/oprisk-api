"""
Django admin customization for custom user model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from users.models import User


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""

    ordering = ["id"]
    list_display = ["email", "full_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (
            _("Organizational structure"),
            {
                "fields": (
                    "business_unit",
                    "role",
                    "manager",
                )
            },
        ),
        (
            _("External data"),
            {
                "fields": (
                    "external_id",
                    "external_source",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login",)}),
    )
    readonly_fields = ["last_login", "external_id", "external_source"]


admin.site.register(User, UserAdmin)
