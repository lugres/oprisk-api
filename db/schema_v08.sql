-- v0_8_mvp_ready_mix
-- based on tested v0_7
-- added/changed:
-- 1) Basel taxonomy (event types, business lines and link to internal risk categories).
-- 2) all primary keys are named "id", entities are always in plural.
-- 3) TIMESTAMP -> TIMESTAMPTZ to be ready for different zones
-- 4) Entity-specific audit tables and triggers (incident_audit, measure_audit, etc.)
-- 5) Custom incident routing (e.g. IT events in Retail → IT Ops Retail BU)
-- 6) "manager_id" field/pointer and light AD fields in "users" table.
-- 7) required fields for each stage of incident workflow to show user. 
-- 8) SLA durations for X/Y/Z days of inc. in a state to send notifications.
--      + new draft_due_at in incident table; and draft_due_at in SLA_config.
--      + renaming of columns to reflect updated transitions' names:
--      - verification_due_at -> review_due_at; authorization_due_at -> validation_due_at;
--      - verification_days -> review_days; authorization_days -> validation_days;
--      - discovered_time -> discovered_at; registered_time -> created_at;
-- 9) simplified event types for UI to ensure early notifications for critical events
-- 10) unified notifications table for all entities (incidents, measures, KRIs, etc.)
-- plus some minor adjustments and enhancements


-- for testing environment only! Backup data if needed!
--DROP DATABASE IF EXISTS oprisk;
--CREATE DATABASE oprisk;
-- then use "\c oprisk" and "\i schema.sql" in psql 
-- to connect to the database and get schema created 

-- =========================
-- Reference Tables
-- =========================

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE basel_event_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INT REFERENCES basel_event_types(id) ON DELETE SET NULL
    -- 7 top-level Basel categories (e.g. Internal Fraud, External Fraud, etc.)
);

-- simple event types (4 + other) are needed for early notifications based on routes
-- selected by employee/manager in UI, mapped to basel types by ORM at validation
-- a concept, not tested with sample data and queries
CREATE TABLE simplified_event_types_ref (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,        -- Display name, e.g. "Fraud", "IT/Cyber", "Compliance", ...
    short_desc TEXT NOT NULL,          -- Short description
    front_end_hint TEXT,               -- Examples for users
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- eases mapping job for orm, basel types are needed for auditors & regulators
CREATE TABLE simplified_to_basel_event_map (
    id SERIAL PRIMARY KEY,
    simplified_id INT NOT NULL REFERENCES simplified_event_types_ref(id) ON DELETE CASCADE,
    basel_id INT NOT NULL REFERENCES basel_event_types(id) ON DELETE CASCADE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (simplified_id, basel_id)  -- avoid duplicate mappings
);


CREATE TABLE basel_business_lines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id INT REFERENCES basel_business_lines(id) ON DELETE SET NULL

    -- 8 Basel business lines (e.g. Retail Banking, Corporate Finance, etc.)
);

CREATE TABLE risk_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- map internal risk categories to Basel event types
CREATE TABLE risk_category_event_type (
  risk_category_id INT REFERENCES risk_categories(id) ON DELETE CASCADE,
  basel_event_type_id INT REFERENCES basel_event_types(id) ON DELETE CASCADE,
  PRIMARY KEY (risk_category_id, basel_event_type_id)
);

CREATE TABLE loss_causes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

CREATE TABLE business_units (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INT REFERENCES business_units(id) ON DELETE SET NULL
);

CREATE TABLE business_processes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id INT REFERENCES business_processes(id) ON DELETE SET NULL,
    business_unit_id INT REFERENCES business_units(id) ON DELETE SET NULL
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    business_unit_id INT REFERENCES business_units(id) ON DELETE SET NULL
);

-- status reference tables to ensure correct workflow
CREATE TABLE incident_status_ref (
  id SERIAL PRIMARY KEY,
  -- e.g., 'DRAFT','PENDING_REVIEW','PENDING_VALIDATION','VALIDATED','CLOSED'
  code VARCHAR(50) UNIQUE NOT NULL,     
  name VARCHAR(100) NOT NULL
);

