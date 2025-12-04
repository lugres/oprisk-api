"""
Django admin customization for reference/central taxonomy tables.
"""

from django.contrib import admin

from references import models

admin.site.register(models.Role)
# admin.site.register(models.BusinessUnit)
admin.site.register(models.BaselBusinessLine)
# admin.site.register(models.BaselEventType)
# admin.site.register(models.BusinessProcess)
admin.site.register(models.Product)


@admin.register(models.BaselEventType)
class BaselEventTypeAdmin(admin.ModelAdmin):
    # This line is REQUIRED to support autocomplete_fields in RiskAdmin
    search_fields = ("name",)
    list_display = ("name",)


@admin.register(models.BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    # This line is REQUIRED to support autocomplete_fields in ControlAdmin
    search_fields = ("name",)
    list_display = ("name",)


@admin.register(models.BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    # This line is REQUIRED to support autocomplete_fields in ControlAdmin
    search_fields = ("name",)
    list_display = ("name",)
