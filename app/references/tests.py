"""
Simple "smoke tests" to ensure the models can be created and
have a sensible string representation.
Simple tests for admin interface are in the users app, test_admin.py
"""

from django.test import TestCase
from .models import Role, BusinessUnit


class ReferenceModelTests(TestCase):

    def test_role_model(self):
        """Test that a Role can be created
        and has a correct string representation."""
        role = Role.objects.create(
            name="Manager", description="A manager role."
        )
        self.assertEqual(str(role), "Manager")

    def test_business_unit_model(self):
        """Test that a BusinessUnit can be created
        and has a correct string representation."""
        bu = BusinessUnit.objects.create(name="Retail Banking")
        self.assertEqual(str(bu), "Retail Banking")
