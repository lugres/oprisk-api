"""
Django admin customization for reference/central taxonomy tables.
"""

from django.contrib import admin

from references import models

admin.site.register(models.Role)
admin.site.register(models.BusinessUnit)
