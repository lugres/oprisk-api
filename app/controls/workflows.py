"""
Domain layer for Controls.
Defines permission rules and validation logic for control lifecycle.
Aims to be Django-unaware domain layer; operates on primitives (str, int).
"""

from dataclasses import dataclass


@dataclass
class LinkabilityReason:
    """Represents a reason why a control can't be linked."""

    code: str
    message: str
    suggestion: str


class ControlBusinessLogic:
    """Stateless business logic for controls."""

    @staticmethod
    def is_control_linkable(control_level: str, is_active: bool) -> bool:
        """
        Indicates if this control can be linked to risks.
        Rule: Only LOCAL, ACTIVE controls are linkable.
        """
        return control_level == "LOCAL" and is_active

    @staticmethod
    def get_linkability_reasons(
        control_level: str, is_active: bool, control_level_display: str
    ) -> list[LinkabilityReason]:
        """
        Returns detailed information about why a control isn't linkable.
        Returns empty list if linkable.
        """
        reasons = []

        if control_level != "LOCAL":
            reasons.append(
                LinkabilityReason(
                    code="NOT_LOCAL",
                    message=f"This is a {control_level_display} control."
                    " Only LOCAL implementations can be linked to risks.",
                    suggestion="Create a LOCAL implementation in your Business"
                    " Unit first.",
                )
            )

        if not is_active:
            reasons.append(
                LinkabilityReason(
                    code="INACTIVE",
                    message="This control is inactive.",
                    suggestion="Activate the control before linking.",
                )
            )

        return reasons

    @staticmethod
    def validate_deactivation(risk_statuses: list[str]) -> bool:
        """
        Validates if control can be deactivated based on linked risks status.
        Rule: Cannot deactivate control if it is linked to any ACTIVE risks.
        """
        return "ACTIVE" not in risk_statuses


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
