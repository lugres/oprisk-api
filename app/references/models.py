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
