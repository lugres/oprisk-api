"""
Domain layer - pure, Django-unaware, state machine for measures.
Validates measure transitions as prescribed by business rules.
"""


class MeasureTransitionError(Exception):
    """Custom exception for invalid state transitions."""

    pass


class MeasurePermissionError(Exception):
    """Custom exception for permission failures on measures."""

    pass


# --- 1. Transition Validation ---

# Define the allowed transitions as a pure dictionary (Domain Logic)
ALLOWED_TRANSITIONS = {
    "OPEN": {
        "IN_PROGRESS": ["Employee", "Manager"],  # 'Employee' = responsible
    },
    "IN_PROGRESS": {
        "PENDING_REVIEW": ["Employee", "Manager"],
        "CANCELLED": ["Risk Officer"],
    },
    "PENDING_REVIEW": {
        "IN_PROGRESS": ["Risk Officer"],
        "COMPLETED": ["Risk Officer"],
        "CANCELLED": ["Risk Officer"],
    },
}


def validate_transition(
    from_status_code: str, to_status_code: str, role_name: str
):
    """
    Validates if a role is allowed to perform a state transition.
    Raises MeasureTransitionError if the transition is not allowed.
    """
    allowed_roles = ALLOWED_TRANSITIONS.get(from_status_code, {}).get(
        to_status_code
    )

    if not allowed_roles:
        raise MeasureTransitionError(
            f"Transition from '{from_status_code}' to '{to_status_code}'"
            " is not defined."
        )

    if role_name not in allowed_roles:
        raise MeasureTransitionError(
            f"Role '{role_name}' is not authorized to move from "
            f"'{from_status_code}' to '{to_status_code}'."
        )

    # If no exception, the transition is valid
    return True


# --- 2. Contextual Permissions (Logic moved from Serializer) ---


def get_contextual_role_name(measure, user) -> str:
    """
    [PURE DOMAIN LOGIC]
    Gets the user's "workflow role" for this specific measure.
    Assumes 'measure' and 'user' objects are pre-fetched.
    """
    # Failsafe for missing user or role
    if not user or not user.role:
        return "Unknown"

    # Failsafe for missing measure data
    if not measure.responsible:
        return user.role.name  # Can't be responsible, so just use base role

    # This is the "do-er" logic from our API contract:
    # Use .id comparison for safety, as objects might be different instances
    is_responsible = user.id == measure.responsible.id

    # Check for manager's existence *before* comparing ID
    is_mgr_of_responsible = (
        measure.responsible.manager
        and user.id == measure.responsible.manager.id
    )

    if is_responsible or is_mgr_of_responsible:
        # For transitions, the responsible user or their manager
        # acts as the 'Employee' (the "doer")
        return "Employee"

    # Otherwise, their assigned role is their workflow role.
    return user.role.name


def get_available_transitions(
    measure_status_code: str, user_role_name: str
) -> list:
    """
    [PURE DOMAIN LOGIC]
    Gets a list of available transition actions based on
    the current state and role.
    """
    # ... (This function's internal logic was correct and remains the same)
    transitions = []
    possible_transitions = ALLOWED_TRANSITIONS.get(measure_status_code, {})

    for to_status, allowed_roles in possible_transitions.items():
        if user_role_name in allowed_roles:
            # ... (action_map logic remains the same)
            action_map = {
                "IN_PROGRESS": {
                    "action": "start-progress",
                    "name": "Start Progress",
                },
                "PENDING_REVIEW": {
                    "action": "submit-for-review",
                    "name": "Submit for Review",
                },
                "COMPLETED": {
                    "action": "complete",
                    "name": "Complete Measure",
                },
                "CANCELLED": {"action": "cancel", "name": "Cancel Measure"},
            }
            if (
                measure_status_code == "PENDING_REVIEW"
                and to_status == "IN_PROGRESS"
            ):
                action_map["IN_PROGRESS"] = {
                    "action": "return-to-progress",
                    "name": "Return to Progress",
                }

            if action_map.get(to_status):
                transitions.append(action_map[to_status])

    return transitions


def get_user_permissions(
    measure, user, editable_fields: set, available_transitions: list
) -> dict:
    """
    [PURE DOMAIN LOGIC]
    Calculates the fine-grained permissions for a user against a measure.
    Now accepts available_transitions to prevent recalculation.
    """
    # 1. can_edit
    can_edit = any(
        f in editable_fields
        for f in ["description", "deadline", "responsible"]
    )

    # 2. can_delete (add safety checks)
    is_creator_or_mgr = False
    if measure.created_by:  # Failsafe
        is_creator_or_mgr = (
            user.id == measure.created_by.id
            or
            # Check for manager's existence
            (
                measure.created_by.manager
                and user.id == measure.created_by.manager.id
            )
        )
    can_delete = measure.status.code == "OPEN" and is_creator_or_mgr

    # 3. can_transition
    can_transition = bool(available_transitions)

    return {
        "can_edit": can_edit,
        "can_delete": can_delete,
        "can_transition": can_transition,
    }
