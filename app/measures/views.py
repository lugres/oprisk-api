"""
Views for the measures APIs.
"""

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Measure
from . import serializers
from . import services
from .workflows import MeasureTransitionError, MeasurePermissionError
from .permissions import (
    IsMeasureResponsibleOrManager,
    IsMeasureParticipant,
    IsCreatorOrManagerForDelete,
)
from incidents.permissions import IsRoleRiskOfficer

from .filters import MeasureFilter


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class MeasureViewSet(viewsets.ModelViewSet):
    """View for managing measures APIs."""

    queryset = Measure.objects.all().select_related(
        "status", "responsible", "created_by"
    )
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_class = MeasureFilter

    def get_queryset(self):
        """
        Implement data segregation based on user role.
        """
        user = self.request.user
        queryset = super().get_queryset()

        if not user.role:
            return queryset.none()  # Failsafe

        if user.role.name == "Risk Officer":
            # Risk Officers see all in their BU
            return (
                queryset.filter(
                    Q(responsible__business_unit=user.business_unit)
                    | Q(created_by__business_unit=user.business_unit)
                )
                .distinct()
                .order_by("-id")
            )

        if user.role.name == "Manager":
            # Manager sees their own, their reports'
            return (
                queryset.filter(
                    Q(responsible=user)
                    | Q(created_by=user)
                    | Q(responsible__manager=user)
                    | Q(created_by__manager=user)
                )
                .distinct()
                .order_by("-id")
            )

        # Default: Employee sees their own (responsible or created)
        return (
            queryset.filter(Q(responsible=user) | Q(created_by=user))
            .distinct()
            .order_by("-id")
        )

    def get_serializer_class(self):
        """Return the serializer class for request based on action."""
        if self.action == "list":
            return serializers.MeasureListSerializer
        if self.action == "create":
            return serializers.MeasureCreateSerializer
        if self.action in ["update", "partial_update"]:
            return serializers.MeasureUpdateSerializer
        if self.action == "submit_for_review":
            return serializers.MeasureEvidenceSerializer
        if self.action in ["return_to_progress", "cancel"]:
            return serializers.MeasureReasonSerializer
        if self.action == "complete":
            return serializers.MeasureClosureCommentSerializer
        if self.action == "add_comment":
            return serializers.MeasureCommentSerializer
        if self.action in ["link_to_incident", "unlink_from_incident"]:
            return serializers.MeasureLinkIncidentSerializer

        return serializers.MeasureDetailSerializer

    def get_serializer_context(self):
        """Pass user role and request into the serializer."""
        context = super().get_serializer_context()
        context["user_role"] = self.request.user.role
        context["request"] = self.request  # For DetailSerializer
        return context

    # --- Core CRUD Actions ---

    def create(self, request, *args, **kwargs):
        """
        Create a new measure.
        Permission: Manager or Risk Officer only.
        """
        if not (
            request.user.role.name == "Manager"
            or request.user.role.name == "Risk Officer"
        ):
            return Response(
                {"error": "You do not have permission to create measures."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use service to create
        measure = services.create_measure(
            user=request.user,
            description=serializer.validated_data["description"],
            responsible=serializer.validated_data["responsible"],
            deadline=serializer.validated_data["deadline"],
            incident_id=serializer.validated_data.get("incident_id"),
        )

        return Response(
            serializers.MeasureDetailSerializer(measure).data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a measure.
        Permission: Creator/Manager AND status must be OPEN.
        """
        measure = self.get_object()

        try:
            # Check permissions
            perm_check = IsCreatorOrManagerForDelete()
            if not perm_check.has_object_permission(request, self, measure):
                raise MeasurePermissionError(
                    "You do not have permission to delete this measure."
                )

            # Check status (Business Rule)
            if measure.status.code != "OPEN":
                raise MeasureTransitionError(
                    "Only OPEN measures can be deleted. "
                    "Use 'cancel' for other statuses."
                )

            measure.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except (MeasureTransitionError, MeasurePermissionError) as e:
            # Return 403 for permission errors, 400 for business logic errors
            err_status = (
                status.HTTP_403_FORBIDDEN
                if isinstance(e, MeasurePermissionError)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"error": str(e)}, status=err_status)

        # return super().destroy(request, *args, **kwargs)

    # --- Workflow Actions ---

    def _handle_workflow_action(self, request, service_func, *args, **kwargs):
        """Generic helper for workflow actions."""
        measure = self.get_object()
        try:
            updated_measure = service_func(
                measure=measure, user=request.user, **kwargs
            )
            return Response(
                serializers.MeasureDetailSerializer(updated_measure).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureResponsibleOrManager],
    )
    def start_progress(self, request, pk=None):
        return self._handle_workflow_action(request, services.start_progress)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureResponsibleOrManager],
    )
    def submit_for_review(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request, services.submit_for_review, **serializer.validated_data
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def return_to_progress(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request, services.return_to_progress, **serializer.validated_data
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def complete(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request, services.complete, **serializer.validated_data
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def cancel(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request, services.cancel, **serializer.validated_data
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def add_comment(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request, services.add_comment, **serializer.validated_data
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def link_to_incident(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request,
            services.link_measure_to_incident,
            incident=serializer.validated_data["incident_id"],
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def unlink_from_incident(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._handle_workflow_action(
            request,
            services.unlink_measure_from_incident,
            incident=serializer.validated_data["incident_id"],
        )
