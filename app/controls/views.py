"""
Views for the controls API.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Control
from . import serializers, services, filters
from .workflows import ControlPermissionError, ControlValidationError


class ControlPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"


class ControlViewSet(viewsets.ModelViewSet):
    queryset = Control.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = ControlPagination
    filterset_class = filters.ControlFilter

    def get_queryset(self):
        # Data segregation
        q_filter = services.get_control_visibility_filter(self.request.user)
        return (
            super()
            .get_queryset()
            .filter(q_filter)
            .select_related("business_unit", "owner", "created_by")
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return serializers.ControlCreateUpdateSerializer
        if self.action == "list":
            return serializers.ControlListSerializer
        return serializers.ControlDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            control = services.create_control(
                user=request.user, **serializer.validated_data
            )
            return Response(
                serializers.ControlDetailSerializer(control).data,
                status=status.HTTP_201_CREATED,
            )
        except ControlPermissionError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_403_FORBIDDEN
            )

    def update(self, request, *args, **kwargs):
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
                serializers.ControlDetailSerializer(control).data,
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
        instance = self.get_object()
        try:
            services.delete_control(control=instance, user=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ControlPermissionError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
