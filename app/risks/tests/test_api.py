"""
Test suite for risks API.
Tests business logic, workflows, permissions, and API endpoints.
Following the pattern from measures/test_api.py.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from risks.models import Risk, RiskStatus, RiskCategory
from incidents.models import Incident, IncidentStatusRef
from measures.models import Measure, MeasureStatusRef
from references.models import (
    BaselEventType,
    BusinessUnit,
    BusinessProcess,
    Product,
    Role,
)

User = get_user_model()

# All test classes inside this file:
#  RiskTestBase - shared setup (users, roles, etc.)
#  RiskQuerysetTests - data segregation by role
#  RiskCRUDTests - create/delete operations with permissions
#  RiskFieldLevelSecurityTests - Dynamic field editing based on status & role
#  RiskWorkflowTests - state machine transitions
#  RiskBaselWorkflowTests - Basel event type validation throughout workflow
#  RiskLinkingTests - relationships - linking/unlinking incidents and measures
#  RiskValidationTests - business rules validation
#  RiskFilteringTests - query parameter filtering and search
#  RiskResponseFormatTests - serializer output and structure
#  RiskIntegrationTests - end-to-end workflows

# --- Helper Functions ---


def create_user(email, password, role, business_unit, manager=None):
    """Helper to create users with role and business unit."""
    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        business_unit=business_unit,
        manager=manager,
    )
    return user


def risk_list_url():
    """Return URL for risk list endpoint."""
    return reverse("risks:risk-list")


def risk_detail_url(risk_id):
    """Return URL for risk detail endpoint."""
    return reverse("risks:risk-detail", args=[risk_id])


def risk_action_url(risk_id, action):
    """Return URL for risk action endpoint."""
    return reverse(f"risks:risk-{action}", args=[risk_id])


# --- Base Test Class ---


class RiskTestBase(TestCase):
    """Base test class with common setup for all risk tests."""

    def setUp(self):
        self.client = APIClient()

        # --- Create roles ---
        self.role_mgr, _ = Role.objects.get_or_create(name="Manager")
        self.role_risk, _ = Role.objects.get_or_create(name="Risk Officer")
        self.role_emp, _ = Role.objects.get_or_create(name="Employee")

        # --- Create business units ---
        self.bu_ops, _ = BusinessUnit.objects.get_or_create(name="Operations")
        self.bu_risk, _ = BusinessUnit.objects.get_or_create(
            name="Risk Management"
        )

        # --- Create Basel event types ---
        self.basel_internal_fraud = BaselEventType.objects.create(
            name="Internal Fraud", description="IF"
        )
        self.basel_external_fraud = BaselEventType.objects.create(
            name="External Fraud", description="EF"
        )
        self.basel_system_failure = BaselEventType.objects.create(
            name="Business Disruption and System Failures", description="BDSF"
        )

        # --- Create risk categories with Basel mappings ---
        self.fraud_category = RiskCategory.objects.create(name="Fraud Risk")
        self.fraud_category.basel_event_types.add(
            self.basel_internal_fraud, self.basel_external_fraud
        )

        self.it_category = RiskCategory.objects.create(
            name="IT/Data/Cyber Risk"
        )
        self.it_category.basel_event_types.add(
            self.basel_system_failure, self.basel_external_fraud
        )

        self.legal_category = RiskCategory.objects.create(
            name="Legal & Compliance Risk"
        )
        self.legal_category.basel_event_types.add(self.basel_internal_fraud)

        # --- Create context references ---
        self.process = BusinessProcess.objects.create(
            name="Payment Processing"
        )
        self.product = Product.objects.create(name="Credit Card")

        # --- Create users ---
        self.risk_officer = create_user(
            "risk@example.com", "tstpw123", self.role_risk, self.bu_ops
        )
        self.manager = create_user(
            "manager@example.com", "tstpw123", self.role_mgr, self.bu_ops
        )
        self.owner_user = create_user(
            "owner@example.com",
            "tstpw123",
            self.role_mgr,
            self.bu_ops,
        )
        self.other_manager = create_user(
            "other_mgr@example.com",
            "tstpw123",
            self.role_mgr,
            self.bu_ops,
        )
        self.employee = create_user(
            "employee@example.com",
            "tstpw123",
            self.role_emp,
            self.bu_ops,
            self.manager,
        )

        # --- Create test incidents for linking ---
        inc_status, _ = IncidentStatusRef.objects.get_or_create(
            code="DRAFT", defaults={"name": "Draft"}
        )
        self.incident = Incident.objects.create(
            title="Test Incident for Linking",
            created_by=self.manager,
            status=inc_status,
            business_unit=self.bu_ops,
        )

        # --- Create test measures for linking ---
        measure_status, _ = MeasureStatusRef.objects.get_or_create(
            code="OPEN", defaults={"name": "Open"}
        )
        self.measure = Measure.objects.create(
            description="Test Measure for Linking",
            created_by=self.manager,
            responsible=self.employee,
            status=measure_status,
        )

        # --- Create test risks in different statuses ---
        self.risk_draft = Risk.objects.create(
            title="Draft Risk - Fraud Detection Gap",
            description="Inadequate fraud detection in payment processing",
            risk_category=self.fraud_category,
            business_unit=self.bu_ops,
            business_process=self.process,
            product=self.product,
            status=RiskStatus.DRAFT,
            created_by=self.manager,
            owner=self.owner_user,
            inherent_likelihood=4,
            inherent_impact=3,
        )

        self.risk_assessed = Risk.objects.create(
            title="Assessed Risk - System Outage",
            description="Risk of critical system failure during peak hours",
            risk_category=self.it_category,
            basel_event_type=self.basel_system_failure,
            business_unit=self.bu_ops,
            business_process=self.process,
            status=RiskStatus.ASSESSED,
            created_by=self.manager,
            owner=self.owner_user,
            inherent_likelihood=5,
            inherent_impact=4,
            residual_likelihood=2,
            residual_impact=3,
            submitted_for_review_at=timezone.now(),
            submitted_by=self.manager,
        )

        self.risk_active = Risk.objects.create(
            title="Active Risk - Data Breach",
            description="Risk of unauthorized data access",
            risk_category=self.it_category,
            basel_event_type=self.basel_external_fraud,
            business_unit=self.bu_ops,
            status=RiskStatus.ACTIVE,
            created_by=self.risk_officer,
            owner=self.owner_user,
            inherent_likelihood=4,
            inherent_impact=5,
            residual_likelihood=2,
            residual_impact=2,
            validated_at=timezone.now(),
            validated_by=self.risk_officer,
        )

        self.risk_retired = Risk.objects.create(
            title="Retired Risk - Legacy System",
            description="Risk from decommissioned legacy system",
            risk_category=self.it_category,
            basel_event_type=self.basel_system_failure,
            business_unit=self.bu_ops,
            status=RiskStatus.RETIRED,
            created_by=self.risk_officer,
            owner=self.owner_user,
            inherent_likelihood=3,
            inherent_impact=3,
            residual_likelihood=1,
            residual_impact=1,
            retirement_reason=(
                "System decommissioned after migration to cloud platform"
            ),
        )

        # Risk in other business unit (for access control tests)
        self.risk_other_bu = Risk.objects.create(
            title="Other BU Risk",
            description="Risk in different business unit",
            risk_category=self.fraud_category,
            business_unit=self.bu_risk,
            status=RiskStatus.DRAFT,
            created_by=create_user(
                "other_bu@example.com",
                "tstpw123",
                self.role_mgr,
                self.bu_risk,
            ),
            owner=create_user(
                "other_bu_owner@example.com",
                "tstpw123",
                self.role_mgr,
                self.bu_risk,
            ),
        )


# --- Queryset and Data Segregation Tests ---


class RiskQuerysetTests(RiskTestBase):
    """Test data segregation and queryset filtering."""

    def test_get_queryset_manager_sees_own_bu_risks(self):
        """Test Manager can see risks in their business unit."""
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(risk_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        risk_ids = [r["id"] for r in res.data["results"]]

        # Should see risks in bu_ops
        self.assertIn(self.risk_draft.id, risk_ids)
        self.assertIn(self.risk_assessed.id, risk_ids)
        self.assertIn(self.risk_active.id, risk_ids)

        # Should NOT see risks in bu_risk
        self.assertNotIn(self.risk_other_bu.id, risk_ids)

    def test_get_queryset_risk_officer_sees_all_in_bu(self):
        """Test Risk Officer can see all risks in their BU."""
        self.client.force_authenticate(user=self.risk_officer)
        res = self.client.get(risk_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        risk_ids = [r["id"] for r in res.data["results"]]

        # Should see all risks in bu_ops
        self.assertIn(self.risk_draft.id, risk_ids)
        self.assertIn(self.risk_assessed.id, risk_ids)
        self.assertIn(self.risk_active.id, risk_ids)
        self.assertIn(self.risk_retired.id, risk_ids)

        # Should NOT see risks in bu_risk
        self.assertNotIn(self.risk_other_bu.id, risk_ids)

    def test_risk_officer_cannot_see_other_bu_risks(self):
        """Test Risk Officer cannot access risks from other BUs."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_other_bu.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_sees_limited_risks(self):
        """Test Employee has limited visibility."""
        self.client.force_authenticate(user=self.employee)
        res = self.client.get(risk_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Employee should have minimal access
        # ! (exact rules depend on your implementation - see BRD! doc)

    ### Employee

    # **Definition:** General bank employee with read-only access to the risk register.

    # **Permissions:**
    # - View risks related to their business unit
    # - View public risk reports and dashboards
    # - Suggest new risks to their Manager (via email/chat, not in-app)

    # **Responsibilities:**
    # - Report risk-related observations to their Manager
    # - Participate in RCSA workshops when invited
    # - Follow risk mitigation procedures

    def test_unauthenticated_access_fails(self):
        """Test that unauthenticated requests are rejected."""
        res = self.client.get(risk_list_url())
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# --- CRUD Tests ---


class RiskCRUDTests(RiskTestBase):
    """Test basic CRUD operations and permissions."""

    def test_create_risk_as_manager(self):
        """Test Manager can create a new risk in DRAFT status."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "title": "New Risk - Payment Fraud",
            "description": "Risk of fraudulent payment transactions",
            "risk_category": self.fraud_category.id,
            "business_unit": self.bu_ops.id,
            "business_process": self.process.id,
            "owner": self.owner_user.id,
        }
        res = self.client.post(risk_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        risk = Risk.objects.get(id=res.data["id"])
        self.assertEqual(risk.status, RiskStatus.DRAFT)
        self.assertEqual(risk.created_by, self.manager)
        self.assertEqual(risk.owner, self.owner_user)
        self.assertEqual(risk.risk_category, self.fraud_category)
        self.assertIsNone(risk.basel_event_type)  # Optional in DRAFT

    def test_create_risk_as_risk_officer(self):
        """Test Risk Officer can create a new risk."""
        self.client.force_authenticate(user=self.risk_officer)
        payload = {
            "title": "New Risk - Cyber Attack",
            "description": "Risk of targeted cyber attack",
            "risk_category": self.it_category.id,
            "business_unit": self.bu_ops.id,
            "owner": self.owner_user.id,
        }
        res = self.client.post(risk_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        risk = Risk.objects.get(id=res.data["id"])
        self.assertEqual(risk.status, RiskStatus.DRAFT)
        self.assertEqual(risk.created_by, self.risk_officer)

    def test_create_risk_as_employee_fails(self):
        """Test Employee cannot create risks."""
        self.client.force_authenticate(user=self.employee)
        payload = {
            "title": "This Should Fail",
            "description": "Employee has no permission",
            "risk_category": self.fraud_category.id,
            "business_unit": self.bu_ops.id,
            "owner": self.owner_user.id,
        }
        res = self.client.post(risk_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Manager or Risk Officer", str(res.data["error"]))

    def test_create_risk_without_title_fails(self):
        """Test creating risk without title fails validation."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "description": "Missing title",
            "risk_category": self.fraud_category.id,
            "business_unit": self.bu_ops.id,
            "owner": self.owner_user.id,
        }
        res = self.client.post(risk_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", str(res.data))

    def test_create_risk_without_category_fails(self):
        """Test creating risk without risk_category fails."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "title": "Test Risk",
            "description": "Missing category",
            "business_unit": self.bu_ops.id,
            "owner": self.owner_user.id,
        }
        res = self.client.post(risk_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("risk_category", str(res.data))

    def test_delete_draft_risk_as_creator_succeeds(self):
        """Test creator can delete a risk in DRAFT status."""
        self.client.force_authenticate(user=self.manager)
        url = risk_detail_url(self.risk_draft.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Risk.objects.filter(id=self.risk_draft.id).exists())

    def test_delete_draft_risk_as_risk_officer_succeeds(self):
        """Test Risk Officer can delete a risk in DRAFT status."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_draft.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Risk.objects.filter(id=self.risk_draft.id).exists())

    def test_delete_active_risk_fails(self):
        """Test cannot delete risk that is not in DRAFT status."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_active.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Risk.objects.filter(id=self.risk_active.id).exists())

    def test_delete_risk_as_unrelated_user_fails(self):
        """Test other users cannot delete risks."""
        self.client.force_authenticate(user=self.other_manager)
        url = risk_detail_url(self.risk_draft.id)
        res = self.client.delete(url)

        # Should be blocked by queryset filter (404)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Risk.objects.filter(id=self.risk_draft.id).exists())


# --- Field-Level Security Tests ---


class RiskFieldLevelSecurityTests(RiskTestBase):
    """Test dynamic field editing based on status and role."""

    def test_manager_can_edit_inherent_scores_in_draft(self):
        """Test Manager can edit inherent scores in DRAFT status."""
        self.client.force_authenticate(user=self.manager)
        url = risk_detail_url(self.risk_draft.id)
        res = self.client.patch(
            url, {"inherent_likelihood": 5, "inherent_impact": 5}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_draft.refresh_from_db()
        self.assertEqual(self.risk_draft.inherent_likelihood, 5)
        self.assertEqual(self.risk_draft.inherent_impact, 5)

    def test_manager_can_edit_description_in_draft(self):
        """Test Manager can edit description in DRAFT status."""
        self.client.force_authenticate(user=self.manager)
        url = risk_detail_url(self.risk_draft.id)
        new_desc = "Updated risk description with more details"
        res = self.client.patch(url, {"description": new_desc})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_draft.refresh_from_db()
        self.assertEqual(self.risk_draft.description, new_desc)

    def test_risk_officer_can_edit_residual_scores_in_assessed(self):
        """Test Risk Officer can edit residual scores in ASSESSED status."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_assessed.id)
        res = self.client.patch(
            url, {"residual_likelihood": 1, "residual_impact": 2}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_assessed.refresh_from_db()
        self.assertEqual(self.risk_assessed.residual_likelihood, 1)
        self.assertEqual(self.risk_assessed.residual_impact, 2)

    def test_manager_cannot_edit_residual_scores_in_assessed(self):
        """Test Manager cannot edit residual scores in ASSESSED status."""
        self.client.force_authenticate(user=self.manager)
        url = risk_detail_url(self.risk_assessed.id)
        original_residual_likelihood = self.risk_assessed.residual_likelihood
        res = self.client.patch(url, {"residual_likelihood": 5})

        # Request succeeds but field is read-only
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_assessed.refresh_from_db()
        self.assertEqual(
            self.risk_assessed.residual_likelihood,
            original_residual_likelihood,
        )

    def test_cannot_edit_active_risk(self):
        """Test ACTIVE risks are read-only for all users."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_active.id)
        original_desc = self.risk_active.description
        res = self.client.patch(url, {"description": "Try to edit"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_active.refresh_from_db()
        self.assertEqual(self.risk_active.description, original_desc)

    def test_cannot_edit_retired_risk(self):
        """Test RETIRED risks are read-only."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_retired.id)
        original_title = self.risk_retired.title
        res = self.client.patch(url, {"title": "Try to edit"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_retired.refresh_from_db()
        self.assertEqual(self.risk_retired.title, original_title)


# --- Workflow Transition Tests ---


class RiskWorkflowTests(RiskTestBase):
    """Test state machine transitions and workflow actions."""

    def test_manager_can_submit_draft_risk_for_review(self):
        """Test Manager can move DRAFT → ASSESSED."""
        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_draft.refresh_from_db()
        self.assertEqual(self.risk_draft.status, RiskStatus.ASSESSED)
        self.assertIsNotNone(self.risk_draft.submitted_for_review_at)
        self.assertEqual(self.risk_draft.submitted_by, self.manager)

    def test_risk_officer_can_submit_draft_risk(self):
        """Test Risk Officer can submit DRAFT → ASSESSED."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_draft.refresh_from_db()
        self.assertEqual(self.risk_draft.status, RiskStatus.ASSESSED)

    def test_employee_cannot_submit_risk_for_review(self):
        """Test Employee cannot submit risks."""
        self.client.force_authenticate(user=self.employee)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        # Should fail due to queryset filtering or permission
        self.assertIn(
            res.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_submit_without_inherent_scores_fails(self):
        """Test submission fails without inherent risk scores."""
        self.risk_draft.inherent_likelihood = None
        self.risk_draft.inherent_impact = None
        self.risk_draft.save()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Inherent risk scores required", str(res.data))

    def test_submit_without_risk_category_fails(self):
        """Test submission fails without risk category."""
        # Create risk without category (using direct DB to bypass validation)
        risk_no_cat = Risk.objects.create(
            title="Risk Without Category",
            description="Test",
            risk_category=self.fraud_category,  # Will clear below
            status=RiskStatus.DRAFT,
            created_by=self.manager,
            owner=self.manager,
            business_unit=self.bu_ops,
            inherent_likelihood=3,
            inherent_impact=3,
        )
        # Clear category
        Risk.objects.filter(id=risk_no_cat.id).update(risk_category=None)
        risk_no_cat.refresh_from_db()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(risk_no_cat.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Risk category must be selected", str(res.data))

    def test_submit_with_only_likelihood_fails(self):
        """Test submission fails with partial inherent scores."""
        self.risk_draft.inherent_likelihood = 4
        self.risk_draft.inherent_impact = None
        self.risk_draft.save()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_risk_officer_can_approve_assessed_risk(self):
        """Test Risk Officer can move ASSESSED → ACTIVE."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_assessed.refresh_from_db()
        self.assertEqual(self.risk_assessed.status, RiskStatus.ACTIVE)
        self.assertIsNotNone(self.risk_assessed.validated_at)
        self.assertEqual(self.risk_assessed.validated_by, self.risk_officer)

    def test_manager_cannot_approve_risk(self):
        """Test Manager cannot approve risks."""
        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Only Risk Officers can approve", str(res.data))

    def test_approve_without_residual_scores_fails(self):
        """Test approval fails without residual risk scores."""
        self.risk_assessed.residual_likelihood = None
        self.risk_assessed.residual_impact = None
        self.risk_assessed.save()

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Residual risk scores required", str(res.data))

    def test_approve_without_basel_type_fails(self):
        """Test approval fails without Basel event type."""
        self.risk_assessed.basel_event_type = None
        self.risk_assessed.save()

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Basel event type must be selected", str(res.data))

    def test_approve_with_residual_greater_than_inherent_fails(self):
        """Test approval fails if residual risk > inherent risk."""
        self.risk_assessed.inherent_likelihood = 2
        self.risk_assessed.inherent_impact = 2  # Inherent = 4
        self.risk_assessed.residual_likelihood = 3
        self.risk_assessed.residual_impact = 3  # Residual = 9
        self.risk_assessed.save()

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Residual risk", str(res.data))
        self.assertIn("cannot exceed", str(res.data))

    # ! Direct approval from DRAFT to ACTIVE should be allowed (workshop case)
    # def test_approve_from_draft_fails(self):
    #     """Test cannot approve directly from DRAFT status."""
    #     self.client.force_authenticate(user=self.risk_officer)
    #     url = risk_action_url(self.risk_draft.id, "approve")
    #     res = self.client.post(url)

    #     self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_risk_officer_can_send_back_for_revision(self):
        """Test Risk Officer can move ASSESSED → DRAFT."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "send-back")
        payload = {"reason": "Need more detail on inherent impact assessment"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_assessed.refresh_from_db()
        self.assertEqual(self.risk_assessed.status, RiskStatus.DRAFT)
        self.assertIn(payload["reason"], self.risk_assessed.notes)

    def test_send_back_without_reason_fails(self):
        """Test send back requires reason payload."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "send-back")
        res = self.client.post(url, {})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", str(res.data))

    def test_manager_cannot_send_back_risk(self):
        """Test Manager cannot send back risks."""
        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_assessed.id, "send-back")
        payload = {"reason": "Test"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_risk_officer_can_request_reassessment(self):
        """Test Risk Officer can move ACTIVE → ASSESSED for reassessment."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_active.id, "request-reassessment")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_active.refresh_from_db()
        self.assertEqual(self.risk_active.status, RiskStatus.ASSESSED)
        self.assertIsNotNone(self.risk_active.submitted_for_review_at)

    def test_manager_cannot_request_reassessment(self):
        """Test Manager cannot request reassessment."""
        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_active.id, "request-reassessment")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_risk_officer_can_retire_active_risk(self):
        """Test Risk Officer can move ACTIVE → RETIRED."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_active.id, "retire")
        reason = (
            "Business process discontinued after merger with another division"
        )
        payload = {"reason": reason}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_active.refresh_from_db()
        self.assertEqual(self.risk_active.status, RiskStatus.RETIRED)
        self.assertEqual(self.risk_active.retirement_reason, reason)

    def test_risk_officer_can_retire_assessed_risk(self):
        """Test Risk Officer can retire risk in ASSESSED status."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "retire")
        reason = "Risk no longer applicable after policy change"
        payload = {"reason": reason}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_assessed.refresh_from_db()
        self.assertEqual(self.risk_assessed.status, RiskStatus.RETIRED)

    def test_retire_without_reason_fails(self):
        """Test retirement requires reason payload."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_active.id, "retire")
        res = self.client.post(url, {})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", str(res.data))

    def test_retire_with_short_reason_fails(self):
        """Test retirement requires substantial reason (20+ chars)."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_active.id, "retire")
        payload = {"reason": "Too short"}  # Less than 20 chars
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least 20 characters", str(res.data))

    def test_manager_cannot_retire_risk(self):
        """Test Manager cannot retire risks."""
        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_active.id, "retire")
        payload = {
            "reason": "This should fail regardless of reason length here"
        }
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_retire_draft_risk(self):
        """Test cannot retire risk in DRAFT status."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_draft.id, "retire")
        payload = {"reason": "Valid reason with enough characters here"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Transition from 'DRAFT' to 'RETIRED' is not defined",
            str(res.data),
        )


# --- Basel Event Type Workflow Tests ---


class RiskBaselWorkflowTests(RiskTestBase):
    """Test Basel event type workflow validation."""

    def test_can_submit_without_basel_type(self):
        """Test risk can be submitted without Basel type (opt in DRAFT)."""
        self.risk_draft.basel_event_type = None
        self.risk_draft.save()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.risk_draft.refresh_from_db()
        self.assertEqual(self.risk_draft.status, RiskStatus.ASSESSED)

    def test_submit_with_valid_basel_type_succeeds(self):
        """Test submission with valid Basel type succeeds."""
        self.risk_draft.basel_event_type = self.basel_internal_fraud
        self.risk_draft.save()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_submit_with_invalid_basel_type_fails(self):
        """Test submission fails with Basel type not mapped to category."""
        # fraud_category allows internal/external fraud, NOT system_failure
        self.risk_draft.basel_event_type = self.basel_system_failure
        self.risk_draft.save()

        self.client.force_authenticate(user=self.manager)
        url = risk_action_url(self.risk_draft.id, "submit-for-review")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not valid for risk category", str(res.data))

    def test_cannot_approve_without_basel_type(self):
        """Test approval requires Basel type to be set."""
        self.risk_assessed.basel_event_type = None
        self.risk_assessed.save()

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Basel event type must be selected", str(res.data))

    def test_approve_validates_basel_type_consistency(self):
        """Test approval validates Basel type is valid for category."""
        # Set invalid Basel type
        self.risk_assessed.basel_event_type = self.basel_internal_fraud
        # it_category doesn't allow internal_fraud
        self.risk_assessed.save()

        self.client.force_authenticate(user=self.risk_officer)
        url = risk_action_url(self.risk_assessed.id, "approve")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not valid for risk category", str(res.data))

    def test_patch_risk_with_invalid_basel_type_fails(self):
        """Test PATCH with invalid Basel type fails validation."""
        self.client.force_authenticate(user=self.risk_officer)
        url = risk_detail_url(self.risk_assessed.id)
        # Try to set Basel type not allowed for it_category
        res = self.client.patch(
            url, {"basel_event_type": self.basel_internal_fraud.id}
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not valid for risk category", str(res.data))
