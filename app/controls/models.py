"""
Data models for the controls app.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel, OwnedModel
from references.models import BusinessProcess, BusinessUnit


class ControlType(models.TextChoices):
    PREVENTIVE = "PREVENTIVE", _("Preventive")
    DETECTIVE = "DETECTIVE", _("Detective")
    CORRECTIVE = "CORRECTIVE", _("Corrective")


class ControlNature(models.TextChoices):
    MANUAL = "MANUAL", _("Manual")
    AUTOMATED = "AUTOMATED", _("Automated")
    HYBRID = "HYBRID", _("IT-Dependent Manual")


class ControlFrequency(models.TextChoices):
    CONTINUOUS = "CONTINUOUS", _("Continuous")
    DAILY = "DAILY", _("Daily")
    WEEKLY = "WEEKLY", _("Weekly")
    MONTHLY = "MONTHLY", _("Monthly")
    QUARTERLY = "QUARTERLY", _("Quarterly")
    ANNUALLY = "ANNUALLY", _("Annually")
    AD_HOC = "AD_HOC", _("Ad-hoc - Event Driven")


class Control(TimestampedModel, OwnedModel):
    """
    Central Library of Controls.
    Describes the mechanism designed to mitigate risks.
    """

    # 1. Identification
    title = models.CharField(max_length=255)
    description = models.TextField()
    reference_doc = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Link to control procedure document or wiki"),
    )

    # 2. Design Characteristics
    control_type = models.CharField(
        max_length=20,
        choices=ControlType.choices,
        default=ControlType.PREVENTIVE,
    )
    control_nature = models.CharField(
        max_length=20,
        choices=ControlNature.choices,
        default=ControlNature.MANUAL,
    )
    control_frequency = models.CharField(
        max_length=20,
        choices=ControlFrequency.choices,
        help_text=_("How often this control is performed"),
    )

    # 3. Design Effectiveness (The "Inherent Strength" of the control)
    effectiveness = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Design effectiveness rating (1-5)"),
    )

    # 4. Context & Ownership
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this control is currently operational"),
    )
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        related_name="controls",
        help_text=_("The unit that owns/operates this control"),
    )
    business_process = models.ForeignKey(
        BusinessProcess,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="controls",
        help_text="Primary business process this control applies to",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_controls",
        help_text=_("User responsible for operating/maintaining this control"),
    )

    def __str__(self):
        return self.title
