"""
Serializers for incidents API.
"""

from rest_framework import serializers

from incidents.models import Incident, IncidentStatusRef


class IncidentStatusRefSerializer(serializers.ModelSerializer):
    """Serializer for Incident Status objects."""

    class Meta:
        model = IncidentStatusRef
        fields = ["id", "code", "name"]


class IncidentSerializer(serializers.ModelSerializer):
    """Serializer for incidents."""

    status = IncidentStatusRefSerializer(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "description",
            "status",
            "gross_loss_amount",
            "currency_code",
            "created_at",
        ]
        read_only_fields = ["id"]


class IncidentDetailSerializer(IncidentSerializer):
    """Serializer for incident detail view."""

    class Meta(IncidentSerializer.Meta):
        fields = IncidentSerializer.Meta.fields + [
            "start_time",
            "end_time",
            "business_unit",
            "simplified_event_type",
        ]
