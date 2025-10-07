"""
Tests for the Django admin modifications, custom user model.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse


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
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
            full_name="Test User",
        )

    def test_users_list(self):
        """Test that users are listed on the page."""
        url = reverse("admin:users_user_changelist")
        res = self.client.get(url)

        self.assertContains(res, self.user.full_name)
        self.assertContains(res, self.user.email)
