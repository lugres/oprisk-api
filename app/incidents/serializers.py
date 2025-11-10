"""
Serializers for incidents API.
"""

from rest_framework import serializers

from incidents.models import (
    Incident,
    IncidentStatusRef,
    IncidentEditableField,
)

from users.serializers import UserNestedSerializer
from references.serializers import BusinessUnitSerializer


class IncidentStatusRefSerializer(serializers.ModelSerializer):
    """Serializer for Incident Status objects."""

    class Meta:
        model = IncidentStatusRef
        fields = ["id", "code", "name"]


class IncidentListSerializer(serializers.ModelSerializer):
    """Serializer for the incident LIST view (lightweight)."""

    status = IncidentStatusRefSerializer(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "status",
            "gross_loss_amount",
            "created_at",
        ]
        read_only_fields = ["id"]


class IncidentDetailSerializer(IncidentListSerializer):
    """Serializer for the incident DETAIL view (comprehensive, RO focus)."""

    status = IncidentStatusRefSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)
    business_unit = BusinessUnitSerializer(read_only=True)

    class Meta(IncidentListSerializer.Meta):

        fields = IncidentListSerializer.Meta.fields + [
            "description",
            "business_unit",
            "simplified_event_type",
            "start_time",
            "end_time",
            "recovery_amount",
            "net_loss_amount",
            "created_by",
            "notes",
        ]


class IncidentCreateSerializer(serializers.ModelSerializer):
    """Serializer for CREATE action (writable fields)."""

    # By default, ModelSrlzr treats FKs as PrimaryKeyRelatedField for writes.
    class Meta:
        model = Incident
        # List only the fields an employee can create/edit initially.
        fields = [
            "title",
            "description",
            "business_unit",
            "simplified_event_type",
            "gross_loss_amount",
            "currency_code",
            "near_miss",
        ]


class IncidentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for UPDATE action (writable fields), now dynamic.
    Fields are made read-only based on user role and incident status,
    configured in the IncidentEditableField model.
    """

    # By default, ModelSrlzr treats FKs as PrimaryKeyRelatedField for writes.
    class Meta:
        model = Incident
        # List *all* fields that are *ever* editable
        fields = [
            "title",
            "description",
            # "status",  # added
            "business_unit",
            "simplified_event_type",
            "gross_loss_amount",
            "currency_code",
            "near_miss",
            "start_time",
            "end_time",
            "recovery_amount",
            "net_loss_amount",
            "business_process",
            "product",
            "basel_event_type",
        ]
        read_only_fields = ["status"]

    def __init__(self, *args, **kwargs):
        # Call super() first
        super().__init__(*args, **kwargs)

        # Get context passed from the ViewSet
        context = self.context
        role = context.get("user_role")

        # Get the status directly from the serializer's instance
        status = None
        if hasattr(self, "instance") and self.instance:
            status = self.instance.status

        # Failsafe: If no role or status, make all fields read-only
        if not role or not status:
            for field_name in self.fields:
                self.fields[field_name].read_only = True
            return

        # Get the set of fields this user is allowed to edit
        editable_fields = set(
            IncidentEditableField.objects.filter(
                status=status, role=role
            ).values_list("field_name", flat=True)
        )

        # Mark all other fields in this serializer as read-only
        for field_name in self.fields:
            if field_name not in editable_fields:
                self.fields[field_name].read_only = True


class ReturnActionSerializer(serializers.Serializer):
    """Serializer to validate the required 'reason' for return actions."""

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=500,  # Example length limit
    )
