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
    ControlLevel,
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

        # central risk team
        cls.bu_risk_central = BusinessUnit.objects.create(
            name="Risk Management"
        )
        cls.central_risk_officer = User.objects.create_user(
            email="central_ro@example.com",
            password="pass123",
            business_unit=cls.bu_risk_central,
        )

        # Create a STANDARD control (no BU)
        cls.standard_control = Control.objects.create(
            title="Group Dual Signature Policy",
            description=(
                "Organization-wide policy: Checks over $10k require"
                " two authorized signatures."
            ),
            reference_doc="http://wiki.corp/policy/fin-001",
            control_type=ControlType.PREVENTIVE,
            control_nature=ControlNature.MANUAL,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=5,
            control_level=ControlLevel.STANDARD,
            business_unit=None,  # Standard controls have no BU
            business_process=None,  # Can be None for standards
            created_by=cls.central_risk_officer,
            owner=cls.central_risk_officer,  # Group Risk owns standards
            is_active=True,
        )

        # Create a fully populated valid control
        cls.control = Control.objects.create(
            title="Dual Signature Check - finance implementation",
            description=(
                "Finance BU implementation: Checks over $10k require two"
                " authorized signatures from Finance approvers."
            ),
            reference_doc="http://wiki.corp/policy/fin-001-finance",
            control_type=ControlType.PREVENTIVE,
            control_nature=ControlNature.MANUAL,
            control_frequency=ControlFrequency.AD_HOC,
            effectiveness=4,  # Design effectiveness (1-5)
            control_level=ControlLevel.LOCAL,
            parent_control=cls.standard_control,
            business_unit=cls.bu,
            business_process=cls.process,
            created_by=cls.risk_officer,
            owner=cls.owner,
            is_active=True,
        )

    def test_control_creation_happy_path(self):
        """Test that a control is created with correct fields and values."""
        self.assertIsInstance(self.control, Control)
        self.assertEqual(
            self.control.title, "Dual Signature Check - finance implementation"
        )
        self.assertEqual(self.control.effectiveness, 4)
        self.assertTrue(self.control.is_active)
        self.assertEqual(self.control.control_level, ControlLevel.LOCAL)
        self.assertEqual(self.control.parent_control, self.standard_control)
        self.assertEqual(self.control.business_unit, self.bu)

        # Check string representation
        self.assertEqual(
            str(self.control),
            "[LOC] Dual Signature Check - finance implementation",
        )

    def test_default_values(self):
        """Test that optional fields use correct defaults."""
        simple_control_std = Control.objects.create(
            title="Standard Simple Backup",
            description="Organization-wide Daily DB backup policy",
            control_level=ControlLevel.STANDARD,
            business_unit=None,
            owner=self.central_risk_officer,
            created_by=self.central_risk_officer,
        )

        # Verify defaults from model definition
        self.assertTrue(simple_control_std.is_active)
        self.assertEqual(
            simple_control_std.control_type, ControlType.PREVENTIVE
        )
        self.assertEqual(
            simple_control_std.control_nature, ControlNature.MANUAL
        )
        self.assertEqual(
            simple_control_std.control_level, ControlLevel.STANDARD
        )
        self.assertIsNone(simple_control_std.effectiveness)
        self.assertIsNone(simple_control_std.business_unit)
        self.assertIsNone(simple_control_std.parent_control)

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

    # --- New Tests for Hierarchical Rules ---

    def test_standard_control_cannot_have_parent(self):
        """Test Rule 1: STANDARD controls cannot have parent controls."""
        invalid_standard = Control(
            title="Invalid Standard",
            description="Standard with parent (invalid)",
            control_level=ControlLevel.STANDARD,
            parent_control=self.standard_control,
            owner=self.central_risk_officer,
            created_by=self.central_risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            invalid_standard.full_clean()

        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn(
            "Standard controls cannot have parent", str(cm.exception)
        )

    def test_local_control_must_have_parent(self):
        """Test Rule 2: LOCAL controls must have parent."""
        invalid_local = Control(
            title="Invalid Local",
            description="Local without parent (invalid)",
            control_level=ControlLevel.LOCAL,
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            invalid_local.full_clean()

        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn("must reference a parent", str(cm.exception))

    def test_local_control_must_have_business_unit(self):
        """Test Rule 3: LOCAL controls must have BU."""
        invalid_local = Control(
            title="Invalid Local",
            description="Local without BU (invalid)",
            control_level=ControlLevel.LOCAL,
            parent_control=self.standard_control,
            owner=self.owner,
            created_by=self.risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            invalid_local.full_clean()

        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn("must belong to a business unit", str(cm.exception))

    def test_standard_control_cannot_have_business_unit(self):
        """Test Rule 4: STANDARD controls should not have BU."""
        invalid_standard = Control(
            title="Invalid Standard",
            description="Standard with BU (invalid)",
            control_level=ControlLevel.STANDARD,
            business_unit=self.bu,
            owner=self.central_risk_officer,
            created_by=self.central_risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            invalid_standard.full_clean()

        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn(
            "should not be assigned to a specific business unit",
            str(cm.exception),
        )

    def test_cannot_be_own_parent(self):
        """Test Rule 5a: Control cannot be its own parent."""
        # Create and save a control first
        control = Control.objects.create(
            title="Test Control",
            description="Test",
            control_level=ControlLevel.LOCAL,
            parent_control=self.standard_control,
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )

        # Try to make it its own parent
        control.parent_control = control
        with self.assertRaises(ValidationError) as cm:
            control.full_clean()

        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn("cannot be its own parent", str(cm.exception))

    def test_circular_reference_prevention(self):
        """Test Rule 5b: Circular parent-child relationships are prevented."""
        # Create a chain: standard -> local1
        local1 = Control.objects.create(
            title="Local 1",
            description="First local",
            control_level=ControlLevel.LOCAL,
            parent_control=self.standard_control,
            business_unit=self.bu,
            owner=self.owner,
            created_by=self.risk_officer,
        )

        # Try to create circular reference: standard -> local1 -> standard
        self.standard_control.parent_control = local1
        self.standard_control.control_level = ControlLevel.LOCAL
        self.standard_control.business_unit = self.bu

        with self.assertRaises(ValidationError) as cm:
            self.standard_control.full_clean()

        # Should fail due to circular reference
        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn(
            "Circular parent-child relationship detected", str(cm.exception)
        )

    def test_get_inheritance_chain(self):
        """Test that inheritance chain is correctly retrieved."""
        chain = self.control.get_inheritance_chain()

        self.assertEqual(len(chain), 2)
        self.assertEqual(chain[0], self.standard_control)
        self.assertEqual(chain[1], self.control)

        # Standard control should only have itself
        std_chain = self.standard_control.get_inheritance_chain()
        self.assertEqual(len(std_chain), 1)
        self.assertEqual(std_chain[0], self.standard_control)

    def test_get_all_children(self):
        """Test that all descendant controls are retrieved."""
        # Create another local implementation
        local2 = Control.objects.create(
            title="IT Dual Signature Implementation",
            description="IT BU implementation",
            control_level=ControlLevel.LOCAL,
            parent_control=self.standard_control,
            business_unit=BusinessUnit.objects.create(name="IT"),
            owner=self.owner,
            created_by=self.risk_officer,
        )

        children = self.standard_control.get_all_children()

        self.assertEqual(len(children), 2)
        self.assertIn(self.control, children)
        self.assertIn(local2, children)

        # Local controls should have no children
        self.assertEqual(len(self.control.get_all_children()), 0)

    def test_valid_local_implementation_creation(self):
        """Test creating a valid LOCAL control that inherits from STANDARD."""
        local = Control.objects.create(
            title="HR Dual Signature Implementation",
            description="HR-specific implementation",
            control_level=ControlLevel.LOCAL,
            parent_control=self.standard_control,
            business_unit=BusinessUnit.objects.create(name="HR"),
            owner=self.owner,
            created_by=self.risk_officer,
            control_frequency=ControlFrequency.MONTHLY,
            effectiveness=3,
        )

        self.assertEqual(local.control_level, ControlLevel.LOCAL)
        self.assertEqual(local.parent_control, self.standard_control)
        self.assertIsNotNone(local.business_unit)
        self.assertEqual(str(local), "[LOC] HR Dual Signature Implementation")

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
        """
        Test that title, description, bu, and owner are always required.
        Business unit is only required for LOCAL controls.
        """
        # Test missing basic required fields
        control = Control(control_type=ControlType.DETECTIVE)
        with self.assertRaises(ValidationError) as cm:
            control.full_clean()

        errors = cm.exception.message_dict
        self.assertIn("title", errors)
        self.assertIn("description", errors)
        self.assertIn("owner", errors)
        # business_unit is NOT in errors because default is STANDARD
        #  (no BU required)

        # Test LOCAL control without BU should fail
        local_control = Control(
            title="Local Test",
            description="Test",
            control_level=ControlLevel.LOCAL,
            control_frequency=ControlFrequency.DAILY,
            parent_control=self.standard_control,
            owner=self.owner,
            created_by=self.risk_officer,
        )
        with self.assertRaises(ValidationError) as cm:
            local_control.full_clean()

        # Should fail because LOCAL requires business_unit, checked by clean()
        self.assertIn("__all__", cm.exception.message_dict)
        self.assertIn(
            "Local controls must belong to a business unit.",
            str(cm.exception),
        )

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

    def test_on_delete_protect_parent_control(self):
        """Test that deleting a parent control with children is BLOCKED."""
        with self.assertRaises(IntegrityError):
            self.standard_control.delete()

        # Verify child still exists
        self.control.refresh_from_db()
        self.assertIsNotNone(self.control.parent_control)
