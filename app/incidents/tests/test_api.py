"""
Tests for incidents API.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from incidents.models import Incident, IncidentStatusRef, AllowedTransition
from references.models import Role, BusinessUnit

from incidents.serializers import (
    IncidentListSerializer,
    IncidentDetailSerializer,
)


INCIDENTS_LIST_URL = reverse("incidents:incident-list")
# INCIDENTS_CREATE_URL = reverse("incidents:incident-create")


def detail_url(incident_id):
    """Create and return an incident detail URL."""
    return reverse("incidents:incident-detail", args=[incident_id])


def create_incident(user, **params):
    """Create and return a sample incident (helper function)."""
    defaults = {
        "title": "Sample incident title",
        "description": "Sample description",
        "gross_loss_amount": Decimal("999.99"),
        "currency_code": "USD",
    }
    defaults.update(params)

    incident = Incident.objects.create(created_by=user, **defaults)
    return incident


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicIncidentApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIncidentApiTests(TestCase):
    """Test authenticated API requests.
    Cover basic CRUD & Filtering.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="test@example.com", password="testp123")

        self.client.force_authenticate(user=self.user)

        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.status_pending = IncidentStatusRef.objects.create(
            code="PENDING_REVIEW", name="Pending"
        )

    def test_retrieve_incidents(self):
        """Test retrieving a list of incidents."""
        create_incident(user=self.user, status=self.status_draft)
        create_incident(user=self.user, status=self.status_pending)

        res = self.client.get(INCIDENTS_LIST_URL)

        incidents = Incident.objects.all().order_by("-id")
        serializer = IncidentListSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_list_limited_to_user(self):
        """Test list of incidents is limited to authenticated user only."""
        other_user = create_user(email="other@example.com", password="test123")
        create_incident(user=other_user, status=self.status_draft)
        create_incident(user=self.user, status=self.status_pending)

        res = self.client.get(INCIDENTS_LIST_URL)

        incidents = Incident.objects.filter(created_by=self.user)
        serializer = IncidentListSerializer(incidents, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_incidents_are_ordered_by_newest_first(self):
        """Test incidents are ordered by ID descending."""
        incident1 = create_incident(user=self.user, status=self.status_draft)
        incident2 = create_incident(user=self.user, status=self.status_draft)

        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.data[0]["id"], incident2.id)
        self.assertEqual(res.data[1]["id"], incident1.id)

    def test_filter_incidents_by_status(self):
        """Test filtering incidents by their status."""
        incident_draft = create_incident(
            user=self.user, status=self.status_draft
        )
        create_incident(user=self.user, status=self.status_pending)

        # Filter for DRAFT incidents
        res = self.client.get(INCIDENTS_LIST_URL, {"status__code": "DRAFT"})
        serializer_draft = IncidentListSerializer(incident_draft)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], serializer_draft.data["id"])

    def test_filter_incidents_by_near_miss(self):
        """Test filtering incidents by the near_miss flag."""
        incident1 = create_incident(
            user=self.user, status=self.status_draft, near_miss=True
        )
        incident2 = create_incident(
            user=self.user, status=self.status_draft, near_miss=False
        )

        res_true = self.client.get(INCIDENTS_LIST_URL, {"near_miss": "true"})
        res_false = self.client.get(INCIDENTS_LIST_URL, {"near_miss": "false"})

        self.assertEqual(len(res_true.data), 1)
        self.assertEqual(res_true.data[0]["id"], incident1.id)
        self.assertEqual(len(res_false.data), 1)
        self.assertEqual(res_false.data[0]["id"], incident2.id)

    def test_get_incident_detail(self):
        """Test get incident detail."""
        incident = create_incident(user=self.user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.get(url)

        serializer = IncidentDetailSerializer(incident)
        self.assertEqual(res.data, serializer.data)

    def test_create_incident(self):
        """Test creating an incident via API endpoint."""
        payload = {
            "title": "Test incident title",
            "description": "Test description",
            # "status": self.status_draft.id,
            "gross_loss_amount": Decimal("199.99"),
            "currency_code": "EUR",
        }
        res = self.client.post(INCIDENTS_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        incident = Incident.objects.get(id=res.data["id"])
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.status.code, self.status_draft.code)
        self.assertEqual(incident.created_by, self.user)

    def test_partial_update_incident(self):
        """Test partial update of an incident with PATCH."""
        original_description = "Details on incident"
        incident = create_incident(
            user=self.user,
            status=self.status_draft,
            title="Sample incident title",
            description=original_description,
        )

        payload = {"title": "New incident title"}
        url = detail_url(incident.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.description, original_description)
        self.assertEqual(incident.created_by, self.user)

    def test_full_update_incident(self):
        """Test fully updating an incident with PUT."""
        incident = create_incident(user=self.user, status=self.status_draft)
        payload = {
            "title": "Full New Title",
            "description": "Full new description.",
            # "status": self.status_pending.id,
        }
        url = detail_url(incident.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.description, payload["description"])
        # self.assertEqual(incident.status.id, payload["status"])
        self.assertEqual(incident.created_by, self.user)

    def test_update_existent_incident_user_returns_error(self):
        """Test changing the incident's user results in an error."""
        new_user = create_user(email="user2@example.com", password="tstpsw12")
        incident = create_incident(user=self.user, status=self.status_draft)

        payload = {"user": new_user.id}
        url = detail_url(incident.id)
        self.client.patch(url, payload)

        incident.refresh_from_db()
        self.assertEqual(incident.created_by, self.user)

    def test_delete_incident(self):
        """Test deleting an incident is successful."""
        incident = create_incident(user=self.user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Incident.objects.filter(id=incident.id).exists())

    def test_delete_other_users_incident_error(self):
        """Test trying to delete another user's incident returns an error."""
        new_user = create_user(email="user2@example.com", password="tstpsw12")
        incident = create_incident(user=new_user, status=self.status_draft)

        url = detail_url(incident.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Incident.objects.filter(id=incident.id).exists())

    # Transitions - submit - old tests for initial endpoint, COMMENTED OUT
    # def test_submit_incident_action_success(self):
    #     """Test the custom action to submit a DRAFT incident."""
    #     incident = create_incident(user=self.user, status=self.status_draft)
    #     url = reverse("incidents:incident-submit", args=[incident.id])

    #     res = self.client.post(url)
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)

    #     incident.refresh_from_db()
    #     self.assertEqual(incident.status.code, "PENDING_REVIEW")

    # def test_submit_incident_wrong_status_fails(self):
    #     """Test that submitting an incident not in DRAFT status fails."""
    #     incident = create_incident(user=self.user,status=self.status_pending)
    #     url = reverse("incidents:incident-submit", args=[incident.id])

    #     res = self.client.post(url)
    #     self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # def test_submit_incident_not_owner_fails(self):
    #     """Test that a user cannot submit an incident they did not create."""
    #     new_user = create_user(email="user2@example.com", password="tstps12")
    #     incident = create_incident(user=new_user, status=self.status_draft)
    #     url = reverse("incidents:incident-submit", args=[incident.id])

    #     res = self.client.post(url)
    #     # This will fail with 404 because get_queryset already filters by usr
    #     self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class IncidentApiTransitionsPermissionsTests(TestCase):
    """Test authenticated API requests.
    Cover Workflows & Permissions.
    """

    def setUp(self):
        self.client = APIClient()

        # --- Create Roles & Statuses ---
        self.role_emp = Role.objects.create(name="Employee")
        self.role_mgr = Role.objects.create(name="Manager")
        self.role_risk = Role.objects.create(name="Risk Officer")

        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.status_pending_review = IncidentStatusRef.objects.create(
            code="PENDING_REVIEW", name="Pending Manager Review"
        )
        self.status_pending_validation = IncidentStatusRef.objects.create(
            code="PENDING_VALIDATION", name="Pending Risk Validation"
        )
        self.status_validated = IncidentStatusRef.objects.create(
            code="VALIDATED", name="Validated"
        )

        # --- Create BUs ---
        self.bu_retail = BusinessUnit.objects.create(name="Retail")
        self.bu_corp = BusinessUnit.objects.create(name="Corporate")

        # --- Create Users ---
        self.manager = create_user(
            email="manager@example.com",
            password="testpsw123",
            role=self.role_mgr,
            business_unit=self.bu_retail,
        )
        self.employee1 = create_user(
            email="emp1@example.com",
            password="testpsw123",
            role=self.role_emp,
            business_unit=self.bu_retail,
            manager=self.manager,
        )
        self.employee2 = create_user(
            email="emp2@example.com",
            password="testpsw123",
            role=self.role_emp,
            business_unit=self.bu_retail,
            manager=self.manager,
        )
        self.risk_officer = create_user(
            email="risk@example.com",
            password="testpsw123",
            role=self.role_risk,
            business_unit=self.bu_retail,
        )
        self.other_bu_emp = create_user(
            email="other@example.com",
            password="testpsw123",
            role=self.role_emp,
            business_unit=self.bu_corp,
        )

        # --- Create Incidents ---
        self.incident_emp1 = create_incident(
            user=self.employee1,
            status=self.status_draft,
            business_unit=self.bu_retail,
            title="Emp1 Incident",
        )
        self.incident_emp2 = create_incident(
            user=self.employee2,
            status=self.status_pending_review,
            business_unit=self.bu_retail,
            title="Emp2 Incident",
        )
        self.incident_mgr = create_incident(
            user=self.manager,
            status=self.status_draft,
            business_unit=self.bu_retail,
            title="Manager Incident",
        )
        self.incident_other_bu = create_incident(
            user=self.other_bu_emp,
            status=self.status_draft,
            business_unit=self.bu_corp,
            title="Corp Incident",
        )
        # Create an incident ready for validation
        self.incident_emp1_pending_validation = create_incident(
            user=self.employee1,
            status=self.status_pending_validation,  # Set initial status
            business_unit=self.bu_retail,
            title="Emp1 Pending Validation",
            assigned_to=self.risk_officer,  # Assume it was assigned on review
        )

        # --- Configure State Machine ---
        AllowedTransition.objects.create(
            from_status=self.status_draft,
            to_status=self.status_pending_review,
            role=self.role_emp,
        )
        AllowedTransition.objects.create(
            from_status=self.status_pending_review,
            to_status=self.status_pending_validation,
            role=self.role_mgr,
        )
        # Add rule for validation
        AllowedTransition.objects.create(  # To test 'validate' endpoint
            from_status=self.status_pending_validation,
            to_status=self.status_validated,
            role=self.role_risk,  # Only Risk Officer can validate
        )

    # --- Test Layer 1: Data Segregation (get_queryset) ---

    def test_employee_sees_only_own_incidents(self):
        """Test an employee can see only his incidents."""
        self.client.force_authenticate(user=self.employee1)
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[1]["title"], "Emp1 Incident")

    def test_manager_sees_own_and_team_incidents(self):
        """Test a manager can see only his team's incidents and his own."""
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 4)  # emp1, emp2, and their own
        titles = {item["title"] for item in res.data}
        self.assertIn("Emp1 Incident", titles)
        self.assertIn("Emp2 Incident", titles)
        self.assertIn("Manager Incident", titles)

    def test_risk_officer_sees_all_bu_incidents(self):
        """Test risk officer can see all incidents of a BU."""
        self.client.force_authenticate(user=self.risk_officer)
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(res.data), 4
        )  # emp1, emp2, manager (all in bu_retail)
        titles = {item["title"] for item in res.data}
        self.assertIn("Emp1 Incident", titles)
        self.assertNotIn(
            "Corp Incident", titles
        )  # Does not see other BU's incident

    # --- Test Layer 2: Action Permissions (permission_classes) ---

    def test_employee_can_submit_own_incident(self):
        """Test an employee can submit his own incident for review."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse(
            "incidents:incident-submit", args=[self.incident_emp1.id]
        )
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1.refresh_from_db()
        self.assertEqual(self.incident_emp1.status.code, "PENDING_REVIEW")

    def test_employee_cannot_submit_other_incident(self):
        """Test an employee can NOT submit other's incident for review."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse("incidents:incident-submit", args=[self.incident_mgr.id])
        res = self.client.post(url)

        self.assertEqual(
            res.status_code, status.HTTP_404_NOT_FOUND
        )  # Fails get_queryset first

    def test_manager_can_review_team_incident(self):
        """Test a manager can review an incident from his team."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-review", args=[self.incident_emp2.id]
        )
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp2.refresh_from_db()
        self.assertEqual(self.incident_emp2.status.code, "PENDING_VALIDATION")

    def test_employee_cannot_review_incident(self):
        """Test an employee can NOT review incident."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse(
            "incidents:incident-review", args=[self.incident_emp2.id]
        )
        res = self.client.post(url)

        self.assertEqual(
            res.status_code, status.HTTP_404_NOT_FOUND
        )  # Fails get_queryset

    def test_risk_officer_can_validate_incident(self):
        """Test Risk Officer successfully validates an incident."""
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-validate",
            args=[self.incident_emp1_pending_validation.id],
        )
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1_pending_validation.refresh_from_db()

        # Check domain logic (status change)
        self.assertEqual(
            self.incident_emp1_pending_validation.status, self.status_validated
        )
        # Check service side-effects
        self.assertEqual(
            self.incident_emp1_pending_validation.validated_by,
            self.risk_officer,
        )
        self.assertIsNone(
            self.incident_emp1_pending_validation.assigned_to
        )  # Assignment should be cleared

    def test_manager_cannot_validate_incident(self):
        """Test Manager is blocked by permission class from validating."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-validate",
            args=[self.incident_emp1_pending_validation.id],
        )
        res = self.client.post(url)

        # Should fail Layer 2 permission check
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Test Layer 3: Domain Logic (workflow.py) ---

    def test_transition_fails_if_role_is_wrong(self):
        """Test that a submit fails if the rule doesn't allow the role."""
        # We configured submit to only be allowed by 'Employee' role.
        # Let's test what happens if a 'Manager' tries to submit.
        self.client.force_authenticate(user=self.manager)
        url = reverse("incidents:incident-submit", args=[self.incident_mgr.id])
        res = self.client.post(url)

        # The IsIncidentCreator permission passes (it's their own incident)
        # But the *domain logic* should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Role 'Manager' is not authorized", res.data["error"])

    def test_transition_fails_if_wrong_state(self):
        """Test submitting an already-submitted incident fails."""
        self.client.force_authenticate(user=self.employee2)
        # This incident is already PENDING_REVIEW
        url = reverse(
            "incidents:incident-submit", args=[self.incident_emp2.id]
        )
        res = self.client.post(url)

        # The permission passes (it's their incident), but the
        # domain logic (workflow.py) should reject the state transition.
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is not defined", res.data["error"])

    def test_review_incident_side_effects_assignment(self):
        """Test that reviewing an incident correctly assigns it
        to a Risk Officer."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-review", args=[self.incident_emp2.id]
        )
        self.client.post(url)

        self.incident_emp2.refresh_from_db()

        # Test the side-effects of the service function
        self.assertEqual(
            self.incident_emp2.status, self.status_pending_validation
        )
        self.assertEqual(self.incident_emp2.reviewed_by, self.manager)
        self.assertEqual(self.incident_emp2.assigned_to, self.risk_officer)

    def test_manager_cannot_submit_own_incident(self):
        """Test manager is blocked by business rules."""
        self.client.force_authenticate(user=self.manager)
        # The manager can *see* and access this incident (Layer 1 & 2 pass)
        url = reverse("incidents:incident-submit", args=[self.incident_mgr.id])

        res = self.client.post(url)

        # But transition is forbidden by business rules (Layer 3),
        # caught by validate_transition(), thus should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_validate_incident_in_wrong_state(self):
        """Test validating an incident not in PENDING_VALIDATION fails."""
        # Use the incident still in DRAFT status
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-validate",
            args=[self.incident_emp1.id],  # incident_emp1 is DRAFT
        )
        res = self.client.post(url)

        # Permission passes, but domain logic should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Transition from 'DRAFT' to 'VALIDATED' is not defined.",
            res.data["error"],
        )
