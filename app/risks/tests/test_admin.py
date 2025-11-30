"""
Tests for the Django admin interface of the risks app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from risks.models import Risk, RiskCategory, RiskStatus
from references.models import BaselEventType, BusinessUnit

User = get_user_model()


class RiskAdminTests(TestCase):
    """
    Tests for the Django admin interface of the risks app using the Client.
    This method avoids complex mocking and guarantees that custom
    list_display, fieldsets, and inlines load correctly.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified data for all tests."""
        # Create an administrative user for login
        cls.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpw123",
        )
        cls.user = User.objects.create_user(
            email="owner@example.com",
            password="userpw123",
        )
        cls.client = Client()

        # Create necessary reference data
        cls.bu = BusinessUnit.objects.create(name="Test BU")
        cls.basel_type = BaselEventType.objects.create(name="Internal Fraud")
        cls.category = RiskCategory.objects.create(name="Fraud Risk")
        cls.category.basel_event_types.add(cls.basel_type)

        # Create a sample Risk instance
        cls.risk = Risk.objects.create(
            title="System Outage Risk",
            description="Test description",
            status=RiskStatus.DRAFT,
            risk_category=cls.category,
            basel_event_type=cls.basel_type,
            owner=cls.user,
            created_by=cls.user,
            business_unit=cls.bu,
        )

    def setUp(self):
        """Log in the admin before each test method."""
        self.client.force_login(self.admin_user)

    # ----------------------------------------
    # Risk Model Tests
    # ----------------------------------------

    def test_risk_changelist_loads(self):
        """Test the changelist page for Risk model loads (HTTP 200)."""
        url = reverse("admin:risks_risk_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_risk_add_page_loads(self):
        """Test the add page for Risk model loads (HTTP 200)."""

        url = reverse("admin:risks_risk_add")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_risk_change_page_loads_and_includes_fieldsets(self):
        """Test the change page loads and checks for key fieldsets."""
        url = reverse("admin:risks_risk_change", args=[self.risk.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test for key fields from the custom RiskAdmin fieldsets
        # 1. Field from "Context & Classification" fieldset
        self.assertContains(response, 'name="risk_category"')

        # 2. Field from "Assessment Scores" fieldset
        self.assertContains(response, 'name="inherent_likelihood"')

        # 3. Check for the IncidentRisk inline by looking for its header title
        self.assertContains(response, "Incident to Risk Links")

    def test_risk_list_display_fields_render(self):
        """Test that key list_display fields render correctly."""
        url = reverse("admin:risks_risk_changelist")
        response = self.client.get(url)

        # Check for content from the Risk object
        self.assertContains(response, self.risk.title)
        # Check for content from related objects/properties
        self.assertContains(response, self.risk.owner.email)
        self.assertContains(response, self.risk.risk_category.name)

    # ----------------------------------------
    # RiskCategory Model Tests
    # ----------------------------------------

    def test_riskcategory_changelist_loads(self):
        """Test the changelist page for RiskCat model loads (HTTP 200)."""
        url = reverse("admin:risks_riskcategory_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_riskcategory_add_page_loads(self):
        """Test the add page for RiskCategory model loads (HTTP 200)."""
        url = reverse("admin:risks_riskcategory_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_riskcategory_change_page_includes_basel_inline(self):
        """Test the change page for RiskCat includes the Basel M2M inline."""
        url = reverse(
            "admin:risks_riskcategory_change", args=[self.category.pk]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Check for a field name from the RiskCategoryToBaselEventTypeInline
        # (e.g., the label for the basel_event_type field)
        self.assertContains(response, "Basel event type")
        self.assertContains(response, self.basel_type.name)
