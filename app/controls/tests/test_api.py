"""
Test suite for controls API.
Tests business logic, permissions, and integration with Risks module.
Based on controls_design_specs_detailed.md.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from controls.models import (
    Control,
    ControlType,
    ControlNature,
    ControlFrequency,
)
from risks.models import Risk, RiskStatus, RiskCategory, RiskControl
from references.models import BusinessUnit, BusinessProcess, Role

User = get_user_model()

# The test suite is divided into the following logical test classes:
#  ControlTestBase: Shared setup (Roles, Users, Reference Data).
#  ControlCRUDTests: Basic lifecycle (Create, Update, Deactivate) by Role.
#  ControlQuerysetTests: Visibility rules (Risk Officer vs. Employee).
#  RiskControlLinkingTests: The critical integration with the Risks app.
#  ControlValidationTests: Business rule enforcement.
#  ControlFilterTests: Search and filtering capabilities.

# --- Helper Functions ---


def create_user(email, password, role, business_unit):
    return User.objects.create_user(
        email=email,
        password=password,
        role=role,
        business_unit=business_unit,
    )


def control_list_url():
    return reverse("controls:control-list")


def control_detail_url(control_id):
    return reverse("controls:control-detail", args=[control_id])


def risk_action_url(risk_id, action):
    # Used for linking tests (endpoints reside in Risks app)
    return reverse(f"risks:risk-{action}", args=[risk_id])


# --- Base Test Class ---


class ControlTestBase(TestCase):
    """Base setup for Control tests."""

    def setUp(self):
        self.client = APIClient()

        # --- Roles ---
        self.role_ro, _ = Role.objects.get_or_create(name="Risk Officer")
        self.role_mgr, _ = Role.objects.get_or_create(name="Manager")
        self.role_emp, _ = Role.objects.get_or_create(name="Employee")

        # --- Reference Data ---
        self.bu_finance, _ = BusinessUnit.objects.get_or_create(name="Finance")
        self.bu_it, _ = BusinessUnit.objects.get_or_create(name="IT")
        self.process_ap = BusinessProcess.objects.create(
            name="Accounts Payable"
        )
        self.category = RiskCategory.objects.create(name="Financial Risk")

        # --- Users ---
        self.risk_officer = create_user(
            "ro@example.com", "passt123", self.role_ro, self.bu_finance
        )
        self.manager = create_user(
            "mgr@example.com", "passt123", self.role_mgr, self.bu_finance
        )
        self.employee = create_user(
            "emp@example.com", "passt123", self.role_emp, self.bu_finance
        )
        # Cross-BU user
        self.it_manager = create_user(
            "it_mgr@example.com", "passt123", self.role_mgr, self.bu_it
        )

        # --- Controls (Seed Data) ---
        self.control_active = Control.objects.create(
            title="Dual Signature",
            description="Checks > $10k require 2 signatures",
            control_type=ControlType.PREVENTIVE,
            control_nature=ControlNature.MANUAL,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=5,
            business_unit=self.bu_finance,
            business_process=self.process_ap,
            owner=self.manager,
            is_active=True,
            created_by=self.risk_officer,
        )

        self.control_inactive = Control.objects.create(
            title="Legacy Log",
            description="Deprecated manual log",
            control_type=ControlType.DETECTIVE,
            business_unit=self.bu_finance,
            owner=self.manager,
            is_active=False,
            created_by=self.risk_officer,
        )

        # --- Risks (For Linking Tests) ---
        self.risk_draft = Risk.objects.create(
            title="Draft Risk",
            description="Test Risk",
            status=RiskStatus.DRAFT,
            risk_category=self.category,
            business_unit=self.bu_finance,
            owner=self.manager,
            created_by=self.manager,
        )

        self.risk_active = Risk.objects.create(
            title="Active Risk",
            description="Live Risk",
            status=RiskStatus.ACTIVE,
            risk_category=self.category,
            business_unit=self.bu_finance,
            owner=self.manager,
            created_by=self.risk_officer,
            # Active risks technically need other fields set,
            # simplified for linking tests
        )


# --- CRUD Tests ---


class ControlCRUDTests(ControlTestBase):
    """
    FR-1.1: Create Control
    FR-1.4: Update Control
    FR-1.5: Deactivate Control
    """

    def test_create_control_as_risk_officer(self):
        """Test Risk Officer can create a new control in the library."""
        self.client.force_authenticate(user=self.risk_officer)
        payload = {
            "title": "New Automated Recon",
            "description": "Daily auto-reconciliation of GL",
            "control_type": ControlType.DETECTIVE,
            "control_nature": ControlNature.AUTOMATED,
            "control_frequency": ControlFrequency.DAILY,
            "effectiveness": 4,
            "business_unit": self.bu_finance.id,
            "owner": self.manager.id,
            "reference_doc": "http://policy/123",
        }
        res = self.client.post(control_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        control = Control.objects.get(id=res.data["id"])
        self.assertEqual(control.title, "New Automated Recon")
        self.assertTrue(control.is_active)  # Default is active
        self.assertEqual(control.created_by, self.risk_officer)

    def test_create_control_as_manager_fails(self):
        """Test Manager CANNOT create controls (Library managed centrally)."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "title": "Manager Control",
            "description": "Should fail",
            "control_frequency": ControlFrequency.DAILY,  # required field
            "business_unit": self.bu_finance.id,
            "owner": self.manager.id,
        }
        res = self.client.post(control_list_url(), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_control_as_risk_officer(self):
        """Test Risk Officer can update control attributes."""
        self.client.force_authenticate(user=self.risk_officer)
        url = control_detail_url(self.control_active.id)
        res = self.client.patch(url, {"effectiveness": 3})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.control_active.refresh_from_db()
        self.assertEqual(self.control_active.effectiveness, 3)

    def test_deactivate_control(self):
        """Test Risk Officer can deactivate a control (Soft Delete)."""
        self.client.force_authenticate(user=self.risk_officer)
        url = control_detail_url(self.control_active.id)
        # We use PATCH to set is_active=False
        res = self.client.patch(url, {"is_active": False})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.control_active.refresh_from_db()
        self.assertFalse(self.control_active.is_active)

    def test_delete_control_fails_for_all(self):
        """Test DELETE method is strictly forbidden (use deactivation)."""
        self.client.force_authenticate(user=self.risk_officer)
        url = control_detail_url(self.control_active.id)
        res = self.client.delete(url)

        # Depending on implementation preference: 405 Method Not Allowed or
        #  403 Forbidden
        # Usually 405 if we remove the 'destroy' mixin, 403 if we permission
        #  it out.
        # Assuming we restrict permissions or don't implement destroy()
        self.assertIn(
            res.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN],
        )


