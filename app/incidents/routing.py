"""
Incident routing evaluator based on rules in JSON predicates.
Routing rules are stored in IncidentRoutingRule data model.
"""

from decimal import Decimal, InvalidOperation
from .models import IncidentRoutingRule, Incident


def evaluate_routing_for_incident(incident: Incident) -> dict | None:
    """
    Evaluates active routing rules against an incident and returns
    the first match based on priority.

    Returns:
        A dictionary containing
        {"route_to_role_id": int | None, "route_to_bu_id": int |
        None, "rule_id": int}
        or None if no rule matches.
    """
    # Fetch active rules ordered by priority (lower number = higher priority)
    rules = IncidentRoutingRule.objects.filter(active=True).order_by(
        "priority", "id"
    )

    for rule in rules:
        predicate = rule.predicate or {}
        match = True  # Assume match until a condition fails

        # --- Evaluate Predicate Conditions ---

        # 1. min_amount
        if "min_amount" in predicate:
            try:
                min_amount = Decimal(predicate["min_amount"])
                # Treat None/missing amount as 0 for comparison
                incident_amount = incident.gross_loss_amount or Decimal("0")
                if incident_amount < min_amount:
                    match = False
            except (InvalidOperation, TypeError, ValueError):
                # If predicate value is invalid or comparison fails,
                # rule doesn't match
                match = False

        # 2. basel_event_type_id
        # (check only if previous conditions still match)
        if match and "basel_event_type_id" in predicate:
            try:
                # Ensure predicate value is an integer
                predicate_event_id = int(predicate["basel_event_type_id"])
                # Check if incident's event type ID matches
                if (
                    not incident.basel_event_type_id
                    or incident.basel_event_type_id != predicate_event_id
                ):
                    match = False
            except (TypeError, ValueError):
                match = False  # Predicate value is not a valid int

        # 3. business_unit_id (check only if previous conditions still match)
        if match and "business_unit_id" in predicate:
            try:
                # Ensure predicate value is an integer
                predicate_bu_id = int(predicate["business_unit_id"])
                # Check if incident's BU ID matches
                if (
                    not incident.business_unit_id
                    or incident.business_unit_id != predicate_bu_id
                ):
                    match = False
            except (TypeError, ValueError):
                match = False  # Predicate value is not a valid int

        # --- Return if Match Found ---
        if match:
            return {
                "route_to_role_id": rule.route_to_role_id,
                "route_to_bu_id": rule.route_to_bu_id,
                "rule_id": rule.id,
            }

    # If loop finishes without any match
    return None
