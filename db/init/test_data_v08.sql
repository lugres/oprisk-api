-- test_data.sql
-- Seed data for v0_8 schema (roles, basel taxonomy, BUs, users, routing rules, SLA, required fields, risks, incidents, controls, measures, KRIs)
-- Run AFTER you applied the v0_8 schema.

-- -------------------------
-- 1) Roles
-- -------------------------
INSERT INTO roles (name, description) VALUES
 ('Employee', 'Regular reporting employee'),
 ('Manager', 'First-line manager / supervisor'),
 ('Risk Officer', 'Operational Risk / ORM (2nd line)'),
 ('IT Admin', 'IT operations'),
 ('InfoSec', 'Information Security team'),
 ('Fraud Investigator', 'Fraud Investigation Unit'),
 ('Group ORM', 'Group-level ORM team'),
 ('Audit/Admin', 'Audit or system admin');

-- -------------------------
-- 2) Basel taxonomy (top-level categories)
--    Using industry-aligned top-level Basel event types
-- -------------------------
INSERT INTO basel_event_types (name, description) VALUES
 ('Internal Fraud','Internal fraud (staff, management)'),
 ('External Fraud','External fraud (clients, third parties)'),
 ('Employment Practices & Workplace Safety','Employment practices and workplace safety'),
 ('Clients, Products & Business Practices','Client/product problems and practices'),
 ('Business Disruption & System Failures','IT outages, security incidents, system failures'),
 ('Execution, Delivery & Process Management','Execution / processing failures'),
 ('Damage to Physical Assets','Loss / damage of physical assets');

-- -------------------------
-- 3) Basel business lines (simplified examples)
-- -------------------------
INSERT INTO basel_business_lines (name, description) VALUES
 ('Retail Banking','Retail banking business line'),
 ('Wholesale Banking','Wholesale / Corporate banking'),
 ('Treasury','Treasury and Markets'),
 ('Payments','Payments and Cards'),
 ('IT & Operations','IT and operations services'),
 ('Human Resources','HR and recruitment'),
 ('Wealth Management','Wealth management');

-- -------------------------
-- 4) Risk categories and mapping to Basel event types
-- -------------------------
INSERT INTO risk_categories (name, description) VALUES
 ('Operational Risk','Operational risk general'),
 ('IT Risk','Risks related to IT and systems'),
 ('Fraud Risk','Fraud risk'),
 ('Compliance Risk','Regulatory and compliance risk');

-- map risk categories to Basel event types (some examples)
INSERT INTO risk_category_event_type (risk_category_id, basel_event_type_id)
VALUES
 ((SELECT id FROM risk_categories WHERE name='Fraud Risk'), (SELECT id FROM basel_event_types WHERE name='External Fraud')),
 ((SELECT id FROM risk_categories WHERE name='Fraud Risk'), (SELECT id FROM basel_event_types WHERE name='Internal Fraud')),
 ((SELECT id FROM risk_categories WHERE name='IT Risk'), (SELECT id FROM basel_event_types WHERE name='Business Disruption & System Failures')),
 ((SELECT id FROM risk_categories WHERE name='Operational Risk'), (SELECT id FROM basel_event_types WHERE name='Execution, Delivery & Process Management'));

-- -------------------------
-- 5) Loss causes
-- -------------------------
INSERT INTO loss_causes (name, description) VALUES
 ('System Failure','Unexpected outage of systems'),
 ('Human Error','Error by staff/third party in process'),
 ('External Fraud','Third-party fraud (card, payment, social engineering)'),
 ('Regulatory Breach','Breach resulting in regulatory fine');

-- -------------------------
-- 6) Business units (BUs)
-- -------------------------
INSERT INTO business_units (name) VALUES
 ('Wholesale'),
 ('Retail'),
 ('Operations'),
 ('Risk Management'),
 ('IT'),
 ('Fraud Unit'),
 ('InfoSec'),
 ('Group ORM'),
 ('Audit');

-- -------------------------
-- 7) Business processes
-- -------------------------
INSERT INTO business_processes (name, business_unit_id) VALUES
 ('Trade Finance', (SELECT id FROM business_units WHERE name='Wholesale')),
 ('Credit Cards', (SELECT id FROM business_units WHERE name='Retail')),
 ('Reconciliation', (SELECT id FROM business_units WHERE name='Operations')),
 ('Risk Assessment', (SELECT id FROM business_units WHERE name='Risk Management')),
 ('Core Banking Systems', (SELECT id FROM business_units WHERE name='IT')),
 ('Fraud Investigation', (SELECT id FROM business_units WHERE name='Fraud Unit')),
 ('Security Monitoring', (SELECT id FROM business_units WHERE name='InfoSec'));

