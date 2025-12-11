"""
Tests for the models in the measures app.
Focuses on data integrity, field validation, and model behavior.
Does NOT test business logic (see test_api.py).
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model

from risks.models import (
    Risk,
    RiskStatus,
    RiskCategory,
    RiskCategoryToBaselEventType,
    IncidentRisk,
    RiskMeasure,
    RiskControl,
)
from incidents.models import Incident, IncidentStatusRef
from measures.models import Measure
from controls.models import Control
from references.models import (
    BaselEventType,
    BusinessUnit,
    BusinessProcess,
    Product,
)

User = get_user_model()


class RiskModelTests(TestCase):
    """Tests for the core Risk model and its basic behavior."""

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

    # --- Basic CRUD Tests ---

    def test_risk_creation(self):
        """Test basic risk creation and default status."""
        self.assertIsInstance(self.risk, Risk)
        self.assertEqual(self.risk.status, RiskStatus.DRAFT)
        self.assertEqual(self.risk.created_by, self.user)
        self.assertIsNotNone(self.risk.created_at)

    def test_risk_str_representation(self):
        """Test Risk __str__ method."""
        self.risk.id = 42
        expected = "Risk #42: System Outage Risk"
        self.assertEqual(str(self.risk), expected)

    # --- Field Constraint Tests ---

    def test_title_is_required(self):
        """Test that title cannot be blank."""
        risk = Risk(
            description="Test",
            risk_category=self.category,
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        with self.assertRaises(ValidationError) as cm:
            risk.full_clean()

        self.assertIn("title", cm.exception.message_dict)

    def test_description_is_required(self):
        """Test that description cannot be blank."""
        risk = Risk(
            title="Test",
            risk_category=self.category,
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        with self.assertRaises(ValidationError) as cm:
            risk.full_clean()

        self.assertIn("description", cm.exception.message_dict)

    def test_risk_category_is_required(self):
        """Test that risk_category cannot be null."""
        with self.assertRaises(ValidationError):
            Risk.objects.create(
                title="Test",
                description="Test",
                risk_category=None,
                created_by=self.user,
                owner=self.user,
            )

    def test_title_max_length(self):
        """Test title respects max_length of 255."""
        long_title = "A" * 256
        risk = Risk(
            title=long_title,
            description="Test",
            risk_category=self.category,
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        with self.assertRaises(ValidationError):
            risk.full_clean()

    # --- Database Constraint Tests ---

    def test_on_delete_protect_for_category(self):
        """Test that deleting a RiskCategory fails if a Risk references it."""
        # 1. Verify PROTECT works (cannot delete category while risk uses it)
        with self.assertRaises(IntegrityError):
            self.category.delete()

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

    # --- Score Validator Tests ---

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

    def test_inherent_risk_score_with_only_likelihood(self):
        """Test that partial scores return None."""
        self.risk.inherent_likelihood = 4
        self.risk.inherent_impact = None
        self.assertIsNone(self.risk.inherent_risk_score)

    def test_inherent_risk_score_with_only_impact(self):
        """Test that partial scores return None."""
        self.risk.inherent_likelihood = None
        self.risk.inherent_impact = 3
        self.assertIsNone(self.risk.inherent_risk_score)

    def test_risk_score_boundary_values(self):
        """Test risk scores at boundaries."""
        # Minimum score
        self.risk.inherent_likelihood = 1
        self.risk.inherent_impact = 1
        self.assertEqual(self.risk.inherent_risk_score, 1)

        # Maximum score
        self.risk.residual_likelihood = 5
        self.risk.residual_impact = 5
        self.assertEqual(self.risk.residual_risk_score, 25)

    # --- Timestamp Tests ---

    def test_created_at_auto_set(self):
        """Test that created_at is automatically set."""
        self.assertIsNotNone(self.risk.created_at)

    def test_updated_at_auto_updates(self):
        """Test that updated_at changes on save."""
        import time

        original_updated = self.risk.updated_at

        time.sleep(0.01)

        self.risk.description = "Updated"
        self.risk.save()

        self.assertGreater(self.risk.updated_at, original_updated)


# M2M Relationship Tests


class RiskCategoryTests(TestCase):
    """Tests for RiskCategory and Basel event type mapping."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for risk category and Basel mapping tests."""
        cls.basel_type = BaselEventType.objects.create(name="Internal Fraud")
        cls.basel_type_2 = BaselEventType.objects.create(name="External Fraud")
        cls.category = RiskCategory.objects.create(name="Fraud Risk")
        cls.category.basel_event_types.add(cls.basel_type)

    def test_risk_category_str_representation(self):
        """Test RiskCategory __str__ method."""
        self.assertEqual(str(self.category), "Fraud Risk")

    def test_risk_category_to_basel_event_type_creation(self):
        """Test successful M2M link creation."""
        self.assertTrue(
            RiskCategoryToBaselEventType.objects.filter(
                risk_category=self.category, basel_event_type=self.basel_type
            ).exists()
        )

        # Create second link
        link_2 = RiskCategoryToBaselEventType.objects.create(
            risk_category=self.category, basel_event_type=self.basel_type_2
        )
        self.assertIsInstance(link_2, RiskCategoryToBaselEventType)
        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 2)

    def test_risk_category_to_basel_unique_constraint(self):
        """Test unique_together constraint on link table."""
        with self.assertRaises(IntegrityError):
            RiskCategoryToBaselEventType.objects.create(
                risk_category=self.category, basel_event_type=self.basel_type
            )

    def test_risk_category_to_basel_cascade(self):
        """Test that deleting RiskCategory cascades to link table."""
        RiskCategoryToBaselEventType.objects.create(
            risk_category=self.category, basel_event_type=self.basel_type_2
        )

        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 2)

        self.category.delete()

        # Both links should be gone due to CASCADE
        self.assertEqual(RiskCategoryToBaselEventType.objects.count(), 0)

    def test_risk_category_to_basel_str_representation(self):
        """Test RiskCategoryToBaselEventType __str__ method."""
        link = RiskCategoryToBaselEventType.objects.get(
            risk_category=self.category, basel_event_type=self.basel_type
        )
        expected = f"{self.category.name} → {self.basel_type.name}"
        self.assertEqual(str(link), expected)


