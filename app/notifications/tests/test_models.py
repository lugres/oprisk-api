"""
Tests for the models of the notifications app.
"""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from references.models import Role
from incidents.models import Incident, IncidentStatusRef
from notifications.models import Notification, UserNotification

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
            f"ROUTING_NOTIFY for INCIDENT {self.incident.id}",
        )

    def test_user_notification_link(self):
        """Test the link between Notification and UserNotification."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
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
            with transaction.atomic():  # atomic transaction needed
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

    def test_user_notification_mark_as_read(self):
        """Test marking a notification as read updates timestamps."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
        )
        user_notif = UserNotification.objects.create(
            notification=notification, user=self.user
        )

        self.assertIsNone(user_notif.read_at)

        # Mark as read
        user_notif.is_read = True
        user_notif.read_at = timezone.now()
        user_notif.save()

        user_notif.refresh_from_db()
        self.assertTrue(user_notif.is_read)
        self.assertIsNotNone(user_notif.read_at)

    def test_notification_deletion_cascades_to_user_notifications(self):
        """Test deleting a notification removes associated UserNotification."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
        )
        UserNotification.objects.create(
            notification=notification, user=self.user
        )

        notification_id = notification.id
        notification.delete()

        # UserNotification should be deleted
        self.assertFalse(
            UserNotification.objects.filter(
                notification_id=notification_id
            ).exists()
        )

    def test_user_deletion_cascades_to_user_notifications(self):
        """Test deleting a user removes their UserNotifications."""
        user2 = User.objects.create_user(
            email="user2@test.com", password="passw123"
        )
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
        )
        UserNotification.objects.create(notification=notification, user=user2)

        # Verify notification exists before cascade deletion
        self.assertEqual(UserNotification.objects.count(), 1)
        # Store the user ID before deletion
        user2_id = user2.id
        user2.delete()

        # UserNotification for user2 should be deleted
        self.assertFalse(
            UserNotification.objects.filter(user_id=user2_id).exists()
        )
        # No notifications still exist
        self.assertEqual(UserNotification.objects.count(), 0)

    def test_notification_multiple_user_notifications(self):
        """Test one notification can have multiple UserNotifications."""
        user2 = User.objects.create_user(
            email="user2@test.com", password="passw123"
        )
        user3 = User.objects.create_user(
            email="user3@test.com", password="passw123"
        )

        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.ROUTING_NOTIFY,
            recipient_role=self.role,  # Sent to role, not individual
        )

        # Create UserNotifications for multiple users
        UserNotification.objects.create(
            notification=notification, user=self.user
        )
        UserNotification.objects.create(notification=notification, user=user2)
        UserNotification.objects.create(notification=notification, user=user3)

        self.assertEqual(
            UserNotification.objects.filter(notification=notification).count(),
            3,
        )

    def test_notification_status_transitions(self):
        """Test notification can transition through statuses."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.INCIDENT_OVERDUE,
        )

        self.assertEqual(notification.status, Notification.Status.QUEUED)

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.attempts = 1
        notification.save()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertIsNotNone(notification.sent_at)
        self.assertEqual(notification.attempts, 1)

    def test_notification_error_tracking(self):
        """Test notification can track delivery failures."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.MEASURE,
            entity_id=999,
            event_type=Notification.EventType.MEASURE_OVERDUE,
            method=Notification.Method.EMAIL,
        )

        notification.status = Notification.Status.FAILED
        notification.last_error = "SMTP connection timeout"
        notification.attempts = 3
        notification.save()

        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.Status.FAILED)
        self.assertEqual(notification.attempts, 3)
        self.assertIn("timeout", notification.last_error)

    def test_notification_ordering(self):
        """Test notifications are ordered by created_at descending."""
        n1 = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
        )
        # Ensure a time difference
        time_travel = timezone.now() + timezone.timedelta(seconds=1)
        with self.settings(NOW_OVERRIDE=time_travel):
            n2 = Notification.objects.create(
                entity_type=Notification.EntityType.INCIDENT,
                entity_id=self.incident.id,
                event_type=Notification.EventType.ROUTING_NOTIFY,
            )

        notifications = list(Notification.objects.all())
        self.assertEqual(notifications[0].id, n2.id)  # Most recent first
        self.assertEqual(notifications[1].id, n1.id)

    def test_notification_with_payload(self):
        """Test notification can store JSON payload."""
        payload = {"key": "value", "count": 42, "nested": {"data": True}}
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.KRI,
            entity_id=123,
            event_type=Notification.EventType.CUSTOM,
            payload=payload,
        )

        notification.refresh_from_db()
        self.assertEqual(notification.payload, payload)

    def test_notification_risk_and_action_fields(self):
        """Test the priority, requires_action, and action_url fields."""
        payload_url = "/incidents/review/123"
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.ROUTING_NOTIFY,
            recipient_role=self.role,
            # Set the new fields
            priority=Notification.Priority.HIGH,
            requires_action=True,
            action_url=payload_url,
        )

        notification.refresh_from_db()

        self.assertEqual(notification.priority, Notification.Priority.HIGH)
        self.assertTrue(notification.requires_action)
        self.assertEqual(notification.action_url, payload_url)

    def test_notification_priority_default(self):
        """Test that priority defaults to MEDIUM."""
        notification = Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=self.incident.id,
            event_type=Notification.EventType.CUSTOM,
            recipient_role=self.role,
        )
        self.assertEqual(notification.priority, Notification.Priority.MEDIUM)
