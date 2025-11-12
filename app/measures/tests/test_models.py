"""
Tests for the models in the measures app.
"""

from datetime import date
import time

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError


from measures.models import Measure, MeasureStatusRef

User = get_user_model()


class MeasureModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up data for testing measure models."""
        cls.user = User.objects.create_user(
            email="test@example.com", password="testpsw123"
        )
        cls.status_open = MeasureStatusRef.objects.create(
            code="OPEN", name="Open"
        )
        cls.status_done = MeasureStatusRef.objects.create(
            code="DONE", name="Done"
        )

    def test_create_measure_status_ref(self):
        """Test creating a MeasureStatusRef."""
        self.assertEqual(self.status_open.code, "OPEN")
        self.assertEqual(str(self.status_open), "Open")

    def test_measure_status_ref_code_unique(self):
        """Test the 'code' field is unique."""
        with self.assertRaises(IntegrityError):
            MeasureStatusRef.objects.create(code="OPEN", name="Another Open")

    def test_create_measure_with_defaults(self):
        """Test creating a minimal Measure sets the default status."""
        # This test assumes Measure model's 'status' field
        # has a default value pointing to the 'OPEN' status.
        measure = Measure.objects.create(
            description="Test default status", created_by=self.user
        )

        self.assertEqual(measure.description, "Test default status")
        self.assertEqual(measure.status, self.status_open)
        self.assertEqual(str(measure), "Test default status"[:50])

    def test_create_measure_with_default_status(self):
        """Test that new measures get OPEN status by default."""
        # Ensure OPEN status exists (from data migration)
        MeasureStatusRef.objects.get_or_create(
            code="OPEN", defaults={"name": "Open"}
        )

        measure = Measure.objects.create(
            description="Test default status",
            created_by=self.user,
            # No status specified
        )

        measure.refresh_from_db()

        # Depending on solution, this might be set in .save() or serializer
        self.assertEqual(measure.status.code, "OPEN")

    def test_create_measure_without_status_ref(self):
        """Test creating a measure when default status doesn't exist."""
        # Clear all statuses
        MeasureStatusRef.objects.all().delete()

        measure = Measure.objects.create(
            description="Test without status", created_by=self.user
        )

        # Should handle gracefully
        self.assertIsNone(measure.status)

    def test_create_full_measure(self):
        """Test creating a Measure with all fields."""
        user2 = User.objects.create_user(
            email="user2@test.com", password="tstpsw123"
        )
        test_date = date(2025, 12, 31)

        measure = Measure.objects.create(
            description="This is a fully detailed measure for testing.",
            created_by=self.user,
            responsible=user2,
            deadline=test_date,
            status=self.status_done,
        )

        self.assertEqual(measure.responsible, user2)
        self.assertEqual(measure.deadline, test_date)
        self.assertEqual(measure.status, self.status_done)
        self.assertEqual(
            str(measure), "This is a fully detailed measure for testing."[:50]
        )

    def test_on_delete_responsible_set_null(self):
        """Test that deleting the responsible user sets the field to NULL."""
        # This test assumes `on_delete=models.SET_NULL`
        resp_user = User.objects.create_user(
            email="resp@example.com", password="pw"
        )
        measure = Measure.objects.create(
            description="Test responsible user deletion",
            created_by=self.user,
            responsible=resp_user,
        )
        self.assertEqual(measure.responsible, resp_user)

        # Delete the responsible user
        resp_user.delete()
        measure.refresh_from_db()

        self.assertIsNone(measure.responsible)

    def test_on_delete_created_by_set_null(self):
        """Test that deleting the creating user sets the field to NULL."""
        # This test assumes `on_delete=models.SET_NULL`
        creator_user = User.objects.create_user(
            email="creator@example.com", password="tstpsw123"
        )
        measure = Measure.objects.create(
            description="Test creator user deletion", created_by=creator_user
        )
        self.assertEqual(measure.created_by, creator_user)

        # Delete the creating user
        creator_user.delete()
        measure.refresh_from_db()

        self.assertIsNone(measure.created_by)

    def test_on_delete_status_set_null(self):
        """Test that deleting the status ref sets the field to NULL."""
        # This test assumes `on_delete=models.SET_NULL`
        status_temp = MeasureStatusRef.objects.create(
            code="TEMP", name="Temporary"
        )
        measure = Measure.objects.create(
            description="Test status deletion",
            created_by=self.user,
            status=status_temp,
        )
        self.assertEqual(measure.status, status_temp)

        # Delete the status
        status_temp.delete()
        measure.refresh_from_db()

        self.assertIsNone(measure.status)

    # test field validations and constraints
    def test_description_required(self):
        """Test that description is required."""
        with self.assertRaises(IntegrityError):
            Measure.objects.create(created_by=self.user)

    def test_description_max_length(self):
        """Test description can handle long text."""
        long_description = "A" * 10000
        measure = Measure.objects.create(
            description=long_description, created_by=self.user
        )
        self.assertEqual(len(measure.description), 10000)

    def test_status_code_max_length(self):
        """Test status code respects max_length."""
        long_code = "A" * 51  # One more than max_length
        with self.assertRaises(
            Exception
        ):  # Could be ValidationError or DataError
            MeasureStatusRef.objects.create(code=long_code, name="Test")

    # timestamp tests
    def test_created_at_auto_set(self):
        """Test that created_at is automatically set."""
        measure = Measure.objects.create(
            description="Test timestamps", created_by=self.user
        )
        self.assertIsNotNone(measure.created_at)

    def test_updated_at_auto_updates(self):
        """Test that updated_at changes on save."""
        measure = Measure.objects.create(
            description="Test update", created_by=self.user
        )
        original_updated = measure.updated_at

        # Small delay to ensure time difference
        time.sleep(0.01)

        measure.description = "Updated description"
        measure.save()

        self.assertGreater(measure.updated_at, original_updated)

    def test_closed_at_initially_null(self):
        """Test that closed_at is initially null."""
        measure = Measure.objects.create(
            description="Test closure", created_by=self.user
        )
        self.assertIsNone(measure.closed_at)
