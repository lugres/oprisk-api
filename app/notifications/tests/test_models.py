"""
Tests for the models of the notifications app.
"""

from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from references.models import Role
from incidents.models import Incident, IncidentStatusRef
from .models import Notification, UserNotification

User = get_user_model()


class NotificationModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up data for testing notification models."""
        cls.user = User.objects.create_user(
            email="test@user.com", password="testpsw123"
        )
        cls.role = Role.objects.create(name="Risk Officer")
        status = IncidentStatusRef.objects.create(code="DRAFT", name="Draft")
        cls.incident = Incident.objects.create(
            title="Test Incident", created_by=cls.user, status=status
        )

    def test_create_incident_notification_defaults(self):
        """Test creating a notification sets default values correctly."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.ROUTING_NOTIFY,
            recipient_role=self.role,
        )

        self.assertEqual(notification.status, Notification.Status.QUEUED)
        self.assertEqual(notification.method, Notification.Method.SYSTEM)
        self.assertEqual(notification.attempts, 0)
        self.assertTrue(notification.active)
        self.assertEqual(
            str(notification),
            f"ROUTING_NOTIFY for incident {self.incident.id}",
        )

    def test_user_notification_link(self):
        """Test the link between Notification and UserNotification."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
            recipient=self.user,
        )
        user_notif = UserNotification.objects.create(
            notification=notification, user=self.user
        )

        self.assertFalse(user_notif.is_read)
        self.assertEqual(user_notif.user, self.user)
        self.assertEqual(user_notif.notification, notification)

    def test_notification_active_unique_constraint(self):
        """Test the 'ux_notifications_active' partial unique constraint."""
        # Create the first active notification
        Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.INCIDENT_OVERDUE,
            sla_stage=Notification.SlaStage.DRAFT,
            recipient_role=self.role,
            active=True,
        )

        # Try to create an identical active notification
        with self.assertRaises(IntegrityError):
            Notification.objects.create(
                entity_type=Notification.EntityType.INCIDENT,
                entity_id=self.incident.id,
                event_type=Notification.EventType.INCIDENT_OVERDUE,
                sla_stage=Notification.SlaStage.DRAFT,
                recipient_role=self.role,
                active=True,  # Fails because this is active
            )

        # Creating a *non-active* duplicate is allowed
        Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.INCIDENT_OVERDUE,
            sla_stage=Notification.SlaStage.DRAFT,
            recipient_role=self.role,
            active=False,  # This should pass
        )

    def test_user_notification_unique_together(self):
        """Test a user can only have one read status per notification."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
        )
        UserNotification.objects.create(
            notification=notification, user=self.user
        )

        # Try to create a duplicate link
        with self.assertRaises(IntegrityError):
            UserNotification.objects.create(
                notification=notification, user=self.user
            )
