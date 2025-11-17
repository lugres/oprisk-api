"""
Object-level permissions for measures.
"""

from rest_framework import permissions


class IsMeasureResponsible(permissions.BasePermission):
    """Allows access only to the measure's responsible user."""

    def has_object_permission(self, request, view, obj):
        return obj.responsible == request.user


class IsMeasureResponsibleOrManager(permissions.BasePermission):
    """Allows access to the responsible user or their manager."""

    def has_object_permission(self, request, view, obj):
        if not obj.responsible:
            return False
        return (
            request.user == obj.responsible
            or request.user == obj.responsible.manager
        )


class IsMeasureCreator(permissions.BasePermission):
    """Allows access only to the measure's creator."""

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class IsMeasureCreatorOrManager(permissions.BasePermission):
    """Allows access to the creator or their manager."""

    def has_object_permission(self, request, view, obj):
        if not obj.created_by:
            return False
        return (
            request.user == obj.created_by
            or request.user == obj.created_by.manager
        )


class IsMeasureParticipant(permissions.BasePermission):
    """
    Allows access to anyone involved (creator, responsible, manager)
    or a Risk Officer.
    """

    def has_object_permission(self, request, view, obj):
        is_resp_or_mgr = obj.responsible and (
            request.user == obj.responsible
            or request.user == obj.responsible.manager
        )
        is_creator_or_mgr = obj.created_by and (
            request.user == obj.created_by
            or request.user == obj.created_by.manager
        )
        is_risk = request.user.role.name == "Risk Officer"

        return is_resp_or_mgr or is_creator_or_mgr or is_risk


class IsCreatorOrManagerForDelete(permissions.BasePermission):
    """
    Specific permission for DELETE.
    Allows creator or their manager.
    """

    def has_object_permission(self, request, view, obj):
        if not obj.created_by:
            return False

        # Added Risk Officer based on
        # test_delete_open_measure_as_manager_succeeds
        # Let's adjust to match your test name:
        if not obj.created_by:
            return False

        is_creator_or_their_manager = (
            request.user == obj.created_by
            or request.user == obj.created_by.manager
        )
        # Your test 'test_delete_open_measure_as_manager_succeeds' uses
        # self.manager, who is the manager of the *creator*.
        return is_creator_or_their_manager
