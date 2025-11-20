"""
Application layer - Django-aware orchestrator service for measure objects.
Enforces business rules.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import Measure, MeasureStatusRef, MeasureEditableField

from .workflows import (
    MeasureTransitionError,
    MeasurePermissionError,
    validate_transition,
    get_available_transitions,
    get_user_permissions,
    get_contextual_role_name,
    can_user_delete_measure,
    can_user_add_comment,
)
from incidents.models import Incident, IncidentMeasure

User = get_user_model()

# --- HELPER FUNCTIONS ---


# --- moved from workflow.py ---
def _append_to_notes(
    measure: Measure, user: User, note_prefix: str, content: str
):
    """
    Appends a new, timestamped entry to the measure's 'notes' field.
    e.g., [2025-11-14 09:30 - user@example.com - EVIDENCE]:
    Submitted for review.
    """
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    new_note = (
        f"[{timestamp} - {user.email} - {note_prefix}]:\n"
        f"{content}\n"
        f"{'-' * 20}\n"
    )
    # Prepend new notes to the top
    measure.notes = new_note + measure.notes


# --- CONTEXTUAL DATA SERVICE (for retrieve()) ---


def get_measure_context(measure: Measure, user: User) -> dict:
    """
    [APPLICATION SERVICE]
    Gathers all contextual data for the MeasureDetailSerializer.
    This is the single source of truth for this logic.
    """
    # 1. Get contextual role (called ONCE)
    contextual_role_name = get_contextual_role_name(measure, user)

    # 2. Get available transitions (called ONCE)
    available_transitions = get_available_transitions(
        measure.status.code, contextual_role_name
    )

    # 3. Get editable fields (DB query, belongs in service layer)
    editable_fields = set(
        MeasureEditableField.objects.filter(
            status=measure.status, role=user.role
        ).values_list("field_name", flat=True)
    )

    # 4. Get fine-grained permissions (pass transitions in)
    permissions = get_user_permissions(
        measure, user, editable_fields, available_transitions
    )

    return {
        "available_transitions": available_transitions,
        "permissions": permissions,
    }


# --- CREATE, DELETE, LINK ---


@transaction.atomic
def create_measure(
    *,
    user: User,
    description: str,
    responsible: User,
    deadline: timezone.datetime,
    incident_id=None,  # incident_id can be obj or int
) -> Measure:
    """
    Creates a new measure.
    The 'created_by' is set to the request user.
    The default status is set to 'OPEN' by the model's save() method.
    """
    # Check creation permission first

    # if not user.role or user.role.name not in ("Manager", "Risk Officer"):
    #     raise MeasurePermissionError(
    #         "Only users with the Manager or Risk Officer role can create measures."
    #     )

    measure = Measure.objects.create(
        description=description,
        responsible=responsible,
        deadline=deadline,
        created_by=user,
    )

    # Handle the "create-and-link" test case
    # No need for try/except block as incident_id is pre-validated
    # by MeasureCreateSerializer.
    if incident_id:
        # If it's an Incident object, use it. If it's an int, get it.
        if isinstance(incident_id, Incident):
            incident = incident_id
        else:
            # safe - serializer already validated it exists
            incident = Incident.objects.get(id=incident_id)

        # We can call our other service function here
        link_measure_to_incident(measure=measure, user=user, incident=incident)

    return measure


# moved from the ViewSet
@transaction.atomic
def delete_measure(*, measure: Measure, user: User):
    """
    Service to delete a measure, enforcing business rules.
    Permission: Creator/Manager AND status must be OPEN.
    """
    # 1. Permission & Status check by calling pure func from Domain
    if not can_user_delete_measure(measure, user):
        raise MeasurePermissionError(
            "You do not have permission to delete this measure."
        )

    # 2. Execution
    measure.delete()


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
            f"Measure {measure.id} is already linked to "
            f"Incident {incident.id}."
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
    # No transition validation needed, just a permission check by Domain
    if not can_user_add_comment(measure, user):
        raise MeasurePermissionError(
            "You do not have permission to comment on this measure."
        )

    _append_to_notes(measure, user, "COMMENT", comment)
    measure.save(update_fields=["notes"])
    return measure


@transaction.atomic
def start_progress(*, measure: Measure, user: User) -> Measure:
    """
    Moves a measure from OPEN to IN_PROGRESS.
    Permission: Responsible user or their Manager.
    """
    role = get_contextual_role_name(measure, user)
    validate_transition(measure.status.code, "IN_PROGRESS", role)

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
    role = get_contextual_role_name(measure, user)
    validate_transition(measure.status.code, "PENDING_REVIEW", role)

    measure.status = MeasureStatusRef.objects.get(code="PENDING_REVIEW")
    _append_to_notes(measure, user, "EVIDENCE", evidence)
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
    # Check permission FIRST - only Risk Officer can do this
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError(
            "Only Risk Officers can return measures to progress."
        )

    # Then validate the state transition
    role = get_contextual_role_name(measure, user)
    validate_transition(measure.status.code, "IN_PROGRESS", role)

    measure.status = MeasureStatusRef.objects.get(code="IN_PROGRESS")
    _append_to_notes(measure, user, "REASON FOR RETURN", reason)
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
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError(
            "Only Risk Officers can complete measures."
        )

    role = get_contextual_role_name(measure, user)
    validate_transition(measure.status.code, "COMPLETED", role)

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
    if not user.role or user.role.name != "Risk Officer":
        raise MeasurePermissionError("Only Risk Officers can cancel measures.")

    role = get_contextual_role_name(measure, user)
    validate_transition(measure.status.code, "CANCELLED", role)

    measure.status = MeasureStatusRef.objects.get(code="CANCELLED")
    measure.closed_at = timezone.now()
    _append_to_notes(measure, user, "REASON FOR CANCELLATION", reason)
    measure.save(update_fields=["status", "notes", "closed_at", "updated_at"])
    return measure
