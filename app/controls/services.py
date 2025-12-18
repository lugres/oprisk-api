"""
Application layer for Controls.
Orchestrates CRUD operations and enforces business rules.
"""

from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Control, ControlLevel
from risks.models import RiskStatus
from .workflows import (
    ControlPermissionError,
    ControlValidationError,
    is_bu_risk_officer,
    is_group_risk_officer,
    is_manager,
    can_create_standard_control,
    can_create_local_control,
    can_edit_control,
    validate_deactivation_allowed,
)

User = get_user_model()


def get_control_context(control: Control, user: User) -> dict:
    """
    Gathers contextual data for the ControlDetailSerializer.
    Returns permissions and metadata specific to this user/control.
    """
    # 1. Calculate Permissions
    can_edit = can_edit_control(user, control)

    # Check if linked to any ACTIVE risks (blocking deactivation)
    # control.risks is the related_name from Risk.controls M2M
    has_active_risks = control.risks.filter(status=RiskStatus.ACTIVE).exists()

    permissions = {
        "can_edit": can_edit,
        # Deactivation is allowed only for ROs AND if no active links exist
        "can_deactivate": can_edit and not has_active_risks,
        "can_delete": False,  # Hard delete is never allowed in this API
    }

    # 2. Calculate Metadata
    linked_risks_count = control.risks.count()
    active_risks_count = control.risks.filter(status=RiskStatus.ACTIVE).count()

    return {
        "permissions": permissions,
        "linked_risks_count": linked_risks_count,
        "active_risks_count": active_risks_count,
    }


def get_control_visibility_filter(user) -> Q:
    """
    Returns a Q object for filtering controls based on user role and context.

    Business Rules:
    - Central/Group Risk Officer:
        - All STANDARD, all LOCAL controls across organization.
    - BU Risk Officer:
        - All STANDARD, all LOCAL controls in their BU (active and inactive).
        - All LOCAL controls linked to risks in their BU.
    - Manager:
        - All STANDARD controls.
        - Active LOCAL controls in their Business Unit.
        - Active LOCAL controls linked to Risks they own (also in other BUs).
    - Employee:
        - All STANDARD controls.
        - Active LOCAL controls in their Business Unit.
        - Active LOCAL controls linked to Risks in their Business Unit.
    """
    if not user or not user.role:
        return Q(pk__in=[])

    # 1. Central/Group Risk Officer (God View)
    if is_group_risk_officer(user):
        return Q()

    # 1.1 STANDARD controls visible to all
    standard = Q(control_level=ControlLevel.STANDARD)

    # 2. BU Risk Officer: (Standard + Local in BU + Linked to risks)
    if is_bu_risk_officer(user):
        return (
            standard
            | Q(
                control_level=ControlLevel.LOCAL,
                business_unit=user.business_unit,
            )
            | Q(
                control_level=ControlLevel.LOCAL,
                risks__business_unit=user.business_unit,
            )
        )  # Can see STANDARD, all LOCAL in BU and linked

    # 3. Base Filter for Manager/Employee: Control Must be LOCAL and Active
    base_local_filter = Q(
        control_level=ControlLevel.LOCAL,
        is_active=True,
    )
    # 3.1 Rule A: In their BU
    bu_filter = Q(business_unit=user.business_unit)

    # 4. Manager Logic
    if is_manager(user):
        # Rule B: Linked to risks they own (Cross-BU visibility exception)
        # 'risks' is the related_name from Risk.controls M2M
        risk_link_filter = Q(risks__owner=user) | Q(
            risks__business_unit=user.business_unit
        )

        # (Standard) OR (Local+Active AND (In BU OR Linked + to Owned Risk))
        return standard | base_local_filter & (bu_filter | risk_link_filter)

    # 5. Employee Logic (Default)
    # Rule B: Linked to risks in their BU (Contextual visibility)
    risk_link_filter = Q(risks__business_unit=user.business_unit)

    # (Standard) OR (Local+Active AND (In BU OR Linked to BU Risk))
    return standard | base_local_filter & (bu_filter | risk_link_filter)


@transaction.atomic
def create_standard_control(*, user: User, **validated_data) -> Control:
    """Factory for Standard Controls."""
    if not can_create_standard_control(user):
        raise ControlPermissionError(
            "Only Group Risk Officers can create standard controls."
        )

    # Enforce Standard properties
    validated_data["business_unit"] = None
    validated_data["control_level"] = ControlLevel.STANDARD
    validated_data["parent_control"] = None

    control = Control(created_by=user, **validated_data)
    control.full_clean()  # Trigger model validation
    control.save()
    return control


@transaction.atomic
def create_local_control(*, user: User, **validated_data) -> Control:
    """
    Factory for Local Controls.
    """
    if not can_create_local_control(user):
        raise ControlPermissionError(
            "Only Risk Officers can create local controls."
        )

    # Enforce Local properties
    validated_data["control_level"] = ControlLevel.LOCAL

    # Get the target BU from request or default to user's BU
    target_bu = validated_data.get("business_unit")

    # Security: BU ROs can only create in their own BU
    if is_bu_risk_officer(user):
        # BU RO: Force their BU, ignore any input
        validated_data["business_unit"] = user.business_unit
    elif target_bu is None:
        # Group RO forgot to specify BU - require it
        raise ControlValidationError(
            "business_unit is required for LOCAL controls."
        )
    # else: Group RO specified a BU, allow it

    # Automatically set created_by
    control = Control(created_by=user, **validated_data)
    control.full_clean()  # Trigger model validation (checks parent existence)
    control.save()
    return control


@transaction.atomic
def update_control(
    *, control: Control, user: User, **validated_data
) -> Control:
    """
    Updates an existing control.
    Enforces validation if deactivating.
    """
    if not can_edit_control(user, control):
        raise ControlPermissionError(
            "You do not have permission to edit this control."
        )

    # Check for attempted structural changes
    forbidden_fields = ["control_level", "parent_control", "business_unit"]
    attempted_changes = [f for f in forbidden_fields if f in validated_data]

    if attempted_changes:
        raise ControlValidationError(
            f"Cannot modify structural fields: {', '.join(attempted_changes)}"
        )

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

    control.full_clean()
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
