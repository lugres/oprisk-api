"""
Data models for the notifications app.
Unified - used by all app (incidents, measures) to create notifications.
Celery will ensure notifications' delivery in the async mode.
"""

from django.db import models
from django.conf import settings
from django.db.models import Q


# To prevent circular dependencies - No direct import of other apps' models


class Notification(models.Model):
    """
    A unified, asynchronous notification queue for all entities.
    Based on the v0_8 schema.
    """

    class EntityType(models.TextChoices):
        INCIDENT = "INCIDENT", "Incident"
        MEASURE = "MEASURE", "Measure"
        KRI = "KRI", "Key Risk Indicator"

    class EventType(models.TextChoices):
        ROUTING_NOTIFY = "ROUTING_NOTIFY", "Routing Notification"
        INCIDENT_OVERDUE = "INCIDENT_OVERDUE", "Incident Overdue"
        MEASURE_OVERDUE = "MEASURE_OVERDUE", "Measure Overdue"
        KRI_OVERDUE = "KRI_OVERDUE", "KRI Overdue"
        CUSTOM = "CUSTOM", "Custom"

    class SlaStage(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REVIEW = "REVIEW", "Review"
        VALIDATION = "VALIDATION", "Validation"

    class Method(models.TextChoices):
        SYSTEM = "SYSTEM", "System (in-app)"
        EMAIL = "EMAIL", "Email"
        SLACK = "SLACK", "Slack"
        WEBHOOK = "WEBHOOK", "Webhook"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    # Polymorphic link to the source entity (e.g., an Incident)
    entity_type = models.CharField(
        max_length=30,
        choices=EntityType.choices,
    )  # e.g., 'incident', 'measure'
    entity_id = models.IntegerField()

    # What triggered this?
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    sla_stage = models.CharField(
        max_length=30, choices=SlaStage.choices, blank=True, null=True
    )
    routing_rule_id = models.IntegerField(blank=True, null=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # User who caused it might be deleted
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )

    # Who is this for?
    recipient_role = models.ForeignKey(
        "references.Role",  # Use string path to avoid circular import
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Notification is intended for this role(audit).",
    )

    # When?
    created_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(
        blank=True, null=True
    )  # e.g., the SLA deadline

    # How?
    method = models.CharField(
        max_length=30, choices=Method.choices, default=Method.SYSTEM
    )
    payload = models.JSONField(blank=True, null=True)  # Extra context

    # Risk Management Fields
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.MEDIUM
    )
    requires_action = models.BooleanField(default=False)
    action_url = models.CharField(max_length=500, blank=True, null=True)

    # State
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    attempts = models.IntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        # Replicates the SQL partial unique index for idempotency
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "entity_type",
                    "entity_id",
                    "event_type",
                    "sla_stage",
                    "recipient_role",
                ],
                condition=Q(active=True),
                name="ux_notifications_active",
            )
        ]

    def __str__(self):
        return f"{self.event_type} for {self.entity_type} {self.entity_id}"


class UserNotification(models.Model):
    """
    Maps a single Notification to multiple users (e.g., if sent to a Role)
    and tracks their individual read status.
    """

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("notification", "user")
