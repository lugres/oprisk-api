"""
Object-level permissions.
"""

from rest_framework import permissions


class IsIncidentCreator(permissions.BasePermission):
    """Object-level permission to only allow the incident creator."""

    message = "Only the incident creator can submit an incident."

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class IsIncidentManager(permissions.BasePermission):
    """Object-level permission to only allow the creator's manager."""

    message = (
        "Only the manager of the incident creator can review an incident."
    )

    def has_object_permission(self, request, view, obj):
        if not obj.created_by:
            return False
        return obj.created_by.manager == request.user


class IsUserInRole(permissions.BasePermission):
    """
    View-level permission to allow access only to users with a specific role.
    Usage: permission_classes=[IsUserInRole('Risk Officer', 'Admin')]
    """

    message = "User does not have required role to get an access."

    def __init__(self, *role_names):
        self.role_names = set(role_names)

    def has_permission(self, request, view):
        if not request.user.role:
            return False
        return request.user.role.name in self.role_names
