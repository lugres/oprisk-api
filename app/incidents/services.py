"""
Django-aware service
"""

from django.contrib.auth import get_user_model


from .models import Incident, IncidentStatusRef

User = get_user_model()


def create_incident(*, user: User, **kwargs) -> Incident:
    """Service function to create a new incident with default DRAFT status."""
    draft_status = IncidentStatusRef.objects.get(code="DRAFT")
    # The 'status' key is removed from kwargs if it exists to enforce default
    kwargs.pop("status", None)
    return Incident.objects.create(
        created_by=user, status=draft_status, **kwargs
    )


def submit_incident(*, incident: Incident) -> Incident:
    """Service function to handle business logic of submitting an incident."""
    pending_status = IncidentStatusRef.objects.get(code="PENDING_REVIEW")
    incident.status = pending_status

    # Placeholder for future logic
    # if incident.created_by.manager:
    #     incident.assigned_to = incident.created_by.manager
    # calculate_sla(incident)
    # check_routing_rules(incident)

    incident.save()
    return incident
