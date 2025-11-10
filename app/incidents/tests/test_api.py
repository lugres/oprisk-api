"""
Tests for incidents API.
"""

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient

from incidents.models import (
    Incident,
    IncidentStatusRef,
    AllowedTransition,
    IncidentRoutingRule,
    SimplifiedEventTypeRef,
    SlaConfig,
    IncidentRequiredField,
    IncidentEditableField,
)
from references.models import (
    Role,
    BusinessUnit,
    BaselEventType,
    BusinessProcess,
    Product,
)

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

        # --- NEW: Add Role and Status for context ---
        self.role_emp, _ = Role.objects.get_or_create(name="Employee")
        # ensure user has a role - needed for dynamic field editing logic
        self.user = create_user(
            email="test@example.com",
            password="testp123",
            role=self.role_emp,
        )

        self.client.force_authenticate(user=self.user)

        self.status_draft = IncidentStatusRef.objects.create(
            code="DRAFT", name="Draft"
        )
        self.status_pending = IncidentStatusRef.objects.create(
            code="PENDING_REVIEW", name="Pending"
        )
        # Adding draft SLA
        SlaConfig.objects.create(key="draft_days", value_int=7)

        # --- NEW: Configure editable fields for this test class ---
        # The user is an 'Employee' now, so we allow editing 'title'
        # and 'description' fields in DRAFT status, matching main config.
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="title",
        )
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="description",
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
        test_time = timezone.now()
        with self.settings(NOW_OVERRIDE=test_time):
            res = self.client.post(INCIDENTS_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        incident = Incident.objects.get(id=res.data["id"])
        self.assertEqual(incident.title, payload["title"])
        self.assertEqual(incident.status.code, self.status_draft.code)
        self.assertEqual(incident.created_by, self.user)
        # Check SLA logic
        expected_due_date = (test_time + timedelta(days=7)).date()
        self.assertEqual(incident.draft_due_at.date(), expected_due_date)
        self.assertIsNone(incident.review_due_at)
        self.assertIsNone(incident.validation_due_at)

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
        self.role_fraud = Role.objects.create(name="Fraud Investigator")

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
        self.status_closed = IncidentStatusRef.objects.create(
            code="CLOSED", name="Closed"
        )

        # --- Create BUs ---
        self.bu_retail = BusinessUnit.objects.create(name="Retail")
        self.bu_corp = BusinessUnit.objects.create(name="Corporate")

        # --- Add Event for Routing Rule ---
        self.event_fraud = SimplifiedEventTypeRef.objects.create(name="Fraud")

        # --- Add Data for Dynamic Field Validation ---
        self.process_cards = BusinessProcess.objects.create(
            name="Credit Cards", business_unit=self.bu_retail
        )
        self.basel_fraud = BaselEventType.objects.create(name="External Fraud")
        self.product_card = Product.objects.create(name="Regular Credit Card")

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
            simplified_event_type=self.event_fraud,  # dyn fld vld
            title="Emp1 Incident",
        )
        self.incident_emp2 = create_incident(
            user=self.employee2,
            status=self.status_pending_review,
            business_unit=self.bu_retail,
            simplified_event_type=self.event_fraud,  # dyn fld vld
            product=self.product_card,
            business_process=self.process_cards,
            title="Emp2 Incident",
        )
        self.incident_mgr = create_incident(
            user=self.manager,
            status=self.status_draft,
            business_unit=self.bu_retail,
            simplified_event_type=self.event_fraud,  # dyn fld vld
            title="Manager Incident",
        )
        self.incident_other_bu = create_incident(
            user=self.other_bu_emp,
            status=self.status_draft,
            business_unit=self.bu_corp,
            title="Corp Incident",
        )
        # Specifically for test_cannot_validate_incident_in_wrong_state
        self.incident_emp1_draft_for_validation = create_incident(
            user=self.employee1,
            status=self.status_draft,  # Set DRAFT
            business_unit=self.bu_retail,
            title="Emp1 in Draft to test validation",
            basel_event_type=self.basel_fraud,  # dyn fld vld
            net_loss_amount=Decimal("199.95"),
            currency_code="EUR",
        )

        # Create an incident ready for validation
        self.incident_emp1_pending_validation = create_incident(
            user=self.employee1,
            status=self.status_pending_validation,  # Set initial status
            business_unit=self.bu_retail,
            title="Emp1 Pending Validation",
            assigned_to=self.risk_officer,  # Assume it was assigned on review
            basel_event_type=self.basel_fraud,  # dyn fld vld
            net_loss_amount=Decimal("199.95"),
            currency_code="EUR",
        )
        # Create incident ready for return actions
        self.incident_emp2_pending_review = create_incident(
            user=self.employee2,
            status=self.status_pending_review,
            business_unit=self.bu_retail,
            title="Emp2 Pending Review",
            assigned_to=self.manager,  # Assume assigned to manager
        )
        # Create an incident ready for closing
        self.incident_emp1_validated = create_incident(
            user=self.employee1,
            status=self.status_validated,
            business_unit=self.bu_retail,
            title="Emp1 Validated Incident",
            validated_by=self.risk_officer,  # Assume validated by RO
        )
        # Incident for testing routing
        self.incident_emp2_fraud_review = create_incident(
            user=self.employee2,
            status=self.status_pending_review,
            business_unit=self.bu_retail,
            title="Emp2 Fraud Incident for review",  # Will match routing rule
            simplified_event_type=self.event_fraud,
            business_process=self.process_cards,
            product=self.product_card,
        )
        # Incident for submit test that is MISSING data
        self.incident_emp1_draft_missing_data = create_incident(
            user=self.employee1,
            status=self.status_draft,
            business_unit=self.bu_retail,
            title="Emp1 Draft Missing Simplified event type",
            simplified_event_type=None,  # is NULL
        )
        # Incident for review test that is MISSING product
        self.incident_emp2_review_missing_amount = create_incident(
            user=self.employee2,
            status=self.status_pending_review,
            business_unit=self.bu_retail,
            title="Emp2 Review Missing Product",
            simplified_event_type=self.event_fraud,
            product=None,  # Explicitly NULL
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
        # Add rules for returning incidents
        AllowedTransition.objects.create(
            from_status=self.status_pending_review,
            to_status=self.status_draft,
            role=self.role_mgr,  # Manager returns
        )
        AllowedTransition.objects.create(
            from_status=self.status_pending_validation,
            to_status=self.status_pending_review,
            role=self.role_risk,  # Risk Officer returns
        )
        # Add rule for closing incidents
        AllowedTransition.objects.create(
            from_status=self.status_validated,
            to_status=self.status_closed,
            role=self.role_risk,  # Only Risk Officer can close
        )

        # --- Create a specific, high-priority routing rule for testing ---
        IncidentRoutingRule.objects.create(
            description="Route all Fraud to Fraud Team",
            predicate={"simplified_event_type": self.event_fraud.id},
            route_to_role=self.role_fraud,
            priority=10,  # High priority
            active=True,
        )

        # --- Configure SLA ---
        SlaConfig.objects.create(key="draft_days", value_int=7)
        SlaConfig.objects.create(key="review_days", value_int=5)
        SlaConfig.objects.create(key="validation_days", value_int=10)

        # --- Configure Required Fields ---

        # 1. To move to PENDING_REVIEW (checked by submit_incident)
        # 'title', 'description', 'gross_loss_amount' are handled by the model.
        IncidentRequiredField.objects.create(
            status=self.status_pending_review,  # Target status for submit
            field_name="simplified_event_type",  # Field required to submit
        )
        # 2. To move to PENDING_VALIDATION (checked by review_incident)
        # Manager ensures these are set before escalating to Risk.
        IncidentRequiredField.objects.create(
            status=self.status_pending_validation,
            field_name="product",
        )
        IncidentRequiredField.objects.create(
            status=self.status_pending_validation,  # Target status for review
            field_name="business_process",  # Field required to review
        )
        IncidentRequiredField.objects.create(
            status=self.status_pending_validation,
            field_name="gross_loss_amount",
        )
        IncidentRequiredField.objects.create(
            status=self.status_pending_validation,
            field_name="simplified_event_type",
        )
        # 3. To move to VALIDATED (checked by validate_incident)
        # Risk Officer must fill these before validating.
        IncidentRequiredField.objects.create(
            status=self.status_validated, field_name="basel_event_type"
        )
        IncidentRequiredField.objects.create(
            status=self.status_validated, field_name="net_loss_amount"
        )
        IncidentRequiredField.objects.create(
            status=self.status_validated, field_name="currency_code"
        )

        # --- Configure Editable Fields ---

        # 1: Employee @ DRAFT
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="title",
        )
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="description",
        )
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="simplified_event_type",
        )
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="near_miss",
        )
        IncidentEditableField.objects.create(
            status=self.status_draft,
            role=self.role_emp,
            field_name="gross_loss_amount",  # "draft loss"
        )

        # 2: Manager @ PENDING_REVIEW
        IncidentEditableField.objects.create(
            status=self.status_pending_review,
            role=self.role_mgr,
            field_name="business_process",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_review,
            role=self.role_mgr,
            field_name="product",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_review,
            role=self.role_mgr,
            field_name="gross_loss_amount",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_review,
            role=self.role_mgr,
            field_name="simplified_event_type",
        )

        # 3: Risk Officer @ PENDING_VALIDATION
        # "Can change all other fields"
        # We'll list the key ones, especially those the manager couldn't edit
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="basel_event_type",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="recovery_amount",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="net_loss_amount",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="currency_code",
        )
        # Also grant them permission to edit fields from previous steps
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="title",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="description",
        )
        IncidentEditableField.objects.create(
            status=self.status_pending_validation,
            role=self.role_risk,
            field_name="gross_loss_amount",
        )

        # 5: CLOSED status
        # NO rules for CLOSED status, meaning all fields become read-only.

    # --- Test Layer 1: Data Segregation (get_queryset) ---

    def test_employee_sees_only_own_incidents(self):
        """Test an employee can see only his incidents."""
        self.client.force_authenticate(user=self.employee1)
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 5)
        self.assertEqual(res.data[4]["title"], "Emp1 Incident")

    def test_manager_sees_own_and_team_incidents(self):
        """Test a manager can see only his team's incidents and his own."""
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(INCIDENTS_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 10)  # emp1, emp2, and their own
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
            len(res.data), 10
        )  # emp1, emp2, manager (all in bu_retail)
        titles = {item["title"] for item in res.data}
        self.assertIn("Emp1 Incident", titles)
        self.assertNotIn(
            "Corp Incident", titles
        )  # Does not see other BU's incident

    # --- Test Layer 2: Action Permissions (permission_classes) ---

    def test_employee_can_submit_own_incident(self):
        """Test an employee can submit his own incident for review.
        Submit assigns to manager and updates SLA fields."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse(
            "incidents:incident-submit", args=[self.incident_emp1.id]
        )

        test_time = timezone.now()
        with self.settings(NOW_OVERRIDE=test_time):
            res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1.refresh_from_db()
        self.assertEqual(self.incident_emp1.status.code, "PENDING_REVIEW")
        # Check fallback assignment - no routing
        self.assertEqual(self.incident_emp1.assigned_to, self.manager)
        # --- Check SLA logic ---
        # 5 days expected from SlaConfig
        expected_due_date = (test_time + timedelta(days=5)).date()
        # Old timer cleared
        self.assertIsNone(self.incident_emp1.draft_due_at)
        # New timer set
        self.assertEqual(
            self.incident_emp1.review_due_at.date(), expected_due_date
        )

    def test_review_incident_creates_notification_on_route_match(self):
        """Test that reviewing an incident creates a
        Notification if a rule matches."""
        # Use the new, robust notification model
        from notifications.models import Notification

        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-review",
            args=[self.incident_emp2_fraud_review.id],
        )

        self.assertEqual(Notification.objects.count(), 0)  # Pre-condition

        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check that a notification was created
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.first()

        # Verify the new polymorphic and queue fields
        self.assertEqual(
            notification.entity_type, Notification.EntityType.INCIDENT
        )
        self.assertEqual(
            notification.entity_id, self.incident_emp2_fraud_review.id
        )
        self.assertEqual(
            notification.event_type, Notification.EventType.ROUTING_NOTIFY
        )
        self.assertEqual(notification.status, Notification.Status.QUEUED)
        self.assertEqual(notification.triggered_by, self.manager)
        self.assertEqual(notification.recipient_role_id, self.role_fraud.id)

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

    # Tests for 'validate' action
    def test_risk_officer_can_validate_incident(self):
        """Test Risk Officer successfully validates an incident
        and clears SLA."""
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
        # Assignment should be cleared
        self.assertIsNone(self.incident_emp1_pending_validation.assigned_to)
        # --- Check SLA logic ---
        # Timer cleared
        self.assertIsNone(
            self.incident_emp1_pending_validation.validation_due_at
        )
        # History set
        self.assertIsNotNone(
            self.incident_emp1_pending_validation.validated_at
        )

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

    # --- Tests for 'return' actions ---
    def test_manager_can_return_to_draft_with_reason(self):
        """Test manager can return an incident (PENDING_REVIEW to DRAFT).
        Reason is required. draft_due_at is recomputed."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-return-to-draft",
            args=[self.incident_emp2_pending_review.id],
        )
        # Include a reason in the payload
        payload = {"reason": "Needs more details in description."}

        test_time = timezone.now()
        with self.settings(NOW_OVERRIDE=test_time):
            res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp2_pending_review.refresh_from_db()

        self.assertEqual(
            self.incident_emp2_pending_review.status, self.status_draft
        )
        # Assignment should be cleared
        self.assertIsNone(self.incident_emp2_pending_review.assigned_to)
        # Check that the reason was added to notes
        self.assertIn(
            payload["reason"], self.incident_emp2_pending_review.notes
        )
        self.assertIn(
            self.manager.email, self.incident_emp2_pending_review.notes
        )
        # Check SLA logic
        # Assuming draft_days is 7
        expected_due_date = (test_time + timedelta(days=7)).date()
        self.assertEqual(
            self.incident_emp2_pending_review.draft_due_at.date(),
            expected_due_date,
        )
        # Old timer cleared
        self.assertIsNone(self.incident_emp2_pending_review.review_due_at)

    def test_return_to_draft_fails_without_reason(self):
        """Test returning to draft fails if reason payload is missing."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-return-to-draft",
            args=[self.incident_emp2_pending_review.id],
        )
        res = self.client.post(url, {})  # Empty payload

        # Should fail serializer validation
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", res.data)
        self.assertIn("required", str(res.data["reason"]))

    def test_return_to_draft_fails_with_blank_reason(self):
        """Test returning to draft fails if reason payload is blank."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-return-to-draft",
            args=[self.incident_emp2_pending_review.id],
        )
        res = self.client.post(url, {"reason": ""})  # Blank reason

        # Should fail serializer validation
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", res.data)
        self.assertIn("blank", str(res.data["reason"]))

    def test_manager_cannot_return_to_review(self):
        """Test Manager is blocked by permissions from returning to review."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-return-to-review",
            args=[self.incident_emp1_pending_validation.id],
        )
        res = self.client.post(url)
        # Should fail Layer 2 permission check (IsRoleRiskOfficer needed)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_return_to_draft(self):
        """Test employee is blocked by permission class from returning."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse(
            "incidents:incident-return-to-draft",
            args=[self.incident_emp2_pending_review.id],
        )
        res = self.client.post(url)
        # Should fail Layer 2 permission check
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_risk_officer_can_return_to_review_with_reason(self):
        """Test Risk Officer successfully returns incident with reason.
        review_due_at is recomputed."""
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-return-to-review",
            args=[self.incident_emp1_pending_validation.id],
        )
        payload = {"reason": "Incorrect category assigned."}
        test_time = timezone.now()
        with self.settings(NOW_OVERRIDE=test_time):
            res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1_pending_validation.refresh_from_db()
        self.assertEqual(
            self.incident_emp1_pending_validation.status,
            self.status_pending_review,
        )
        # Check on assignment logic - reassign to manager
        self.assertEqual(
            self.incident_emp1_pending_validation.assigned_to, self.manager
        )
        # Check notes for reason
        self.assertIn(
            payload["reason"], self.incident_emp1_pending_validation.notes
        )
        self.assertIn(
            self.risk_officer.email,
            self.incident_emp1_pending_validation.notes,
        )
        # Check SLA logic
        expected_due_date = (test_time + timedelta(days=5)).date()
        self.assertEqual(
            self.incident_emp1_pending_validation.review_due_at.date(),
            expected_due_date,
        )
        # Old timer cleared
        self.assertIsNone(
            self.incident_emp1_pending_validation.validation_due_at
        )

    def test_return_to_review_fails_without_reason(self):
        """Test returning to review fails if reason payload is missing."""
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-return-to-review",
            args=[self.incident_emp1_pending_validation.id],
        )
        res = self.client.post(url, {})  # Empty payload

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", res.data)

    # --- Tests for 'close' action ---
    def test_risk_officer_can_close_incident(self):
        """Test Risk Officer successfully closes a VALIDATED incident."""
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-close", args=[self.incident_emp1_validated.id]
        )
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1_validated.refresh_from_db()

        # Check domain logic (status change)
        self.assertEqual(
            self.incident_emp1_validated.status, self.status_closed
        )
        # Check service side-effects
        self.assertEqual(
            self.incident_emp1_validated.closed_by, self.risk_officer
        )
        self.assertIsNotNone(self.incident_emp1_validated.closed_at)
        self.assertIsNone(self.incident_emp1_validated.assigned_to)

    def test_manager_cannot_close_incident(self):
        """Test Manager is blocked by permission class from closing."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-close", args=[self.incident_emp1_validated.id]
        )
        res = self.client.post(url)

        # Should fail Layer 2 permission check (IsRoleRiskOfficer needed)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Tests for Dynamic Field Validation (Layer 2.5) ---

    def test_submit_fails_if_required_field_is_missing(self):
        """Test submit action fails if 'simplified_event_type' is missing."""
        self.client.force_authenticate(user=self.employee1)
        url = reverse(
            "incidents:incident-submit",
            args=[self.incident_emp1_draft_missing_data.id],
        )
        res = self.client.post(url)

        # This is a validation failure, so expect 400
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
        # Check that the error message clearly identifies the missing field
        self.assertIn("simplified_event_type", res.data["error"])
        self.assertIn("required for PENDING_REVIEW", res.data["error"])

        # Also ensure the status did NOT change
        self.incident_emp1_draft_missing_data.refresh_from_db()
        self.assertEqual(
            self.incident_emp1_draft_missing_data.status, self.status_draft
        )

    def test_review_fails_if_required_field_is_missing(self):
        """Test review action fails if 'product' is NULL."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-review",
            args=[self.incident_emp2_review_missing_amount.id],
        )
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
        self.assertIn("product", res.data["error"])
        self.assertIn("required for PENDING_VALIDATION", res.data["error"])

    def test_validate_fails_if_required_field_is_missing(self):
        """Test validate action fails if 'basel_event_type' is missing."""
        self.client.force_authenticate(user=self.risk_officer)
        # This incident is ready for validation but I'll remove required field
        incident = self.incident_emp1_pending_validation
        incident.basel_event_type = None
        incident.net_loss_amount = Decimal("100.00")  # Has this one
        incident.currency_code = "USD"  # And this one
        incident.save()

        url = reverse("incidents:incident-validate", args=[incident.id])
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("basel_event_type", res.data["error"])

    def test_validate_fails_if_multiple_fields_are_missing(self):
        """Test validate action lists all missing fields."""
        self.client.force_authenticate(user=self.risk_officer)
        incident = self.incident_emp1_pending_validation
        incident.basel_event_type = None  # Missing
        incident.net_loss_amount = None  # Missing
        incident.currency_code = "USD"  # Has this one
        incident.save()

        url = reverse("incidents:incident-validate", args=[incident.id])
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = res.data["error"]
        self.assertIn("basel_event_type", error_msg)
        self.assertIn("net_loss_amount", error_msg)

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
        to a Risk Officer and updates SLA fields."""
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-review", args=[self.incident_emp2.id]
        )

        test_time = timezone.now()
        with self.settings(NOW_OVERRIDE=test_time):
            self.client.post(url)

        self.incident_emp2.refresh_from_db()

        # Test the side-effects of the service function
        self.assertEqual(
            self.incident_emp2.status, self.status_pending_validation
        )
        self.assertEqual(self.incident_emp2.reviewed_by, self.manager)
        self.assertEqual(self.incident_emp2.assigned_to, self.risk_officer)
        # --- Check SLA logic ---
        # 10 days from SlaConfig
        expected_due_date = (test_time + timedelta(days=10)).date()
        # Old timer cleared
        self.assertIsNone(self.incident_emp2.review_due_at)
        self.assertEqual(
            self.incident_emp2.validation_due_at.date(),
            expected_due_date,
        )

    # --- Tests for 'validate' action ---
    def test_cannot_validate_incident_in_wrong_state(self):
        """Test validating an incident not in PENDING_VALIDATION fails."""
        # Use the incident still in DRAFT status
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-validate",
            args=[self.incident_emp1_draft_for_validation.id],  # in DRAFT
        )
        res = self.client.post(url)

        # Permission passes, but domain logic should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Transition from 'DRAFT' to 'VALIDATED' is not defined.",
            res.data["error"],
        )

    # --- Tests for 'return' actions ---
    def test_cannot_return_to_draft_from_wrong_state(self):
        """Test returning to draft fails if not in PENDING_REVIEW."""
        # Use the incident already pending validation
        self.client.force_authenticate(user=self.manager)
        url = reverse(
            "incidents:incident-return-to-draft",
            args=[self.incident_emp1_pending_validation.id],
        )
        payload = {"reason": "Testing wrong state"}
        res = self.client.post(url, payload)

        # Permission passes, but domain logic should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", res.data)
        self.assertIn(
            "Transition from 'PENDING_VALIDATION' to 'DRAFT' is not defined.",
            res.data["error"],
        )

    # --- Tests for 'close' action ---
    def test_cannot_close_incident_in_wrong_state(self):
        """Test closing an incident not in VALIDATED status fails."""
        # Use the incident still in DRAFT status
        self.client.force_authenticate(user=self.risk_officer)
        url = reverse(
            "incidents:incident-close",
            args=[self.incident_emp1.id],  # incident_emp1 is DRAFT
        )
        res = self.client.post(url)

        # Permission passes, but domain logic should fail
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Transition from 'DRAFT' to 'CLOSED' is not defined.",
            res.data["error"],
        )

    # --- Tests for Dynamic Field-Level Security (PATCH) ---

    def test_employee_can_edit_allowed_field_in_draft(self):
        """Test Employee can PATCH 'title' on their DRAFT incident."""
        self.client.force_authenticate(user=self.employee1)
        url = detail_url(self.incident_emp1.id)  # self.incident_emp1 is DRAFT
        new_title = "Title Updated by Employee"

        res = self.client.patch(url, {"title": new_title})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1.refresh_from_db()
        self.assertEqual(self.incident_emp1.title, new_title)

    def test_employee_cannot_edit_disallowed_field_in_draft(self):
        """Test Employee's PATCH to 'basel_event_type' is IGNORED in DRAFT."""
        self.client.force_authenticate(user=self.employee1)
        incident = self.incident_emp1  # DRAFT status
        url = detail_url(incident.id)

        res = self.client.patch(
            url,
            {"basel_event_type": self.basel_fraud.id},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # Request is OK
        incident.refresh_from_db()
        self.assertIsNone(incident.basel_event_type)  # Field is unchanged

    def test_employee_cannot_edit_allowed_field_in_wrong_status(self):
        """Test Employee's PATCH to 'title' is IGNORED in PENDING_VALIDATION"""
        self.client.force_authenticate(user=self.employee1)
        # This incident is PENDING_VALIDATION
        incident = self.incident_emp1_pending_validation
        original_title = incident.title
        url = detail_url(incident.id)

        res = self.client.patch(
            url, {"title": "This update should be ignored"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        # The title remains unchanged
        self.assertEqual(incident.title, original_title)

    def test_risk_officer_can_edit_their_fields_in_validation(self):
        """Test Risk Officer CAN edit 'gross_loss_amount' in PENDING_VALIDN"""
        self.client.force_authenticate(user=self.risk_officer)
        incident = self.incident_emp1_pending_validation
        url = detail_url(incident.id)
        new_amount = Decimal("12345.67")

        res = self.client.patch(url, {"gross_loss_amount": new_amount})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        incident.refresh_from_db()
        self.assertEqual(incident.gross_loss_amount, new_amount)

    def test_all_fields_are_readonly_in_closed_status(self):
        """Test that NO fields are editable once an incident is CLOSED."""
        self.client.force_authenticate(user=self.risk_officer)
        # self.incident_emp1_validated is VALIDATED, let's close it
        close_url = reverse(
            "incidents:incident-close", args=[self.incident_emp1_validated.id]
        )
        self.client.post(close_url)

        self.incident_emp1_validated.refresh_from_db()
        self.assertEqual(
            self.incident_emp1_validated.status, self.status_closed
        )

        # Now, try to PATCH the closed incident
        patch_url = detail_url(self.incident_emp1_validated.id)
        original_title = self.incident_emp1_validated.title
        res = self.client.patch(patch_url, {"title": "This must be ignored"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.incident_emp1_validated.refresh_from_db()
        # Title remains unchanged
        self.assertEqual(self.incident_emp1_validated.title, original_title)
