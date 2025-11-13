"""
Tests for the Django admin interface of the measures app.
"""

from django.contrib import admin
from measures.models import Measure, MeasureStatusRef


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
