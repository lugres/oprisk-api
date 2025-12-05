"""
Filters for the controls API.
"""

import django_filters
from django.db.models import Q

from .models import Control


class ControlFilter(django_filters.FilterSet):
    business_unit = django_filters.NumberFilter(field_name="business_unit__id")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Control
        fields = [
            "is_active",
            "control_type",
            "control_nature",
            "business_unit",
        ]

    def filter_search(self, queryset, name, value):

        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )
