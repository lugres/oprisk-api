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


# Simplified Event type will be moved to "incidents" due to high cohesion
# class SimplifiedEventTypeRef(models.Model):
#     """Simple event types (4 + other) for early stages of incident's
#       lifecycle; selected by employee/manager in UI, mapped to Basel."""

#     name = models.CharField(max_length=100)
#     short_desc = models.TextField()
#     front_end_hint = models.TextField(blank=True, null=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = "Simplified Event Type"
#         verbose_name_plural = "Simplified Event Types"

#     def __str__(self):
#         return self.name


# class SimplifiedToBaselEventMap(models.Model):
#     """Map simplified event type to Basel event types."""

#     simplified = models.ForeignKey(
#         SimplifiedEventTypeRef, on_delete=models.CASCADE
#     )
#     basel = models.ForeignKey(BaselEventType, on_delete=models.CASCADE)
#     is_default = models.BooleanField(default=False)

#     class Meta:
#         verbose_name = "Simplified to Basel Event Map"
#         verbose_name_plural = "Simplified to Basel Event Maps"
#         unique_together = (("simplified", "basel"),)  # avoid duplicates


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