# --- Queryset Visibility Tests ---


class ControlQuerysetTests(ControlTestBase):
    """
    FR-1.2: View Control Library
    Tests visibility rules for different roles.
    """

    def test_risk_officer_sees_all_controls(self):
        """Risk Officer sees both active and inactive controls."""
        self.client.force_authenticate(user=self.risk_officer)
        res = self.client.get(control_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_active.id, ids)
        self.assertIn(self.control_inactive.id, ids)

    def test_manager_sees_only_active_controls(self):
        """Manager sees only active controls by default."""
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(control_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_active.id, ids)
        self.assertNotIn(self.control_inactive.id, ids)

    def test_employee_sees_only_active_controls(self):
        """Employee sees only active controls."""
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(control_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_active.id, ids)
        self.assertNotIn(self.control_inactive.id, ids)


# --- Linking Tests (Integration with Risks) ---


class RiskControlLinkingTests(ControlTestBase):
    """
    FR-2.1: Link Control to Risk
    FR-2.3: Unlink Control from Risk
    These test endpoints on the Risks API (`/api/risks/{id}/link-to-control/`).
    """

    def test_risk_officer_can_link_control_to_risk(self):
        """Test linking an active control to a DRAFT risk."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "link-to-control")
        payload = {
            "control_id": self.control_active.id,
            "notes": "Primary mitigation for fraud",
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify Link in DB
        self.assertTrue(
            RiskControl.objects.filter(
                risk=self.risk_draft, control=self.control_active
            ).exists()
        )

        # Verify Notes
        link = RiskControl.objects.get(
            risk=self.risk_draft, control=self.control_active
        )
        self.assertEqual(link.notes, "Primary mitigation for fraud")

    def test_link_inactive_control_fails(self):
        """Test cannot link an INACTIVE control to a risk."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "link-to-control")
        payload = {"control_id": self.control_inactive.id}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactive", str(res.data).lower())

    def test_link_duplicate_control_fails(self):
        """Test cannot link the same control twice."""
        # Setup: Link once
        RiskControl.objects.create(
            risk=self.risk_draft,
            control=self.control_active,
            linked_by=self.risk_officer,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "link-to-control")
        res = self.client.post(url, {"control_id": self.control_active.id})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already linked", str(res.data).lower())

    def test_unlink_control_from_risk(self):
        """Test unlinking a control."""
        # Setup
        RiskControl.objects.create(
            risk=self.risk_draft,
            control=self.control_active,
            linked_by=self.risk_officer,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "unlink-from-control")
        res = self.client.post(url, {"control_id": self.control_active.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(
            RiskControl.objects.filter(
                risk=self.risk_draft, control=self.control_active
            ).exists()
        )


# --- Validation Logic Tests ---


class ControlValidationTests(ControlTestBase):
    """
    FR-1.5 (Business Rules): Constraints on modification/deactivation.
    """

    def setUp(self):
        super().setUp()
        # Create a link to an ACTIVE risk
        RiskControl.objects.create(
            risk=self.risk_active,
            control=self.control_active,
            linked_by=self.risk_officer,
        )

    def test_cannot_deactivate_control_linked_to_active_risk(self):
        """Test deactivation fails if control is used in an ACTIVE risk."""
        self.client.force_authenticate(user=self.risk_officer)
        url = control_detail_url(self.control_active.id)

        # Try to deactivate
        res = self.client.patch(url, {"is_active": False})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("linked to active risks", str(res.data).lower())

        # Verify state did not change
        self.control_active.refresh_from_db()
        self.assertTrue(self.control_active.is_active)

    def test_can_update_description_of_linked_control(self):
        """Test non-structural updates (description) allowed even if linked."""
        self.client.force_authenticate(user=self.risk_officer)
        url = control_detail_url(self.control_active.id)

        res = self.client.patch(url, {"description": "Updated text"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.control_active.refresh_from_db()
        self.assertEqual(self.control_active.description, "Updated text")


# --- Filter & Search Tests ---


class ControlFilterTests(ControlTestBase):
    """
    FR-1.2: Filter/Search capabilities.
    """

    def test_filter_by_control_type(self):
        self.client.force_authenticate(user=self.risk_officer)
        url = f"{control_list_url()}?control_type={ControlType.DETECTIVE}"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_inactive.id, ids)
        self.assertNotIn(self.control_active.id, ids)

    def test_filter_by_business_unit(self):
        # Create control in IT
        ctrl_it = Control.objects.create(
            title="IT Control",
            business_unit=self.bu_it,
            owner=self.it_manager,
            created_by=self.risk_officer,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = f"{control_list_url()}?business_unit={self.bu_finance.id}"
        res = self.client.get(url)

        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_active.id, ids)
        self.assertNotIn(ctrl_it.id, ids)

    def test_search_by_text(self):
        self.client.force_authenticate(user=self.risk_officer)
        url = f"{control_list_url()}?search=Signature"
        res = self.client.get(url)

        ids = [c["id"] for c in res.data["results"]]
        self.assertIn(self.control_active.id, ids)
        self.assertNotIn(self.control_inactive.id, ids)
