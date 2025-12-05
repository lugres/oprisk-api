"""
Domain layer for Controls.
Defines permission rules and validation logic for control lifecycle.
"""

from risks.models import RiskStatus


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


def validate_deactivation(control):
    """
    Validates if a control can be deactivated.
    Rule: Cannot deactivate a control if it is linked to any ACTIVE risks.
    """
    # We query the related risks through the RiskControl link
    # Assuming related_name='risks' on the M2M or traversing the link model
    # The M2M in Risk model is: controls = ManyToManyField(...,
    # related_name='risks')
    # So control.risks.all() gives us the risks.

    active_links = control.risks.filter(status=RiskStatus.ACTIVE).exists()

    if active_links:
        raise ControlValidationError(
            "Cannot deactivate control because it is linked to ACTIVE risks."
        )
