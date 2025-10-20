"""
Serializers for incidents API.
"""

from rest_framework import serializers

from incidents.models import Incident, IncidentStatusRef

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


class IncidentDetailSerializer(serializers.ModelSerializer):
    """Serializer for the incident DETAIL view (comprehensive, RO focus)."""

    status = IncidentStatusRefSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)
    business_unit = BusinessUnitSerializer(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "description",
            "status",
            "created_by",
            "business_unit",
            "simplified_event_type",
            "start_time",
            "end_time",
            "gross_loss_amount",
            "recovery_amount",
            "net_loss_amount",
        ]


class IncidentCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for CREATE and UPDATE actions (writable fields)."""

    # By default, ModelSrlzr treats FKs as PrimaryKeyRelatedField for writes.
    class Meta:
        model = Incident
        # List only the fields an employee can create/edit initially.
        fields = [
            "id",
            "title",
            "description",
            "status",
            "business_unit",
            "simplified_event_type",
            "gross_loss_amount",
            "currency_code",
            "near_miss",
        ]
        read_only_fields = ["id"]
