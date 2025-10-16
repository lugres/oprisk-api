"""
Filters for incidents API.
"""

from django_filters import rest_framework as filters
from .models import Incident


class IncidentFilter(filters.FilterSet):
    """FilterSet for the Incident model."""

    # This allows filtering by the 'code' field on the related Status model.
    status__code = filters.CharFilter(
        field_name="status__code", lookup_expr="iexact"
    )

    class Meta:
        model = Incident
        fields = [
            "status__code",  # The filter we defined above
            "near_miss",  # A simple boolean filter
        ]
