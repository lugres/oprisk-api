"""
Django admin customization for custom user model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


class UserAdmin(BaseUserAdmin):
    """Define the admin pages for users."""

    ordering = ["id"]
    list_display = ["email", "full_name"]


admin.site.register(User, UserAdmin)
