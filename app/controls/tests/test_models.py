"""
Tests for the models in the controls app.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.contrib.auth import get_user_model

from controls.models import (
    Control,
    ControlType,
    ControlNature,
    ControlFrequency,
)
from references.models import BusinessUnit, BusinessProcess

User = get_user_model()


class ControlModelTest(TestCase):
    """Tests for the Control model (Library definition)."""

    @classmethod
    def setUpTestData(cls):
        # Create dependencies
        cls.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpassword",
        )
        cls.risk_officer = User.objects.create_user(
            email="ro@example.com",
            password="password123_ro",
        )
        cls.bu = BusinessUnit.objects.create(name="Finance")
        cls.process = BusinessProcess.objects.create(name="Accounts Payable")

        # Create a fully populated valid control
        cls.control = Control.objects.create(
            title="Dual Signature Check",
            description="Checks over $10k require two authorized signatures.",
            reference_doc="http://wiki.corp/policy/fin-001",
            control_type=ControlType.PREVENTIVE,
            control_nature=ControlNature.MANUAL,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=5,  # Design effectiveness (1-5)
            business_unit=cls.bu,
            business_process=cls.process,
            created_by=cls.risk_officer,
            owner=cls.owner,
            is_active=True,
        )

    def test_control_creation_happy_path(self):
        """Test that a control is created with correct fields and values."""
        self.assertIsInstance(self.control, Control)
        self.assertEqual(self.control.title, "Dual Signature Check")
        self.assertEqual(self.control.effectiveness, 5)
        self.assertTrue(self.control.is_active)
        # Check string representation
        self.assertEqual(str(self.control), "Dual Signature Check")

    def test_default_values(self):
        """Test that optional fields use correct defaults."""
        simple_control = Control.objects.create(
            title="Simple Backup",
            description="Daily DB backup",
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )

        # Verify defaults from model definition
        self.assertTrue(simple_control.is_active)
        self.assertEqual(simple_control.control_type, ControlType.PREVENTIVE)
        self.assertEqual(simple_control.control_nature, ControlNature.MANUAL)
        self.assertIsNone(simple_control.effectiveness)

    # --- Validation Tests ---

    def test_effectiveness_score_validation(self):
        """Test that effectiveness must be between 1 and 5."""
        # 1. Test Valid values
        self.control.effectiveness = 1
        self.control.full_clean()  # Should pass
        self.control.effectiveness = 5
        self.control.full_clean()  # Should pass

        # 2. Test Invalid: Too high
        self.control.effectiveness = 6
        with self.assertRaises(ValidationError) as cm:
            self.control.full_clean()
        self.assertIn("effectiveness", cm.exception.message_dict)

        # 3. Test Invalid: Too low
        self.control.effectiveness = 0
        with self.assertRaises(ValidationError) as cm:
            self.control.full_clean()
        self.assertIn("effectiveness", cm.exception.message_dict)

    def test_effectiveness_can_be_null(self):
        """Test that effectiveness can be left blank (undetermined)."""
        self.control.effectiveness = None
        self.control.full_clean()  # Should not raise validation error
        self.control.save()
        self.assertIsNone(self.control.effectiveness)

    def test_required_fields(self):
        """Test that title, description, bu, and owner are required."""
        control = Control(control_type=ControlType.DETECTIVE)
        with self.assertRaises(ValidationError) as cm:
            control.full_clean()

        errors = cm.exception.message_dict
        self.assertIn("title", errors)
        self.assertIn("description", errors)
        self.assertIn("business_unit", errors)
        self.assertIn("owner", errors)

    # --- Integrity & Relationship Tests ---

    def test_on_delete_protect_owner(self):
        """
        Test that deleting a User who owns a control is BLOCKED.
        Controls are critical assets;
        ownership must be transferred, not deleted.
        """
        with self.assertRaises(IntegrityError):
            self.owner.delete()

    def test_on_delete_protect_business_unit(self):
        """
        Test that deleting a Business Unit that owns controls is BLOCKED.
        """
        with self.assertRaises(IntegrityError):
            self.bu.delete()

    def test_on_delete_protect_business_process(self):
        """
        Test that attempt deleting a Business Process does NOT delete
        the control. It should just raise IntegrityError.
        """
        with self.assertRaises(IntegrityError):
            self.process.delete()

        self.control.refresh_from_db()
        self.assertIsNotNone(self.control.business_process)
        self.assertTrue(Control.objects.filter(id=self.control.id).exists())
