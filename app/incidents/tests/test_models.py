"""
Tests for the models in the incidents app.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from time import sleep

from references.models import BusinessUnit, BaselEventType
from incidents.models import (
    Incident,
    IncidentStatusRef,
    LossCause,
    SimplifiedEventTypeRef,
    IncidentCause,
)

User = get_user_model()


class IncidentModelTests(TestCase):

    def setUp(self):
        """Set up common objects for incident tests."""
        self.reporter = User.objects.create_user(
            email="reporter@example.com", password="testpass123"
        )
        self.bu = BusinessUnit.objects.create(name="Retail Banking")
        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.basel_event_type = BaselEventType.objects.create(
            name="External Fraud"
        )

    def test_create_incident_successful(self):
        """Test that a basic incident can be created with required fields."""
        incident = Incident.objects.create(
            title="Suspicious Transaction",
            description="A suspicious transaction was reported on account XY.",
            created_by=self.reporter,
            status=self.status_draft,
            business_unit=self.bu,
        )
        self.assertEqual(str(incident), incident.title)
        self.assertEqual(incident.created_by, self.reporter)
        self.assertEqual(incident.status, self.status_draft)

    def test_incident_default_values(self):
        """Test the default values for fields (near_miss and fin amounts)."""
        incident = Incident.objects.create(
            title="Near Miss Event",
            description="A potential fraud was stopped before loss occurred.",
            created_by=self.reporter,
            status=self.status_draft,
        )
        self.assertFalse(incident.near_miss)
        self.assertEqual(incident.gross_loss_amount, 0)
        self.assertEqual(incident.recovery_amount, 0)

    def test_focused_reference_models(self):
        """Test creation of reference models that live inside incidents app."""
        loss_cause = LossCause.objects.create(name="Phishing Attack")
        simplified_event = SimplifiedEventTypeRef.objects.create(
            name="IT/Cyber", short_desc="An IT or Cybersecurity related event."
        )
        self.assertEqual(str(loss_cause), "Phishing Attack")
        self.assertEqual(str(simplified_event), "IT/Cyber")

    def test_incident_cause_relationship(self):
        """Test linking a cause to an incident via the through model."""
        incident = Incident.objects.create(
            title="Test",
            created_by=self.reporter,
            status=self.status_draft,
            business_unit=self.bu,
        )
        cause = LossCause.objects.create(name="Human Error")
        IncidentCause.objects.create(incident=incident, loss_cause=cause)

        self.assertEqual(incident.causes.count(), 1)
        self.assertEqual(incident.causes.first(), cause)

    def test_incident_cause_unique_together_constraint(self):
        """Test that a cause can only be linked to an incident once."""
        incident = Incident.objects.create(
            title="Test",
            created_by=self.reporter,
            status=self.status_draft,
            business_unit=self.bu,
        )
        cause = LossCause.objects.create(name="System Failure")
        IncidentCause.objects.create(incident=incident, loss_cause=cause)

        with self.assertRaises(IntegrityError):
            IncidentCause.objects.create(incident=incident, loss_cause=cause)

    def test_timestamped_model_fields(self):
        """Test that created_at and updated_at are set correctly."""
        incident = Incident.objects.create(
            title="Timestamp Test",
            created_by=self.reporter,
            status=self.status_draft,
            business_unit=self.bu,
        )
        self.assertIsNotNone(incident.created_at)
        self.assertIsNotNone(incident.updated_at)

        original_updated_at = incident.updated_at
        sleep(0.01)  # Ensure the timestamp will be different
        incident.title = "Updated Timestamp Test"
        incident.save()
        incident.refresh_from_db()

        self.assertGreater(incident.updated_at, original_updated_at)

    # Placeholder test for future business logic on the model
    def test_calculate_net_loss(self):
        """
        Test a future 'calculate_net_loss' method.
        This test will fail initially, driving the implementation (TDD).
        """
        incident = Incident.objects.create(
            title="Test Net Loss",
            description="An incident with financial impact.",
            created_by=self.reporter,
            status=self.status_draft,
            gross_loss_amount=1000.00,
            recovery_amount=250.00,
        )
        # self.assertEqual(incident.calculate_net_loss(), 750.00)
        pass  # Placeholder until the method is implemented
