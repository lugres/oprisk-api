"""
Tests for the Django admin interface of the measures app.
"""

from django.contrib import admin
from measures.models import Measure, MeasureStatusRef, MeasureEditableField


@admin.register(Measure)
class MeasureAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "status",
        "responsible",
        "deadline",
        "created_by",
    )
    list_filter = ("status", "deadline", "responsible")
    search_fields = ("description", "responsible__email")


@admin.register(MeasureStatusRef)
class MeasureStatusRefAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(MeasureEditableField)
class MeasureEditableFieldAdmin(admin.ModelAdmin):
    list_display = ("status", "role", "field_name")
    list_filter = ("status", "role")
    search_fields = ("field_name",)
