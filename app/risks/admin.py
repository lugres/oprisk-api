"""
Django admin and customizations for models of the risks app.
"""

from django.contrib import admin

from .models import (
    Risk,
    RiskCategory,
    RiskCategoryToBaselEventType,
    IncidentRisk,
    RiskMeasure,
    RiskControl,
)

# --- Inline Admin for M2M Linkages ---


class RiskCategoryToBaselEventTypeInline(admin.TabularInline):
    """Inline to manage Basel mappings directly on the RiskCat admin page."""

    model = RiskCategoryToBaselEventType
    extra = 1  # Number of empty forms to display


class IncidentRiskInline(admin.TabularInline):
    """Inline to link/unlink Incidents directly on the Risk admin page."""

    model = IncidentRisk
    extra = 0
    raw_id_fields = ("incident",)  # Use a lookup widget for better perform


class RiskMeasureInline(admin.TabularInline):
    """Inline to link/unlink Measures directly on the Risk admin page."""

    model = RiskMeasure
    extra = 0
    raw_id_fields = ("measure",)  # Use a lookup widget


class RiskControlInline(admin.TabularInline):
    """Inline to link/unlink Control directly on the Risk admin page."""

    model = RiskControl
    extra = 0
    raw_id_fields = ("control",)  # Use a lookup widget


# --- Main Model Admins ---


@admin.register(RiskCategory)
class RiskCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    inlines = [RiskCategoryToBaselEventTypeInline]  # Show the M2M mapping


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    # Fieldsets group related fields for a cleaner form layout
    fieldsets = (
        (
            "Identification",
            {
                "fields": ("title", "description", "status", "notes"),
            },
        ),
        (
            "Context & Classification",
            {
                "fields": (
                    "risk_category",
                    "basel_event_type",
                    "business_unit",
                    "business_process",
                    "product",
                ),
                "description": (
                    "Basel Event Type must be compatible with Risk Category."
                ),
            },
        ),
        (
            "Assessment Scores",
            {
                "fields": (
                    ("inherent_likelihood", "inherent_impact"),
                    ("residual_likelihood", "residual_impact"),
                ),
            },
        ),
        (
            "Ownership & Review",
            {
                "fields": ("owner", "next_review_date", "retirement_reason"),
            },
        ),
        (
            "Audit & Workflow",
            {
                "fields": (
                    "created_by",
                    "submitted_by",
                    "submitted_for_review_at",
                    "validated_by",
                    "validated_at",
                ),
                "classes": ("collapse",),  # Hide audit fields by default
            },
        ),
    )

    list_display = (
        "title",
        "status",
        "owner",
        "risk_category",
        "inherent_risk_score",
        "residual_risk_score",
    )
    list_filter = ("status", "risk_category", "business_unit")
    search_fields = ("title", "description")
    readonly_fields = (
        "created_by",
        "submitted_by",
        "submitted_for_review_at",
        "validated_by",
        "validated_at",
    )
    autocomplete_fields = (
        "owner",
        "created_by",
        "submitted_by",
        "validated_by",
        "risk_category",
        "basel_event_type",
    )

    inlines = [
        IncidentRiskInline,
        RiskMeasureInline,
        RiskControlInline,
    ]  # Manage relationships here


# Register the through models to access them directly (optional)
admin.site.register(IncidentRisk)
admin.site.register(RiskMeasure)
admin.site.register(RiskControl)
