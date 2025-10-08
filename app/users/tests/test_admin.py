"""
Tests for the Django admin modifications, custom user model.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from references.models import Role, BusinessUnit


class AdminSiteCustomUserModelTests(TestCase):
    """Tests for Django Admin, custom user model."""

    def setUp(self):
        """Initial setup, create user and client."""
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
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

    def test_users_list(self):
        """Test that users are listed on the page."""
        url = reverse("admin:users_user_changelist")
        res = self.client.get(url)

        self.assertContains(res, self.user.full_name)
        self.assertContains(res, self.user.email)

    def test_edit_user_page_displays_custom_fields(self):
        """Test that the edit user page works correctly and shows custom fields."""
        url = reverse("admin:users_user_change", args=[self.user.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Organizational structure")
        self.assertContains(res, "business_unit")

    def test_create_user_page(self):
        """Test the create user page works."""
        url = reverse("admin:users_user_add")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_readonly_fields_are_not_editable(self):
        """Test that a POST request cannot change a readonly field."""
        url = reverse("admin:users_user_change", args=[self.user.id])

        # Get the original date_joined value
        original_date_joined = self.user.date_joined

        # Prepare a payload to POST. We will try to change a readonly field.
        payload = {
            "email": "newemail@example.com",
            "full_name": "New Name",
            "role": self.role.id,
            "business_unit": self.bu.id,
            "date_joined_0": "2020-01-01",  # Attempting to change date
            "date_joined_1": "12:00:00",  # Attempting to change time
            # Include other required fields for the form to be valid
            "is_active": "on",
            "is_staff": "",
            "is_superuser": "",
        }

        res = self.client.post(url, payload)

        # Check that the request was successful
        self.assertEqual(res.status_code, 302)  # Successful POST redirects

        # Refresh the user object from the database
        self.user.refresh_from_db()

        # Assert that the regular field was updated
        self.assertEqual(self.user.email, "newemail@example.com")
        # Assert that the readonly field was NOT updated
        self.assertEqual(self.user.date_joined, original_date_joined)

    # keeping these simple tests for references app here so far
    def test_references_changelist_pages_load(self):
        """Test that the changelist pages for reference models load correctly."""
        urls = [
            reverse("admin:references_role_changelist"),
            reverse("admin:references_businessunit_changelist"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
