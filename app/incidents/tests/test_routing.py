"""
Tests for incident custom routing.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

# Import models needed for setup and routing logic
from incidents.models import (
    Incident,
    IncidentRoutingRule,
    SimplifiedEventTypeRef,
)
from references.models import Role, BusinessUnit  # , BaselEventType

# Import the routing evaluation function (to be created)
from incidents.routing import evaluate_routing_for_incident


User = get_user_model()


class IncidentRoutingEvaluationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up data shared across all tests in this class."""
        # --- Reference Data ---
        cls.bu_retail = BusinessUnit.objects.create(name="Retail")
        cls.bu_corp = BusinessUnit.objects.create(name="Corporate")
        cls.bu_group_orm = BusinessUnit.objects.create(
            name="Group ORM"
        )  # For Rule A target
        cls.bu_infosec = BusinessUnit.objects.create(
            name="InfoSec"
        )  # For Rule B target
        cls.bu_fraud = BusinessUnit.objects.create(
            name="Fraud Unit"
        )  # For Rule C target

        # Simplified event types for early stage (submit/review)
        cls.event_simple_it_disruption = SimplifiedEventTypeRef.objects.create(
            name="IT / Data / Cyber"
        )
        cls.event_simple_fraud = SimplifiedEventTypeRef.objects.create(
            name="Fraud"
        )
        cls.event_simple_other = SimplifiedEventTypeRef.objects.create(
            name="Other / Unsure"
        )  # Non-matching event

        # This is now for 'phase 2' routing (validate)
        # cls.event_it_disruption = BaselEventType.objects.create(
        #     name="Business Disruption & System Failures"
        # )
        # cls.event_ext_fraud = BaselEventType.objects.create(
        #     name="External Fraud"
        # )
        # cls.event_other = BaselEventType.objects.create(
        #     name="Damage Physical Assets"
        # )  # Non-matching event

        cls.role_infosec = Role.objects.create(name="InfoSec")
        cls.role_fraud_inv = Role.objects.create(name="Fraud Investigator")
        cls.role_group_orm = Role.objects.create(
            name="Group ORM"
        )  # Optional role target for Rule A

        # --- Routing Rules (Mirroring SQL test_data.sql examples) ---

        # Rule A: Material losses > $1,000,000 -> Group ORM BU
        # (High Priority)
        cls.rule_a = IncidentRoutingRule.objects.create(
            description="Material losses > $1M -> Group ORM BU",
            predicate={"min_amount": "1000000.00"},
            route_to_bu=cls.bu_group_orm,
            priority=5,
        )

        # Rule B: IT/security events in Retail -> InfoSec Role + BU
        # (Medium Priority)
        cls.rule_b = IncidentRoutingRule.objects.create(
            description="IT/security events in Retail -> InfoSec",
            predicate={
                "simplified_event_type_id": cls.event_simple_it_disruption.id,
                "business_unit_id": cls.bu_retail.id,
            },
            route_to_role=cls.role_infosec,
            route_to_bu=cls.bu_infosec,
            priority=10,
        )

        # Rule C: All external fraud incidents -> Fraud Role + BU
        # (Medium-Low Priority)
        cls.rule_c = IncidentRoutingRule.objects.create(
            description="Fraud -> Fraud Investigation Unit",
            predicate={"simplified_event_type_id": cls.event_simple_fraud.id},
            route_to_role=cls.role_fraud_inv,
            route_to_bu=cls.bu_fraud,
            priority=15,
        )

        # Rule D: Catch-all for Retail BU
        # (Low Priority - like SQL Rule 3 in Python setup)
        cls.rule_d = IncidentRoutingRule.objects.create(
            description="General Retail Event Fallback",
            predicate={"business_unit_id": cls.bu_retail.id},
            route_to_bu=cls.bu_retail,  # Route to the BU itself
            priority=100,
        )

        # --- Test Incidents (Dedicated object per scenario) ---

        # Incident designed to match Rule A (high amount, any BU/event)
        cls.incident_for_rule_a = Incident(
            title="Large Loss Incident",
            business_unit=cls.bu_corp,  # Doesn't matter for this rule
            simplified_event_type=cls.event_simple_other,  # Doesn't matter
            gross_loss_amount=Decimal("2000000.00"),
        )

        # Incident designed to match Rule B (IT event in Retail)
        cls.incident_for_rule_b = Incident(
            title="Retail IT Outage",
            business_unit=cls.bu_retail,
            simplified_event_type=cls.event_simple_it_disruption,
            gross_loss_amount=Decimal("50000.00"),  # Below Rule A threshold
        )

        # Incident designed to match Rule C (External Fraud, any BU)
        cls.incident_for_rule_c = Incident(
            title="Corp Card Fraud",
            business_unit=cls.bu_corp,  # Different BU
            simplified_event_type=cls.event_simple_fraud,
            gross_loss_amount=Decimal("25000.00"),  # Below Rule A threshold
        )

        # Incident designed to only match Rule D
        # (Retail BU, non-matching event/amount)
        cls.incident_for_rule_d = Incident(
            title="Minor Retail Issue",
            business_unit=cls.bu_retail,
            simplified_event_type=cls.event_simple_other,  # No match B or C
            gross_loss_amount=Decimal("100.00"),  # Doesn't match A
        )

        # Incident designed to match NO rules
        # (Corp BU, non-matching event/amount)
        cls.incident_no_match = Incident(
            title="Corp Asset Damage",
            business_unit=cls.bu_corp,
            simplified_event_type=cls.event_simple_other,
            gross_loss_amount=Decimal("500.00"),
        )

        # Incident with missing amount data (should not match Rule A)
        cls.incident_missing_amount = Incident(
            title="Retail Fraud - Amount TBD",
            business_unit=cls.bu_retail,
            simplified_event_type=cls.event_simple_fraud,  # Could match Rule C
            gross_loss_amount=None,
        )

    def test_routing_matches_amount_rule_a(self):
        """Test Rule A (min_amount) matches and wins due to priority."""
        routing_result = evaluate_routing_for_incident(
            self.incident_for_rule_a
        )
        self.assertIsNotNone(routing_result)
        self.assertEqual(routing_result["rule_id"], self.rule_a.id)
        self.assertIsNone(routing_result["route_to_role_id"])
        self.assertEqual(
            routing_result["route_to_bu_id"], self.bu_group_orm.id
        )

    def test_routing_matches_bu_and_event_rule_b(self):
        """Test Rule B (BU + Event) matches."""
        routing_result = evaluate_routing_for_incident(
            self.incident_for_rule_b
        )
        self.assertIsNotNone(routing_result)
        self.assertEqual(routing_result["rule_id"], self.rule_b.id)
        self.assertEqual(
            routing_result["route_to_role_id"], self.role_infosec.id
        )
        self.assertEqual(routing_result["route_to_bu_id"], self.bu_infosec.id)

    def test_routing_matches_event_rule_c(self):
        """Test Rule C (Event only) matches."""
        routing_result = evaluate_routing_for_incident(
            self.incident_for_rule_c
        )
        self.assertIsNotNone(routing_result)
        self.assertEqual(routing_result["rule_id"], self.rule_c.id)
        self.assertEqual(
            routing_result["route_to_role_id"], self.role_fraud_inv.id
        )
        self.assertEqual(routing_result["route_to_bu_id"], self.bu_fraud.id)

    def test_routing_matches_fallback_bu_rule_d(self):
        """Test Rule D (BU only fallback) matches when others don't."""
        routing_result = evaluate_routing_for_incident(
            self.incident_for_rule_d
        )
        self.assertIsNotNone(routing_result)
        self.assertEqual(routing_result["rule_id"], self.rule_d.id)
        self.assertIsNone(routing_result["route_to_role_id"])
        self.assertEqual(routing_result["route_to_bu_id"], self.bu_retail.id)

    def test_routing_no_match_returns_none(self):
        """Test that None is returned when no rules match."""
        routing_result = evaluate_routing_for_incident(self.incident_no_match)
        self.assertIsNone(routing_result)

    def test_routing_handles_missing_amount_correctly(self):
        """Test missing amount prevents matching Rule A,
        falls back correctly."""
        # This incident has event=Fraud, so it should match Rule C
        routing_result = evaluate_routing_for_incident(
            self.incident_missing_amount
        )
        self.assertIsNotNone(routing_result)
        self.assertEqual(
            routing_result["rule_id"], self.rule_c.id
        )  # Should match Rule C
