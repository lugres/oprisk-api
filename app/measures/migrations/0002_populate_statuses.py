# Manually created to populate statuses for measures.
# Needed to have a default OPEN status for a newly created measure.

from django.db import migrations


def create_default_statuses(apps, schema_editor):
    MeasureStatusRef = apps.get_model("measures", "MeasureStatusRef")
    MeasureStatusRef.objects.get_or_create(
        code="OPEN",
        defaults={"name": "Measure identified but not yet started"},
    )
    MeasureStatusRef.objects.get_or_create(
        code="COMPLETED",
        defaults={"name": "Measure successfully implemented"},
    )
    # Add other statuses here if needed (e.g., IN_PROGRESS, CANCELLED)
    MeasureStatusRef.objects.get_or_create(
        code="IN_PROGRESS",
        defaults={"name": "Work on the measure is actively underway"},
    )
    MeasureStatusRef.objects.get_or_create(
        code="PENDING_REVIEW",
        defaults={
            "name": "Measure implementation completed, awaiting verification",
        },
    )
    MeasureStatusRef.objects.get_or_create(
        code="CANCELLED",
        defaults={
            "name": "Measure no longer needed or rejected by management",
        },
    )


def reverse_default_statuses(apps, schema_editor):
    MeasureStatusRef = apps.get_model("measures", "MeasureStatusRef")
    MeasureStatusRef.objects.filter(
        code__in=[
            "OPEN",
            "COMPLETED",
            "IN_PROGRESS",
            "PENDING_REVIEW",
            "CANCELLED",
        ]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("measures", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_default_statuses, reverse_default_statuses
        ),
    ]
