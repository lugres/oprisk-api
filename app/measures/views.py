"""
Views for the measures APIs.
"""

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

    def _get_fully_loaded_user(self):
        """
        Helper method to get the fully-loaded user object with related data.
        Returns None if user is not authenticated or doesn't exist.
        """
        if not self.request.user.is_authenticated:
            return None

        try:
            return (
                get_user_model()
                .objects.select_related("role", "manager", "business_unit")
                .get(id=self.request.user.id)
            )
        except get_user_model().DoesNotExist:
            return None

    def get_queryset(self):
        """
        Implement data segregation based on user role.
        """
        # 1. Get the fully-loaded user object for filtering.
        user = self._get_fully_loaded_user()
        if not user or not user.role:
            return super().get_queryset().none()

        # 2. Start with the base queryset and pre-fetch all
        #    Measure-related objects needed for permissions.
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

        # 3. Apply role-based filtering from service layer
        visibility_filter = services.get_measure_visibility_filter(user)

        return queryset.filter(visibility_filter).distinct().order_by("-id")

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
        context["request"] = self.request  # For DetailSerializer
        return context

    # Override retrieve to use the new context logic
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single measure with contextual data.
        """
        instance = self.get_object()
        context = self.get_serializer_context()

        # get fully-loaded user, add its contextual data (perms & trans)
        user = self._get_fully_loaded_user()
        if user:
            contextual_data = services.get_measure_context(
                measure=instance, user=user
            )
            context.update(contextual_data)

        serializer = self.get_serializer(instance, context=context)
        return Response(serializer.data)

    # --- Core CRUD Actions ---

    def create(self, request, *args, **kwargs):
        """
        Create a new measure.
        Permission: Manager or Risk Officer only (enforced in services).

        Returns:
        201 Created: Measure created successfully
        400 Bad Request: Invalid data or transition error
        403 Forbidden: User lacks permission to create measures
        """

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
        except (MeasurePermissionError, MeasureTransitionError) as e:
            # Catch potential errors - permission or create-and-link
            err_status = (
                status.HTTP_403_FORBIDDEN
                if isinstance(e, MeasurePermissionError)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"error": str(e)}, status=err_status)
        except Exception as e:
            # Catch unexpected errors; in future - log for debugging:
            # logger = logging.getLogger(__name__)
            # logger.exception(f"Unexpected error creating measure: {e}")
            return Response(
                {"error": "An unexpected error occurred - " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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
        except (MeasurePermissionError, MeasureTransitionError) as e:
            # Catch potential errors from create-and-link
            err_status = (
                status.HTTP_403_FORBIDDEN
                if isinstance(e, MeasurePermissionError)
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"error": str(e)}, status=err_status)

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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

    @action(detail=True, methods=["post"])
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
