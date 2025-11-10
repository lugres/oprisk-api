"""
Django admin and customizations for models of core incidents app.
"""

from django.contrib import admin

from incidents import models

admin.site.register(models.SimplifiedEventTypeRef)
admin.site.register(models.SimplifiedToBaselEventMap)
admin.site.register(models.LossCause)
admin.site.register(models.IncidentStatusRef)
admin.site.register(models.Incident)
admin.site.register(models.IncidentCause)
admin.site.register(models.IncidentRoutingRule)
admin.site.register(models.IncidentRequiredField)
admin.site.register(models.SlaConfig)
admin.site.register(models.AllowedTransition)


@admin.register(models.IncidentEditableField)
class IncidentEditableFieldAdmin(admin.ModelAdmin):
    list_display = ("status", "role", "field_name")
    list_filter = ("status", "role")
    search_fields = ("field_name",)
