"""
Filters for the measures API.
"""

import django_filters
from django.utils import timezone
from .models import Measure


class MeasureFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status__code")

    responsible = django_filters.CharFilter(method="filter_by_responsible")
    created_by = django_filters.CharFilter(method="filter_by_created_by")

    incident = django_filters.NumberFilter(field_name="incidents__id")

    deadline_before = django_filters.DateFilter(
        field_name="deadline", lookup_expr="lte"
    )
    deadline_after = django_filters.DateFilter(
        field_name="deadline", lookup_expr="gte"
    )

    is_overdue = django_filters.BooleanFilter(method="filter_by_is_overdue")

    search = django_filters.CharFilter(
        field_name="description", lookup_expr="icontains"
    )

    ordering = django_filters.OrderingFilter(
        fields=(
            ("deadline", "deadline"),
            ("created_at", "created_at"),
        )
    )

    class Meta:
        model = Measure
        fields = [
            "status",
            "responsible",
            "created_by",
            "incident",
            "deadline_before",
            "deadline_after",
            "is_overdue",
            "search",
        ]

    def filter_by_responsible(self, queryset, name, value):
        if value == "me":
            return queryset.filter(responsible=self.request.user)
        return queryset.filter(responsible_id=value)

    def filter_by_created_by(self, queryset, name, value):
        if value == "me":
            return queryset.filter(created_by=self.request.user)
        return queryset.filter(created_by_id=value)

    def filter_by_is_overdue(self, queryset, name, value):
        if value:
            return queryset.filter(
                status__code__in=["OPEN", "IN_PROGRESS"],
                deadline__lt=timezone.now().date(),
            )
        return queryset
