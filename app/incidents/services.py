"""
Application layer - Django-aware orchestrator service for incident objects.
Loads transition rules, calls Domain for validation, handles DB transactions.
Updates SLA details, evaluates custom routing rules, triggers notifications.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    Incident,
    IncidentStatusRef,
    AllowedTransition,
    SlaConfig,
    IncidentRequiredField,
)
from .workflows import validate_transition, RequiredFieldsError
from .routing import evaluate_routing_for_incident
from notifications.models import Notification

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


# --- SLA helper ---
def _get_sla_days(key: str, default: int) -> int:
    """Fetches an SLA configuration value from the DB, with a fallback."""
    try:
        return SlaConfig.objects.get(key=key).value_int
    except SlaConfig.DoesNotExist:
        return default


# --- Validation Helper Function ---
def _validate_required_fields(incident: Incident, target_status_code: str):
    """
    Checks if an incident has all required fields for the target status.
    Raises RequiredFieldsError if any fields are missing.
    """
    try:
        # Get the status we are transitioning TO
        target_status = IncidentStatusRef.objects.get(code=target_status_code)
    except IncidentStatusRef.DoesNotExist:
        return  # This shouldn't happen if workflows are set up, safe to exit

    # Find all fields marked as required for this target status
    required_fields = IncidentRequiredField.objects.filter(
        status=target_status
    )
    missing_fields = []

    for field in required_fields:
        field_name = field.field_name
        # Check if the attribute on the incident is None
        # This works for Null ForeignKeys, empty DecimalFields, etc.
        if getattr(incident, field_name, None) is None:
            missing_fields.append(field_name)

    if missing_fields:
        # If any fields are missing, raise the specific error
        field_list = ", ".join(missing_fields)
        raise RequiredFieldsError(
            f"Fields {field_list} are required for {target_status_code}."
        )


# --- Service Functions ---


@transaction.atomic
def create_incident(*, user: User, **kwargs) -> Incident:
    """Service function to create a new incident with default DRAFT status."""
    draft_status = IncidentStatusRef.objects.get(code="DRAFT")
    # The 'status' key is removed from kwargs if it exists to enforce default
    kwargs.pop("status", None)

    # --- Set initial SLA ---
    draft_days = _get_sla_days(key="draft_days", default=7)
    draft_due_at = timezone.now() + timedelta(days=draft_days)
    kwargs.pop("draft_due_at", None)
    kwargs["review_due_at"] = None
    kwargs["validation_due_at"] = None

    return Incident.objects.create(
        created_by=user,
        status=draft_status,
        draft_due_at=draft_due_at,
        **kwargs,
    )


@transaction.atomic
def submit_incident(*, incident: Incident, user: User) -> Incident:
    """Submits an incident for review and applies routing/SLA."""

    # --- Field Validation ---
    # Check fields required for the *target* status 'PENDING_REVIEW'
    _validate_required_fields(incident, "PENDING_REVIEW")

    # --- Workflow Validation ---
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="PENDING_REVIEW",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )
    pending_status = IncidentStatusRef.objects.get(code="PENDING_REVIEW")
    incident.status = pending_status

    # --- Reverted routing logic ---
    # Primary workflow stays unchanged (Employee -> Manager -> Risk),
    # instead a notification is triggered when routing rule is matched.
    # Assignment is now simple: just assign to the manager.
    if user.manager:
        incident.assigned_to = user.manager
    else:
        incident.assigned_to = None  # Or assign to a default review pool
    # --- End reverted routing logic ---

    # --- SLA logic ---
    review_days = _get_sla_days(key="review_days", default=5)
    incident.review_due_at = timezone.now() + timedelta(days=review_days)
    incident.draft_due_at = None  # Clear old timer

    # Placeholder for future logic
    # calculate_sla(incident)
    # check_routing_rules(incident)

    incident.save(
        update_fields=[
            "status",
            "assigned_to",
            "updated_at",
            "review_due_at",
            "draft_due_at",
        ]
    )
    return incident


@transaction.atomic
def review_incident(*, incident: Incident, user: User) -> Incident:
    """Reviews a PENDING_REVIEW incident, moving it to PENDING_VALIDATION.
    Assigns to Risk Officer, triggers notifications, and sets SLA."""

    # --- Field Validation ---
    # Check fields required for the *target* status 'PENDING_VALIDATION'
    _validate_required_fields(incident, "PENDING_VALIDATION")

    # --- Workflow Validation ---
    transition_rules = _get_transition_rules()
    validate_transition(
        from_status=incident.status.code,
        to_status="PENDING_VALIDATION",
        role_name=user.role.name if user.role else "",
        allowed_transitions=transition_rules,
    )

    new_status = IncidentStatusRef.objects.get(code="PENDING_VALIDATION")

    # --- Primary workflow (ownership) ---
    new_assigned_user = _find_risk_officer(incident.business_unit)
    incident.status = new_status
    incident.reviewed_by = user  # Log who reviewed it
    incident.assigned_to = new_assigned_user  # Assign to the Risk Officer

    # --- SLA logic ---
    validation_days = _get_sla_days(key="validation_days", default=10)
    incident.validation_due_at = timezone.now() + timedelta(
        days=validation_days
    )
    incident.review_due_at = None  # Clear old timer

    incident.save(
        update_fields=[
            "status",
            "assigned_to",
            "reviewed_by",
            "updated_at",
            "validation_due_at",
            "review_due_at",
        ]
    )

    # --- Parallel workflow (awareness) ---
    routing_result = evaluate_routing_for_incident(incident)
    if routing_result:
        # A rule matched. Create a notification.
        Notification.objects.create(
            entity_type=Notification.EntityType.INCIDENT,
            entity_id=incident.id,
            event_type=Notification.EventType.ROUTING_NOTIFY,
            triggered_by=user,
            recipient_role_id=routing_result.get("route_to_role_id"),
            # Note: recipient_role_id is used to match the routing rule's
            # A Celery task would later find all users with this role
            # and create UserNotification entries for them.
            routing_rule_id=routing_result.get("rule_id"),
            payload={
                "title": incident.title,
                "message": f"Incident '{incident.title}' was reviewed "
                f"and requires awareness.",
                "incident_url": f"/incidents/{incident.id}/",  # Example pld
            },
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

    # --- SLA logic ---
    incident.validation_due_at = None  # Clear old timer

    incident.save(
        update_fields=[
            "status",
            "validated_by",
            "validated_at",
            "assigned_to",
            "updated_at",
            "validation_due_at",
        ]
    )
    return incident


@transaction.atomic
def return_to_draft(
    *, incident: Incident, user: User, reason: str
) -> Incident:
    """Returns a PENDING_REVIEW incident to DRAFT, reason is required,
    resets SLA."""
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

    # --- SLA logic ---
    draft_days = _get_sla_days(key="draft_days", default=7)
    incident.draft_due_at = timezone.now() + timedelta(days=draft_days)
    incident.review_due_at = None  # Clear old timer

    incident.save(
        update_fields=[
            "status",
            "assigned_to",
            "updated_at",
            "notes",
            "draft_due_at",
            "review_due_at",
        ]
    )
    return incident


@transaction.atomic
def return_to_review(
    *, incident: Incident, user: User, reason: str
) -> Incident:
    """Returns a PENDING_VALIDATION incident to PENDING_REVIEW, with reason,
    resets SLA."""
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

    # --- SLA logic ---
    review_days = _get_sla_days(key="review_days", default=5)
    incident.review_due_at = timezone.now() + timedelta(days=review_days)
    incident.validation_due_at = None  # Clear old timer

    incident.save(
        update_fields=[
            "status",
            "assigned_to",
            "updated_at",
            "notes",
            "review_due_at",
            "validation_due_at",
        ]
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
