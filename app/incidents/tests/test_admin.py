"""
Tests for the Django admin interface of the incidents app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from incidents.models import Incident, IncidentStatusRef
from references.models import Role, BusinessUnit

User = get_user_model()


class IncidentAdminTests(TestCase):

    def setUp(self):
        """Create a logged-in superuser client and user."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="test_pass123",
        )
        self.client.force_login(self.admin_user)

        self.role = Role.objects.create(name="Employee")
        self.bu = BusinessUnit.objects.create(name="Retail")
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
            full_name="Test User",
            role=self.role,
            business_unit=self.bu,
        )

    def test_incident_changelist_loads(self):
        """Test that the incident changelist page loads correctly."""
        url = reverse("admin:incidents_incident_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_incident_add_page_loads(self):
        """Test that the incident add page loads correctly."""
        url = reverse("admin:incidents_incident_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_incident_change_page_loads(self):
        """Test that the incident change page loads correctly."""
        status = IncidentStatusRef.objects.create(code="DRAFT", name="Draft")
        incident = Incident.objects.create(
            title="Test Incident",
            status=status,
            created_by=self.user,
        )
        url = reverse("admin:incidents_incident_change", args=[incident.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
