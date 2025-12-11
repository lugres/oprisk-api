"""
Tests for the models in the controls app.
Focused on data integrity (constraints, cascades),
field validation (required fields, ranges, max lengths, enums),
and model behavior (defaults, timestamps, nullability).
Business logic will be in the test_api.py.
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

    def test_control_with_no_business_process_allowed(self):
        """Test that business_process is optional (nullable)."""
        control = Control.objects.create(
            title="Generic Control",
            description="Not process-specific",
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
            control_frequency=ControlFrequency.DAILY,
        )
        self.assertIsNone(control.business_process)

    def test_timestamped_fields_auto_populate(self):
        """Test that TimestampedModel fields are auto-populated."""
        control = Control.objects.create(
            title="Timestamped Control",
            description="Testing timestamps",
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )

        self.assertIsNotNone(control.created_at)
        self.assertIsNotNone(control.updated_at)

        # On creation, timestamps should be very close (within 1 second)
        time_diff = abs(
            (control.updated_at - control.created_at).total_seconds()
        )
        self.assertLess(time_diff, 1.0)

        # Update and verify updated_at changes
        original_created = control.created_at
        original_updated = control.updated_at
        control.description = "Updated description"
        control.save()

        self.assertEqual(control.created_at, original_created)
        self.assertGreater(control.updated_at, original_updated)

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

    def test_control_title_max_length(self):
        """Test that title enforces max_length=255."""
        long_title = "A" * 256
        control = Control(
            title=long_title,
            description="Test",
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            control.full_clean()
        self.assertIn("title", cm.exception.message_dict)

    def test_reference_doc_max_length(self):
        """Test that reference_doc enforces max_length=255."""
        long_ref = "http://example.com/" + "A" * 250
        control = Control(
            title="Test Control",
            description="Test",
            reference_doc=long_ref,
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            control.full_clean()
        self.assertIn("reference_doc", cm.exception.message_dict)

    def test_control_type_choices_are_valid(self):
        """Test that all ControlType choices work."""
        for control_type, _ in ControlType.choices:
            control = Control.objects.create(
                title=f"Control {control_type}",
                description=f"Testing {control_type}",
                control_type=control_type,
                business_unit=self.bu,
                owner=self.owner,
                created_by=self.risk_officer,
            )
            self.assertEqual(control.control_type, control_type)
            control.delete()

    def test_control_nature_choices_are_valid(self):
        """Test that all ControlNature choices work."""
        for nature, _ in ControlNature.choices:
            control = Control.objects.create(
                title=f"Control {nature}",
                description=f"Testing {nature}",
                control_nature=nature,
                business_unit=self.bu,
                owner=self.owner,
                created_by=self.risk_officer,
            )
            self.assertEqual(control.control_nature, nature)
            control.delete()

    def test_control_frequency_choices_are_valid(self):
        """Test that all ControlFrequency choices work."""
        for freq, _ in ControlFrequency.choices:
            control = Control.objects.create(
                title=f"Control {freq}",
                description=f"Testing {freq}",
                control_frequency=freq,
                business_unit=self.bu,
                owner=self.owner,
                created_by=self.risk_officer,
            )
            self.assertEqual(control.control_frequency, freq)
            control.delete()

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
