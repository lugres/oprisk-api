"""
Application layer - orchestrator service for risk objects.
Enforces business rules and data integrity.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Risk, RiskStatus, IncidentRisk, RiskMeasure, RiskControl
from .workflows import (
    RiskTransitionError,
    RiskPermissionError,
    RiskValidationError,
    validate_transition,
    get_available_transitions,
    get_user_permissions,
    get_contextual_role_name,
    can_user_create_risk,
    can_user_add_comment,
    can_user_link_controls,
    validate_bu_alignment_for_control_linking,
    validate_risk_status_for_linking,
    validate_risk_status_for_unlinking,
)
from incidents.models import Incident
from measures.models import Measure
from controls.models import Control
from controls.workflows import is_group_risk_officer

User = get_user_model()

# --- HELPER FUNCTIONS ---


def _append_to_notes(risk: Risk, user: User, note_prefix: str, content: str):
    """Appends a timestamped entry to the risk's notes field."""
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    new_note = (
        f"[{timestamp} - {user.email} - {note_prefix}]:\n"
        f"{content}\n"
        f"{'-' * 20}\n"
    )
    risk.notes = new_note + risk.notes


def _check_user_can_link_controls(user: User) -> None:
    """
    Application-level permission check for linking.
    Raises RiskPermissionError if not allowed.
    """
    if not can_user_link_controls(
        user.role.name if user.role else "",
    ):
        raise RiskPermissionError(
            "Only Risk Officers can link/unlink controls to risks."
        )


# --- CONTEXTUAL DATA SERVICE ---


def get_risk_context(risk: Risk, user: User) -> dict:
    """
    [APPLICATION SERVICE]
    Gathers contextual data for the RiskDetailSerializer.
    """
    role_name = get_contextual_role_name(user)

    # Get available transitions
    available_transitions = get_available_transitions(risk.status, role_name)

    # Get permissions
    permissions = get_user_permissions(risk, user, available_transitions)

    return {
        "available_transitions": available_transitions,
        "permissions": permissions,
    }


# --- VISIBILITY FILTER ---


def get_risk_visibility_filter(user) -> Q:
    """
    Returns a Q filter for risks visible to the given user.
    """
    if not user or not user.role:
        return Q(pk__in=[])

    if user.role.name == "Risk Officer":
        # Risk Officers see all in their BU
        return Q(business_unit=user.business_unit)

    if user.role.name == "Manager":
        # Managers see risks in their BU (broader than just owned)
        return Q(business_unit=user.business_unit)

    # Employee: Limited visibility (e.g., by BU or assignment)
    # For now, let's restrict to BU to match tests
    return Q(business_unit=user.business_unit)


# --- CRUD OPERATIONS ---


@transaction.atomic
def create_risk(
    *,
    user: User,
    title: str,
    description: str,
    risk_category,
    business_unit,
    owner,
    **kwargs,
) -> Risk:
    """
    Creates a new risk. Enforces creation permissions.
    """
    if not can_user_create_risk(user):
        raise RiskPermissionError(
            (
                "Only users with the Manager or Risk Officer role"
                " can create risks."
            )
        )

    # Validate owner is in same BU (Business Rule)
    if owner.business_unit != business_unit:
        raise RiskPermissionError(
            "Owner must belong to the selected Business Unit."
        )

    risk = Risk.objects.create(
        title=title,
        description=description,
        risk_category=risk_category,
        business_unit=business_unit,
        owner=owner,
        created_by=user,
        status=RiskStatus.DRAFT,
        **kwargs,
    )
    return risk


@transaction.atomic
def delete_risk(*, risk: Risk, user: User):
    """
    Service to delete a risk.
    Permission: Creator/Risk Officer AND status must be DRAFT.
    """
    # 1. Status Check
    if risk.status != RiskStatus.DRAFT:
        raise RiskPermissionError("Only DRAFT risks can be deleted.")

    # 2. Permission Check (Creator or Risk Officer)
    is_creator = risk.created_by and user.id == risk.created_by.id
    is_risk_officer = user.role and user.role.name == "Risk Officer"

    if not (is_creator or is_risk_officer):
        raise RiskPermissionError(
            "You do not have permission to delete this risk."
        )

    risk.delete()


