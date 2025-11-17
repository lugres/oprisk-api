"""
Project-wide abstract base classes.
"""

from django.db import models
from django.conf import settings


class TimestampedModel(models.Model):
    """Abstract data model, provides created_at, updated_at."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OwnedModel(models.Model):
    """Abstract data model, provides created_by."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(class)s_created",
    )

    class Meta:
        abstract = True
