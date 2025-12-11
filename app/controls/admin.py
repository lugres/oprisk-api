"""
Django admin and customizations for models of the controls app.
"""

from django.contrib import admin
from .models import Control


@admin.register(Control)
class ControlAdmin(admin.ModelAdmin):
    """Admin interface for the Control Library."""

    # Organize fields into logical groups
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "title",
                    "description",
                    "reference_doc",
                    "is_active",
                ),
            },
        ),
        (
            "Design Characteristics",
            {
                "fields": (
                    ("control_type", "control_nature"),
                    ("control_frequency", "effectiveness"),
                ),
                "description": (
                    "Define the inherent design of the control mechanism."
                ),
            },
        ),
        (
            "Context & Ownership",
            {
                "fields": ("business_unit", "business_process", "owner"),
            },
        ),
        (
            "Audit",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # Columns displayed in the list view
    list_display = (
        "title",
        "control_type",
        "control_frequency",
        "effectiveness",
        "business_unit",
        "owner",
        "is_active",
    )

    # Sidebar filters for finding controls quickly
    list_filter = (
        "is_active",
        "control_type",
        "control_nature",
        "control_frequency",
        "effectiveness",
        "business_unit",
    )

    # Search bar config
    search_fields = ("title", "description", "reference_doc")

    # Read-only audit fields
    readonly_fields = ("created_by", "created_at", "updated_at")

    # Optimize FK lookups
    # (Prerequisite: Related admins must have search_fields defined)
    autocomplete_fields = ("business_unit", "business_process", "owner")

    def save_model(self, request, obj, form, change):
        """Automatically set created_by on creation."""
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
