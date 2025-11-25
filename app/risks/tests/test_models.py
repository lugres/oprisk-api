"""
Tests for the models in the measures app.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model

# from datetime import date
# from django.utils import timezone
# from unittest.mock import MagicMock

# Assuming these models exist and are imported correctly
from risks.models import (
    Risk,
    RiskStatus,
    RiskCategory,
    RiskCategoryToBaselEventType,
    IncidentRisk,
    RiskMeasure,
)
from incidents.models import Incident, IncidentStatusRef
from measures.models import Measure
from references.models import (
    BaselEventType,
    BusinessUnit,
    BusinessProcess,
    Product,
)

User = get_user_model()


class RiskModelTests(TestCase):
    """Tests for the core Risk model and its relationships."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for testing risk models (single entity focused)."""
        # Create a basic user for ownership and audit fields
        cls.user = User.objects.create_user(
            email="manager@example.com",
            password="password123",
        )
        cls.risk_officer = User.objects.create_user(
            email="ro@example.com",
            password="password123_ro",
        )

        # Create necessary reference data
        cls.basel_type = BaselEventType.objects.create(
            name="Execution, Delivery, & Process Mgmt"
        )
        cls.basel_type_2 = BaselEventType.objects.create(
            name="IT System Failure"
        )
        cls.bu = BusinessUnit.objects.create(name="Sales")
        cls.process = BusinessProcess.objects.create(name="Order Fulfillment")
        cls.product_ref = Product.objects.create(name="Software License")

        cls.category = RiskCategory.objects.create(name="Process Failure")
        cls.category.basel_event_types.add(cls.basel_type)

        # Create a minimal Risk instance
        cls.risk = Risk.objects.create(
            title="System Outage Risk",
            description="Risk of key system failure during peak hours.",
            status=RiskStatus.DRAFT,
            created_by=cls.user,
            owner=cls.user,
            risk_category=cls.category,
            business_unit=cls.bu,
        )

    # Model Integrity and Constraint Tests

    def test_risk_creation(self):
        """Test basic risk creation and default status."""
        self.assertIsInstance(self.risk, Risk)
        self.assertEqual(self.risk.status, RiskStatus.DRAFT)
        self.assertEqual(self.risk.created_by, self.user)
        self.assertIsNotNone(self.risk.created_at)

    def test_on_delete_protect_for_category(self):
        """Test that deleting a RiskCategory fails if a Risk references it."""
        # 1. Verify PROTECT works (cannot delete category while risk uses it)
        with self.assertRaises(IntegrityError):
            self.category.delete()

        # # Test deletion succeeds if no Risk references it
        # self.risk.risk_category = None
        # self.risk.save()
        # self.category.delete()

        # 2. Verify deletion works when the reference is removed
        # Since risk_category is NOT nullable, we must delete the Risk itself
        # to free up the Category.
        self.risk.delete()  # Delete the risk
        self.category.delete()  # Now category deletion should succeed

        # Verify it's gone
        self.assertFalse(
            RiskCategory.objects.filter(id=self.category.id).exists()
        )

    def test_on_delete_protect_for_owner(self):
        """Test that deleting a User fails if they own a Risk."""
        # Risk is owned by self.user
        with self.assertRaises(IntegrityError):
            self.user.delete()

    def test_score_validators(self):
        """Test that scores must be between 1 and 5 (inclusive)."""
        # Test min value violation
        self.risk.inherent_likelihood = 0
        with self.assertRaises(ValidationError):
            self.risk.full_clean()

        # Test max value violation
        self.risk.inherent_likelihood = 6
        with self.assertRaises(ValidationError):
            self.risk.full_clean()

        # Test valid value
        self.risk.inherent_likelihood = 5
        self.risk.full_clean()  # Should not raise

    # Computed Property Tests

    def test_inherent_risk_score_calculation(self):
        """Test the inherent_risk_score property."""
        # Should return None if scores are missing (DRAFT state)
        self.assertIsNone(self.risk.inherent_risk_score)

        # Test high score
        self.risk.inherent_likelihood = 5
        self.risk.inherent_impact = 4
        self.assertEqual(self.risk.inherent_risk_score, 20)

    def test_residual_risk_score_calculation(self):
        """Test the residual_risk_score property."""
        # Should return None if scores are missing
        self.assertIsNone(self.risk.residual_risk_score)

        # Test low score
        self.risk.residual_likelihood = 1
        self.risk.residual_impact = 2
        self.assertEqual(self.risk.residual_risk_score, 2)

    # !- test fails, too complex, replaced with other 3 simpler tests below

    # def test_risk_category_to_basel_event_type_integrity(self):
    #     """Test the M2M through model unique constraint and foreign keys."""

    #     # 1. Verify the pre-existing link (1, 1) from setUpTestData exists.
    #     # We don't need to create it again to prove it exists.
    #     self.assertTrue(
    #         RiskCategoryToBaselEventType.objects.filter(
    #             risk_category=self.category, basel_event_type=self.basel_type
    #         ).exists()
    #     )

    #     # 2. Test successful creation of a NEW link (1, 2).
    #     link_1 = RiskCategoryToBaselEventType.objects.create(
    #         risk_category=self.category, basel_event_type=self.basel_type_2
    #     )
    #     self.assertIsInstance(link_1, RiskCategoryToBaselEventType)

    #     # 3. Test unique constraint enforcement (Try to create 1, 2 again).
    #     with self.assertRaises(IntegrityError):
    #         RiskCategoryToBaselEventType.objects.create(
    #             risk_category=self.category,
    #             basel_event_type=self.basel_type_2,
    #         )

    #     # 4. Test that deleting the category cascades to the link table.
    #     # We must delete the Risk first because of on_delete=PROTECT
    #     # on the Category.
    #     self.risk.delete()
    #     self.category.delete()

    #     # Both links should be gone due to CASCADE.
    #     self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 0)

    def test_risk_category_to_basel_event_type_creation(self):
        """Test successful M2M link creation and check link count."""
        # 1. Assert pre-existing link (1, 1) from setUpTestData is there.
        self.assertTrue(
            RiskCategoryToBaselEventType.objects.filter(
                risk_category=self.category, basel_event_type=self.basel_type
            ).exists()
        )

        # 2. Successfully create the NEW link (1, 2).
        link_2 = RiskCategoryToBaselEventType.objects.create(
            risk_category=self.category, basel_event_type=self.basel_type_2
        )
        self.assertIsInstance(link_2, RiskCategoryToBaselEventType)
        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 2)

    def test_risk_category_to_basel_event_type_unique_constraint(self):
        """Dedicated test for IntegrityError on unique_together constraint."""
        # The link (1, 1) is created in setUpTestData. Try to create it again.
        with self.assertRaises(IntegrityError):
            RiskCategoryToBaselEventType.objects.create(
                risk_category=self.category, basel_event_type=self.basel_type
            )

    def test_risk_category_to_basel_event_type_cascade(self):
        """Test that deleting RiskCategory cascades to delete link rows."""
        # Create the second link (1, 2) necessary for the cascade check.
        RiskCategoryToBaselEventType.objects.create(
            risk_category=self.category, basel_event_type=self.basel_type_2
        )

        # Count should be 2: (1, 1) from setup, (1, 2) from above.
        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 2)

        # 1. Must delete the Risk object first
        # (due to on_delete=PROTECT on Category).
        self.risk.delete()

        # 2. Now delete the Category, which should CASCADE to the link table.
        self.category.delete()

        # Assert both links are gone due to CASCADE
        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 0)