@transaction.atomic
def update_risk(*, risk: Risk, user: User, data: dict) -> Risk:
    """
    Service to update a risk instance with validated data.
    """
    # Note: Field-level permissions are handled by the serializer
    # before reaching here. This service performs the persistence.

    # Update fields
    for field, value in data.items():
        setattr(risk, field, value)

    risk.save()
    return risk


# --- WORKFLOW ACTIONS ---


@transaction.atomic
def add_comment(*, risk: Risk, user: User, comment: str) -> Risk:
    """Add a comment to a risk."""
    if risk.status == RiskStatus.RETIRED:
        raise RiskTransitionError("retired risk cannot be modified")

    if not can_user_add_comment(risk, user):
        raise RiskPermissionError("You do not have permission to comment.")

    _append_to_notes(risk, user, "COMMENT", comment)
    risk.save(update_fields=["notes"])
    return risk


@transaction.atomic
def submit_for_review(*, risk: Risk, user: User) -> Risk:
    """DRAFT -> ASSESSED"""
    role = get_contextual_role_name(user)
    validate_transition(risk.status, RiskStatus.ASSESSED, role)

    # Business Validation
    if not (risk.inherent_likelihood and risk.inherent_impact):
        raise RiskTransitionError(
            "Inherent risk scores required before submission."
        )
    if not risk.risk_category:
        raise RiskTransitionError("Risk category must be selected.")

    # Check mapping consistency if basel is present
    if (
        risk.basel_event_type
        and risk.basel_event_type
        not in risk.risk_category.basel_event_types.all()
    ):
        raise RiskTransitionError(
            "Basel event type is not valid for risk category."
        )

    risk.status = RiskStatus.ASSESSED
    risk.submitted_for_review_at = timezone.now()
    risk.submitted_by = user
    risk.save()
    return risk


@transaction.atomic
def approve(*, risk: Risk, user: User) -> Risk:
    """ASSESSED -> ACTIVE"""
    role = get_contextual_role_name(user)
    validate_transition(risk.status, RiskStatus.ACTIVE, role)

    # Business Validation
    if not (risk.residual_likelihood and risk.residual_impact):
        raise RiskTransitionError("Residual risk scores required.")
    if not risk.basel_event_type:
        raise RiskTransitionError("Basel event type must be selected.")

    # Check mapping consistency
    if risk.basel_event_type not in risk.risk_category.basel_event_types.all():
        raise RiskTransitionError(
            "Basel event type is not valid for risk category."
        )

    # Check score logic
    inherent = risk.inherent_risk_score or 0
    residual = risk.residual_risk_score or 0
    if residual > inherent:
        raise RiskTransitionError(
            "Residual risk score cannot exceed inherent risk score."
        )

    # At least one control must be linked
    if risk.controls.count() == 0:
        raise RiskTransitionError(
            "At least one control must be linked before approval."
        )

    risk.status = RiskStatus.ACTIVE
    risk.validated_at = timezone.now()
    risk.validated_by = user
    risk.save()
    return risk


@transaction.atomic
def send_back(*, risk: Risk, user: User, reason: str) -> Risk:
    """ASSESSED -> DRAFT"""
    role = get_contextual_role_name(user)
    validate_transition(risk.status, RiskStatus.DRAFT, role)

    risk.status = RiskStatus.DRAFT
    _append_to_notes(risk, user, "RETURNED FOR REVISION", reason)
    risk.save()
    return risk


@transaction.atomic
def request_reassessment(*, risk: Risk, user: User) -> Risk:
    """ACTIVE -> ASSESSED"""
    role = get_contextual_role_name(user)
    validate_transition(risk.status, RiskStatus.ASSESSED, role)

    risk.status = RiskStatus.ASSESSED
    risk.submitted_for_review_at = timezone.now()
    # submitted_by remains original or could be updated
    risk.save()
    return risk


@transaction.atomic
def retire(*, risk: Risk, user: User, reason: str) -> Risk:
    """ACTIVE/ASSESSED -> RETIRED"""
    role = get_contextual_role_name(user)
    validate_transition(risk.status, RiskStatus.RETIRED, role)

    risk.status = RiskStatus.RETIRED
    risk.retirement_reason = reason
    risk.save()
    return risk


