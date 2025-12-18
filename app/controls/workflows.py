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


# --- Role Helpers ---


def is_risk_officer(user) -> bool:
    """
    Identifies a Risk Officer in general.
    Logic: a user has a role AND role belongs to 'Risk Officer'.
    """
    return user and user.role and user.role.name == "Risk Officer"


def is_group_risk_officer(user) -> bool:
    """
    Identifies a Central/Group Risk Officer.
    Logic: Must be a Risk Officer AND belong to 'Risk Management' BU.
    """
    if not is_risk_officer(user):
        return False
    return user.business_unit and user.business_unit.name == "Risk Management"


def is_bu_risk_officer(user) -> bool:
    """
    Identifies a Business Unit Risk Officer.
    Logic: Risk Officer NOT in 'Risk Management'.
    """
    if not is_risk_officer(user):
        return False
    return not is_group_risk_officer(user)


def is_manager(user) -> bool:
    """Identifies a Manager."""
    return user and user.role and user.role.name == "Manager"


# --- Permission Logic ---


def can_create_standard_control(user) -> bool:
    """Only Central/Group Risk Officers can create STANDARD controls."""
    return is_group_risk_officer(user)


def can_create_local_control(user) -> bool:
    """Central Risk Officers and RO from BU can create LOCAL controls."""
    return is_group_risk_officer(user) or is_bu_risk_officer(user)


def can_edit_control(user, control) -> bool:
    """
    - Group RO: Can edit ALL controls.
    - BU RO: Can only edit LOCAL controls in their BU.
    """
    if not user or not user.role:
        return False

    if is_group_risk_officer(user):
        return True

    if is_bu_risk_officer(user):
        # Must be LOCAL and in same BU
        return (
            control.control_level == "LOCAL"
            and control.business_unit == user.business_unit
        )

    return False


def validate_deactivation_allowed(risk_statuses: list) -> bool:
    """
    Validates if a control can be deactivated based on linked risks statuses.
    Rule: Cannot deactivate control if it is linked to any ACTIVE risks.
    """
    # Check if any risk is ACTIVE (status code "ACTIVE")
    return "ACTIVE" not in risk_statuses
