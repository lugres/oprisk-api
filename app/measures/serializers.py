"""
Serializers for the measures API.
"""

from django.utils import timezone
from datetime import date


from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Measure, MeasureStatusRef, MeasureEditableField
from incidents.models import Incident
from incidents.serializers import IncidentListSerializer
from users.serializers import UserNestedSerializer

# --- Re-usable Action Payload Serializers ---


class MeasureReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=10, max_length=1000)


class MeasureCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(min_length=1, max_length=1000)


class MeasureEvidenceSerializer(serializers.Serializer):
    evidence = serializers.CharField(min_length=10, max_length=2000)


class MeasureClosureCommentSerializer(serializers.Serializer):
    closure_comment = serializers.CharField(min_length=10, max_length=2000)


class MeasureLinkIncidentSerializer(serializers.Serializer):
    incident_id = serializers.PrimaryKeyRelatedField(
        queryset=Incident.objects.all()
    )


# --- Core Serializers ---


class MeasureStatusRefSerializer(serializers.ModelSerializer):
    """Serializer for Measure Status objects."""

    class Meta:
        model = MeasureStatusRef
        fields = ["code", "name"]


class MeasureListSerializer(serializers.ModelSerializer):
    """Serializer for list view, with minimal nested data."""

    status = MeasureStatusRefSerializer(read_only=True)
    responsible = UserNestedSerializer(read_only=True)

    class Meta:
        model = Measure
        fields = [
            "id",
            "description",
            "status",
            "responsible",
            "deadline",
            "created_at",
        ]


class MeasureDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer with all computed and related fields."""

    status = MeasureStatusRefSerializer(read_only=True)
    responsible = UserNestedSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)

    # --- Computed Fields (for tests) ---
    is_overdue = serializers.SerializerMethodField()
    linked_incidents = serializers.SerializerMethodField()

    # --- Contextual Fields (for tests) ---
    available_transitions = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Measure
        fields = [
            "id",
            "description",
            "status",
            "responsible",
            "created_by",
            "deadline",
            "notes",
            "closure_comment",
            "created_at",
            "updated_at",
            "closed_at",
            "is_overdue",
            "linked_incidents",
            "available_transitions",
            "permissions",
        ]

    def get_is_overdue(self, obj):
        if obj.deadline and obj.status.code in ("OPEN", "IN_PROGRESS"):
            return obj.deadline < timezone.now().date()
        return False

    def get_linked_incidents(self, obj):
        # Simple serializer for linked incidents

        incidents = obj.incidents.all()
        return IncidentListSerializer(
            incidents, many=True, context=self.context
        ).data

    def get_available_transitions(self, obj):
        # Logic to show what actions are possible
        # This will be based on user permissions from context
        request = self.context.get("request")
        if not request:
            return []

        # This logic can be expanded, but for now:
        user = request.user
        transitions = []

        is_responsible_or_mgr = obj.responsible and (
            user == obj.responsible or user == obj.responsible.manager
        )
        is_risk_officer = user.role and user.role.name == "Risk Officer"

        if obj.status.code == "OPEN" and is_responsible_or_mgr:
            transitions.append(
                {"action": "start-progress", "name": "Start Progress"}
            )
        if obj.status.code == "IN_PROGRESS" and is_responsible_or_mgr:
            transitions.append(
                {"action": "submit-for-review", "name": "Submit for Review"}
            )
        if obj.status.code == "PENDING_REVIEW" and is_risk_officer:
            transitions.append(
                {"action": "return-to-progress", "name": "Return to Progress"}
            )
            transitions.append(
                {"action": "complete", "name": "Complete Measure"}
            )

        # # We'd build a permission helper for this, but for now:
        # is_responsible = (user == obj.responsible) or (
        #     user == obj.responsible.manager
        # )
        # is_risk_officer = user.role.name == "Risk Officer"

        # if obj.status.code == "OPEN" and is_responsible:
        #     transitions.append(
        #         {"action": "start-progress", "name": "Start Progress"}
        #     )
        # if obj.status.code == "IN_PROGRESS" and is_responsible:
        #     transitions.append(
        #         {"action": "submit-for-review", "name": "Submit for Review"}
        #     )
        # if obj.status.code == "PENDING_REVIEW" and is_risk_officer:
        #     transitions.append(
        #         {"action": "return-to-progress", "name": "Return to Progress"}
        #     )
        #     transitions.append(
        #         {"action": "complete", "name": "Complete Measure"}
        #     )

        return transitions

    def get_permissions(self, obj):
        # Logic to show what user can do
        request = self.context.get("request")
        if not request:
            return {}

        user = request.user

        can_edit = False
        can_delete = False
        # We need to get the editable fields for the *current* user/status
        editable_fields = set(
            MeasureEditableField.objects.filter(
                status=obj.status, role=user.role
            ).values_list("field_name", flat=True)
        )
        # Check if there are any fields they can edit
        can_edit = any(
            f in editable_fields
            for f in ["description", "deadline", "responsible"]
        )

        is_creator_or_mgr = obj.created_by and (
            user == obj.created_by or user == obj.created_by.manager
        )
        if obj.status.code == "OPEN" and is_creator_or_mgr:
            can_delete = True

        # can_edit = (
        #     obj.status.code == "OPEN"
        #     and (user == obj.responsible or user == obj.created_by)
        # ) or (
        #     obj.status.code == "IN_PROGRESS"
        #     and user.role.name == "Risk Officer"
        # )
        # can_delete = obj.status.code == "OPEN" and user == obj.created_by

        return {
            "can_edit": can_edit,
            "can_delete": can_delete,
            "can_transition": bool(self.get_available_transitions(obj)),
        }


class MeasureCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new measure."""

    # incident_id is used for the "create-and-link" test
    incident_id = serializers.PrimaryKeyRelatedField(
        queryset=Incident.objects.all(), write_only=True, required=False
    )

    responsible = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=True
    )

    class Meta:
        model = Measure
        fields = [
            "description",
            "responsible",
            "deadline",
            "status",
            "incident_id",
        ]
        read_only_fields = ["status"]

    def validate_deadline(self, value):
        if value and value < date.today():
            raise serializers.ValidationError(
                "Deadline cannot be in the past."
            )
        return value


class MeasureUpdateSerializer(serializers.ModelSerializer):
    """
    Dynamic serializer for PATCH.
    Fields are made read-only based on user role and measure status.
    """

    responsible = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        required=False,  # Allow partial updates
    )

    class Meta:
        model = Measure
        fields = [
            "description",
            "deadline",
            "responsible",
        ]  # All fields a user *might* edit

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # This sets self.instance

        # Get context passed from the ViewSet
        context = self.context
        role = context.get("user_role")

        # Get status from the serializer's instance
        status_obj = None
        if hasattr(self, "instance") and self.instance:
            status_obj = self.instance.status

        # Failsafe: If no role or status, make all fields read-only
        if not role or not status_obj:
            for field_name in self.fields:
                self.fields[field_name].read_only = True
            return

        # Get the set of fields this user is allowed to edit
        editable_fields = set(
            MeasureEditableField.objects.filter(
                status=status_obj, role=role
            ).values_list("field_name", flat=True)
        )

        # Mark all other fields in this serializer as read-only
        for field_name in self.fields:
            if field_name not in editable_fields:
                self.fields[field_name].read_only = True
