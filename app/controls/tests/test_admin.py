"""
Tests for the Django admin interface of the controls app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from controls.models import Control, ControlType, ControlFrequency
from references.models import BusinessUnit, BusinessProcess

User = get_user_model()


class ControlAdminTests(TestCase):
    """
    Tests for the Control Library admin interface.
    """

    @classmethod
    def setUpTestData(cls):
        # 1. Setup Users
        cls.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass",
        )
        cls.owner_user = User.objects.create_user(
            email="owner@example.com",
            password="userpass",
        )

        # 2. Setup Reference Data
        cls.bu_finance = BusinessUnit.objects.create(name="Finance")
        cls.proc_ap = BusinessProcess.objects.create(name="Accounts Payable")

        # 3. Setup Controls
        cls.control_active = Control.objects.create(
            title="Dual Signature",
            description="Checks > $10k require 2 signatures",
            control_type=ControlType.PREVENTIVE,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=5,
            business_unit=cls.bu_finance,
            business_process=cls.proc_ap,
            owner=cls.owner_user,
            is_active=True,
            created_by=cls.admin_user,
        )

        cls.control_inactive = Control.objects.create(
            title="Legacy Manual Log",
            description="Deprecated manual log",
            control_type=ControlType.DETECTIVE,
            business_unit=cls.bu_finance,
            owner=cls.owner_user,
            is_active=False,
            created_by=cls.admin_user,
        )

        cls.client = Client()

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_control_changelist_loads(self):
        """Test the changelist page loads successfully."""
        url = reverse("admin:controls_control_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dual Signature")
        self.assertContains(response, "Legacy Manual Log")

    def test_control_add_page_loads(self):
        """Test the add page loads successfully."""
        url = reverse("admin:controls_control_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for fieldset headers
        self.assertContains(response, "Design Characteristics")
        self.assertContains(response, "Context &amp; Ownership")

    def test_control_change_page_loads(self):
        """Test the change page loads with correct data."""
        url = reverse(
            "admin:controls_control_change", args=[self.control_active.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify fields contain correct data
        self.assertContains(response, 'value="Dual Signature"')
        # Check that owner is selected correctly in the autocomplete/select
        # (Note: Autocomplete widgets render differently,
        # but we can check the input value)
        self.assertContains(response, f'value="{self.owner_user.pk}"')

    def test_filter_by_active_status(self):
        """Test filtering controls by is_active status."""
        url = reverse("admin:controls_control_changelist")

        # Filter: Active = Yes (1)
        response = self.client.get(url, {"is_active__exact": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dual Signature")
        self.assertNotContains(response, "Legacy Manual Log")

    def test_filter_by_control_type(self):
        """Test filtering controls by type."""
        url = reverse("admin:controls_control_changelist")

        # Filter: Type = Detective
        response = self.client.get(
            url, {"control_type__exact": ControlType.DETECTIVE}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Legacy Manual Log")
        self.assertNotContains(response, "Dual Signature")

    def test_search_functionality(self):
        """Test search by title."""
        url = reverse("admin:controls_control_changelist")
        response = self.client.get(url, {"q": "Dual"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dual Signature")
        self.assertNotContains(response, "Legacy Manual Log")
