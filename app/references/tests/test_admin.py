"""
Tests for the Django admin interface of the references app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from references.models import BusinessUnit


class ReferenceAdminTests(TestCase):

    def setUp(self):
        """Create a logged-in superuser client."""
        self.client = Client()
        admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="test_pass123",
        )
        self.client.force_login(admin_user)

    def test_changelist_pages_load_successfully(self):
        """Test that the changelist for each model loads correctly."""
        model_names = [
            "role",
            "businessunit",
            "baselbusinessline",
            "baseleventtype",
            "businessprocess",
            "product",
        ]
        for name in model_names:
            url = reverse(f"admin:references_{name}_changelist")
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200, f"Failed for {name} changelist"
            )

    def test_add_pages_load_successfully(self):
        """Test that the add page for each model loads correctly."""

        model_names = [
            "role",
            "businessunit",
            "baselbusinessline",
            "baseleventtype",
            "businessprocess",
            "product",
        ]
        for name in model_names:
            url = reverse(f"admin:references_{name}_add")
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 200, f"Failed for {name} add page"
            )

    def test_change_page_loads_successfully(self):
        """Test that the change page for a sample model loads correctly."""

        bu = BusinessUnit.objects.create(name="Test BU")
        url = reverse("admin:references_businessunit_change", args=[bu.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
