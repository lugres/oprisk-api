"""
Data models for the measures app.
"""

from django.db import models
from django.conf import settings

from core.models import TimestampedModel, OwnedModel


class MeasureStatusRef(models.Model):
    """
    Status taxonomy for measures to ensure workflow:
    OPEN, IN_PROGRESS, etc.
    """

    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Measure(TimestampedModel, OwnedModel):
    """
    Measures track planned actions (corrective or preventive).
    Include a description of what should be done to prevent risk from
    materializing or risk incident from happening again, who should do what,
    and a deadline; can be focused on eliminating consequences of a risk event
    or on eliminating root causes (improving internal controls).
    """

    description = models.TextField(blank=False)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="responsible_measures",
    )
    deadline = models.DateField(blank=True, null=True)
    status = models.ForeignKey(
        MeasureStatusRef,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    closed_at = models.DateTimeField(blank=True, null=True)
    closure_comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.description[:50]

    def save(self, *args, **kwargs):
        """
        Overrides save to set the default 'OPEN' status.
        """
        # Set default status only on creation (when self.pk is None)
        # and if a status hasn't been provided.
        if not self.pk and not self.status_id:
            try:
                self.status = MeasureStatusRef.objects.get(code="OPEN")
            except MeasureStatusRef.DoesNotExist:
                # This handles the edge case where the data migration
                # hasn't run, but we don't want the app to crash.
                # A warning could be logged here.
                pass

        super().save(*args, **kwargs)
