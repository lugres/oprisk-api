"""
Tests for the Django admin interface of the notifications app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class NotificationAdminTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpw123",
        )
        self.client.force_login(self.admin_user)

    def test_notification_changelist_loads(self):
        """Test the changelist page for Notification model loads."""
        url = reverse("admin:notifications_notification_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_notification_add_page_loads(self):
        """Test the add page for Notification model loads."""
        url = reverse("admin:notifications_notification_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_notification_changelist_loads(self):
        """Test the changelist page for UserNotification model loads."""
        url = reverse("admin:notifications_usernotification_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_notification_add_page_loads(self):
        """Test the add page for UserNotification model loads."""
        url = reverse("admin:notifications_usernotification_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
