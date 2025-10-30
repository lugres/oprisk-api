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
from .routing import evaluate_routing_for_incident

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


def _find_user_from_routing(routing_result: dict) -> User | None:
    """
    Attempts to find a single user matching the routing rule.
    Finds the first user that matches the combination of role and/or BU.
    """
    role_id = routing_result.get("route_to_role_id")
    bu_id = routing_result.get("route_to_bu_id")

    if not role_id and not bu_id:
        # Rule is incomplete, no one to assign
        return None

    query = User.objects.all()
    if role_id:
        query = query.filter(role_id=role_id)
    if bu_id:
        query = query.filter(business_unit_id=bu_id)

    return query.first()  # Returns the first matching user or None


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

    # --- New Routing Logic ---
    assigned_user = None
    routing_result = evaluate_routing_for_incident(incident)

    if routing_result:
        assigned_user = _find_user_from_routing(routing_result)

    # Apply assignment: Rule > Manager > None
    if assigned_user:
        incident.assigned_to = assigned_user
    elif user.manager:
        incident.assigned_to = user.manager  # Fallback logic
    else:
        incident.assigned_to = None
    # --- End New Routing Logic ---

    # Side-effect: Assign to manager if they exist
    # if user.manager:
    #     incident.assigned_to = user.manager

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


@transaction.atomic
def return_to_draft(
    *, incident: Incident, user: User, reason: str
) -> Incident:
    """Returns a PENDING_REVIEW incident to DRAFT, reason is required."""
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="DRAFT",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="DRAFT")

    # Apply side-effects
    incident.status = new_status
    incident.assigned_to = None  # Clear assignment when returned
    # Add reason to notes
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    note_prefix = (
        f"[{timestamp} Returned to Draft by {user.email}]: {reason}\n---\n"
    )
    incident.notes = note_prefix + (incident.notes or "")

    incident.save(
        update_fields=["status", "assigned_to", "updated_at", "notes"]
    )  # Add 'notes'/'reason' if used
    return incident


@transaction.atomic
def return_to_review(
    *, incident: Incident, user: User, reason: str
) -> Incident:
    """Returns a PENDING_VALIDATION incident to PENDING_REVIEW, with reason."""
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="PENDING_REVIEW",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="PENDING_REVIEW")

    # Apply side-effects
    incident.status = new_status
    # Re-assign back to the manager who originally reviewed it,
    # or creator's manager
    if incident.reviewed_by:
        incident.assigned_to = incident.reviewed_by  # Reassign to reviewer
    elif incident.created_by and incident.created_by.manager:
        incident.assigned_to = (
            incident.created_by.manager
        )  # Fallback to creator's manager
    else:
        incident.assigned_to = None  # Clear if no one to assign back to

    # Append reason to notes
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
    note_prefix = (
        f"[{timestamp} Returned to Review by {user.email}]: {reason}\n---\n"
    )
    incident.notes = note_prefix + (incident.notes or "")

    incident.save(
        update_fields=["status", "assigned_to", "updated_at", "notes"]
    )
    return incident


@transaction.atomic
def close_incident(*, incident: Incident, user: User) -> Incident:
    """Closes a VALIDATED incident."""
    transition_rules = _get_transition_rules()
    # Domain Layer validation
    validate_transition(
        from_status=incident.status.code,
        to_status="CLOSED",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="CLOSED")

    # Apply side-effects
    incident.status = new_status
    incident.closed_by = user
    incident.closed_at = timezone.now()  # Record closing time
    incident.assigned_to = None  # Clear assignment

    incident.save(
        update_fields=[
            "status",
            "closed_by",
            "closed_at",
            "assigned_to",
            "updated_at",
        ]
    )
    return incident
