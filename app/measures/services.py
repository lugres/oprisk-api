"""
Application layer - Django-aware orchestrator service for measure objects.
Enforces business rules.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import Measure, MeasureStatusRef

from .workflows import (
    MeasureTransitionError,
    MeasurePermissionError,
    append_to_notes,
)
from incidents.models import Incident, IncidentMeasure

User = get_user_model()


# --- CREATE & LINK ---


@transaction.atomic
def create_measure(
    *,
    user: User,
    description: str,
    responsible: User,
    deadline: timezone.datetime,
    incident_id: int = None,
) -> Measure:
    """
    Creates a new measure.
    The 'created_by' is set to the request user.
    The default status is set to 'OPEN' by the model's save() method.
    """
    measure = Measure.objects.create(
        description=description,
        responsible=responsible,
        deadline=deadline,
        created_by=user,
    )

    # Handle the "create-and-link" test case
    if incident_id:
        try:
            incident = Incident.objects.get(id=incident_id)
            # We can call our other service function here
            link_measure_to_incident(
                measure=measure, user=user, incident=incident
            )
        except Incident.DoesNotExist:
            # Fail silently, or raise a validation error if preferred
            pass

    return measure


@transaction.atomic
def link_measure_to_incident(
    *, measure: Measure, user: User, incident: Incident
):
    """
    Links a measure to an incident.
    """
    # Test for: test_link_to_incident_fails_if_measure_is_cancelled
    if measure.status.code == "CANCELLED":
        raise MeasureTransitionError("Cannot link a cancelled measure.")

    # Test for: test_link_to_incident_fails_if_already_linked
    link, created = IncidentMeasure.objects.get_or_create(
        incident=incident, measure=measure
    )

    if not created:
        raise MeasureTransitionError(
            f"Measure {measure.id} is already linked to Incident {incident.id}."
        )


@transaction.atomic
def unlink_measure_from_incident(
    *, measure: Measure, user: User, incident: Incident
):
    """
    Unlinks a measure from an incident.
    """
    # Test for: test_unlink_from_incident_fails_if_not_linked
    try:
        link = IncidentMeasure.objects.get(incident=incident, measure=measure)
        link.delete()
    except IncidentMeasure.DoesNotExist:
        raise MeasureTransitionError(
            f"Measure {measure.id} is not linked to Incident {incident.id}."
        )


# --- WORKFLOW ACTIONS ---


@transaction.atomic
def add_comment(*, measure: Measure, user: User, comment: str) -> Measure:
    """Appends a comment to the measure's notes."""
    append_to_notes(measure, user, "COMMENT", comment)
    measure.save(update_fields=["notes"])
    return measure


@transaction.atomic
def start_progress(*, measure: Measure, user: User) -> Measure:
    """
    Moves a measure from OPEN to IN_PROGRESS.
    Permission: Responsible user or their Manager.
    """
    # Test for: test_start_progress_fails_if_already_in_progress
    if measure.status.code != "OPEN":
        raise MeasureTransitionError(
            "Measure must be in OPEN status to start."
        )

    # Permission check (from tests)
    if not (
        user == measure.responsible or user == measure.responsible.manager
    ):
        raise MeasurePermissionError(
            "Only the responsible user or their manager can start progress."
        )

    measure.status = MeasureStatusRef.objects.get(code="IN_PROGRESS")
    measure.save(update_fields=["status", "updated_at"])
    return measure


@transaction.atomic
def submit_for_review(
    *, measure: Measure, user: User, evidence: str
) -> Measure:
    """
    Moves a measure from IN_PROGRESS to PENDING_REVIEW.
    Permission: Responsible user or their Manager.
    """
    # Test for: test_submit_for_review_fails_from_open
    if measure.status.code != "IN_PROGRESS":
        raise MeasureTransitionError(
            "Measure must be IN_PROGRESS to submit for review."
        )

    # Permission check (from tests)
    if not (
        user == measure.responsible or user == measure.responsible.manager
    ):
        raise MeasurePermissionError(
            "Only the responsible user or their manager can submit for review."
        )

    measure.status = MeasureStatusRef.objects.get(code="PENDING_REVIEW")
    append_to_notes(measure, user, "EVIDENCE", evidence)
    measure.save(update_fields=["status", "notes", "updated_at"])
    return measure


@transaction.atomic
def return_to_progress(
    *, measure: Measure, user: User, reason: str
) -> Measure:
    """
    Moves a measure from PENDING_REVIEW back to IN_PROGRESS.
    Permission: Risk Officer only.
    """
    # Test for: test_complete_fails_from_in_progress (and others)
    if measure.status.code != "PENDING_REVIEW":
        raise MeasureTransitionError(
            "Measure must be PENDING_REVIEW to be returned."
        )

    # Permission check (from tests)
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError(
            "Only a Risk Officer can return a measure."
        )

    measure.status = MeasureStatusRef.objects.get(code="IN_PROGRESS")
    append_to_notes(measure, user, "REASON FOR RETURN", reason)
    measure.save(update_fields=["status", "notes", "updated_at"])
    return measure


@transaction.atomic
def complete(
    *,
    measure: Measure,
    user: User,
    closure_comment: str,
) -> Measure:
    """
    Moves a measure from PENDING_REVIEW to COMPLETED.
    Permission: Risk Officer only.
    """
    # Test for: test_complete_fails_from_in_progress
    if measure.status.code != "PENDING_REVIEW":
        raise MeasureTransitionError(
            "Measure must be PENDING_REVIEW to be completed."
        )

    # Permission check (from tests)
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError(
            "Only a Risk Officer can complete a measure."
        )

    measure.status = MeasureStatusRef.objects.get(code="COMPLETED")
    measure.closure_comment = closure_comment
    measure.closed_at = timezone.now()
    measure.save(
        update_fields=["status", "closure_comment", "closed_at", "updated_at"]
    )
    return measure


@transaction.atomic
def cancel(*, measure: Measure, user: User, reason: str) -> Measure:
    """
    Moves a measure to CANCELLED.
    Permission: Risk Officer only.
    """
    # Test for: test_cancel_fails_on_open_measure
    if measure.status.code not in ["IN_PROGRESS", "PENDING_REVIEW"]:
        raise MeasureTransitionError(
            "Cannot cancel a measure that is not IN_PROGRESS or PENDING_REVIEW. Use DELETE for OPEN measures."
        )

    # Permission check (from tests)
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError(
            "Only a Risk Officer can cancel a measure."
        )

    measure.status = MeasureStatusRef.objects.get(code="CANCELLED")
    measure.closed_at = timezone.now()
    append_to_notes(measure, user, "REASON FOR CANCELLATION", reason)
    measure.save(update_fields=["status", "notes", "closed_at", "updated_at"])
    return measure
