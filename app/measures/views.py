"""
Views for the measures APIs.
"""

from django.db.models import Q
from django.contrib.auth import get_user_model
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
)
from incidents.permissions import IsRoleRiskOfficer

from .filters import MeasureFilter


class StandardResultsSetPagination(PageNumberPagination):
    """Provides pagination for output."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class MeasureViewSet(viewsets.ModelViewSet):
    """View for managing measures APIs."""

    queryset = Measure.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_class = MeasureFilter

    def get_queryset(self):
        """
        Implement data segregation based on user role.
        """
        # 1. Get the fully-loaded user object for filtering.
        user = self.request.user
        if user.is_authenticated:
            try:
                # Pre-fetch role and manager for the user
                user = (
                    get_user_model()
                    .objects.select_related("role", "manager")
                    .get(id=self.request.user.id)
                )
            except get_user_model().DoesNotExist:
                return super().get_queryset().none()
        else:
            return super().get_queryset().none()

        # 2. Start with the base queryset and pre-fetch all
        #    Measure-related objects we will need for permissions.
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "status",
                "responsible",
                "responsible__role",
                "responsible__manager",  # <-- Explicitly pre-fetch manager
                "created_by",
                "created_by__role",
                "created_by__manager",  # <-- Explicitly pre-fetch manager
            )
        )

        # 3. Apply role-based filtering (this logic is correct)
        if not user.role:
            return queryset.none()

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
        """
        Pass user role and request into the serializer.
        For 'retrieve', also pass contextual permissions.
        """
        context = super().get_serializer_context()
        # context["user_role"] = self.request.user.role
        context["request"] = self.request  # For DetailSerializer
        return context

    # Override retrieve to use the new context logic
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single measure with contextual data.
        """
        instance = self.get_object()
        context = self.get_serializer_context()

        # Add contextual permissions and transitions for retrieve
        if request.user.is_authenticated:
            try:
                # Get fully-loaded user
                user = (
                    get_user_model()
                    .objects.select_related("role", "manager")
                    .get(id=request.user.id)
                )
                # Get contextual data from service layer
                contextual_data = services.get_measure_context(
                    measure=instance, user=user
                )
                context.update(contextual_data)
            except get_user_model().DoesNotExist:
                pass  # Skip contextual data if user not found

        serializer = self.get_serializer(instance, context=context)
        return Response(serializer.data)

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

        try:
            measure = services.create_measure(
                user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            # Catch potential errors from create-and-link
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a measure.
        Permission: Creator/Manager AND status must be OPEN.
        """
        measure = self.get_object()

        try:
            services.delete_measure(measure=measure, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (MeasureTransitionError, MeasurePermissionError) as e:
            err_status = (
                status.HTTP_403_FORBIDDEN
                if isinstance(e, MeasurePermissionError)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"error": str(e)}, status=err_status)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureResponsibleOrManager],
    )
    def start_progress(self, request, pk=None):
        """
        Action to move a measure from OPEN to IN_PROGRESS.
        Permission: Responsible user or their Manager.
        """
        measure = self.get_object()
        try:
            updated_measure = services.start_progress(
                measure=measure, user=request.user
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureResponsibleOrManager],
    )
    def submit_for_review(self, request, pk=None):
        """
        Action to move a measure from IN_PROGRESS to PENDING_REVIEW.
        Permission: Responsible user or their Manager.
        """
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_measure = services.submit_for_review(
                measure=measure, user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def return_to_progress(self, request, pk=None):
        """
        Action to return a measure from PENDING_REVIEW back to IN_PROGRESS.
        Permission: Risk Officer only. Reason is required.
        """
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_measure = services.return_to_progress(
                measure=measure, user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def complete(self, request, pk=None):
        """
        Action to move a measure from PENDING_REVIEW to COMPLETED.
        Permission: Risk Officer only. Closure comment is required.
        """
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_measure = services.complete(
                measure=measure, user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsRoleRiskOfficer],
    )
    def cancel(self, request, pk=None):
        """
        Action to move a measure to CANCELLED.
        Permission: Risk Officer only. Reason is required.
        """
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_measure = services.cancel(
                measure=measure, user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def add_comment(self, request, pk=None):
        """Action to add an ad-hoc comment for a measure in progress."""
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_measure = services.add_comment(
                measure=measure, user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.MeasureDetailSerializer(
                    updated_measure, context=self.get_serializer_context()
                ).data,
                status=status.HTTP_200_OK,
            )
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def link_to_incident(self, request, pk=None):
        """An action to link a measure to an incident."""
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.link_measure_to_incident(
                measure=measure,
                user=request.user,
                incident=serializer.validated_data["incident_id"],
            )
            return Response({"status": "linked"}, status=status.HTTP_200_OK)
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsMeasureParticipant],
    )
    def unlink_from_incident(self, request, pk=None):
        """An action to link a measure to an incident."""
        measure = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.unlink_measure_from_incident(
                measure=measure,
                user=request.user,
                incident=serializer.validated_data["incident_id"],
            )
            return Response({"status": "unlinked"}, status=status.HTTP_200_OK)
        except (MeasureTransitionError, MeasurePermissionError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
