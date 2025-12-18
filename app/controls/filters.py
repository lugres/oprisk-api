"""
Filters for the controls API.
"""

import django_filters
from django.db.models import Q

from .models import Control, ControlLevel


class ControlFilter(django_filters.FilterSet):
    business_unit = django_filters.NumberFilter(field_name="business_unit__id")
    control_level = django_filters.ChoiceFilter(choices=ControlLevel.choices)
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Control
        fields = [
            "is_active",
            "control_level",
            "control_type",
            "control_nature",
            "business_unit",
        ]

    def filter_search(self, queryset, name, value):

        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )
