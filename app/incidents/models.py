"""
Data models for the incident domain.
"""

from django.db import models
from django.conf import settings


from core.models import TimestampedModel, OwnedModel
from references.models import (
    Role,
    BusinessUnit,
    Product,
    BusinessProcess,
    BaselEventType,
    BaselBusinessLine,
)

# from risks.models import Risk # <-- Will be needed for IncidentRisk later
# from measures.models import Measure # <-- Will be needed for IncidentMeasure


# Simplified Event type is moved to "incidents" due to high cohesion
class SimplifiedEventTypeRef(models.Model):
    """Simple event types (4 + other) for early stages of incident's
    lifecycle; selected by employee/manager in UI, mapped to Basel."""

    name = models.CharField(max_length=100)
    short_desc = models.TextField()
    front_end_hint = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Simplified Event Type"
        verbose_name_plural = "Simplified Event Types"

    def __str__(self):
        return self.name


class SimplifiedToBaselEventMap(models.Model):
    """Map simplified event type to Basel event types."""

    simplified = models.ForeignKey(
        SimplifiedEventTypeRef, on_delete=models.CASCADE
    )
    basel = models.ForeignKey(BaselEventType, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Simplified to Basel Event Map"
        verbose_name_plural = "Simplified to Basel Event Maps"
        unique_together = (("simplified", "basel"),)  # avoid duplicates


class LossCause(models.Model):
    """Root causes of risk loss events."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Loss Causes"

    def __str__(self):
        return self.name


class IncidentStatusRef(models.Model):
    """Status taxonomy to ensure workflow: DRAFT, PENDING_REVIEW, etc."""

    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Incident Status"
        verbose_name_plural = "Incident Statuses"

    def __str__(self):
        return self.name


class Incident(TimestampedModel, OwnedModel):
    """Represent operational risk events - core business domain."""

    title = models.CharField(max_length=255)
    description = models.TextField()
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    discovered_at = models.DateTimeField(blank=True, null=True)

    # Foreign Keys with sensible on_delete and related_name
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    # BusinessProcess will live in the 'references' app as well
    business_process = models.ForeignKey(
        BusinessProcess,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, blank=True, null=True
    )
    basel_event_type = models.ForeignKey(
        BaselEventType, on_delete=models.PROTECT, blank=True, null=True
    )
    basel_business_line = models.ForeignKey(
        BaselBusinessLine, on_delete=models.PROTECT, blank=True, null=True
    )

    # NEW: To store the user's initial choice of simplified event type.
    simplified_event_type = models.ForeignKey(
        SimplifiedEventTypeRef,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Simplified event type chosen by the employee in UI.",
    )

    # PROTECT is safer for critical links than SET_NULL or CASCADE
    status = models.ForeignKey(
        IncidentStatusRef, on_delete=models.PROTECT, related_name="incidents"
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="assigned_incidents",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="validated_incidents",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="closed_incidents",
    )

    validated_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    # SLA Timestamps
    draft_due_at = models.DateTimeField(blank=True, null=True)
    review_due_at = models.DateTimeField(blank=True, null=True)
    validation_due_at = models.DateTimeField(blank=True, null=True)

    # Soft delete fields
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="deleted_incidents",
    )

    # Financial fields with defaults
    gross_loss_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    recovery_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    net_loss_amount = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    currency_code = models.CharField(max_length=3, blank=True, null=True)
    near_miss = models.BooleanField(
        default=False, help_text="Near miss: True/False"
    )
    notes = models.TextField(blank=True, null=True)

    # to access related objects  via the ORM.
    causes = models.ManyToManyField(
        LossCause, through="IncidentCause", related_name="incidents"
    )

    def __str__(self):
        return self.title


# Many-to-Many through tables, refined to be Django-idiomatic
class IncidentCause(models.Model):
    """Many-to-Many link table; multiple causes per incident."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE)
    loss_cause = models.ForeignKey(LossCause, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("incident", "loss_cause"),)


class IncidentRoutingRule(models.Model):
    """Simple custom routing for incidents based on JSON predicates."""

    route_to_role = models.ForeignKey(
        Role, on_delete=models.CASCADE, blank=True, null=True
    )
    route_to_bu = models.ForeignKey(
        BusinessUnit, on_delete=models.CASCADE, blank=True, null=True
    )
    predicate = models.JSONField()
    priority = models.IntegerField(default=100)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.description or f"Rule {self.id}"


class IncidentRequiredField(models.Model):
    """Ensures progressive field disclosure at each workflow stage."""

    status = models.ForeignKey(IncidentStatusRef, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    required = models.BooleanField(default=False)

    class Meta:
        unique_together = (("status", "field_name"),)


class SlaConfig(models.Model):
    """Deadlines for each workflow stage; re-calculated during transitions;
    trigger reminders/notifications."""

    key = models.CharField(primary_key=True, max_length=50)
    value_int = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key


# --- State Machine Configuration Model ---
class AllowedTransition(models.Model):
    """
    A config model for data-driven state machine.
    Defines which roles can move an incident from one status to another.
    """

    from_status = models.ForeignKey(
        IncidentStatusRef, on_delete=models.CASCADE, related_name="+"
    )
    to_status = models.ForeignKey(
        IncidentStatusRef, on_delete=models.CASCADE, related_name="+"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        help_text="The role required to perform this transition.",
    )

    class Meta:
        unique_together = ("from_status", "to_status", "role")
        verbose_name = "Allowed Workflow Transition"

    def __str__(self):
        return (
            f"{self.from_status.code} -> {self.to_status.code}"
            f" [{self.role.name}]"
        )
