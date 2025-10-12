"""
Reference/central taxonomy tables to support core business apps.
Prevents circular dependencies.
"""

from django.db import models


class Role(models.Model):
    """Support access control and permission management."""

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class BusinessUnit(models.Model):
    """Hierarchical structures capture real-world company organization;
    self-referencing parent IDs support nested hierarchies."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.name


class BaselBusinessLine(models.Model):
    """8 main Basel business lines; nested hierarchies."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        verbose_name = "Basel Business Line"
        verbose_name_plural = "Basel Business Lines"

    def __str__(self):
        return self.name


class BaselEventType(models.Model):
    """7 main Basel event types; nested hierarchies."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        verbose_name = "Basel Event Type"
        verbose_name_plural = "Basel Event Types"

    def __str__(self):
        return self.name


class BusinessProcess(models.Model):
    """Capture operational workflows and responsibilities;
    linked to business units; stored hierarchically."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )
    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        verbose_name = "Business Process"
        verbose_name_plural = "Business Processes"

    def __str__(self):
        return self.name


class Product(models.Model):
    """Capture business products; associated with processes (optionally
    - multiple); linked to business unit."""

    name = models.CharField(max_length=255)
    business_unit = models.ForeignKey(
        BusinessUnit, on_delete=models.SET_NULL, blank=True, null=True
    )

    def __str__(self):
        return self.name
