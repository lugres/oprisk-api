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

from incidents.serializers import (
    IncidentListSerializer,
    IncidentDetailSerializer,
)


INCIDENTS_LIST_URL = reverse("incidents:incident-list")
# INCIDENTS_CREATE_URL = reverse("incidents:incident-create")


def detail_url(incident_id):
    """Create and return an incident detail URL."""
    return reverse("incidents:incident-detail", args=[incident_id])


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


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicIncidentApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIncidentApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="test@example.com", password="testp123")

        self.client.force_authenticate(user=self.user)

        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.status_pending = IncidentStatusRef.objects.create(
            code="PENDING_REVIEW", name="Pending"
        )

    def test_retrieve_incidents(self):
        """Test retrieving a list of incidents."""
        create_incident(user=self.user, status=self.status_draft)
        create_incident(user=self.user, status=self.status_pending)

        res = self.client.get(INCIDENTS_LIST_URL)

        incidents = Incident.objects.all().order_by("-id")
        serializer = IncidentListSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_list_limited_to_user(self):
        """Test list of incidents is limited to authenticated user only."""
        other_user = create_user(email="other@example.com", password="test123")
        create_incident(user=other_user, status=self.status_draft)
        create_incident(user=self.user, status=self.status_pending)

        res = self.client.get(INCIDENTS_LIST_URL)

        incidents = Incident.objects.filter(created_by=self.user)
        serializer = IncidentListSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_are_ordered_by_newest_first(self):
        """Test incidents are ordered by ID descending."""
        incident1 = create_incident(user=self.user, status=self.status_draft)
        incident2 = create_incident(user=self.user, status=self.status_draft)

        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.data[0]["id"], incident2.id)
        self.assertEqual(res.data[1]["id"], incident1.id)

    def test_filter_incidents_by_status(self):
        """Test filtering incidents by their status."""
        incident_draft = create_incident(
            user=self.user, status=self.status_draft
        )
        create_incident(user=self.user, status=self.status_pending)

        # Filter for DRAFT incidents
        res = self.client.get(INCIDENTS_LIST_URL, {"status__code": "DRAFT"})
        serializer_draft = IncidentListSerializer(incident_draft)

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

        res_true = self.client.get(INCIDENTS_LIST_URL, {"near_miss": "true"})
        res_false = self.client.get(INCIDENTS_LIST_URL, {"near_miss": "false"})

        self.assertEqual(len(res_true.data), 1)
        self.assertEqual(res_true.data[0]["id"], incident1.id)
        self.assertEqual(len(res_false.data), 1)
        self.assertEqual(res_false.data[0]["id"], incident2.id)

    def test_get_incident_detail(self):
        """Test get incident detail."""
        incident = create_incident(user=self.user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.get(url)

        serializer = IncidentDetailSerializer(incident)
        self.assertEqual(res.data, serializer.data)

    def test_create_incident(self):
        """Test creating an incident via API endpoint."""
        payload = {
            "title": "Test incident title",
            "description": "Test description",
            # "status": self.status_draft.id,
            "gross_loss_amount": Decimal("199.99"),
            "currency_code": "EUR",
        }
        res = self.client.post(INCIDENTS_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        incident = Incident.objects.get(id=res.data["id"])
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.status.code, self.status_draft.code)
        self.assertEqual(incident.created_by, self.user)

    def test_partial_update_incident(self):
        """Test partial update of an incident with PATCH."""
        original_description = "Details on incident"
        incident = create_incident(
            user=self.user,
            status=self.status_draft,
            title="Sample incident title",
            description=original_description,
        )

        payload = {"title": "New incident title"}
        url = detail_url(incident.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.description, original_description)
        self.assertEqual(incident.created_by, self.user)

    def test_full_update_incident(self):
        """Test fully updating an incident with PUT."""
        incident = create_incident(user=self.user, status=self.status_draft)
        payload = {
            "title": "Full New Title",
            "description": "Full new description.",
            "status": self.status_pending.id,
        }
        url = detail_url(incident.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.description, payload["description"])
        self.assertEqual(incident.status.id, payload["status"])
        self.assertEqual(incident.created_by, self.user)

    def test_update_existent_incident_user_returns_error(self):
        """Test changing the incident's user results in an error."""
        new_user = create_user(email="user2@example.com", password="tstpsw12")
        incident = create_incident(user=self.user, status=self.status_draft)

        payload = {"user": new_user.id}
        url = detail_url(incident.id)
        self.client.patch(url, payload)

        incident.refresh_from_db()
        self.assertEqual(incident.created_by, self.user)

    def test_delete_incident(self):
        """Test deleting an incident is successful."""
        incident = create_incident(user=self.user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Incident.objects.filter(id=incident.id).exists())

    def test_delete_other_users_incident_error(self):
        """Test trying to delete another user's incident returns an error."""
        new_user = create_user(email="user2@example.com", password="tstpsw12")
        incident = create_incident(user=new_user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Incident.objects.filter(id=incident.id).exists())

    # Transitions - submit
    def test_submit_incident_action_success(self):
        """Test the custom action to submit a DRAFT incident."""
        incident = create_incident(user=self.user, status=self.status_draft)
        url = reverse("incidents:incident-submit", args=[incident.id])

        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        incident.refresh_from_db()
        self.assertEqual(incident.status.code, "PENDING_REVIEW")

    def test_submit_incident_wrong_status_fails(self):
        """Test that submitting an incident not in DRAFT status fails."""
        incident = create_incident(user=self.user, status=self.status_pending)
        url = reverse("incidents:incident-submit", args=[incident.id])

        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_incident_not_owner_fails(self):
        """Test that a user cannot submit an incident they did not create."""
        new_user = create_user(email="user2@example.com", password="tstpsw12")
        incident = create_incident(user=new_user, status=self.status_draft)
        url = reverse("incidents:incident-submit", args=[incident.id])

        res = self.client.post(url)
        # This will fail with 404 because get_queryset already filters by user
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
