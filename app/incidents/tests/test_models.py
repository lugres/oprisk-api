"""
Tests for the models in the incidents app.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from references.models import BusinessUnit, BaselEventType
from incidents.models import (
    Incident,
    IncidentStatusRef,
    LossCause,
    SimplifiedEventTypeRef,
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
            reported_by=self.reporter,
            status=self.status_draft,
            business_unit=self.bu,
        )
        self.assertEqual(str(incident), incident.title)
        self.assertEqual(incident.reported_by.email, self.reporter.email)
        self.assertEqual(incident.status.code, self.status_draft.code)

    def test_incident_default_values(self):
        """Test the default values for fields (near_miss and fin amounts)."""
        incident = Incident.objects.create(
            title="Near Miss Event",
            description="A potential fraud was stopped before loss occurred.",
            reported_by=self.reporter,
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

    # Placeholder test for future business logic on the model
    def test_calculate_net_loss(self):
        """
        Test a future 'calculate_net_loss' method.
        This test will fail initially, driving the implementation (TDD).
        """
        incident = Incident.objects.create(
            title="Test Net Loss",
            description="An incident with financial impact.",
            reported_by=self.reporter,
            status=self.status_draft,
            gross_loss_amount=1000.00,
            recovery_amount=250.00,
        )
        # self.assertEqual(incident.calculate_net_loss(), 750.00)
        pass  # Placeholder until the method is implemented