-- -------------------------
-- 8) Products
-- -------------------------
INSERT INTO products (name, business_unit_id) VALUES
 ('Corporate Loan', (SELECT id FROM business_units WHERE name='Wholesale')),
 ('Credit Card', (SELECT id FROM business_units WHERE name='Retail')),
 ('Payments Service', (SELECT id FROM business_units WHERE name='Payments') )
ON CONFLICT DO NOTHING; -- 'Payments' BU might not exist — ignore if not

-- -------------------------
-- 9) Incident / Measure status refs
-- -------------------------
INSERT INTO incident_status_ref (code, name) VALUES
 ('DRAFT','Draft'),
 ('PENDING_REVIEW','Pending Manager Review'),
 ('PENDING_VALIDATION','Pending Risk Validation'),
 ('VALIDATED','Validated'),
 ('CLOSED','Closed');

INSERT INTO measure_status_ref (code, name) VALUES
 ('OPEN','Open'),
 ('IN_PROGRESS','In Progress'),
 ('DONE','Done'),
 ('OVERDUE','Overdue'),
 ('CANCELLED','Cancelled');

-- -------------------------
-- 10) SLA config (industry sensible defaults)
-- -------------------------
INSERT INTO sla_config (key, value_int) VALUES
 ('draft_days', 5),
 ('review_days', 3),
 ('validation_days', 7)
 ON CONFLICT (key) DO UPDATE SET value_int = EXCLUDED.value_int; -- idempotent

-- -------------------------
-- 11) incident_required_fields
--     Note: we use status_id lookups to remain stable
-- -------------------------
-- DRAFT
INSERT INTO incident_required_fields (status_id, field_name, required) VALUES
 ((SELECT id FROM incident_status_ref WHERE code='DRAFT'), 'title', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='DRAFT'), 'description', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='DRAFT'), 'business_unit_id', FALSE), -- auto-filled
 ((SELECT id FROM incident_status_ref WHERE code='DRAFT'), 'near_miss', FALSE), -- employee may tick
 ((SELECT id FROM incident_status_ref WHERE code='DRAFT'), 'gross_loss_amount', FALSE); -- preliminary

-- PENDING_REVIEW
INSERT INTO incident_required_fields (status_id, field_name, required) VALUES
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'), 'business_process_id', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'), 'product_id', FALSE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'), 'gross_loss_amount', FALSE);

-- PENDING_VALIDATION
INSERT INTO incident_required_fields (status_id, field_name, required) VALUES
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'), 'gross_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'), 'recovery_amount', FALSE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'), 'net_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'), 'currency_code', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'), 'basel_event_type_id', TRUE);

-- VALIDATED & CLOSED (finalization)
INSERT INTO incident_required_fields (status_id, field_name, required) VALUES
 ((SELECT id FROM incident_status_ref WHERE code='VALIDATED'), 'gross_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='VALIDATED'), 'net_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='VALIDATED'), 'currency_code', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='VALIDATED'), 'basel_event_type_id', TRUE);

INSERT INTO incident_required_fields (status_id, field_name, required) VALUES
 ((SELECT id FROM incident_status_ref WHERE code='CLOSED'), 'gross_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='CLOSED'), 'net_loss_amount', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='CLOSED'), 'currency_code', TRUE),
 ((SELECT id FROM incident_status_ref WHERE code='CLOSED'), 'basel_event_type_id', TRUE);

-- -------------------------
-- 12) Routing rules (custom routes requested) 
-- priority: lower = higher priority. We'll use 5,10,15 for demonstration.
--  a) Material losses > $1,000,000 → Group ORM (route_to_bu_id)
--  b) IT/security events in Retail BU (basel_event_type = Business Disruption & System Failures) → InfoSec (route_to_role_id + route_to_bu_id)
--  c) All fraud incidents (basel_event_type = External Fraud) → Fraud Investigation Unit (route_to_role_id + route_to_bu_id)
-- -------------------------
-- a) Material > $1M -> Group ORM BU
INSERT INTO incident_routing_rules (route_to_role_id, route_to_bu_id, predicate, priority, description, active)
VALUES (
  NULL,
  (SELECT id FROM business_units WHERE name = 'Group ORM'),
  jsonb_build_object('min_amount', 1000000),
  5,
  'Material losses > $1M -> Group ORM BU',
  TRUE
);

