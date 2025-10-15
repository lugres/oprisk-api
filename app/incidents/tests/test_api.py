"""
Tests for incidents API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from incidents.models import Incident, IncidentStatusRef

from incidents.serializers import IncidentSerializer


INCIDENTS_URL = reverse("incidents:incident-list")


def create_incident(user, **params):
    """Create and return a sample incident (helper function)."""
    defaults = {
        "title": "Sample incident title",
        "description": "Sample description",
        "gross_loss_amount": Decimal("999.99"),
        "currency_code": "USD",
    }
    defaults.update(params)

    incident = Incident.objects.create(created_by=user, **defaults)
    return incident


class PublicIncidentApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(INCIDENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIncidentApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@example.com",
            password="testpass123",
            full_name="Test User",
        )

        self.client.force_authenticate(user=self.user)

        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.status_pending = IncidentStatusRef.objects.create(
            code="PENDING_REVIEW", name="Pending"
        )

    def test_retrieve_incidents(self):
        """Test retrieving a list of incidents."""
        create_incident(user=self.user)
        create_incident(user=self.user)

        res = self.client.get(INCIDENTS_URL)

        incidents = Incident.objects.all().order_by("-id")
        serializer = IncidentSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_list_limited_to_user(self):
        """Test list of incidents is limited to authenticated user only."""
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="otherpsw123",
        )
        create_incident(user=other_user)
        create_incident(user=self.user)

        res = self.client.get(INCIDENTS_URL)

        incidents = Incident.objects.filter(created_by=self.user)
        serializer = IncidentSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_are_ordered_by_newest_first(self):
        """Test incidents are ordered by ID descending."""
        incident1 = create_incident(user=self.user, status=self.status_draft)
        incident2 = create_incident(user=self.user, status=self.status_draft)

        res = self.client.get(INCIDENTS_URL)

        self.assertEqual(res.data[0]["id"], incident2.id)
        self.assertEqual(res.data[1]["id"], incident1.id)

    def test_filter_incidents_by_status(self):
        """Test filtering incidents by their status."""
        incident_draft = create_incident(
            user=self.user, status=self.status_draft
        )
        create_incident(user=self.user, status=self.status_pending)

        # Filter for DRAFT incidents
        res = self.client.get(INCIDENTS_URL, {"status__code": "DRAFT"})
        serializer_draft = IncidentSerializer(incident_draft)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], serializer_draft.data["id"])

    def test_filter_incidents_by_near_miss(self):
        """Test filtering incidents by the near_miss flag."""
        incident1 = create_incident(
            user=self.user, status=self.status_draft, near_miss=True
        )
        incident2 = create_incident(
            user=self.user, status=self.status_draft, near_miss=False
        )

        res_true = self.client.get(INCIDENTS_URL, {"near_miss": "true"})
        res_false = self.client.get(INCIDENTS_URL, {"near_miss": "false"})

        self.assertEqual(len(res_true.data), 1)
        self.assertEqual(res_true.data[0]["id"], incident1.id)
        self.assertEqual(len(res_false.data), 1)
        self.assertEqual(res_false.data[0]["id"], incident2.id)
