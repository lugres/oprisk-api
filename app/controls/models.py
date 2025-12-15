"""
Data models for the controls app.
Implements the Hierarchical (OOP-like) Control Library pattern.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.models import TimestampedModel, OwnedModel
from references.models import BusinessProcess, BusinessUnit


class ControlLevel(models.TextChoices):
    STANDARD = "STANDARD", _("Standard (Organization-wide)")
    LOCAL = "LOCAL", _("Local (Business Unit Specific Implementation)")


class ControlType(models.TextChoices):
    PREVENTIVE = "PREVENTIVE", _("Preventive")
    DETECTIVE = "DETECTIVE", _("Detective")
    CORRECTIVE = "CORRECTIVE", _("Corrective")


class ControlNature(models.TextChoices):
    MANUAL = "MANUAL", _("Manual")
    AUTOMATED = "AUTOMATED", _("Automated")
    HYBRID = "HYBRID", _("IT-Dependent Manual")


class ControlFrequency(models.TextChoices):
    CONTINUOUS = "CONTINUOUS", _("Continuous")
    DAILY = "DAILY", _("Daily")
    WEEKLY = "WEEKLY", _("Weekly")
    MONTHLY = "MONTHLY", _("Monthly")
    QUARTERLY = "QUARTERLY", _("Quarterly")
    ANNUALLY = "ANNUALLY", _("Annually")
    AD_HOC = "AD_HOC", _("Ad-hoc - Event Driven")


class Control(TimestampedModel, OwnedModel):
    """
    Central Library of Controls.
    Describes the mechanism designed to mitigate risks.

    Structure:
    - STANDARD: Central objectives managed by Group Risk.
    - LOCAL: Specific implementations managed by BU Risk Officers.

    Group Risk - centralized risk team;
    BU Risk Officers - dedicated BU RO or a functional, supplementary role.
    """

    # 1. Identification
    title = models.CharField(max_length=255)
    description = models.TextField()
    reference_doc = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Link to control procedure document or wiki"),
    )

    # 2. Hierarchy & Classification
    control_level = models.CharField(
        max_length=20,
        choices=ControlLevel.choices,
        default=ControlLevel.STANDARD,
        help_text=_(
            "STANDARD: Org-wide policy. LOCAL: BU-specific implementation"
        ),
    )

    parent_control = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="child_controls",
        help_text=_("Parent standard if this is a local implementation"),
    )

    # 3. Design Characteristics
    control_type = models.CharField(
        max_length=20,
        choices=ControlType.choices,
        default=ControlType.PREVENTIVE,
    )
    control_nature = models.CharField(
        max_length=20,
        choices=ControlNature.choices,
        default=ControlNature.MANUAL,
    )
    control_frequency = models.CharField(
        max_length=20,
        choices=ControlFrequency.choices,
        help_text=_("How often this control is performed"),
    )

    # 4. Design Effectiveness (The "Inherent Strength" of the control)
    effectiveness = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text=_("Design effectiveness rating (1-5)"),
    )

    # 4. Context & Ownership
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this control is currently operational"),
    )
    # Business Unit is NULL for Standard controls, REQUIRED for Local controls
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="controls",
        help_text=_("The unit that owns/operates this control"),
    )
    business_process = models.ForeignKey(
        BusinessProcess,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="controls",
        help_text="Primary business process this control applies to",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_controls",
        help_text=_("User responsible for operating/maintaining this control"),
    )

    def clean(self):
        """Enforce hierarchical integrity rules."""
        super().clean()

        # Rule 1: STANDARD controls cannot have parents
        if self.control_level == ControlLevel.STANDARD and self.parent_control:
            raise ValidationError(
                "Standard controls cannot have parent controls."
            )

        # Rule 2: LOCAL controls must have parent
        if (
            self.control_level == ControlLevel.LOCAL
            and not self.parent_control
        ):
            raise ValidationError(
                "Local controls must reference a parent standard control."
            )

        # Rule 3: LOCAL controls must have BU
        if self.control_level == ControlLevel.LOCAL and not self.business_unit:
            raise ValidationError(
                "Local controls must belong to a business unit."
            )

        # Rule 4: STANDARD controls should not have BU (Global)
        # Note: We can relax this if we want BU-specific Standards,
        # but pure hierarchy suggests Standards are Global.
        if self.control_level == ControlLevel.STANDARD and self.business_unit:
            raise ValidationError(
                "Standard controls should not be assigned to a specific"
                " business unit."
            )

        # Rule 5: Cannot create circular references
        if self.parent_control:
            parent = self.parent_control
            # Check strictly against self.id to avoid infinite loops if unsaved
            if self.pk and parent.pk == self.pk:
                raise ValidationError("Control cannot be its own parent.")

            # Traverse up
            while parent:
                if parent.pk == self.pk:
                    raise ValidationError(
                        "Circular parent-child relationship detected."
                    )
                parent = parent.parent_control

    def get_inheritance_chain(self):
        """Returns the full inheritance chain from root to this control."""
        chain = [self]
        parent = self.parent_control
        while parent:
            chain.insert(0, parent)
            parent = parent.parent_control
        return chain

    def get_all_children(self):
        """Returns all descendant controls (children, grandchildren, etc.)."""
        # Note: In a 2-level system (Standard->Local), recursion isn't deep,
        # but this supports future depth if needed.
        children = list(self.child_controls.all())
        for child in list(children):
            children.extend(child.get_all_children())
        return children

    def __str__(self):
        prefix = (
            "STD" if self.control_level == ControlLevel.STANDARD else "LOC"
        )
        return f"[{prefix}] {self.title}"
