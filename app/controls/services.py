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
    Returns a Q object for filtering controls based on user role and context.

    Business Rules:
    - Risk Officer:
        - All controls in their Business Unit (active and inactive).
    - Manager:
        - Active controls in their Business Unit.
        - Active controls linked to Risks they own (even if in other BUs).
    - Employee:
        - Active controls in their Business Unit.
        - Active controls linked to Risks in their Business Unit.
    """
    if not user or not user.role:
        return Q(pk__in=[])

    # 1. Risk Officer: View ALL in their BU (Library Maintenance scope)
    if user.role.name == "Risk Officer":
        return Q(business_unit=user.business_unit) | Q(
            risks__business_unit=user.business_unit
        )  # See all in BU and linked

    # 2. Base Filter for Manager/Employee: Control Must be Active
    base_filter = Q(is_active=True)

    # 3. Manager Logic
    if user.role.name == "Manager":
        # Rule A: In their BU
        bu_filter = Q(business_unit=user.business_unit)
        # Rule B: Linked to risks they own (Cross-BU visibility exception)
        # 'risks' is the related_name from Risk.controls M2M
        risk_link_filter = Q(risks__owner=user)

        return base_filter & (bu_filter | risk_link_filter)

    # 4. Employee Logic (Default)
    # Rule A: In their BU
    bu_filter = Q(business_unit=user.business_unit)
    # Rule B: Linked to risks in their BU (Contextual visibility)
    risk_link_filter = Q(risks__business_unit=user.business_unit)

    return base_filter & (bu_filter | risk_link_filter)


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
