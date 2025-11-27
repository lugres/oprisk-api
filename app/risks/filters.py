"""
Filters for the risks API.
"""

import django_filters
from django.db.models import F, Q


from .models import Risk


class RiskFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(method="filter_status")
    risk_category = django_filters.NumberFilter(field_name="risk_category__id")
    basel_event_type = django_filters.NumberFilter(
        field_name="basel_event_type__id"
    )
    business_unit = django_filters.NumberFilter(field_name="business_unit__id")

    # Owner filtering
    owner = django_filters.CharFilter(method="filter_owner")

    # Score filtering
    inherent_score__gte = django_filters.NumberFilter(
        method="filter_inherent_score"
    )

    # Search
    search = django_filters.CharFilter(method="filter_search")

    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("inherent_likelihood", "inherent_likelihood"),
        )
    )

    class Meta:
        model = Risk
        fields = ["status", "risk_category", "business_unit"]

    def filter_status(self, queryset, name, value):
        statuses = value.split(",")
        return queryset.filter(status__in=statuses)

    def filter_owner(self, queryset, name, value):
        if value == "me":
            return queryset.filter(owner=self.request.user)
        return queryset.filter(owner__id=value)

    def filter_inherent_score(self, queryset, name, value):
        # Inherent score is computed property, so we filter by the raw fields multiplication?
        # OR: Since we can't filter by property in DB, we use annotation or raw logic
        # Simple approach: likelihood * impact >= value
        # Django F expressions allow this:

        return queryset.annotate(
            score=F("inherent_likelihood") * F("inherent_impact")
        ).filter(score__gte=value)

    def filter_search(self, queryset, name, value):

        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )
