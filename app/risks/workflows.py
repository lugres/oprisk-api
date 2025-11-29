"""
Domain layer: pure, Django-unaware state machine for risks.
Validates risk transitions as prescribed by business rules.
"""


class RiskTransitionError(Exception):
    """Custom exception for invalid state transitions."""

    pass


class RiskPermissionError(Exception):
    """Custom exception for permission failures on risks."""

    pass


# --- 1. Transition Validation ---

# Map status strings to role requirements
ALLOWED_TRANSITIONS = {
    "DRAFT": {
        "ASSESSED": ["Manager", "Risk Officer"],  # submit_for_review
        "ACTIVE": ["Risk Officer"],  # direct_activate
    },
    "ASSESSED": {
        "ACTIVE": ["Risk Officer"],  # approve
        "DRAFT": ["Risk Officer"],  # send_back
        "RETIRED": ["Risk Officer"],  # retire
    },
    "ACTIVE": {
        "ASSESSED": ["Risk Officer"],  # request_reassessment
        "RETIRED": ["Risk Officer"],  # retire
    },
    "RETIRED": {},  # Terminal state
}


def validate_transition(
    from_status_code: str, to_status_code: str, role_name: str
):
    """
    Validates if a role is allowed to perform a state transition.
    """
    allowed_roles = ALLOWED_TRANSITIONS.get(from_status_code, {}).get(
        to_status_code
    )

    if not allowed_roles:
        raise RiskTransitionError(
            f"Transition from '{from_status_code}' to '{to_status_code}'"
            " is not defined."
        )

    if role_name not in allowed_roles:
        raise RiskPermissionError(
            f"Role '{role_name}' is not authorized to move from "
            f"'{from_status_code}' to '{to_status_code}'."
        )

    return True


# --- 2. Contextual Permissions (for serializers/views) ---


def get_contextual_role_name(user) -> str:
    """
    [PURE DOMAIN LOGIC]
    Returns the user's role name or 'Unknown'.
    In Risks app, explicit ownership doesn't change the transition role
    (only Manager/Risk Officer roles matter for transitions).
    """
    if not user or not user.role:
        return "Unknown"
    return user.role.name


def get_available_transitions(
    risk_status_code: str, user_role_name: str
) -> list:
    """
    [PURE DOMAIN LOGIC]
    Gets a list of available transition actions based on state and role.
    """
    transitions = []
    possible_transitions = ALLOWED_TRANSITIONS.get(risk_status_code, {})

    for to_status, allowed_roles in possible_transitions.items():
        if user_role_name in allowed_roles:
            # Map specific state pairs to Action Names
            action_map = {}

            if risk_status_code == "DRAFT" and to_status == "ASSESSED":
                action_map = {
                    "action": "submit-for-review",
                    "name": "Submit for Review",
                }
            elif risk_status_code == "ASSESSED" and to_status == "ACTIVE":
                action_map = {"action": "approve", "name": "Approve Risk"}
            elif risk_status_code == "ASSESSED" and to_status == "DRAFT":
                action_map = {
                    "action": "send-back",
                    "name": "Send Back for Revision",
                }
            elif risk_status_code == "ACTIVE" and to_status == "ASSESSED":
                action_map = {
                    "action": "request-reassessment",
                    "name": "Request Reassessment",
                }
            elif to_status == "RETIRED":
                action_map = {"action": "retire", "name": "Retire Risk"}

            if action_map:
                transitions.append(action_map)

    return transitions


def get_user_permissions(risk, user, available_transitions: list) -> dict:
    """
    [PURE DOMAIN LOGIC]
    Calculates fine-grained permissions (edit/delete).
    """
    role_name = user.role.name if user.role else "Unknown"

    # 1. can_edit
    # Manager can edit in DRAFT.
    # Risk Officer can edit in DRAFT, ASSESSED, ACTIVE (limited fields).
    can_edit = False
    if risk.status == "DRAFT" and role_name in ["Manager", "Risk Officer"]:
        can_edit = True
    elif risk.status in ["ASSESSED", "ACTIVE"] and role_name == "Risk Officer":
        can_edit = True

    # 2. can_delete
    # Only Creator or Risk Officer can delete, and ONLY in DRAFT.
    can_delete = False
    if risk.status == "DRAFT":
        is_creator = risk.created_by and user.id == risk.created_by.id
        if is_creator or role_name == "Risk Officer":
            can_delete = True

    # 3. can_transition
    can_transition = bool(available_transitions)

    return {
        "can_edit": can_edit,
        "can_delete": can_delete,
        "can_transition": can_transition,
    }


# --- 3. User Permission Helpers ---


def can_user_create_risk(user) -> bool:
    """Only Managers and Risk Officers can create risks."""
    return user.role and user.role.name in ("Manager", "Risk Officer")


def can_user_add_comment(risk, user) -> bool:
    """
    Participant check for comments:
    - Owner
    - Creator
    - Risk Officer
    - Manager of Owner/Creator
    """
    if user.role and user.role.name == "Risk Officer":
        return True

    # Check ownership/creation
    is_owner = risk.owner and user.id == risk.owner.id
    is_creator = risk.created_by and user.id == risk.created_by.id

    # Check management relationships (if pre-fetched)
    is_owner_mgr = (
        risk.owner and risk.owner.manager and user.id == risk.owner.manager.id
    )
    is_creator_mgr = (
        risk.created_by
        and risk.created_by.manager
        and user.id == risk.created_by.manager.id
    )

    return is_owner or is_creator or is_owner_mgr or is_creator_mgr


def get_editable_fields(risk_status: str, user_role: str) -> set:
    """
    [PURE DOMAIN LOGIC]
    Returns the set of fields that can be edited for a given status and role.
    Any field NOT in this set is effectively Read-Only.
    """
    editable = set()

    if risk_status == "DRAFT":
        # In DRAFT, Managers and Risk Officers can edit core identification
        # and inherent assessment fields.
        if user_role in ["Manager", "Risk Officer"]:
            editable.update(
                {
                    "title",
                    "description",
                    "risk_category",
                    "basel_event_type",
                    "business_unit",
                    "business_process",
                    "product",
                    "owner",
                    "inherent_likelihood",
                    "inherent_impact",
                }
            )
        # Risk Officer can add residual assessment for 'Workshop' mode
        if user_role == "Risk Officer":
            editable.update(
                {
                    "residual_likelihood",
                    "residual_impact",
                }
            )

    elif risk_status == "ASSESSED":
        # In ASSESSED, only the Risk Officer can edit, and primarily
        # to complete the Residual assessment and classification.
        if user_role == "Risk Officer":
            editable.update(
                {
                    "residual_likelihood",
                    "residual_impact",
                    "basel_event_type",
                    "risk_category",
                    # RO might need to fix descriptions too?
                    # For strict RCSA maybe not,
                    # but let's allow context fixes for now.
                    "title",
                    "description",
                    "business_unit",
                    "business_process",
                    "product",
                }
            )
        # Managers cannot edit anything in ASSESSED (pending validation).

    elif risk_status == "ACTIVE":
        # In ACTIVE, the risk is locked.
        # Changes require a Reassessment (Workflow Action).
        # Therefore, NO fields are editable via standard PATCH.
        pass

    elif risk_status == "RETIRED":
        # Retired risks are immutable historical records.
        pass

    return editable
