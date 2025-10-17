"""
Filters for incidents API.
"""

from django_filters import rest_framework as filters
from .models import Incident


class IncidentFilter(filters.FilterSet):
    """FilterSet for the Incident model."""

    # This allows filtering by the 'code' field on the related status object.
    status__code = filters.CharFilter(
        field_name="status__code",
        lookup_expr="iexact",
        help_text="Filter by incident's status code (case-insensitive exact).",
    )

    class Meta:
        model = Incident
        fields = [
            "near_miss",  # A simple boolean filter, auto-generated
        ]