# --- LINKING ---


@transaction.atomic
def link_incident(*, risk: Risk, user: User, incident: Incident):
    """Links a risk to an incident."""
    if risk.status == RiskStatus.RETIRED:
        raise RiskTransitionError("Cannot link retired risks.")

    link, created = IncidentRisk.objects.get_or_create(
        risk=risk, incident=incident
    )
    if not created:
        raise RiskTransitionError("Incident already linked.")


@transaction.atomic
def unlink_incident(*, risk: Risk, user: User, incident: Incident):
    """Unlinks a risk from an incident."""
    try:
        link = IncidentRisk.objects.get(risk=risk, incident=incident)
        link.delete()
    except IncidentRisk.DoesNotExist:
        raise RiskTransitionError("Incident is not linked.")


@transaction.atomic
def link_measure(*, risk: Risk, user: User, measure: Measure):
    """Links a risk to a measure."""
    if risk.status == RiskStatus.RETIRED:
        raise RiskTransitionError("Cannot link measures to retired risks.")

    link, created = RiskMeasure.objects.get_or_create(
        risk=risk, measure=measure
    )
    if not created:
        raise RiskTransitionError("Measure already linked.")


@transaction.atomic
def unlink_measure(*, risk: Risk, user: User, measure: Measure):
    """Unlinks a risk from a measure."""
    try:
        link = RiskMeasure.objects.get(risk=risk, measure=measure)
        link.delete()
    except RiskMeasure.DoesNotExist:
        raise RiskTransitionError("Measure is not linked.")


@transaction.atomic
def link_control(
    *, risk: Risk, user: User, control: Control, notes: str = ""
) -> RiskControl:
    """
    Links a LOCAL control to a risk.
    Application service: orchestrates all validations.
    """

    # 1. Permission check
    _check_user_can_link_controls(user)

    # 2. Control intrinsic linkability (Controls domain)
    if not control.is_linkable:
        reasons = control.get_linkability_reasons()
        error_parts = [r.message for r in reasons]
        suggestion_parts = [r.suggestion for r in reasons if r.suggestion]

        error_msg = "Cannot link control: " + " ".join(error_parts)
        if suggestion_parts:
            error_msg += " " + " ".join(suggestion_parts)

        raise RiskValidationError(error_msg)

    # 3. BU alignment check (Risks domain)
    is_group_ro = is_group_risk_officer(user)
    is_valid, error = validate_bu_alignment_for_control_linking(
        control_bu_id=(
            control.business_unit.id if control.business_unit else None
        ),
        control_bu_name=(
            control.business_unit.name if control.business_unit else ""
        ),
        risk_bu_id=risk.business_unit.id if risk.business_unit else None,
        risk_bu_name=risk.business_unit.name if risk.business_unit else "",
        is_group_ro=is_group_ro,
    )
    if not is_valid:
        raise RiskValidationError(error)

    # 4. Risk status check (Risks domain)
    is_valid, error = validate_risk_status_for_linking(risk.status)
    if not is_valid:
        raise RiskValidationError(error)

    # 5. Duplicate check (Application concern)
    if RiskControl.objects.filter(risk=risk, control=control).exists():
        raise RiskValidationError(
            f"Control '{control.title}' is already linked to this risk."
        )

    # 6. Create link
    link = RiskControl.objects.create(
        risk=risk, control=control, linked_by=user, notes=notes
    )

    return link


@transaction.atomic
def unlink_control(*, risk: Risk, user: User, control: Control):
    """
    Unlinks a control from a risk.
    Application service: orchestrates all validations.
    """

    # 1. Permission check
    _check_user_can_link_controls(user)

    # 2. Check if linked (Application concern)
    try:
        link = RiskControl.objects.get(risk=risk, control=control)
    except RiskControl.DoesNotExist:
        raise RiskValidationError("Control is not linked to this risk.")

    # 3. Risk status and control count check (Risks domain)
    remaining_count = risk.controls.exclude(id=control.id).count()
    is_valid, error = validate_risk_status_for_unlinking(
        risk_status=risk.status, remaining_controls_count=remaining_count
    )
    if not is_valid:
        raise RiskValidationError(error)

    # 4. Delete link
    link.delete()
