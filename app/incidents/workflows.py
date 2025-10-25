"""
Domain layer - pure, Django-unaware, a data-driven state machine.
Validates incident transitions as prescribed by business rules.
"""


class InvalidTransitionError(Exception):
    """Custom exception for invalid state transitions."""

    pass


def validate_transition(
    *,
    from_status: str,
    to_status: str,
    role_name: str,
    allowed_transitions: dict,
):
    """
    Validates a state transition against a given rule set.
    Raises InvalidTransitionError if the transition is not allowed.

    Expected rule structure:
    { 'DRAFT': { 'PENDING_REVIEW': ['Employee', 'Manager'] } }
    """
    if from_status not in allowed_transitions:
        raise InvalidTransitionError(
            f"Status '{from_status}' has no defined transitions."
        )

    if to_status not in allowed_transitions[from_status]:
        raise InvalidTransitionError(
            f"Transition from '{from_status}' to '{to_status}' is not defined."
        )

    allowed_roles = allowed_transitions[from_status][to_status]
    if role_name not in allowed_roles:
        raise InvalidTransitionError(
            f"Role '{role_name}' is not authorized to move from"
            f" '{from_status}' to '{to_status}'."
        )
