# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the
# desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create,
#  modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field
# names.
from django.db import models


class BaselBusinessLines(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "basel_business_lines"


class BaselEventTypes(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey(
        "self", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "basel_event_types"


class BusinessProcesses(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", models.DO_NOTHING, blank=True, null=True
    )
    business_unit = models.ForeignKey(
        "BusinessUnits", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "business_processes"


class BusinessUnits(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "business_units"


class Controls(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    reference_doc = models.CharField(max_length=255, blank=True, null=True)
    effectiveness = models.SmallIntegerField(blank=True, null=True)
    business_process = models.ForeignKey(
        BusinessProcesses, models.DO_NOTHING, blank=True, null=True
    )
    created_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="created_by",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "controls"


class IncidentAudit(models.Model):
    id = models.BigAutoField(primary_key=True)
    incident_id = models.IntegerField()
    operation_type = models.CharField(max_length=10)
    changed_by = models.IntegerField(blank=True, null=True)
    changed_at = models.DateTimeField()
    old_data = models.JSONField(blank=True, null=True)
    new_data = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "incident_audit"


class IncidentCause(models.Model):
    pk = models.CompositePrimaryKey("incident_id", "loss_cause_id")
    incident = models.ForeignKey("Incidents", models.DO_NOTHING)
    loss_cause = models.ForeignKey("LossCauses", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "incident_cause"


class IncidentMeasure(models.Model):
    pk = models.CompositePrimaryKey("incident_id", "measure_id")
    incident = models.ForeignKey("Incidents", models.DO_NOTHING)
    measure = models.ForeignKey("Measures", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "incident_measure"


class IncidentRequiredFields(models.Model):
    pk = models.CompositePrimaryKey("status_id", "field_name")
    status = models.ForeignKey("IncidentStatusRef", models.DO_NOTHING)
    field_name = models.CharField(max_length=100)
    required = models.BooleanField()

    class Meta:
        managed = False
        db_table = "incident_required_fields"


class IncidentRisk(models.Model):
    pk = models.CompositePrimaryKey("incident_id", "risk_id")
    incident = models.ForeignKey("Incidents", models.DO_NOTHING)
    risk = models.ForeignKey("Risks", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "incident_risk"


class IncidentRoutingRules(models.Model):
    route_to_role = models.ForeignKey(
        "Roles", models.DO_NOTHING, blank=True, null=True
    )
    route_to_bu = models.ForeignKey(
        BusinessUnits, models.DO_NOTHING, blank=True, null=True
    )
    predicate = models.JSONField()
    priority = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "incident_routing_rules"


class IncidentStatusRef(models.Model):
    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "incident_status_ref"


class Incidents(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    discovered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    business_unit = models.ForeignKey(
        BusinessUnits, models.DO_NOTHING, blank=True, null=True
    )
    business_process = models.ForeignKey(
        BusinessProcesses, models.DO_NOTHING, blank=True, null=True
    )
    product = models.ForeignKey(
        "Products", models.DO_NOTHING, blank=True, null=True
    )
    basel_event_type = models.ForeignKey(
        BaselEventTypes, models.DO_NOTHING, blank=True, null=True
    )
    basel_business_line = models.ForeignKey(
        BaselBusinessLines, models.DO_NOTHING, blank=True, null=True
    )
    status = models.ForeignKey(
        IncidentStatusRef, models.DO_NOTHING, blank=True, null=True
    )
    reported_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="reported_by",
        blank=True,
        null=True,
    )
    assigned_to = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="assigned_to",
        related_name="incidents_assigned_to_set",
        blank=True,
        null=True,
    )
    validated_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="validated_by",
        related_name="incidents_validated_by_set",
        blank=True,
        null=True,
    )
    validated_at = models.DateTimeField(blank=True, null=True)
    closed_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="closed_by",
        related_name="incidents_closed_by_set",
        blank=True,
        null=True,
    )
    closed_at = models.DateTimeField(blank=True, null=True)
    draft_due_at = models.DateTimeField(blank=True, null=True)
    review_due_at = models.DateTimeField(blank=True, null=True)
    validation_due_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="deleted_by",
        related_name="incidents_deleted_by_set",
        blank=True,
        null=True,
    )
    gross_loss_amount = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    recovery_amount = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    net_loss_amount = models.DecimalField(
        max_digits=18, decimal_places=2, blank=True, null=True
    )
    currency_code = models.CharField(max_length=3, blank=True, null=True)
    near_miss = models.BooleanField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "incidents"


class KeyRiskIndicators(models.Model):
    name = models.CharField(max_length=255)
    definition = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    threshold_green = models.DecimalField(
        max_digits=10, decimal_places=5, blank=True, null=True
    )  # max_digits and decimal_places have been guessed, as this database
    # handles decimal fields as float
    threshold_amber = models.DecimalField(
        max_digits=10, decimal_places=5, blank=True, null=True
    )  # max_digits and decimal_places have been guessed, as this database
    # handles decimal fields as float
    threshold_red = models.DecimalField(
        max_digits=10, decimal_places=5, blank=True, null=True
    )  # max_digits and decimal_places have been guessed, as this database
    # handles decimal fields as float
    frequency = models.CharField(max_length=20, blank=True, null=True)
    responsible = models.ForeignKey(
        "Users", models.DO_NOTHING, blank=True, null=True
    )
    risk = models.ForeignKey("Risks", models.DO_NOTHING, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "key_risk_indicators"


class KriMeasurements(models.Model):
    kri = models.ForeignKey(
        KeyRiskIndicators, models.DO_NOTHING, blank=True, null=True
    )
    period_start = models.DateField()
    period_end = models.DateField()
    value = models.DecimalField(
        max_digits=10, decimal_places=5
    )  # max_digits and decimal_places have been guessed, as this database
    # handles decimal fields as float
    threshold_status = models.CharField(max_length=10, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="recorded_by",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "kri_measurements"


class LossCauses(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "loss_causes"


class MeasureStatusRef(models.Model):
    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "measure_status_ref"


class Measures(models.Model):
    description = models.TextField()
    responsible = models.ForeignKey(
        "Users", models.DO_NOTHING, blank=True, null=True
    )
    deadline = models.DateField(blank=True, null=True)
    status = models.ForeignKey(
        MeasureStatusRef, models.DO_NOTHING, blank=True, null=True
    )
    created_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="created_by",
        related_name="measures_created_by_set",
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    closure_comment = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "measures"


class Notifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    entity_type = models.CharField(max_length=60)
    entity_id = models.IntegerField()
    event_type = models.CharField(max_length=50)
    sla_stage = models.CharField(max_length=20, blank=True, null=True)
    recipient_id = models.IntegerField(blank=True, null=True)
    recipient_role_id = models.IntegerField(blank=True, null=True)
    routing_rule_id = models.IntegerField(blank=True, null=True)
    triggered_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField()
    due_at = models.DateTimeField(blank=True, null=True)
    method = models.CharField(max_length=30)
    payload = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20)
    attempts = models.IntegerField()
    last_error = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "notifications"
        unique_together = (
            (
                "entity_type",
                "entity_id",
                "event_type",
                "sla_stage",
                "recipient_id",
                "recipient_role_id",
            ),
        )


class Products(models.Model):
    name = models.CharField(max_length=255)
    business_unit = models.ForeignKey(
        BusinessUnits, models.DO_NOTHING, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "products"


class RiskCategories(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "risk_categories"


class RiskCategoryEventType(models.Model):
    pk = models.CompositePrimaryKey("risk_category_id", "basel_event_type_id")
    risk_category = models.ForeignKey(RiskCategories, models.DO_NOTHING)
    basel_event_type = models.ForeignKey(BaselEventTypes, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "risk_category_event_type"


class RiskControl(models.Model):
    pk = models.CompositePrimaryKey("risk_id", "control_id")
    risk = models.ForeignKey("Risks", models.DO_NOTHING)
    control = models.ForeignKey(Controls, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "risk_control"


class RiskMeasure(models.Model):
    pk = models.CompositePrimaryKey("risk_id", "measure_id")
    risk = models.ForeignKey("Risks", models.DO_NOTHING)
    measure = models.ForeignKey(Measures, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "risk_measure"


class Risks(models.Model):
    description = models.TextField()
    risk_category = models.ForeignKey(
        RiskCategories, models.DO_NOTHING, blank=True, null=True
    )
    basel_event_type = models.ForeignKey(
        BaselEventTypes, models.DO_NOTHING, blank=True, null=True
    )
    business_unit = models.ForeignKey(
        BusinessUnits, models.DO_NOTHING, blank=True, null=True
    )
    business_process = models.ForeignKey(
        BusinessProcesses, models.DO_NOTHING, blank=True, null=True
    )
    product = models.ForeignKey(
        Products, models.DO_NOTHING, blank=True, null=True
    )
    inherent_likelihood = models.SmallIntegerField(blank=True, null=True)
    inherent_impact = models.SmallIntegerField(blank=True, null=True)
    residual_likelihood = models.SmallIntegerField(blank=True, null=True)
    residual_impact = models.SmallIntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        "Users",
        models.DO_NOTHING,
        db_column="created_by",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "risks"


class Roles(models.Model):
    name = models.CharField(unique=True, max_length=50)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "roles"


class SimplifiedEventTypesRef(models.Model):
    name = models.CharField(max_length=100)
    short_desc = models.TextField()
    front_end_hint = models.TextField(blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "simplified_event_types_ref"


class SimplifiedToBaselEventMap(models.Model):
    simplified = models.ForeignKey(SimplifiedEventTypesRef, models.DO_NOTHING)
    basel = models.ForeignKey(BaselEventTypes, models.DO_NOTHING)
    is_default = models.BooleanField()

    class Meta:
        managed = False
        db_table = "simplified_to_basel_event_map"
        unique_together = (("simplified", "basel"),)


class SlaConfig(models.Model):
    key = models.CharField(primary_key=True, max_length=50)
    value_int = models.IntegerField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "sla_config"


class UserNotifications(models.Model):
    id = models.BigAutoField(primary_key=True)
    notification = models.ForeignKey(Notifications, models.DO_NOTHING)
    user = models.ForeignKey("Users", models.DO_NOTHING)
    is_read = models.BooleanField()
    created_at = models.DateTimeField()
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "user_notifications"


class Users(models.Model):
    username = models.CharField(unique=True, max_length=100)
    email = models.CharField(unique=True, max_length=255)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    business_unit = models.ForeignKey(
        BusinessUnits, models.DO_NOTHING, blank=True, null=True
    )
    role = models.ForeignKey(Roles, models.DO_NOTHING, blank=True, null=True)
    manager = models.ForeignKey(
        "self", models.DO_NOTHING, blank=True, null=True
    )
    external_id = models.CharField(max_length=255, blank=True, null=True)
    external_source = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "users"