CREATE TABLE measure_status_ref (
  id SERIAL PRIMARY KEY,
  code VARCHAR(50) UNIQUE NOT NULL,     -- e.g., 'OPEN','IN_PROGRESS','DONE','OVERDUE','CANCELLED'
  name VARCHAR(100) NOT NULL
);

-- =========================
-- Core Tables
-- =========================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL, -- consider it for login + psw
    full_name VARCHAR(255),
    business_unit_id INT REFERENCES business_units(id) ON DELETE SET NULL,
    role_id INT REFERENCES roles(id) ON DELETE SET NULL,
    manager_id INT NULL REFERENCES users(id), -- required for incid. routing/transitions
    external_id VARCHAR(255) NULL, -- ready for AD sync
    external_source VARCHAR(50) NULL, -- ready for AD sync
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE risks (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    risk_category_id INT REFERENCES risk_categories(id),
    basel_event_type_id INT REFERENCES basel_event_types(id),
    business_unit_id INT REFERENCES business_units(id),
    business_process_id INT REFERENCES business_processes(id),
    product_id INT REFERENCES products(id),
    inherent_likelihood SMALLINT, -- e.g. 1–5
    inherent_impact SMALLINT,
    residual_likelihood SMALLINT,
    residual_impact SMALLINT,
    created_by INT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ,
    CONSTRAINT chk_risk_likelihood_values CHECK (inherent_likelihood BETWEEN 1 AND 5 AND residual_likelihood BETWEEN 1 AND 5),
    CONSTRAINT chk_risk_impact_values CHECK (inherent_impact BETWEEN 1 AND 5 AND residual_impact BETWEEN 1 AND 5)
);

-- indexes for possible typical queries
CREATE INDEX idx_risk_bu ON risks(business_unit_id);
CREATE INDEX idx_risk_process ON risks(business_process_id);
-- CREATE INDEX idx_risk_product ON risks(product_id);
-- CREATE INDEX idx_risk_basel ON risks(basel_event_type_id);

CREATE TABLE incidents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    description TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- internal ownership
    business_unit_id INT REFERENCES business_units(id),
    business_process_id INT REFERENCES business_processes(id),
    product_id INT REFERENCES products(id),

    --mapping for Basel, event-based
    basel_event_type_id INT REFERENCES basel_event_types(id),
    basel_business_line_id INT REFERENCES basel_business_lines(id),

    -- workflow (user → manager → risk team)
    status_id INT REFERENCES incident_status_ref(id),
    reported_by INT REFERENCES users(id), -- creator of the incident (e.g. user)
    assigned_to INT REFERENCES users(id), -- current owner of workflow step (e.g. manager)
    validated_by INT REFERENCES users(id),
    validated_at TIMESTAMPTZ,
    closed_by INT REFERENCES users(id),
    closed_at TIMESTAMPTZ,
    
    -- for notifications during workflow, according to SLA
    -- check Workflow_rules_State_machine_v2 doc for logic
    draft_due_at TIMESTAMPTZ,   -- computed when incident is created in DRAFT
    review_due_at TIMESTAMPTZ,  -- computed on submit
    validation_due_at TIMESTAMPTZ,  -- computed on review

    -- soft delete
    deleted_at TIMESTAMPTZ,
    deleted_by INT REFERENCES users(id),

    -- to enable auditing (or SET LOCAL audit.user_id in every transaction)
    -- updated_by INT NULL REFERENCES users(id),
    
    -- financial data
    gross_loss_amount NUMERIC(18,2) DEFAULT 0,
    recovery_amount NUMERIC(18,2) DEFAULT 0,
    net_loss_amount NUMERIC(18,2),  -- gros minus recovery, managed in app manually by risk officer
    currency_code VARCHAR(3), -- should be 3 letters, ISO-4217 compliant
    near_miss BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT  -- including details on recovery (insurance, legal, third-party, etc.)
);

-- view for active incidents
CREATE OR REPLACE VIEW active_incidents AS
SELECT * FROM incidents WHERE deleted_at IS NULL;

-- indexes for possible typical queries
CREATE INDEX idx_incident_bu ON incidents(business_unit_id);
CREATE INDEX idx_incident_status ON incidents(status_id);
--CREATE INDEX idx_incident_basel ON incidents(basel_event_type_id, basel_business_line_id);

