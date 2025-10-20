"""
Serializers for references app.
"""

from rest_framework import serializers

from .models import BusinessUnit


class BusinessUnitSerializer(serializers.ModelSerializer):
    """Serializer for Business Unit objects."""

    class Meta:
        model = BusinessUnit
        fields = ["id", "name"]
        read_only_fields = ["id"]