# M2M Relationship Tests


class RiskRelationshipTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up data for testing risk models (focused on interaction)."""
        # Create necessary linked entities
        cls.user = User.objects.create_user(
            email="linker@example.com",
            password="tstpsw123",
        )
        cls.category = RiskCategory.objects.create(name="Security")
        cls.bu = BusinessUnit.objects.create(name="IT")

        cls.risk_a = Risk.objects.create(
            title="DDoS Threat",
            description="DDoS Risk",
            created_by=cls.user,
            owner=cls.user,
            risk_category=cls.category,
            business_unit=cls.bu,
        )
        cls.risk_b = Risk.objects.create(
            title="Phishing Threat",
            description="Phishing Risk",
            created_by=cls.user,
            owner=cls.user,
            risk_category=cls.category,
            business_unit=cls.bu,
        )

        cls.inc_status, _ = IncidentStatusRef.objects.get_or_create(
            code="DRAFT", defaults={"name": "Draft"}
        )
        cls.incident = Incident.objects.create(
            title="Major Breach",
            created_by=cls.user,
            business_unit=cls.bu,
            status=cls.inc_status,
        )
        cls.measure = Measure.objects.create(
            description="Implement new firewall",
            created_by=cls.user,
            responsible=cls.user,
            # business_unit=cls.bu,
        )

    def test_incident_risk_linkage(self):
        """Test M2M linking between Risk and Incident."""
        self.risk_a.incidents.add(self.incident)

        # Test risk has incident
        self.assertIn(self.incident, self.risk_a.incidents.all())
        self.assertEqual(self.risk_a.incidents.count(), 1)

        # Test IncidentRisk model integrity
        link = IncidentRisk.objects.get(
            risk=self.risk_a, incident=self.incident
        )
        self.assertIsNotNone(link)

    def test_risk_measure_linkage(self):
        """Test M2M linking between Risk and Measure."""
        self.risk_a.measures.add(self.measure)

        # Test risk has measure
        self.assertIn(self.measure, self.risk_a.measures.all())

        # Test Measure has related risk (uses related_name='risks')
        self.assertIn(self.risk_a, self.measure.risks.all())

        # Test RiskMeasure model integrity
        link = RiskMeasure.objects.get(risk=self.risk_a, measure=self.measure)
        self.assertIsNotNone(link)

    def test_m2m_unique_constraint(self):
        """Test the unique_together constraint on the link tables."""
        IncidentRisk.objects.create(risk=self.risk_a, incident=self.incident)

        with self.assertRaises(IntegrityError):
            # Attempt to create the same link again
            IncidentRisk.objects.create(
                risk=self.risk_a, incident=self.incident
            )