CREATE TABLE controls (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    reference_doc VARCHAR(255),
    effectiveness SMALLINT CHECK (effectiveness BETWEEN 1 AND 5),
    business_process_id INT REFERENCES business_processes(id),
    created_by INT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ
);

CREATE TABLE measures (
    id SERIAL PRIMARY KEY,
    description TEXT NOT NULL,
    responsible_id INT REFERENCES users(id),
    deadline DATE,
    status_id INT REFERENCES measure_status_ref(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES users(id),
    updated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    closure_comment TEXT
);

CREATE TABLE key_risk_indicators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    definition TEXT,
    unit VARCHAR(50),
    threshold_green NUMERIC,
    threshold_amber NUMERIC,
    threshold_red NUMERIC,
    frequency VARCHAR(20) CHECK (frequency IN ('Daily','Weekly','Monthly','Quarterly','Annually')),
    responsible_id INT REFERENCES users(id),
    risk_id INT REFERENCES risks(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Log of KRI measurements 
CREATE TABLE kri_measurements (
    id SERIAL PRIMARY KEY,
    kri_id INT REFERENCES key_risk_indicators(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    value NUMERIC NOT NULL,
    -- threshold will be computed in the app
    threshold_status VARCHAR(10) CHECK (threshold_status IN ('Green', 'Amber', 'Red')),
    comment TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recorded_by INT REFERENCES users(id),
    CONSTRAINT kri_period_order CHECK (period_start <= period_end)
);

CREATE INDEX idx_kri_period ON kri_measurements(kri_id, period_start, period_end);

-- this partial index will only work for big tables!
-- or use "SET enable_seqscan = OFF;" before querying for testing
CREATE INDEX idx_kri_breach_lookup ON kri_measurements(kri_id, period_start, period_end)
WHERE threshold_status <> 'Green';

-- more indexes for general reporting
CREATE INDEX idx_incident_dates ON incidents(discovered_at, created_at);
--CREATE INDEX idx_incident_owner ON incidents(reported_by, validated_by, closed_by);
CREATE INDEX idx_control_process ON controls(business_process_id);
CREATE INDEX idx_measure_assignee ON measures(responsible_id, status_id);

-- =========================
-- Link Tables (many-to-many)
-- =========================

-- Link incidents to known risks
CREATE TABLE incident_risk (
    incident_id INT REFERENCES incidents(id) ON DELETE CASCADE,
    risk_id INT REFERENCES risks(id) ON DELETE CASCADE,
    PRIMARY KEY (incident_id, risk_id)
);

-- corrective
CREATE TABLE incident_measure (
    incident_id INT REFERENCES incidents(id) ON DELETE CASCADE,
    measure_id INT REFERENCES measures(id) ON DELETE CASCADE,
    PRIMARY KEY (incident_id, measure_id)
);

-- multiple causes per incident
CREATE TABLE incident_cause (
    incident_id INT REFERENCES incidents(id) ON DELETE CASCADE,
    loss_cause_id INT REFERENCES loss_causes(id) ON DELETE CASCADE,
    PRIMARY KEY (incident_id, loss_cause_id)
);

CREATE TABLE risk_control (
    risk_id INT REFERENCES risks(id) ON DELETE CASCADE,
    control_id INT REFERENCES controls(id) ON DELETE CASCADE,
    PRIMARY KEY (risk_id, control_id)
);

-- preventive
CREATE TABLE risk_measure (
    risk_id INT REFERENCES risks(id) ON DELETE CASCADE,
    measure_id INT REFERENCES measures(id) ON DELETE CASCADE,
    PRIMARY KEY (risk_id, measure_id)
);

-- =========================
-- Service Tables (audit log for incidents, incident routing, etc.)
-- =========================

-- similar concept can be adapted for other entities (measures, kris, etc.)
CREATE TABLE incident_audit (
    id BIGSERIAL PRIMARY KEY,
    incident_id INT NOT NULL,
    operation_type VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    changed_by INT, -- FK to users.id, nullable for system actions
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    old_data JSONB,
    new_data JSONB
);

-- simple custom routing for incidents based on JSON predicates 
-- no queues, no stages for MVP; only applies at registration → verification.
-- match by BU, category, amount (conditions can be combined)
CREATE TABLE incident_routing_rules (
    id SERIAL PRIMARY KEY,
    route_to_role_id INT REFERENCES roles(id), -- -- who should get it
    route_to_bu_id INT REFERENCES business_units(id), -- -- optional, BU override
    -- routing conditions, e.g. {"business_unit_id":5, "basel_event_type_id":2, "min_amount":10000}
    -- "business_unit_id" as a source of incident - optional, defer for later.
    predicate JSONB NOT NULL, 
    priority INT DEFAULT 100, -- lower = higher priority
    description TEXT,
    active BOOLEAN DEFAULT TRUE
);

-- fields that are required at each workflow stage (draft → review → validate)
-- so frontend can read this matrix and show fields progressively.
CREATE TABLE incident_required_fields (
    -- e.g. 'DRAFT','PENDING_REVIEW',...
    status_id INT NOT NULL REFERENCES incident_status_ref(id) ON DELETE CASCADE,
    -- e.g. 'title','gross_loss_amount',... as in incidents (validate in app)
    field_name VARCHAR(100) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (status_id, field_name)
);

-- SLA for notifications
CREATE TABLE sla_config (
    key VARCHAR(50) PRIMARY KEY,  -- e.g. draft_days, review_days, validation_days
    value_int INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Unified notifications table (polymorphic: entity_type + entity_id), "logical event"
-- will be used by a unified Django app serving all entities (incidents, measures, etc.)
-- notifications are fired based on custom routing and SLA overdue
-- used by Celery workers and Celery Beat tasks, as well as app itself
-- a concept, not tested with sample data and queries
CREATE TABLE notifications (
  id                BIGSERIAL PRIMARY KEY,
  entity_type       VARCHAR(60) NOT NULL,    -- e.g. 'incident', 'measure', 'kri', ...
  entity_id         INT NOT NULL,            -- id within the entity table
  event_type        VARCHAR(50) NOT NULL,    -- 'ROUTING_NOTIFY' | 'INCIDENT_OVERDUE' | 'MEASURE_OVERDUE' | 'CUSTOM' | ...
  sla_stage         VARCHAR(20),             -- 'draft'|'review'|'validation' or NULL
  recipient_id      INT,                     -- specific user (nullable)
  recipient_role_id INT,                     -- role (nullable)
  routing_rule_id   INT,                     -- optional reference to matching rule (no FK for multi-entity)
  triggered_by      INT,                     -- user who caused it (nullable)
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  due_at            TIMESTAMPTZ,             -- the incident/measure due date that triggered notification (nullable)
  method            VARCHAR(30) NOT NULL DEFAULT 'SYSTEM', -- 'SYSTEM'|'EMAIL'|'SLACK'|'WEBHOOK'
  payload           JSONB,                   -- structured context (entity fields, links, suggested fixes)
  status            VARCHAR(20) NOT NULL DEFAULT 'queued', -- queued|sent|failed|canceled
  attempts          INT NOT NULL DEFAULT 0,
  last_error        TEXT,
  sent_at           TIMESTAMPTZ,
  active            BOOLEAN NOT NULL DEFAULT TRUE
);

-- Uniqueness guard for idempotency: one active (queued/sent) notification per entity+event+recipient/role+stage
CREATE UNIQUE INDEX ux_notifications_active
  ON notifications(entity_type, entity_id, event_type, sla_stage, recipient_id, recipient_role_id)
  WHERE active = TRUE;

-- Indexes for reads
-- CREATE INDEX idx_notifications_entity ON notifications(entity_type, entity_id);
-- CREATE INDEX idx_notifications_status ON notifications(status);
-- CREATE INDEX idx_notifications_recipient ON notifications(recipient_id);
-- CREATE INDEX idx_notifications_role ON notifications(recipient_role_id);


-- required for per-user red dot/bell/popup notification functionality in UI.
CREATE TABLE user_notifications (
  id             BIGSERIAL PRIMARY KEY,
  notification_id BIGINT NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
  user_id        INT NOT NULL REFERENCES users(id),
  is_read        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  read_at        TIMESTAMPTZ
);

-- CREATE INDEX idx_user_notifications_user_unread ON user_notifications(user_id, is_read);

-- might be dropped/deleted as notifications are covered ABOVE!
-- to store notifications, emitted based on SLA config params 
-- and computed columns incidents and emailed/pushed by worker.
-- Implementation deferred therefore commented out.
-- CREATE TABLE notifications (
--   id SERIAL PRIMARY KEY,
--   event_type VARCHAR(50) NOT NULL,    -- e.g., INCIDENT_OVERDUE
--   payload JSONB NOT NULL,             -- include incident_id, recipient info
--   recipient_id INT REFERENCES users(id),
--   created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
--   sent_at TIMESTAMPTZ NULL,
--   status VARCHAR(20) NOT NULL DEFAULT 'queued'  -- queued|sent|failed
-- );

-- stub for future external events table. 
-- Implementation deferred therefore commented out.
-- CREATE TABLE external_events (

-- id SERIAL PK, 
-- source_system VARCHAR, 
-- document_ref VARCHAR, 
-- gl_code VARCHAR, 
-- amount NUMERIC, 
-- payload JSONB, 
-- confidence NUMERIC, 
-- status VARCHAR('INBOX','PROMOTED','DISCARDED'),
-- matched_rules JSONB,
-- created_at TIMESTAMP,
-- CONSTRAINT uq_ext_source_doc UNIQUE (source_system, document_ref)

-- );

-- =========================
-- Soft deletion mechanisms (a unified trigger function attached to a table). 
-- This technique required extensive googling and exploring other's solutions,
-- although general logic was clear based on week's 4 ideas.
-- Initially applied for incident table as the most critical data, 
-- easily extended for other tables if needed.
-- app should SET LOCAL audit.user_id in every transaction.
-- =========================

CREATE OR REPLACE FUNCTION soft_delete_trigger()
RETURNS TRIGGER AS $$
BEGIN
  EXECUTE format( -- we need to run dynamic statement for a generic function
    'UPDATE %I SET deleted_at = now(), deleted_by = %s WHERE id = $1.id',
    TG_TABLE_NAME, -- replaces %I with the table the trigger fired on
    CASE -- select correct value for %s placeholder, NULL or content of audit.user_id
      WHEN current_setting('audit.user_id', true) IS NOT NULL
      THEN quote_literal(current_setting('audit.user_id', true)::INT)
      ELSE 'NULL'
    END
  )
  USING OLD; -- this goes into $1 placeholder above, meaning the row being deleted

  RETURN NULL; -- cancel the actual DELETE
END;
$$ LANGUAGE plpgsql;

-- can be applied for other tables as well
CREATE TRIGGER incident_soft_delete
BEFORE DELETE ON incidents
FOR EACH ROW
EXECUTE FUNCTION soft_delete_trigger();

-- =========================
-- Entity-specific audit tables (incident_audit, measure_audit, etc.)
-- Starting with incident, extend as needed.
-- Keeping the triggers simple, no JSONB diffing at this stage (full row snapshot).
-- app should SET LOCAL audit.user_id in every transaction.
-- =========================

-- !!! Trigger was updated to cover cases when audit.user_id is null!
-- see details in Claude's validation of my design!
CREATE OR REPLACE FUNCTION incident_audit_trigger()
RETURNS TRIGGER AS $$
DECLARE
    audit_user_id INT;
BEGIN
    -- Try to get user_id, default to NULL for system operations/wrong input
    BEGIN
        audit_user_id := current_setting('audit.user_id', true)::INT;
    EXCEPTION WHEN OTHERS THEN
        audit_user_id := NULL;
    END;

    IF TG_OP = 'INSERT' THEN
        INSERT INTO incident_audit (incident_id, operation_type, changed_by, old_data, new_data)
        VALUES (NEW.id, TG_OP, audit_user_id, NULL, to_jsonb(NEW));

        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO incident_audit (incident_id, operation_type, changed_by, old_data, new_data)
        VALUES (NEW.id, TG_OP, audit_user_id, to_jsonb(OLD), to_jsonb(NEW));

        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO incident_audit (incident_id, operation_type, changed_by, old_data, new_data)
        VALUES (OLD.id, TG_OP, audit_user_id, to_jsonb(OLD), NULL);

        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- attach trigger to incidents table
CREATE TRIGGER incident_audit
AFTER INSERT OR UPDATE OR DELETE ON incidents
FOR EACH ROW
EXECUTE FUNCTION incident_audit_trigger();
