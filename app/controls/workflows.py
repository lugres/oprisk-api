"""
Domain layer for Controls.
Defines permission rules and validation logic for control lifecycle.
"""


class ControlPermissionError(Exception):
    """Custom exception for permission failures."""

    pass


class ControlValidationError(Exception):
    """Custom exception for business logic validation failures."""

    pass


def can_user_modify_library(user) -> bool:
    """
    Only Risk Officers can create, edit, or deactivate controls in the library.
    """
    return user.role and user.role.name == "Risk Officer"


def validate_deactivation_allowed(risk_statuses: list) -> bool:
    """
    Validates if a control can be deactivated based on linked risks statuses.
    Rule: Cannot deactivate a control if it is linked to any ACTIVE risks.
    """
    # Check if any risk is ACTIVE (status code "ACTIVE")
    return "ACTIVE" not in risk_statuses
