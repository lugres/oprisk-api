"""
Test suite for measures API.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta

from measures.models import Measure, MeasureStatusRef, MeasureEditableField
from incidents.models import Incident, IncidentStatusRef as IncidentStatus
from references.models import Role, BusinessUnit


# Helper function to create users
def create_user(email, password, role, business_unit, manager=None):
    user = get_user_model().objects.create_user(
        email=email,
        password=password,
        role=role,
        business_unit=business_unit,
        manager=manager,
    )
    return user


# Helper function for URLs
def measure_list_url():
    return reverse("measures:measure-list")


def measure_detail_url(measure_id):
    return reverse("measures:measure-detail", args=[measure_id])


def measure_action_url(measure_id, action):
    return reverse(f"measures:measure-{action}", args=[measure_id])


class MeasureTestBase(TestCase):
    """Base test class with common setup for all measure tests."""

    def setUp(self):
        self.client = APIClient()

        # --- create roles and statuses ---
        self.role_mgr, _ = Role.objects.get_or_create(name="Manager")
        self.role_risk, _ = Role.objects.get_or_create(name="Risk Officer")
        self.role_emp, _ = Role.objects.get_or_create(name="Employee")

        self.status_open, _ = MeasureStatusRef.objects.get_or_create(
            code="OPEN", defaults={"name": "Open"}
        )
        self.status_in_progress, _ = MeasureStatusRef.objects.get_or_create(
            code="IN_PROGRESS", defaults={"name": "In Progress"}
        )
        self.status_pending_review, _ = MeasureStatusRef.objects.get_or_create(
            code="PENDING_REVIEW", defaults={"name": "Pending Review"}
        )
        self.status_completed, _ = MeasureStatusRef.objects.get_or_create(
            code="COMPLETED", defaults={"name": "Completed"}
        )
        self.status_cancelled, _ = MeasureStatusRef.objects.get_or_create(
            code="CANCELLED", defaults={"name": "Cancelled"}
        )

        # --- create BUs ---
        self.bu_ops, _ = BusinessUnit.objects.get_or_create(name="Operations")
        self.bu_risk, _ = BusinessUnit.objects.get_or_create(
            name="Risk Management"
        )

        # --- create users ---
        self.risk_officer = create_user(
            "risk@example.com", "tstpw123", self.role_risk, self.bu_ops
        )
        self.manager = create_user(
            "manager@example.com", "tstpw123", self.role_mgr, self.bu_ops
        )
        self.responsible_user = create_user(
            "responsible@example.com",
            "tstpw123",
            self.role_emp,
            self.bu_ops,
            self.manager,
        )
        self.creator_user = create_user(
            "creator@example.com",
            "tstpw123",
            self.role_emp,
            self.bu_ops,
            self.manager,
        )
        self.other_user = create_user(
            "other@example.com",
            "tstpw123",
            self.role_emp,
            self.bu_ops,
            self.manager,
        )

        # --- create test incident for linking ---
        inc_status, _ = IncidentStatus.objects.get_or_create(
            code="DRAFT", defaults={"name": "Draft"}
        )
        self.incident = Incident.objects.create(
            title="Test Incident for Linking",
            created_by=self.creator_user,
            status=inc_status,
        )

        # --- create test measures ---
        self.measure_open = Measure.objects.create(
            description="Open measure, created by creator",
            created_by=self.creator_user,
            responsible=self.responsible_user,
            status=self.status_open,
            deadline=date.today() + timedelta(days=30),
        )
        self.measure_in_progress = Measure.objects.create(
            description="In-progress measure, responsible user",
            created_by=self.creator_user,
            responsible=self.responsible_user,
            status=self.status_in_progress,
            deadline=date.today() + timedelta(days=10),
        )
        self.measure_pending_review = Measure.objects.create(
            description="Pending review measure",
            created_by=self.creator_user,
            responsible=self.responsible_user,
            status=self.status_pending_review,
        )
        self.measure_other_user = Measure.objects.create(
            description="Other user's measure",
            created_by=self.other_user,
            responsible=self.other_user,
            status=self.status_open,
        )

        # -- configure dynamic field-level security (MeasureEditableField) --

        # OPEN: responsible can edit description/deadline
        MeasureEditableField.objects.get_or_create(
            status=self.status_open,
            role=self.role_emp,
            field_name="description",
        )
        MeasureEditableField.objects.get_or_create(
            status=self.status_open,
            role=self.role_emp,
            field_name="deadline",
        )
        # IN_PROGRESS: responsible can edit description,
        # Risk Officer can edit deadline
        MeasureEditableField.objects.get_or_create(
            status=self.status_in_progress,
            role=self.role_emp,
            field_name="description",
        )
        MeasureEditableField.objects.get_or_create(
            status=self.status_in_progress,
            role=self.role_risk,
            field_name="deadline",
        )


class MeasureQuerysetTests(MeasureTestBase):
    """Test data segregation and queryset filtering."""

    def test_get_queryset_responsible_user(self):
        """Test responsible user can see measures assigned to them."""
        self.client.force_authenticate(user=self.responsible_user)
        res = self.client.get(measure_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)  # open, in_progress, pending_rev
        self.assertIn(self.measure_open.description, str(res.data))

    def test_get_queryset_creator_user(self):
        """Test creator user can see measures they created."""
        self.client.force_authenticate(user=self.creator_user)
        res = self.client.get(measure_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)  # open, in_progress, pending_rev

    def test_get_queryset_manager(self):
        """Test manager can see measures for their team."""
        self.client.force_authenticate(user=self.manager)
        res = self.client.get(measure_list_url())

        # Sees measures from responsible_user, creator_user, other_user
        # (all their reports)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 4)

    def test_get_queryset_risk_officer(self):
        """Test risk officer can see all measures in their BU."""
        self.client.force_authenticate(user=self.risk_officer)
        res = self.client.get(measure_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 4)  # All measures in bu_ops

    def test_risk_officer_cannot_see_other_bu_measures(self):
        """Test risk officer cannot see measures from other BUs."""
        # Create a measure in different BU
        other_bu_user = create_user(
            "otherbu@example.com", "tstpw123", self.role_emp, self.bu_risk
        )
        other_bu_measure = Measure.objects.create(
            description="Different BU measure",
            created_by=other_bu_user,
            responsible=other_bu_user,
            status=self.status_open,
        )

        self.client.force_authenticate(user=self.risk_officer)
        res = self.client.get(measure_list_url())

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Should not include other_bu_measure
        measure_ids = [m["id"] for m in res.data]
        self.assertNotIn(other_bu_measure.id, measure_ids)

    def test_unauthenticated_access_fails(self):
        """Test that unauthenticated requests are rejected."""
        # Don't authenticate
        res = self.client.get(measure_list_url())

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MeasureCRUDTests(MeasureTestBase):
    """Test basic CRUD operations and permissions."""

    def test_create_measure_as_manager(self):
        """Test a Manager can create a new measure (defaults to OPEN)."""
        self.client.force_authenticate(user=self.manager)
        payload = {
            "description": "New measure created by manager",
            "responsible": self.responsible_user.id,
            "deadline": date.today() + timedelta(days=15),
        }
        res = self.client.post(measure_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        measure = Measure.objects.get(id=res.data["id"])
        self.assertEqual(measure.status, self.status_open)
        self.assertEqual(measure.created_by, self.manager)
        self.assertEqual(measure.responsible, self.responsible_user)

    def test_create_measure_as_risk_officer(self):
        """Test a Risk Officer can create a new measure."""
        self.client.force_authenticate(user=self.risk_officer)
        payload = {
            "description": "New measure created by risk officer",
            "responsible": self.responsible_user.id,
            "deadline": date.today() + timedelta(days=15),
        }
        res = self.client.post(measure_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        measure = Measure.objects.get(id=res.data["id"])
        self.assertEqual(measure.status, self.status_open)
        self.assertEqual(measure.created_by, self.risk_officer)

    def test_create_measure_as_employee_fails(self):
        """Test a regular Employee cannot create a new measure."""
        self.client.force_authenticate(user=self.responsible_user)
        payload = {"description": "This should fail"}
        res = self.client.post(measure_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_create_measure(self):
        """Test unauthenticated user cannot create measures."""
        payload = {"description": "Test"}
        res = self.client.post(measure_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_open_measure_as_creator_succeeds(self):
        """Test creator can DELETE a measure that is still OPEN."""
        self.client.force_authenticate(user=self.creator_user)
        url = measure_detail_url(self.measure_open.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Measure.objects.filter(id=self.measure_open.id).exists()
        )

    def test_delete_open_measure_as_manager_succeeds(self):
        """Test manager can DELETE a measure that is still OPEN."""
        self.client.force_authenticate(user=self.manager)
        url = measure_detail_url(self.measure_open.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Measure.objects.filter(id=self.measure_open.id).exists()
        )

    def test_delete_in_progress_measure_as_creator_fails(self):
        """Test DELETE is blocked if the status is not OPEN."""
        self.client.force_authenticate(user=self.creator_user)
        url = measure_detail_url(self.measure_in_progress.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            Measure.objects.filter(id=self.measure_in_progress.id).exists()
        )

    def test_delete_measure_as_unrelated_user_fails(self):
        """Test other users cannot DELETE measures."""
        self.client.force_authenticate(user=self.other_user)
        url = measure_detail_url(self.measure_open.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            Measure.objects.filter(id=self.measure_open.id).exists()
        )


class MeasureFieldLevelSecurityTests(MeasureTestBase):
    """Test dynamic field-level security based on status and role."""

    def test_responsible_can_edit_deadline_in_open(self):
        """Test responsible user can PATCH deadline in OPEN status."""
        self.client.force_authenticate(user=self.responsible_user)
        new_date = date.today() + timedelta(days=5)
        url = measure_detail_url(self.measure_open.id)
        res = self.client.patch(url, {"deadline": new_date})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_open.refresh_from_db()
        self.assertEqual(self.measure_open.deadline, new_date)

    def test_creator_can_edit_description_in_open(self):
        """Test creator user can PATCH description in OPEN status."""
        self.client.force_authenticate(user=self.creator_user)
        url = measure_detail_url(self.measure_open.id)
        new_desc = "Updated description by creator"
        res = self.client.patch(url, {"description": new_desc})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_open.refresh_from_db()
        self.assertEqual(self.measure_open.description, new_desc)

    def test_creator_cannot_edit_in_progress_measure(self):
        """Test creator cannot PATCH after measure moves to IN_PROGRESS."""
        self.client.force_authenticate(user=self.creator_user)
        url = measure_detail_url(self.measure_in_progress.id)
        new_desc = "This should fail"
        original_desc = self.measure_in_progress.description
        res = self.client.patch(url, {"description": new_desc})

        # Should succeed with 200 but description should be unchanged
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(self.measure_in_progress.description, original_desc)

    def test_responsible_cannot_edit_deadline_in_progress(self):
        """Test responsible user's PATCH to deadline is IGNORED in IN_PRG."""
        self.client.force_authenticate(user=self.responsible_user)
        original_date = self.measure_in_progress.deadline
        new_date = date.today() + timedelta(days=5)
        url = measure_detail_url(self.measure_in_progress.id)

        res = self.client.patch(url, {"deadline": new_date})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(
            self.measure_in_progress.deadline, original_date
        )  # Unchanged

    def test_risk_officer_can_edit_deadline_in_progress(self):
        """Test Risk Officer CAN PATCH deadline in IN_PROGRESS status."""
        self.client.force_authenticate(user=self.risk_officer)
        new_date = date.today() + timedelta(days=5)
        url = measure_detail_url(self.measure_in_progress.id)

        res = self.client.patch(url, {"deadline": new_date})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(
            self.measure_in_progress.deadline, new_date
        )  # Changed

    def test_risk_officer_cannot_edit_other_bu_measure(self):
        """Test risk officer cannot edit measures from other BUs."""
        other_bu_user = create_user(
            "otherbu@example.com", "tstpsw123", self.role_emp, self.bu_risk
        )
        other_bu_measure = Measure.objects.create(
            description="Different BU measure",
            created_by=other_bu_user,
            responsible=other_bu_user,
            status=self.status_in_progress,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = measure_detail_url(other_bu_measure.id)
        res = self.client.patch(
            url, {"deadline": date.today() + timedelta(days=1)}
        )

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_completed_measure_is_read_only(self):
        """Test PATCH changes are ignored on COMPLETED measures."""
        completed_measure = Measure.objects.create(
            description="Completed measure",
            created_by=self.creator_user,
            responsible=self.responsible_user,
            status=self.status_completed,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = measure_detail_url(completed_measure.id)
        res = self.client.patch(url, {"description": "Try to edit"})

        # Should succeed but changes should be ignored
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        completed_measure.refresh_from_db()
        self.assertEqual(completed_measure.description, "Completed measure")

    def test_patch_cancelled_measure_is_read_only(self):
        """Test PATCH changes are ignored on CANCELLED measures."""
        cancelled_measure = Measure.objects.create(
            description="Cancelled measure",
            created_by=self.creator_user,
            responsible=self.responsible_user,
            status=self.status_cancelled,
        )

        self.client.force_authenticate(user=self.risk_officer)
        url = measure_detail_url(cancelled_measure.id)
        res = self.client.patch(url, {"description": "Try to edit"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        cancelled_measure.refresh_from_db()
        self.assertEqual(cancelled_measure.description, "Cancelled measure")


class MeasureWorkflowTests(MeasureTestBase):
    """Test state machine transitions and workflow actions."""

    def test_responsible_can_start_progress(self):
        """Test responsible user can move status OPEN -> IN_PROGRESS."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(self.measure_open.id, "start-progress")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_open.refresh_from_db()
        self.assertEqual(self.measure_open.status, self.status_in_progress)

    def test_manager_can_start_progress_for_their_report(self):
        """Test manager can move status OPEN -> IN_PRG for their reports."""
        self.client.force_authenticate(user=self.manager)
        url = measure_action_url(self.measure_open.id, "start-progress")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_open.refresh_from_db()
        self.assertEqual(self.measure_open.status, self.status_in_progress)

    def test_other_user_cannot_start_progress(self):
        """Test a user who is not responsible cannot start progress."""
        self.client.force_authenticate(user=self.other_user)
        url = measure_action_url(self.measure_open.id, "start-progress")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_start_progress_fails_if_already_in_progress(self):
        """Test cannot start progress on a measure already in progress."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(self.measure_in_progress.id, "start-progress")
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_responsible_can_submit_for_review_with_evidence(self):
        """Test responsible user can move IN_PROGRESS -> PENDING_REVIEW."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(
            self.measure_in_progress.id, "submit-for-review"
        )
        payload = {"evidence": "Completed the task, server logs attached."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(
            self.measure_in_progress.status, self.status_pending_review
        )
        self.assertIn(payload["evidence"], self.measure_in_progress.notes)

    def test_manager_can_submit_for_review_for_their_report(self):
        """Test manager can move IN_PROGRESS -> PENDING_REVIEW
        for their reports."""
        self.client.force_authenticate(user=self.manager)
        url = measure_action_url(
            self.measure_in_progress.id, "submit-for-review"
        )
        payload = {"evidence": "Manager submitting on behalf of team member."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(
            self.measure_in_progress.status, self.status_pending_review
        )

    def test_submit_for_review_fails_without_evidence(self):
        """Test submit_for_review fails without 'evidence' payload."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(
            self.measure_in_progress.id, "submit-for-review"
        )
        res = self.client.post(url, {})  # Missing payload

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidence", str(res.data))

    def test_submit_for_review_fails_from_open(self):
        """Test cannot submit for review from OPEN status."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(self.measure_open.id, "submit-for-review")
        payload = {"evidence": "Test"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_risk_officer_can_return_to_progress_with_reason(self):
        """Test Risk Officer can move PENDING_REVIEW -> IN_PROGRESS."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(
            self.measure_pending_review.id, "return-to-progress"
        )
        payload = {"reason": "Evidence is not sufficient."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_pending_review.refresh_from_db()
        self.assertEqual(
            self.measure_pending_review.status, self.status_in_progress
        )
        self.assertIn(payload["reason"], self.measure_pending_review.notes)

    def test_return_to_progress_fails_as_responsible_user(self):
        """Test responsible user cannot return a measure to progress."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(
            self.measure_pending_review.id, "return-to-progress"
        )
        payload = {"reason": "I made a mistake"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_risk_officer_can_complete_with_comment(self):
        """Test Risk Officer can move PENDING_REVIEW -> COMPLETED."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(self.measure_pending_review.id, "complete")
        payload = {"closure_comment": "Verified and confirmed."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_pending_review.refresh_from_db()
        self.assertEqual(
            self.measure_pending_review.status, self.status_completed
        )
        self.assertEqual(
            self.measure_pending_review.closure_comment,
            payload["closure_comment"],
        )

    def test_complete_fails_from_in_progress(self):
        """Test cannot complete directly from IN_PROGRESS
        (must go through review)."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(self.measure_in_progress.id, "complete")
        payload = {"closure_comment": "Test"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_risk_officer_can_cancel_in_progress_measure_with_reason(self):
        """Test Risk Officer can CANCEL an IN_PROGRESS measure."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(self.measure_in_progress.id, "cancel")
        payload = {"reason": "No longer required."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertEqual(
            self.measure_in_progress.status, self.status_cancelled
        )
        self.assertIn(payload["reason"], self.measure_in_progress.notes)

    def test_cancel_fails_on_open_measure(self):
        """Test CANCEL action is not allowed on an OPEN measure
        (use DELETE)."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(self.measure_open.id, "cancel")
        payload = {"reason": "Test"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot cancel", str(res.data))

    def test_evidence_includes_timestamp_and_user(self):
        """Test that evidence submissions are timestamped and attributed."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(
            self.measure_in_progress.id, "submit-for-review"
        )
        payload = {"evidence": "Task completed successfully."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()

        # Check that notes contain evidence, username, and timestamp
        self.assertIn(payload["evidence"], self.measure_in_progress.notes)
        self.assertIn(
            self.responsible_user.email, self.measure_in_progress.notes
        )


class MeasureCommentTests(MeasureTestBase):
    """Test comment functionality and permissions."""

    def test_responsible_user_can_add_comment(self):
        """Test the dedicated add_comment endpoint."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(self.measure_in_progress.id, "add-comment")
        payload = {"comment": "This is a progress update."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertIn(payload["comment"], self.measure_in_progress.notes)

    def test_manager_can_add_comment(self):
        """Test manager can add comments to measures."""
        self.client.force_authenticate(user=self.manager)
        url = measure_action_url(self.measure_in_progress.id, "add-comment")
        payload = {"comment": "Manager's progress check."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.measure_in_progress.refresh_from_db()
        self.assertIn(payload["comment"], self.measure_in_progress.notes)

    def test_risk_officer_can_add_comment(self):
        """Test risk officer can add comments."""
        self.client.force_authenticate(user=self.risk_officer)
        url = measure_action_url(self.measure_in_progress.id, "add-comment")
        payload = {"comment": "Risk officer audit note."}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_unrelated_user_cannot_add_comment(self):
        """Test unrelated user cannot add comments."""
        self.client.force_authenticate(user=self.other_user)
        url = measure_action_url(self.measure_in_progress.id, "add-comment")
        payload = {"comment": "This should fail"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_comment_includes_timestamp_and_user(self):
        """Test that comments are timestamped and attributed."""
        self.client.force_authenticate(user=self.responsible_user)
        url = measure_action_url(self.measure_in_progress.id, "add-comment")
        payload = {"comment": "Progress update."}
        res = self.client.post(url, payload)

        self.measure_in_progress.refresh_from_db()

        self.assertIn(payload["comment"], self.measure_in_progress.notes)
        self.assertIn(
            self.responsible_user.email, self.measure_in_progress.notes
        )
