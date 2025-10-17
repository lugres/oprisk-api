"""
Views for the incidents APIs.
"""

from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from incidents.models import Incident
from incidents import serializers
from .filters import IncidentFilter


class IncidentsViewSet(viewsets.ModelViewSet):
    """View for managing incidents APIs."""

    serializer_class = serializers.IncidentDetailSerializer
    queryset = Incident.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    filterset_class = IncidentFilter

    def get_queryset(self):
        """Retrieve incidents for authenticated user."""
        return self.queryset.filter(created_by=self.request.user).order_by(
            "-id"
        )

    def get_serializer_class(self):
        """Return the serializer class for request."""
        if self.action == "list":
            return serializers.IncidentSerializer

        return self.serializer_class