-- b) IT/security events in Retail -> InfoSec (match basel_event_type + business_unit)
INSERT INTO incident_routing_rules (route_to_role_id, route_to_bu_id, predicate, priority, description, active)
VALUES (
  (SELECT id FROM roles WHERE name = 'InfoSec'),
  (SELECT id FROM business_units WHERE name = 'InfoSec'),
  jsonb_build_object(
    'basel_event_type_id', (SELECT id FROM basel_event_types WHERE name = 'Business Disruption & System Failures'),
    'business_unit_id', (SELECT id FROM business_units WHERE name = 'Retail')
  ),
  10,
  'IT/security events in Retail -> InfoSec',
  TRUE
);

-- c) All fraud incidents -> Fraud Investigation Unit
INSERT INTO incident_routing_rules (route_to_role_id, route_to_bu_id, predicate, priority, description, active)
VALUES (
  (SELECT id FROM roles WHERE name = 'Fraud Investigator'),
  (SELECT id FROM business_units WHERE name = 'Fraud Unit'),
  jsonb_build_object('basel_event_type_id', (SELECT id FROM basel_event_types WHERE name = 'External Fraud')),
  15,
  'External fraud -> Fraud Investigation Unit',
  TRUE
);

-- -------------------------
-- 13) Users (managers, employees, ORM, InfoSec, Fraud, Group ORM)
--    Insert managers / special roles first, then employees referencing manager_id.
-- -------------------------
-- Managers / specialists
INSERT INTO users (username, email, full_name, business_unit_id, role_id)
VALUES
 ('bob_mgr', 'bob.manager@bank.com', 'Bob Manager', (SELECT id FROM business_units WHERE name='Retail'), (SELECT id FROM roles WHERE name='Manager')),
 ('wh_mgr', 'wh.manager@bank.com', 'Wendy Wholesale', (SELECT id FROM business_units WHERE name='Wholesale'), (SELECT id FROM roles WHERE name='Manager')),
 ('carol_orm', 'carol.orm@bank.com', 'Carol ORM', (SELECT id FROM business_units WHERE name='Risk Management'), (SELECT id FROM roles WHERE name='Risk Officer')),
 ('eve_infosec', 'eve.infosec@bank.com', 'Eve InfoSec', (SELECT id FROM business_units WHERE name='InfoSec'), (SELECT id FROM roles WHERE name='InfoSec')),
 ('frank_fraud', 'frank.fraud@bank.com', 'Frank Fraud', (SELECT id FROM business_units WHERE name='Fraud Unit'), (SELECT id FROM roles WHERE name='Fraud Investigator')),
 ('greg_grouporm', 'greg.grouporm@bank.com', 'Greg GroupORM', (SELECT id FROM business_units WHERE name='Group ORM'), (SELECT id FROM roles WHERE name='Group ORM'));

-- Employees referencing managers
INSERT INTO users (username, email, full_name, business_unit_id, role_id, manager_id)
VALUES
 ('alice_emp', 'alice@bank.com', 'Alice Employee', (SELECT id FROM business_units WHERE name='Retail'), (SELECT id FROM roles WHERE name='Employee'), (SELECT id FROM users WHERE username='bob_mgr')),
 ('henry_wh_emp', 'henry@bank.com', 'Henry Wholesale', (SELECT id FROM business_units WHERE name='Wholesale'), (SELECT id FROM roles WHERE name='Employee'), (SELECT id FROM users WHERE username='wh_mgr')),
 ('dave_it', 'dave.it@bank.com', 'Dave IT', (SELECT id FROM business_units WHERE name='IT'), (SELECT id FROM roles WHERE name='IT Admin'), NULL);

-- -------------------------
-- 14) Risks (small set)
-- -------------------------
INSERT INTO risks (description, risk_category_id, basel_event_type_id, business_unit_id, business_process_id, product_id,
                   inherent_likelihood, inherent_impact, residual_likelihood, residual_impact, created_by)
