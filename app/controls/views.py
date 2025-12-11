"""
Views for the controls API.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model

from .models import Control
from . import serializers, services, filters
from .workflows import ControlPermissionError, ControlValidationError


class ControlPagination(PageNumberPagination):
    """Provides pagination for output."""

    page_size = 50
    page_size_query_param = "page_size"


class ControlViewSet(viewsets.ModelViewSet):
    """ViewSet for managing controls API."""

    queryset = Control.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ControlPagination
    filterset_class = filters.ControlFilter

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

    def _get_response_serializer(self, instance):
        """
        Helper to return a ControlDetailSerializer with full contextual data.
        """
        context = self.get_serializer_context()
        user = self._get_fully_loaded_user()

        if user:
            contextual_data = services.get_control_context(instance, user)
            context.update(contextual_data)

        return serializers.ControlDetailSerializer(instance, context=context)

    def get_queryset(self):
        """
        Implement data segregation based on user role.
        """
        user = self._get_fully_loaded_user()
        if not user or not user.role:
            return super().get_queryset().none()

        # Pre-fetch for performance and permissions
        queryset = (
            super()
            .get_queryset()
            .select_related("business_unit", "owner", "created_by")
        )

        # Apply visibility rules from service layer
        q_filter = services.get_control_visibility_filter(user)

        # Distinct is required because the filter may use joins
        #  (e.g. risks__owner)
        return queryset.filter(q_filter).distinct().order_by("-id")

    def get_serializer_class(self):
        """Return the serializer class for request based on action."""

        if self.action in ["create", "update", "partial_update"]:
            return serializers.ControlCreateUpdateSerializer
        if self.action == "list":
            return serializers.ControlListSerializer
        return serializers.ControlDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single control with contextual data."""

        instance = self.get_object()
        serializer = self._get_response_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new control.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            control = services.create_control(
                user=request.user, **serializer.validated_data
            )
            return Response(
                self._get_response_serializer(control).data,
                status=status.HTTP_201_CREATED,
            )
        except ControlPermissionError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_403_FORBIDDEN
            )

    def update(self, request, *args, **kwargs):
        """
        Update a control.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        try:
            control = services.update_control(
                control=instance,
                user=request.user,
                **serializer.validated_data
            )
            return Response(
                self._get_response_serializer(control).data,
                status=status.HTTP_200_OK,
            )
        except ControlPermissionError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
        except ControlValidationError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """
        Delete a control.
        """
        instance = self.get_object()
        try:
            services.delete_control(control=instance, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ControlPermissionError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
