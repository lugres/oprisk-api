"""
Serializers for the Controls API.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Control, ControlNature, ControlLevel
from .workflows import is_group_risk_officer
from references.models import BusinessUnit, BusinessProcess
from users.serializers import UserNestedSerializer

User = get_user_model()


class ControlListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    owner = UserNestedSerializer(read_only=True)
    # Simple string repr for BU to avoid extra queries if not needed,
    # or nested if requirements dictate. Let's use simple nested for clarity.
    business_unit_name = serializers.CharField(
        source="business_unit.name", read_only=True
    )
    # parent control title for readability
    parent_control_title = serializers.CharField(
        source="parent_control.title", read_only=True, allow_null=True
    )

    class Meta:
        model = Control
        fields = [
            "id",
            "title",
            "control_level",
            "parent_control",
            "parent_control_title",
            "control_type",
            "control_nature",
            "control_frequency",
            "effectiveness",
            "is_active",
            "business_unit",
            "business_unit_name",
            "owner",
        ]


class ControlDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer with context and hierarchy."""

    owner = UserNestedSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)

    # hierarchy
    parent_control = serializers.SerializerMethodField()
    child_controls = serializers.SerializerMethodField()
    inheritance_chain = serializers.SerializerMethodField()

    # explicit for control nature (based on data model default)
    control_nature = serializers.ChoiceField(
        choices=ControlNature.choices,
        default=ControlNature.MANUAL,
        required=False,
    )

    # Contextual Fields
    permissions = serializers.SerializerMethodField()
    linked_risks_count = serializers.SerializerMethodField(read_only=True)
    active_risks_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Control
        fields = [
            "id",
            "title",
            "description",
            "reference_doc",
            "control_level",
            "control_type",
            "control_nature",
            "control_frequency",
            "effectiveness",
            "is_active",
            "business_unit",
            "business_process",
            "owner",
            "parent_control",
            "child_controls",
            "inheritance_chain",
            "created_by",
            "created_at",
            "updated_at",
            "permissions",
            "linked_risks_count",
            "active_risks_count",
        ]

    def get_parent_control(self, obj):
        """Get control's parent."""
        if obj.parent_control:
            return {
                "id": obj.parent_control.id,
                "title": obj.parent_control.title,
                "control_level": obj.parent_control.control_level,
            }
        return None

    def get_child_controls(self, obj):
        """Show active local implementations."""
        if obj.control_level != ControlLevel.STANDARD:
            return []

        # Get the requesting user from context
        request = self.context.get("request")
        if not request or not request.user:
            return []

        user = request.user
        children = obj.child_controls.filter(is_active=True)

        # Apply same visibility rules as main queryset
        # Group RO: See all (no filter)
        if not is_group_risk_officer(user):
            # BU RO and Manager/Employee:: Only see children in their BU
            children = children.filter(business_unit=user.business_unit)

        return [
            {
                "id": c.id,
                "title": c.title,
                "business_unit": (
                    c.business_unit.name if c.business_unit else "N/A"
                ),
            }
            for c in children
        ]

    def get_inheritance_chain(self, obj):
        """Get control's inheritance chain."""
        chain = obj.get_inheritance_chain()
        return [
            {"id": c.id, "title": c.title, "level": c.control_level}
            for c in chain
        ]

    def get_permissions(self, obj):
        """Get control's permissions from context."""
        return self.context.get("permissions", {})

    def get_linked_risks_count(self, obj):
        """Get computed field from context."""
        return self.context.get("linked_risks_count", {})

    def get_active_risks_count(self, obj):
        """Get computed field from context."""
        return self.context.get("active_risks_count", {})


class ControlCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for writing data."""

    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    business_unit = serializers.PrimaryKeyRelatedField(
        queryset=BusinessUnit.objects.all(),
        required=False,
        allow_null=True,
    )
    business_process = serializers.PrimaryKeyRelatedField(
        queryset=BusinessProcess.objects.all(),
        required=False,
        allow_null=True,
    )
    parent_control = serializers.PrimaryKeyRelatedField(
        queryset=Control.objects.filter(control_level=ControlLevel.STANDARD),
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = Control
        fields = [
            "title",
            "description",
            "reference_doc",
            "control_level",
            "parent_control",
            "control_type",
            "control_nature",
            "control_frequency",
            "effectiveness",
            "is_active",
            "business_unit",
            "business_process",
            "owner",
        ]
