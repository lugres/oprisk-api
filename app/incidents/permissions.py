"""
Object-level permissions.
"""

from rest_framework import permissions


# class CanSubmitIncident(permissions.BasePermission):
#     """Permission to allow only the creator to submit a DRAFT incident."""

#     message = "Only creator can submit an incident, and it must be in DRAFT."

#     def has_object_permission(self, request, view, obj):
#         return request.user == obj.created_by and obj.status.code == "DRAFT"


class IsIncidentCreatorForSubmit(permissions.BasePermission):
    """Object-level permission to only allow the incident creator."""

    message = "Only creator can submit an incident, and it must be in DRAFT."

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user and obj.status.code == "DRAFT"


class IsIncidentManagerForReview(permissions.BasePermission):
    """Object-level permission to only allow the creator's manager."""

    message = (
        "Only manager can review an incident, and it must be"
        " in PENDING_REVIEW."
    )

    def has_object_permission(self, request, view, obj):
        if not obj.created_by:
            return False
        return (
            obj.created_by.manager == request.user
            and obj.status.code == "PENDING_REVIEW"
        )


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
