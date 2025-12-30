"""
Tests for the Django admin interface of the controls app.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from controls.models import (
    Control,
    ControlType,
    ControlFrequency,
    ControlLevel,
    ControlNature,
)
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
        cls.group_risk_user = User.objects.create_user(
            email="group.risk@example.com",
            password="grpass",
        )

        # 2. Setup Reference Data
        cls.bu_finance = BusinessUnit.objects.create(name="Finance")
        cls.bu_it = BusinessUnit.objects.create(name="IT")
        cls.proc_ap = BusinessProcess.objects.create(name="Accounts Payable")

        # 3. Setup Controls - STANDARD first, then LOCAL implementations

        cls.standard_control = Control.objects.create(
            title="Group Dual Signature Policy",
            description=(
                "Organization-wide policy: Checks > $10k require 2 signatures"
            ),
            control_type=ControlType.PREVENTIVE,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=5,
            control_level=ControlLevel.STANDARD,
            business_unit=None,
            owner=cls.group_risk_user,
            is_active=True,
            created_by=cls.admin_user,
        )

        cls.control_active = Control.objects.create(
            title="Finance Dual Signature",
            description=(
                "Finance implementation: Checks > $10k require 2 signatures"
                " from Finance approvers"
            ),
            control_type=ControlType.PREVENTIVE,
            control_frequency=ControlFrequency.AD_HOC,
            control_level=ControlLevel.LOCAL,
            parent_control=cls.standard_control,
            effectiveness=4,
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
            control_level=ControlLevel.LOCAL,
            parent_control=cls.standard_control,
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
        self.assertContains(response, "Group Dual Signature Policy")
        self.assertContains(response, "Finance Dual Signature")
        self.assertContains(response, "Legacy Manual Log")

    def test_control_add_page_loads(self):
        """Test the add page loads successfully."""
        url = reverse("admin:controls_control_add")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for fieldset headers
        self.assertContains(response, "Hierarchy &amp; Classification")
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
        self.assertContains(response, 'value="Finance Dual Signature"')
        # Check that owner is selected correctly in the autocomplete/select
        # (Note: Autocomplete widgets render differently,
        # but we can check the input value)
        self.assertContains(response, f'value="{self.owner_user.pk}"')
        # Check that parent_control is shown
        self.assertContains(response, f'value="{self.standard_control.pk}"')

    def test_filter_by_active_status(self):
        """Test filtering controls by is_active status."""
        url = reverse("admin:controls_control_changelist")

        # Filter: Active = Yes (1)
        response = self.client.get(url, {"is_active__exact": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finance Dual Signature")
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
        self.assertNotContains(response, "Finance Dual Signature")

    def test_search_functionality(self):
        """Test search by title."""
        url = reverse("admin:controls_control_changelist")
        response = self.client.get(url, {"q": "Finance"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finance Dual Signature")
        self.assertNotContains(response, "Legacy Manual Log")

    # New Tests for Hierarchical Features

    def test_filter_by_control_level(self):
        """Test filtering controls by level (STANDARD/LOCAL)."""
        url = reverse("admin:controls_control_changelist")

        # Filter: Level = STANDARD
        response = self.client.get(
            url, {"control_level__exact": ControlLevel.STANDARD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Group Dual Signature Policy")
        self.assertNotContains(response, "Finance Dual Signature")
        self.assertNotContains(response, "Legacy Manual Log")

        # Filter: Level = LOCAL
        response = self.client.get(
            url, {"control_level__exact": ControlLevel.LOCAL}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Finance Dual Signature")
        self.assertContains(response, "Legacy Manual Log")
        # The standard control's title appears in the parent_control column!
        # Therefore check that the standard control's change link
        # doesn't appear in the filtered results
        content = response.content.decode()
        self.assertNotIn(
            f'<a href="/admin/controls/control/'
            f"{self.standard_control.pk}/change/",
            content,
        )

    def test_standard_control_display_in_changelist(self):
        """Test that STANDARD controls display correctly without BU."""
        url = reverse("admin:controls_control_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Standard control should appear
        self.assertContains(response, "Group Dual Signature Policy")
        # It should show STANDARD level
        self.assertContains(response, "STANDARD")

    def test_local_control_shows_parent_in_changelist(self):
        """Test that LOCAL controls show their parent in the list."""
        url = reverse("admin:controls_control_changelist")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should show the local control
        self.assertContains(response, "Finance Dual Signature")
        # Should show it has a parent (the parent control's title or ID)
        self.assertContains(response, "Group Dual Signature Policy")

    def test_create_standard_control(self):
        """Test creating a STANDARD control through admin."""
        url = reverse("admin:controls_control_add")
        data = {
            "title": "New Standard Access Control",
            "description": "Standard policy for access management",
            "control_level": ControlLevel.STANDARD,
            "control_type": ControlType.PREVENTIVE,
            "control_frequency": ControlFrequency.DAILY,
            "control_nature": ControlNature.MANUAL,  # required for validation
            "effectiveness": 4,
            "owner": self.group_risk_user.pk,
            "is_active": True,
            # Note: business_unit should be empty for STANDARD
            "business_unit": "",
            "parent_control": "",
            "business_process": "",
            "reference_doc": "",
        }

        response = self.client.post(url, data, follow=True)

        # Should succeed and redirect to changelist
        self.assertEqual(response.status_code, 200)

        # Verify control was created
        control = Control.objects.get(title="New Standard Access Control")
        self.assertEqual(control.control_level, ControlLevel.STANDARD)
        self.assertIsNone(control.business_unit)
        self.assertIsNone(control.parent_control)

    def test_create_local_control_with_parent(self):
        """Test creating a LOCAL control with parent through admin."""
        url = reverse("admin:controls_control_add")
        data = {
            "title": "IT Dual Signature Implementation",
            "description": "IT department implementation",
            "control_level": ControlLevel.LOCAL,
            "parent_control": self.standard_control.pk,
            "control_type": ControlType.PREVENTIVE,
            "control_nature": ControlNature.MANUAL,  # required for form vldtn
            "control_frequency": ControlFrequency.AD_HOC,
            "effectiveness": 3,
            "business_unit": self.bu_it.pk,
            "owner": self.owner_user.pk,
            "is_active": True,
            "business_process": "",
            "reference_doc": "",
        }

        response = self.client.post(url, data, follow=True)

        # Should succeed
        self.assertEqual(response.status_code, 200)

        # Verify control was created correctly
        control = Control.objects.get(title="IT Dual Signature Implementation")
        self.assertEqual(control.control_level, ControlLevel.LOCAL)
        self.assertEqual(control.parent_control, self.standard_control)
        self.assertEqual(control.business_unit, self.bu_it)

    def test_cannot_create_standard_with_business_unit(self):
        """Test that validation prevents STANDARD controls with BU."""
        url = reverse("admin:controls_control_add")
        data = {
            "title": "Invalid Standard Control",
            "description": "This should fail validation",
            "control_level": ControlLevel.STANDARD,
            "business_unit": self.bu_finance.pk,  # Invalid!
            "control_type": ControlType.PREVENTIVE,
            "control_nature": ControlNature.MANUAL,
            "control_frequency": ControlFrequency.DAILY,
            "owner": self.group_risk_user.pk,
            "is_active": True,
            "parent_control": "",
            "business_process": "",
            "reference_doc": "",
        }

        response = self.client.post(url, data)

        # Should fail with validation error
        self.assertEqual(response.status_code, 200)  # Stays on form

        # Check that the error appears in the response
        form = response.context["adminform"].form
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn(
            (
                "Standard controls should not be assigned to a specific"
                " business unit"
            ),
            form.errors["__all__"][0],
        )

    def test_cannot_create_local_without_parent(self):
        """Test that validation prevents LOCAL controls without parent."""
        url = reverse("admin:controls_control_add")
        data = {
            "title": "Invalid Local Control",
            "description": "This should fail validation",
            "control_level": ControlLevel.LOCAL,
            "parent_control": "",  # Missing parent!
            "business_unit": self.bu_finance.pk,
            "control_type": ControlType.PREVENTIVE,
            "control_nature": ControlNature.MANUAL,
            "control_frequency": ControlFrequency.DAILY,
            "owner": self.owner_user.pk,
            "is_active": True,
            "business_process": "",
            "reference_doc": "",
        }

        response = self.client.post(url, data)

        # Should fail with validation error
        self.assertEqual(response.status_code, 200)  # stays on form

        # Check validation error
        form = response.context["adminform"].form
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn(
            "Local controls must reference a parent standard control",
            form.errors["__all__"][0],
        )

    def test_cannot_create_local_without_business_unit(self):
        """Test that validation prevents LOCAL controls without BU."""
        url = reverse("admin:controls_control_add")
        data = {
            "title": "Invalid Local Control",
            "description": "This should fail validation",
            "control_level": ControlLevel.LOCAL,
            "parent_control": self.standard_control.pk,
            "business_unit": "",  # Missing BU!
            "control_type": ControlType.PREVENTIVE,
            "control_nature": ControlNature.MANUAL,
            "control_frequency": ControlFrequency.DAILY,
            "owner": self.owner_user.pk,
            "is_active": True,
            "business_process": "",
            "reference_doc": "",
        }

        response = self.client.post(url, data)

        # Should fail with validation error
        self.assertEqual(response.status_code, 200)

        # Check validation error
        form = response.context["adminform"].form
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn(
            "Local controls must belong to a business unit",
            form.errors["__all__"][0],
        )

    def test_edit_control_preserves_hierarchy(self):
        """Test editing a control maintains hierarchical relationships."""
        url = reverse(
            "admin:controls_control_change", args=[self.control_active.pk]
        )

        # Get the change form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Update description only
        data = {
            "title": self.control_active.title,
            "description": "Updated description for Finance implementation",
            "control_level": ControlLevel.LOCAL,
            "parent_control": self.standard_control.pk,
            "business_unit": self.bu_finance.pk,
            "control_type": self.control_active.control_type,
            "control_frequency": self.control_active.control_frequency,
            "control_nature": self.control_active.control_nature,
            "effectiveness": self.control_active.effectiveness,
            "owner": self.control_active.owner.pk,
            "is_active": self.control_active.is_active,
            "business_process": self.proc_ap.pk,
            "reference_doc": "",
        }

        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify update worked and hierarchy maintained
        self.control_active.refresh_from_db()
        self.assertEqual(
            self.control_active.description,
            "Updated description for Finance implementation",
        )
        self.assertEqual(
            self.control_active.parent_control, self.standard_control
        )
        self.assertEqual(self.control_active.control_level, ControlLevel.LOCAL)
