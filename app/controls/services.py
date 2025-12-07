"""
Application layer for Controls.
Orchestrates CRUD operations and enforces business rules.
"""

from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Control
from .workflows import (
    ControlPermissionError,
    ControlValidationError,
    can_user_modify_library,
    validate_deactivation_allowed,
)

User = get_user_model()


def get_control_visibility_filter(user) -> Q:
    """
    Returns a Q object for filtering controls based on user role.
    - Risk Officers: View ALL (active and inactive).
    - Managers/Employees: View ACTIVE only.
    """
    if not user or not user.role:
        return Q(pk__in=[])

    if user.role.name == "Risk Officer":
        return Q()  # See all

    # Everyone else sees only active controls
    return Q(is_active=True)


@transaction.atomic
def create_control(*, user: User, **validated_data) -> Control:
    """
    Creates a new control in the library.
    """
    if not can_user_modify_library(user):
        raise ControlPermissionError("Only Risk Officers can create controls.")

    # Automatically set created_by
    control = Control.objects.create(created_by=user, **validated_data)
    return control


@transaction.atomic
def update_control(
    *, control: Control, user: User, **validated_data
) -> Control:
    """
    Updates an existing control.
    Enforces validation if deactivating.
    """
    if not can_user_modify_library(user):
        raise ControlPermissionError("Only Risk Officers can edit controls.")

    # Check if we are attempting to deactivate
    is_active_update = validated_data.get("is_active")
    if is_active_update is False and control.is_active:
        # Get statuses from linked risks (Django ORM)
        linked_risk_statuses = list(
            control.risks.values_list("status", flat=True)
        )
        # Call pure domain function
        if not validate_deactivation_allowed(linked_risk_statuses):
            raise ControlValidationError(
                "Cannot deactivate control linked to ACTIVE risks."
            )

    for field, value in validated_data.items():
        setattr(control, field, value)

    control.save()
    return control


def delete_control(*, control: Control, user: User):
    """
    Strictly forbids deletion of controls to preserve audit trails.
    """
    # Why not to remove 'destroy' from allowed actions in ViewSet?
    # Or not to override .destroy() in ViewSet to return 405 ?
    # Because it's not finally decided by business (still consider
    # allowing deletion with DB audit trigger).

    # The tests expect a 403 or 405. We raise PermissionError to be mapped
    # to 403.
    raise ControlPermissionError(
        "Controls cannot be deleted. Please deactivate them instead."
    )
