"""
Application layer - Django-aware orchestrator service for incident objects.
Loads transition rules, calls Domain for validation, handles DB transactions.
Updates SLA details, evaluates custom routing rules, triggers notifications.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Incident, IncidentStatusRef, AllowedTransition
from .workflows import validate_transition

User = get_user_model()


# Default fallback rules based on core business logic
DEFAULT_TRANSITIONS = {
    "DRAFT": {
        "PENDING_REVIEW": ["Employee", "Manager"]  # Allow creators to submit
    },
    "PENDING_REVIEW": {
        "PENDING_VALIDATION": ["Manager"],  # Manager reviews/verifies
        "DRAFT": ["Manager"],  # Manager can return to draft
    },
    "PENDING_VALIDATION": {
        "VALIDATED": ["Risk Officer", "Group ORM"],  # ORM validates/authorizes
        "PENDING_REVIEW": ["Risk Officer", "Group ORM"],  # ORM can return
    },
    "VALIDATED": {"CLOSED": ["Risk Officer", "Group ORM"]},  # ORM closes
}


# --- Business Rules Loading (Data-Driven) ---
def _get_transition_rules() -> dict:
    """
    Fetches the state machine's rules from the database and builds the
    Python dictionary needed by the Domain layer. Falls back to default.
    """
    rules = {}
    transitions = AllowedTransition.objects.select_related(
        "from_status", "to_status", "role"
    ).all()

    # Use the default if DB config table is empty
    if not transitions:
        return DEFAULT_TRANSITIONS

    for t in transitions:
        if t.from_status.code not in rules:
            rules[t.from_status.code] = {}
        if t.to_status.code not in rules[t.from_status.code]:
            rules[t.from_status.code][t.to_status.code] = []
        rules[t.from_status.code][t.to_status.code].append(t.role.name)
    return rules


def _find_risk_officer(business_unit):
    """
    Finds a Risk Officer.
    Priority 1: A Risk Officer in the same Business Unit.
    Priority 2: Any Risk Officer in the system.
    """
    if business_unit:
        # Q objects are used to build complex queries
        risk_officer = User.objects.filter(
            Q(role__name="Risk Officer") & Q(business_unit=business_unit)
        ).first()
        if risk_officer:
            return risk_officer

    # Fallback: find any Risk Officer
    return User.objects.filter(role__name="Risk Officer").first()


# --- Service Functions ---
@transaction.atomic
def create_incident(*, user: User, **kwargs) -> Incident:
    """Service function to create a new incident with default DRAFT status."""
    draft_status = IncidentStatusRef.objects.get(code="DRAFT")
    # The 'status' key is removed from kwargs if it exists to enforce default
    kwargs.pop("status", None)
    return Incident.objects.create(
        created_by=user, status=draft_status, **kwargs
    )


@transaction.atomic
def submit_incident(*, incident: Incident, user: User) -> Incident:
    """Submits an incident for review."""
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="PENDING_REVIEW",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )
    pending_status = IncidentStatusRef.objects.get(code="PENDING_REVIEW")
    incident.status = pending_status

    # Side-effect: Assign to manager if they exist
    if user.manager:
        incident.assigned_to = user.manager

    # Placeholder for future logic
    # if incident.created_by.manager:
    #     incident.assigned_to = incident.created_by.manager
    # calculate_sla(incident)
    # check_routing_rules(incident)

    incident.save(update_fields=["status", "assigned_to", "updated_at"])
    return incident


@transaction.atomic
def review_incident(*, incident: Incident, user: User) -> Incident:
    """Reviews a PENDING_REVIEW incident, moving it to PENDING_VALIDATION."""
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="PENDING_VALIDATION",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="PENDING_VALIDATION")
    new_assigned_user = _find_risk_officer(incident.business_unit)
    incident.status = new_status
    incident.reviewed_by = user  # Log who reviewed it
    incident.assigned_to = new_assigned_user  # Assign to the Risk Officer

    incident.save(
        update_fields=["status", "assigned_to", "reviewed_by", "updated_at"]
    )
    return incident


@transaction.atomic
def validate_incident(*, incident: Incident, user: User) -> Incident:
    """Validates a PENDING_VALIDATION incident, moving it to VALIDATED."""
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="VALIDATED",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="VALIDATED")
    incident.status = new_status
    incident.validated_by = user
    incident.validated_at = timezone.now()
    incident.assigned_to = None

    incident.save(
        update_fields=[
            "status",
            "validated_by",
            "validated_at",
            "assigned_to",
            "updated_at",
        ]
    )
    return incident