VALUES
 ('Core banking disruption from major outage', (SELECT id FROM risk_categories WHERE name='IT Risk'),
    (SELECT id FROM basel_event_types WHERE name='Business Disruption & System Failures'),
    (SELECT id FROM business_units WHERE name='IT'),
    (SELECT id FROM business_processes WHERE name='Core Banking Systems'),
    NULL, 4,5,3,3, (SELECT id FROM users WHERE username='dave_it')
 ),
 ('Retail card fraud spike', (SELECT id FROM risk_categories WHERE name='Fraud Risk'),
    (SELECT id FROM basel_event_types WHERE name='External Fraud'),
    (SELECT id FROM business_units WHERE name='Retail'),
    (SELECT id FROM business_processes WHERE name='Credit Cards'),
    (SELECT id FROM products WHERE name='Credit Card'),
    5,4,3,3, (SELECT id FROM users WHERE username='alice_emp')
 );

-- -------------------------
-- 15) Incidents (2–4 incidents to exercise routing + workflow)
--    Important: compute draft_due_at using sla_config.draft_days and backdate some created_at to create overdue examples
-- -------------------------
-- 15.1 Incident A: Large Wholesale loss -> should hit Material > $1M rule => assigned to Group ORM (test full lifecycle)
INSERT INTO incidents (title, description, discovered_at, created_at, business_unit_id, business_process_id, product_id,
                       basel_event_type_id, basel_business_line_id, status_id, reported_by, gross_loss_amount, currency_code,
                       draft_due_at)
VALUES (
 'Large Trading Loss',
 'Large trading loss due to failed hedge; large material loss > $1M',
 now() - interval '12 days',                                    -- created 12 days ago (so draft_due likely in past)
 now() - interval '12 days',
 (SELECT id FROM business_units WHERE name='Wholesale'),
 (SELECT id FROM business_processes WHERE name='Trade Finance'),
 NULL,
 (SELECT id FROM basel_event_types WHERE name='Clients, Products & Business Practices'),
 (SELECT id FROM basel_business_lines WHERE name='Wholesale Banking'),
 (SELECT id FROM incident_status_ref WHERE code='DRAFT'),
 (SELECT id FROM users WHERE username='henry_wh_emp'),
 2000000, 'USD',
 -- compute draft_due_at = created_at + draft_days
 (now() - interval '12 days') + ((SELECT value_int FROM sla_config WHERE key='draft_days') || ' days')::interval
);

-- 15.2 Incident B: Retail IT outage -> IT/security events in Retail -> should route to InfoSec
INSERT INTO incidents (title, description, discovered_at, created_at, business_unit_id, business_process_id, product_id,
                       basel_event_type_id, basel_business_line_id, status_id, reported_by, gross_loss_amount, currency_code,
                       draft_due_at)
VALUES (
 'Retail IT Outage',
 'Outage of POS and web payment in Retail store cluster; needs InfoSec attention',
 now() - interval '2 days',
 now() - interval '2 days',
 (SELECT id FROM business_units WHERE name='Retail'),
 (SELECT id FROM business_processes WHERE name='Credit Cards'),
 (SELECT id FROM products WHERE name='Credit Card'),
 (SELECT id FROM basel_event_types WHERE name='Business Disruption & System Failures'),
 (SELECT id FROM basel_business_lines WHERE name='Retail Banking'),
 (SELECT id FROM incident_status_ref WHERE code='DRAFT'),
 (SELECT id FROM users WHERE username='alice_emp'),
 50000, 'USD',
 (now() - interval '2 days') + ((SELECT value_int FROM sla_config WHERE key='draft_days') || ' days')::interval
);

-- 15.3 Incident C: Credit Card Fraud (employee draft, older than draft SLA => overdue in DRAFT)
INSERT INTO incidents (title, description, discovered_at, created_at, business_unit_id, business_process_id, product_id,
                       basel_event_type_id, basel_business_line_id, status_id, reported_by, gross_loss_amount, currency_code,
                       draft_due_at)
VALUES (
 'Credit Card Fraud',
 'Multiple suspicious transactions observed on several cards; preliminary ticket',
 now() - interval '11 days',
 now() - interval '11 days',
 (SELECT id FROM business_units WHERE name='Retail'),
 (SELECT id FROM business_processes WHERE name='Credit Cards'),
 (SELECT id FROM products WHERE name='Credit Card'),
 (SELECT id FROM basel_event_types WHERE name='External Fraud'),
 (SELECT id FROM basel_business_lines WHERE name='Retail Banking'),
 (SELECT id FROM incident_status_ref WHERE code='DRAFT'),
 (SELECT id FROM users WHERE username='alice_emp'),
 25000, 'USD',
 -- backdated draft_due_at so it's overdue now
 (now() - interval '11 days') + ((SELECT value_int FROM sla_config WHERE key='draft_days') || ' days')::interval
);