class RiskBaselValidationTests(TestCase):
    """Tests for Basel event type validation (data integrity via clean())."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for Basel event type test cases."""
        cls.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )

        # Create Basel types
        cls.internal_fraud = BaselEventType.objects.create(
            name="Internal Fraud"
        )
        cls.external_fraud = BaselEventType.objects.create(
            name="External Fraud"
        )
        cls.system_failure = BaselEventType.objects.create(
            name="Business Disruption and System Failures"
        )

        # Create risk categories with mappings
        cls.fraud_category = RiskCategory.objects.create(name="Fraud Risk")
        cls.fraud_category.basel_event_types.add(
            cls.internal_fraud, cls.external_fraud
        )

        cls.it_category = RiskCategory.objects.create(name="IT Risk")
        cls.it_category.basel_event_types.add(cls.system_failure)

        cls.bu = BusinessUnit.objects.create(name="Test BU")

    def test_valid_basel_type_for_category(self):
        """Test that valid Basel type passes clean()."""
        risk = Risk(
            title="Test Risk",
            description="Test",
            risk_category=self.fraud_category,
            basel_event_type=self.internal_fraud,  # Valid
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )
        risk.full_clean()  # Should not raise
        self.assertEqual(risk.basel_event_type, self.internal_fraud)

    def test_invalid_basel_type_for_category_raises_validation_error(self):
        """Test that invalid Basel type fails clean()."""
        risk = Risk(
            title="Test Risk",
            description="Test",
            risk_category=self.fraud_category,
            basel_event_type=self.system_failure,  # INVALID
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        with self.assertRaises(ValidationError) as cm:
            risk.full_clean()

        self.assertIn("basel_event_type", cm.exception.message_dict)
        self.assertIn("not valid for risk category", str(cm.exception))

    def test_basel_type_can_be_null(self):
        """Test that Basel type can be null (optional in DRAFT)."""
        risk = Risk(
            title="Test Risk",
            description="Test",
            risk_category=self.fraud_category,
            basel_event_type=None,  # NULL is OK
            status=RiskStatus.DRAFT,
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )
        risk.full_clean()  # Should not raise
        self.assertIsNone(risk.basel_event_type)

    def test_save_calls_full_clean(self):
        """Test that save() enforces validation via full_clean()."""
        risk = Risk(
            title="Test Risk",
            description="Test",
            risk_category=self.fraud_category,
            basel_event_type=self.system_failure,  # INVALID
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        # save() should call full_clean() and raise
        with self.assertRaises(ValidationError):
            risk.save()

        # Risk should not exist in DB
        self.assertFalse(Risk.objects.filter(title="Test Risk").exists())

    def test_changing_category_with_incompatible_basel_type(self):
        """Test that changing category to incompatible Basel type fails."""
        # Create risk with valid mapping
        risk = Risk.objects.create(
            title="Test Risk",
            description="Test",
            risk_category=self.fraud_category,
            basel_event_type=self.internal_fraud,  # Valid for fraud_category
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        # Change category to IT (doesn't allow internal_fraud)
        risk.risk_category = self.it_category

        with self.assertRaises(ValidationError):
            risk.full_clean()


class RiskRelationshipTests(TestCase):
    """Tests for M2M relationships between Risk and other entities."""

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
        cls.control = Control.objects.create(
            title="Install Firewalls and DDoS sensors",
            description="NOKIA firewalls here",
            business_unit=cls.bu,
            owner=cls.user,
            created_by=cls.user,
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

    def test_risk_control_linkage(self):
        """Test M2M linking between Risk and Control."""
        self.risk_a.controls.add(
            self.control,
            through_defaults={
                "notes": "Mitigates root cause via IT tools",
                "linked_by": self.user,
            },
        )

        # Test risk has control
        self.assertIn(self.control, self.risk_a.controls.all())

        # Test Control has related risk (uses related_name='risks')
        self.assertIn(self.risk_a, self.control.risks.all())

        # Test RiskControl model integrity - both 'link' work
        link = RiskControl.objects.get(risk=self.risk_a, control=self.control)
        # link = self.risk_a.riskcontrol_set.first()
        self.assertIsNotNone(link)
        self.assertEqual(link.notes, "Mitigates root cause via IT tools")

        # RiskControl link has timestamp fields.
        self.assertIsNotNone(link.created_at)
        self.assertIsNotNone(link.updated_at)

    def test_risk_control_link_requires_linked_by(self):
        """Test that RiskControl link requires linked_by user."""
        with self.assertRaises(IntegrityError):
            RiskControl.objects.create(
                risk=self.risk_a,
                control=self.control,
                # Missing linked_by
            )

    def test_risk_control_on_delete_cascade_for_risk(self):
        """Test that deleting risk cascades to RiskControl links."""
        link = RiskControl.objects.create(
            risk=self.risk_a,
            control=self.control,
            linked_by=self.user,
        )
        link_id = link.id

        self.risk_a.delete()

        # Link should be deleted
        self.assertFalse(RiskControl.objects.filter(id=link_id).exists())
        # Control should still exist
        self.assertTrue(Control.objects.filter(id=self.control.id).exists())

    def test_risk_control_on_delete_protect_for_control(self):
        """Test that deleting control with links is blocked (PROTECT)."""
        RiskControl.objects.create(
            risk=self.risk_a,
            control=self.control,
            linked_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            self.control.delete()

        # Both should still exist
        self.assertTrue(Control.objects.filter(id=self.control.id).exists())
        self.assertTrue(Risk.objects.filter(id=self.risk_a.id).exists())

    def test_risk_control_on_delete_protect_for_linked_by_user(self):
        """Test that deleting user who linked is blocked (PROTECT)."""
        linker = User.objects.create_user(
            email="linker2@example.com",
            password="password123",
        )
        RiskControl.objects.create(
            risk=self.risk_a,
            control=self.control,
            linked_by=linker,
        )

        with self.assertRaises(IntegrityError):
            linker.delete()

    def test_risk_control_unique_constraint_enforced(self):
        """Test that unique_together prevents duplicate risk-control links."""
        RiskControl.objects.create(
            risk=self.risk_a,
            control=self.control,
            linked_by=self.user,
            notes="First link",
        )

        # Attempt to create duplicate
        with self.assertRaises(IntegrityError):
            RiskControl.objects.create(
                risk=self.risk_a,
                control=self.control,
                linked_by=self.user,
                notes="Duplicate attempt",
            )

    def test_m2m_unique_constraint(self):
        """Test the unique_together constraint on the link tables."""
        IncidentRisk.objects.create(risk=self.risk_a, incident=self.incident)

        with self.assertRaises(IntegrityError):
            # Attempt to create the same link again
            IncidentRisk.objects.create(
                risk=self.risk_a, incident=self.incident
            )

    def test_risk_can_link_to_multiple_incidents(self):
        """Test that one risk can link to multiple incidents."""
        incident2 = Incident.objects.create(
            title="Second Breach",
            created_by=self.user,
            business_unit=self.bu,
            status=self.inc_status,
        )

        self.risk_a.incidents.add(self.incident, incident2)

        self.assertEqual(self.risk_a.incidents.count(), 2)
        self.assertIn(self.incident, self.risk_a.incidents.all())
        self.assertIn(incident2, self.risk_a.incidents.all())

    def test_incident_can_link_to_multiple_risks(self):
        """Test that one incident can link to multiple risks."""
        self.incident.risks.add(self.risk_a, self.risk_b)

        self.assertEqual(self.incident.risks.count(), 2)
        self.assertIn(self.risk_a, self.incident.risks.all())
        self.assertIn(self.risk_b, self.incident.risks.all())

    def test_risk_can_link_to_multiple_controls(self):
        """Test that one risk can link to multiple controls."""
        control2 = Control.objects.create(
            title="Sign up for CloudFlare service",
            description="CloudFlare service",
            business_unit=self.bu,
            owner=self.user,
            created_by=self.user,
        )

        self.risk_a.controls.add(
            self.control,
            control2,
            through_defaults={
                "notes": "Mitigates root cause with CloudFlare",
                "linked_by": self.user,
            },
        )

        self.assertEqual(self.risk_a.controls.count(), 2)
        self.assertIn(self.control, self.risk_a.controls.all())
        self.assertIn(control2, self.risk_a.controls.all())

    def test_control_can_link_to_multiple_risks(self):
        """Test that one control can link to multiple risks."""
        self.control.risks.add(
            self.risk_a,
            self.risk_b,
            through_defaults={
                "notes": "Mitigates root cause",
                "linked_by": self.user,
            },
        )

        self.assertEqual(self.control.risks.count(), 2)
        self.assertIn(self.risk_a, self.control.risks.all())
        self.assertIn(self.risk_b, self.control.risks.all())


class RiskEdgeCaseTests(TestCase):
    """Tests for edge cases and boundary conditions."""

    @classmethod
    def setUpTestData(cls):
        """Set up data for edge test cases."""
        cls.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )
        cls.basel_type = BaselEventType.objects.create(name="Test Type")
        cls.category = RiskCategory.objects.create(name="Test Category")
        cls.category.basel_event_types.add(cls.basel_type)
        cls.bu = BusinessUnit.objects.create(name="Test BU")

    def test_multiple_risks_same_category_and_basel(self):
        """Test that multiple risks can share category and Basel type."""
        risk1 = Risk.objects.create(
            title="Risk 1",
            description="Test 1",
            risk_category=self.category,
            basel_event_type=self.basel_type,
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        risk2 = Risk.objects.create(
            title="Risk 2",
            description="Test 2",
            risk_category=self.category,
            basel_event_type=self.basel_type,  # Same Basel type
            created_by=self.user,
            owner=self.user,
            business_unit=self.bu,
        )

        self.assertNotEqual(risk1.id, risk2.id)
        self.assertEqual(risk1.basel_event_type, risk2.basel_event_type)

    def test_risk_with_all_optional_context_null(self):
        """Test risk can exist without business_unit, process, product."""
        risk = Risk.objects.create(
            title="Generic Risk",
            description="Test",
            risk_category=self.category,
            business_unit=None,
            business_process=None,
            product=None,
            created_by=self.user,
            owner=self.user,
        )

        self.assertIsNone(risk.business_unit)
        self.assertIsNone(risk.business_process)
        self.assertIsNone(risk.product)
