"""
Serializers for the risks API.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Risk, RiskCategory
from incidents.models import Incident
from measures.models import Measure
from references.models import (
    BaselEventType,
    BusinessUnit,
    BusinessProcess,
    Product,
)
from users.serializers import UserNestedSerializer
from incidents.serializers import IncidentListSerializer
from measures.serializers import MeasureListSerializer
from references.serializers import BusinessUnitSerializer
from .workflows import get_editable_fields, get_contextual_role_name


# --- Action Payloads ---
class RiskCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(min_length=1)


class RiskReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=20)


class RiskLinkIncidentSerializer(serializers.Serializer):
    incident_id = serializers.PrimaryKeyRelatedField(
        queryset=Incident.objects.all()
    )


class RiskLinkMeasureSerializer(serializers.Serializer):
    measure_id = serializers.PrimaryKeyRelatedField(
        queryset=Measure.objects.all()
    )


# --- Core Serializers ---


class RiskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskCategory
        fields = ["id", "name"]


class RiskListSerializer(serializers.ModelSerializer):
    owner = UserNestedSerializer(read_only=True)
    risk_category = RiskCategorySerializer(read_only=True)

    class Meta:
        model = Risk
        fields = [
            "id",
            "title",
            "status",
            "risk_category",
            "owner",
            "created_at",
        ]


class RiskDetailSerializer(serializers.ModelSerializer):
    owner = UserNestedSerializer(read_only=True)
    created_by = UserNestedSerializer(read_only=True)
    risk_category = RiskCategorySerializer(read_only=True)
    business_unit = BusinessUnitSerializer(read_only=True)

    # Computed
    inherent_risk_score = serializers.IntegerField(read_only=True)
    residual_risk_score = serializers.IntegerField(read_only=True)
    incident_count = serializers.IntegerField(
        source="incidents.count", read_only=True
    )
    measure_count = serializers.IntegerField(
        source="measures.count", read_only=True
    )

    # Contextual
    available_transitions = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    linked_incidents = serializers.SerializerMethodField()
    linked_measures = serializers.SerializerMethodField()

    class Meta:
        model = Risk
        fields = [
            "id",
            "title",
            "description",
            "status",
            "notes",
            "risk_category",
            "basel_event_type",
            "business_unit",
            "business_process",
            "product",
            "owner",
            "created_by",
            "inherent_likelihood",
            "inherent_impact",
            "inherent_risk_score",
            "residual_likelihood",
            "residual_impact",
            "residual_risk_score",
            "created_at",
            "updated_at",
            "validated_at",
            "incident_count",
            "measure_count",
            "linked_incidents",
            "linked_measures",
            "available_transitions",
            "permissions",
            "retirement_reason",
        ]

    def get_available_transitions(self, obj):
        """List available transitions for a risk."""
        return self.context.get("available_transitions", [])

    def get_permissions(self, obj):
        """List available permissions for a risk."""
        return self.context.get("permissions", {})

    def get_linked_incidents(self, obj):
        """Display linked incidents."""
        return IncidentListSerializer(obj.incidents.all(), many=True).data

    def get_linked_measures(self, obj):
        """Display linked measures."""
        return MeasureListSerializer(obj.measures.all(), many=True).data


class RiskCreateSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all()
    )
    risk_category = serializers.PrimaryKeyRelatedField(
        queryset=RiskCategory.objects.all()
    )
    business_unit = serializers.PrimaryKeyRelatedField(
        queryset=BusinessUnit.objects.all()
    )
    business_process = serializers.PrimaryKeyRelatedField(
        queryset=BusinessProcess.objects.all(), required=False
    )
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), required=False
    )

    class Meta:
        model = Risk
        fields = [
            "title",
            "description",
            "risk_category",
            "business_unit",
            "business_process",
            "product",
            "owner",
            "inherent_likelihood",
            "inherent_impact",
        ]


class RiskUpdateSerializer(serializers.ModelSerializer):
    """
    Field-level security enforced here dynamically in __init__, via Domain
    helpers - get_editable_fields, get_contextual_role_name.
    """

    owner = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False
    )
    basel_event_type = serializers.PrimaryKeyRelatedField(
        queryset=BaselEventType.objects.all(), required=False
    )
    # Re-declare category to allow updates
    risk_category = serializers.PrimaryKeyRelatedField(
        queryset=RiskCategory.objects.all(), required=False
    )

    class Meta:
        model = Risk
        fields = [
            "title",
            "description",
            "risk_category",
            "basel_event_type",
            "owner",
            "business_unit",  # BU is read-only in validation logic if needed
            "business_process",
            "product",
            "inherent_likelihood",
            "inherent_impact",
            "residual_likelihood",
            "residual_impact",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Get Context
        request = self.context.get("request")
        instance = getattr(self, "instance", None)

        if request and request.user and instance:
            # 2. Determine Role (Application/Domain logic helper)
            # ! request.user might not be fully loaded here depending on view,
            # but get_contextual_role_nm handles the basic role check safely.
            role = get_contextual_role_name(request.user)

            # 3. Get Allowed Fields from Domain Layer
            editable_fields = get_editable_fields(instance.status, role)

            # 4. Enforce Read-Only on all other fields
            for field_name in self.fields:
                if field_name not in editable_fields:
                    self.fields[field_name].read_only = True

    def validate(self, attrs):
        # Validation: Check Basel mapping if changing
        if "basel_event_type" in attrs:
            # If category is also changing, check against new category
            # Otherwise check against existing category
            category = (
                attrs.get("risk_category") or self.instance.risk_category
            )
            basel = attrs["basel_event_type"]

            if category and basel:
                if basel not in category.basel_event_types.all():
                    raise serializers.ValidationError(
                        "Basel event type is not valid for risk category."
                    )
        return attrs
