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
        ]
        read_only_fields = ["id"]
