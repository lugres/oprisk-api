"""
Tests for the Django admin interface of the measures app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from measures.models import Measure, MeasureStatusRef


User = get_user_model()


class MeasureAdminTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpw123",
        )
        self.client.force_login(self.admin_user)

    def test_measure_changelist_loads(self):
        """Test the changelist page for Measure model loads."""
        url = reverse("admin:measures_measure_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_measure_add_page_loads(self):
        """Test the add page for Measure model loads."""
        url = reverse("admin:measures_measure_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_measurestatusref_changelist_loads(self):
        """Test the changelist page for MeasureStatusRef model loads."""
        url = reverse("admin:measures_measurestatusref_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_measurestatusref_add_page_loads(self):
        """Test the add page for MeasureStatusRef model loads."""
        url = reverse("admin:measures_measurestatusref_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_measure_list_display_fields(self):
        """Test that list_display fields render correctly."""

        status, _ = MeasureStatusRef.objects.get_or_create(code="OPEN")
        measure = Measure.objects.create(
            description="Test measure",
            created_by=self.admin_user,
            status=status,
        )

        url = reverse("admin:measures_measure_changelist")
        response = self.client.get(url)

        self.assertContains(response, measure.description)
        self.assertContains(response, status.name)

    def test_measure_search(self):
        """Test search functionality in admin."""
        measure = Measure.objects.create(
            description="Searchable measure", created_by=self.admin_user
        )

        url = reverse("admin:measures_measure_changelist")
        response = self.client.get(url, {"q": "Searchable"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, measure.description)

    def test_measure_filter_by_status(self):
        """Test filtering measures by status."""
        status_open, _ = MeasureStatusRef.objects.get_or_create(code="OPEN")
        status_done, _ = MeasureStatusRef.objects.get_or_create(
            code="COMPLETED"
        )

        Measure.objects.create(
            description="Open measure",
            created_by=self.admin_user,
            status=status_open,
        )
        Measure.objects.create(
            description="Done measure",
            created_by=self.admin_user,
            status=status_done,
        )

        url = reverse("admin:measures_measure_changelist")
        response = self.client.get(url, {"status__id__exact": status_open.id})

        self.assertContains(response, "Open measure")
        self.assertNotContains(response, "Done measure")