-- 15.4 Incident D: Reconciliation error (short example that will be returned by manager to draft)
INSERT INTO incidents (title, description, discovered_at, created_at, business_unit_id, 
                    business_process_id, status_id, reported_by, assigned_to,
                    gross_loss_amount, currency_code, draft_due_at)
VALUES (
 'Reconciliation Error',
 'Daily reconciliation mismatch: suspected human error',
 now() - interval '4 days',
 now() - interval '4 days',
 (SELECT id FROM business_units WHERE name='Operations'),
 (SELECT id FROM business_processes WHERE name='Reconciliation'),
 (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'),
 (SELECT id FROM users WHERE username='henry_wh_emp'),
 (SELECT id FROM users WHERE username='wh_mgr'), -- assigned manager
 0, 'USD',
 (now() - interval '4 days') + ((SELECT value_int FROM sla_config WHERE key='draft_days') || ' days')::interval
);


-- -------------------------
-- 16) Controls
-- -------------------------
INSERT INTO controls (name, description, effectiveness, business_process_id, created_by)
VALUES
 ('Daily Reconciliation','Daily reconciliation of accounts', 4, (SELECT id FROM business_processes WHERE name='Reconciliation'), (SELECT id FROM users WHERE username='henry_wh_emp')),
 ('Firewall Monitoring','Firewall monitoring and patching', 3, (SELECT id FROM business_processes WHERE name='Core Banking Systems'), (SELECT id FROM users WHERE username='dave_it'));

-- -------------------------
-- 17) Measures
-- -------------------------
INSERT INTO measures (description, responsible_id, deadline, status_id, created_by)
VALUES
 ('Block suspicious card numbers', (SELECT id FROM users WHERE username='frank_fraud'), (now() + interval '7 days')::date, (SELECT id FROM measure_status_ref WHERE code='OPEN'), (SELECT id FROM users WHERE username='alice_emp')),
 ('Patch core server', (SELECT id FROM users WHERE username='dave_it'), (now() + interval '14 days')::date, (SELECT id FROM measure_status_ref WHERE code='IN_PROGRESS'), (SELECT id FROM users WHERE username='dave_it'));

-- link a measure to an incident (small sample)
INSERT INTO incident_measure (incident_id, measure_id)
VALUES
 ((SELECT id FROM incidents WHERE title='Credit Card Fraud'), (SELECT id FROM measures WHERE description='Block suspicious card numbers'));

-- -------------------------
-- 18) KRIs and measurements
-- -------------------------
INSERT INTO key_risk_indicators (name, definition, unit, threshold_green, threshold_amber, threshold_red, frequency, responsible_id, risk_id)
VALUES
 ('System Downtime Hours', 'Total hours of downtime per month', 'hours', 2, 5, 10, 'Monthly', (SELECT id FROM users WHERE username='dave_it'), (SELECT id FROM risks WHERE description ILIKE '%Core banking disruption%')),
 ('Ops Staff Turnover %', 'Monthly turnover % in Ops', '%', 5, 10, 20, 'Monthly', (SELECT id FROM users WHERE username='henry_wh_emp'), NULL);

INSERT INTO kri_measurements (kri_id, period_start, period_end, value, threshold_status, recorded_by)
VALUES
 ((SELECT id FROM key_risk_indicators WHERE name='System Downtime Hours'), '2025-08-01', '2025-08-31', 6, 'Amber', (SELECT id FROM users WHERE username='dave_it')),
 ((SELECT id FROM key_risk_indicators WHERE name='Ops Staff Turnover %'), '2025-08-01', '2025-08-31', 12, 'Red', (SELECT id FROM users WHERE username='henry_wh_emp'));

-- -------------------------
-- 19) Incident-Risk, Incident-Cause examples (links)
-- -------------------------
INSERT INTO incident_risk (incident_id, risk_id) VALUES
 ((SELECT id FROM incidents WHERE title='Retail IT Outage'), (SELECT id FROM risks WHERE description ILIKE '%Core banking disruption%'));

INSERT INTO incident_cause (incident_id, loss_cause_id) VALUES
 ((SELECT id FROM incidents WHERE title='Credit Card Fraud'), (SELECT id FROM loss_causes WHERE name='External Fraud'));

-- Done inserting test data.
-- NOTE: incident_audit rows will be created automatically when you perform INSERT/UPDATE/DELETE actions on incidents because the schema's trigger is present.
