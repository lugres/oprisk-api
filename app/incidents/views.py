"""
Views for the incidents APIs.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from incidents.models import Incident
from incidents import serializers
from incidents import services
from .permissions import CanSubmitIncident
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
            return serializers.IncidentListSerializer
        if self.action == "create":
            return serializers.IncidentCreateSerializer
        if self.action in ["update", "partial_update"]:
            return serializers.IncidentUpdateSerializer

        return self.serializer_class

    # def perform_create(self, serializer):
    #     """Create a new incident using service layer."""
    #     # Pass validated data to the service function
    #     services.create_incident(
    #         user=self.request.user, **serializer.validated_data
    #     )
    def create(self, request, *args, **kwargs):
        """Create a new incident using the service layer."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Call the service to create the object
        incident = services.create_incident(
            user=request.user, **serializer.validated_data
        )

        # Now, serialize the NEWLY CREATED object for the response
        response_serializer = serializers.IncidentDetailSerializer(incident)

        return Response(
            response_serializer.data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True, methods=["post"], permission_classes=[CanSubmitIncident]
    )
    def submit(self, request, pk=None):
        """Action to submit an incident from DRAFT to PENDING_REVIEW."""
        incident = self.get_object()
        updated_incident = services.submit_incident(incident=incident)
        serializer = self.get_serializer(updated_incident)
        return Response(serializer.data, status=status.HTTP_200_OK)
