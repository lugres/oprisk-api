"""
Serializers for the Controls API.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Control
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

    class Meta:
        model = Control
        fields = [
            "id",
            "title",
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
    """Full detail serializer."""

    owner = UserNestedSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)

    class Meta:
        model = Control
        fields = [
            "id",
            "title",
            "description",
            "reference_doc",
            "control_type",
            "control_nature",
            "control_frequency",
            "effectiveness",
            "is_active",
            "business_unit",
            "business_process",
            "owner",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ControlCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for writing data."""

    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    business_unit = serializers.PrimaryKeyRelatedField(
        queryset=BusinessUnit.objects.all()
    )
    business_process = serializers.PrimaryKeyRelatedField(
        queryset=BusinessProcess.objects.all(), required=False, allow_null=True
    )
    is_active = serializers.BooleanField(default=True, required=False)

    class Meta:
        model = Control
        fields = [
            "title",
            "description",
            "reference_doc",
            "control_type",
            "control_nature",
            "control_frequency",
            "effectiveness",
            "is_active",
            "business_unit",
            "business_process",
            "owner",
        ]
