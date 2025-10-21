"""
Object-level permissions
"""

from rest_framework import permissions


class CanSubmitIncident(permissions.BasePermission):
    """Permission to allow only the creator to submit a DRAFT incident."""

    message = "Only creator can submit an incident, and it must be in DRAFT."

    def has_object_permission(self, request, view, obj):
        return request.user == obj.created_by and obj.status.code == "DRAFT"
