"""
Simple "smoke tests" to ensure the models can be created and
have a sensible string representation.
"""

from django.test import TestCase
from references.models import (
    Role,
    BusinessUnit,
    BaselBusinessLine,
    BaselEventType,
    BusinessProcess,
    Product,
)


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

    def test_basel_business_line_model(self):
        """Test BaselBusinessLine with a parent-child relationship."""
        parent_line = BaselBusinessLine.objects.create(
            name="Corporate Finance"
        )
        child_line = BaselBusinessLine.objects.create(
            name="Advisory Services", parent=parent_line
        )
        self.assertEqual(str(child_line), "Advisory Services")
        self.assertEqual(child_line.parent, parent_line)

    def test_basel_event_type_model(self):
        """Test BaselEventType creation."""
        event_type = BaselEventType.objects.create(name="Internal Fraud")
        self.assertEqual(str(event_type), "Internal Fraud")

    def test_business_process_model(self):
        """Test BusinessProcess with a ForeignKey to BusinessUnit."""
        bu = BusinessUnit.objects.create(name="Operations")
        process = BusinessProcess.objects.create(
            name="Reconciliation", business_unit=bu
        )
        self.assertEqual(str(process), "Reconciliation")
        self.assertEqual(process.business_unit, bu)

    def test_product_model(self):
        """Test Product creation."""
        product = Product.objects.create(name="Corporate Loan")
        self.assertEqual(str(product), "Corporate Loan")
