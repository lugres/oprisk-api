"""
Data models for the risks app.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel, OwnedModel

from incidents.models import Incident  # Required for M2M link
from measures.models import Measure  # Required for M2M link

# from controls.models import Control # Required for M2M link
from references.models import (
    BaselEventType,
    BusinessUnit,
    BusinessProcess,
    Product,
)

# --- 1. RISK STATUS CHOICES (Workflow) ---


class RiskStatus(models.TextChoices):
    """Defines the workflow statuses for a Risk entity."""

    DRAFT = "DRAFT", _("Draft")
    ASSESSED = "ASSESSED", _("Assessed (Pending Validation)")
    ACTIVE = "ACTIVE", _("Active")
    RETIRED = "RETIRED", _("Retired")


# --- 2. REFERENCE MODELS ---


class RiskCategory(models.Model):
    """
    Internal business risk classification.
    (internal risk taxonomy simplified for business use case)"""

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    # M2M Field using the through table for Basel mapping
    # One category can map to multiple Basel types
    basel_event_types = models.ManyToManyField(
        BaselEventType,
        through="RiskCategoryToBaselEventType",
        related_name="mapped_risk_categories",
        help_text="Which Basel event types are valid for this category",
    )

    class Meta:
        verbose_name_plural = "Risk Categories"

    def __str__(self):
        return self.name


class RiskCategoryToBaselEventType(models.Model):
    """M2M link between RiskCategory and BaselEventTypes."""

    risk_category = models.ForeignKey(RiskCategory, on_delete=models.CASCADE)
    basel_event_type = models.ForeignKey(
        BaselEventType, on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("risk_category", "basel_event_type")
        verbose_name = "Risk Category to Basel Event Type Mapping"


# --- 3. CORE RISK MODEL ---


class Risk(TimestampedModel, OwnedModel):
    """
    The core Risk entity - a potential loss resulting from ...
    inadequate or failed internal processes, people,
    and systems, or from external events.
    Implementing a typical RCSA lifecycle.
    """

    # Essential Identification
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Dual risk taxonomy: Internal + Basel (both required for ACTIVE state)

    # Context - internal risk category
    risk_category = models.ForeignKey(
        RiskCategory,
        on_delete=models.PROTECT,
        # blank=True,
        # null=True,
        help_text="Internal risk category.",
    )

    # External Basel classification (finalized by Risk Officer)
    basel_event_type = models.ForeignKey(
        BaselEventType,
        on_delete=models.PROTECT,
        blank=True,
        null=True,  # Can be null in DRAFT/ASSESSED
        help_text="The specific Basel category for external reporting.",
    )

    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.PROTECT, blank=True, null=True
    )
    business_process = models.ForeignKey(
        BusinessProcess, on_delete=models.PROTECT, blank=True, null=True
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, blank=True, null=True
    )

    # RCSA Assessment Scores (1-5)
    score_validators = [MinValueValidator(1), MaxValueValidator(5)]

    inherent_likelihood = models.SmallIntegerField(
        validators=score_validators, blank=True, null=True
    )
    inherent_impact = models.SmallIntegerField(
        validators=score_validators, blank=True, null=True
    )
    residual_likelihood = models.SmallIntegerField(
        validators=score_validators, blank=True, null=True
    )
    residual_impact = models.SmallIntegerField(
        validators=score_validators, blank=True, null=True
    )

    # Workflow Status
    status = models.CharField(
        max_length=20,
        choices=RiskStatus.choices,
        default=RiskStatus.DRAFT,
    )

    # Ownership and Review
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="owned_risks",
        help_text=(
            "User responsible for managing this risk's"
            " mitigation and review."
        ),
    )
    next_review_date = models.DateField(null=True, blank=True)

    # Workflow/Audit Tracking
    submitted_for_review_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_risks",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="validated_risks",
    )
    retirement_reason = models.TextField(blank=True, null=True)

    # Unified log for reasons and comments (timestamped, user-attributed)
    notes = models.TextField(
        blank=True,
        default="",
        help_text=(
            "General notes, comments, or justification for status changes."
        ),
    )

    # --- Relationships: M2M Fields using 'through' for cleaner access ---
    incidents = models.ManyToManyField(Incident, through="IncidentRisk")
    measures = models.ManyToManyField(
        Measure,
        through="RiskMeasure",
        related_name="risks",
        blank=True,
    )
    # controls = models.ManyToManyField(Control, through="RiskControl")

    # --- Computed Properties (Domain Logic) ---
    @property
    def inherent_risk_score(self) -> int | None:
        """Returns inherent risk score if risk was assessed."""
        if self.inherent_likelihood and self.inherent_impact:
            return self.inherent_likelihood * self.inherent_impact
        return None

    @property
    def residual_risk_score(self) -> int | None:
        """Returns residual risk score if risk was assessed."""
        if self.residual_likelihood and self.residual_impact:
            return self.residual_likelihood * self.residual_impact
        return None

    def __str__(self):
        return f"Risk #{self.id}: {self.title}"


# --- 4. MANY-TO-MANY LINKAGE MODELS (Explicit Through Tables) ---


# !!- decided to keep link model here instead of moving to Incident model
# M2M field 'risks' will be added to Incident for 2-directional linkage
class IncidentRisk(models.Model):
    """Links Incidents to Risks."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("incident", "risk")
        verbose_name = "Incident to Risk Link"


class RiskMeasure(models.Model):
    """Links Risks to Preventive/Mitigating Measures."""

    risk = models.ForeignKey(Risk, on_delete=models.CASCADE)
    measure = models.ForeignKey(Measure, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("risk", "measure")
        verbose_name = "Risk to Measure Link"


# !!- Controls to be added later, maybe to Control model if in separate app
# class RiskControl(models.Model):
#     """Links Risks to Controls."""

#     risk = models.ForeignKey(Risk, on_delete=models.CASCADE)
#     control = models.ForeignKey(Control, on_delete=models.CASCADE)

#     class Meta:
#         unique_together = ("risk", "control")
#         verbose_name = "Risk to Control Link"
