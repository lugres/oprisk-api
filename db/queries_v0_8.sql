-- queries.sql
-- Typical checks, workflow transitions, routing evaluation, SLA overdue checks, audit verification.
-- Run these after test_data.sql (and after you loaded the v0_8 schema).

-- ----------------------------------------------------------------
-- A. Quick confirmation queries
-- ----------------------------------------------------------------

-- 1) List roles
SELECT id, name FROM roles ORDER BY id;

-- 2) Check basel event types
SELECT id, name FROM basel_event_types ORDER BY id;

-- 3) Check routing rules (predicate shown)
SELECT id, priority, description, predicate FROM incident_routing_rules ORDER BY priority;

-- 4) Who are the users (small roster)
SELECT id, username, full_name, (SELECT name FROM roles r WHERE r.id = users.role_id) AS role, 
(SELECT name FROM business_units b WHERE b.id = users.business_unit_id) AS bu, manager_id
FROM users
ORDER BY id;

-- All incidents with statuses and assigned_to username
SELECT i.id, i.title, s.code AS status, r.username AS reported_by, a.username AS assigned_to, 
    d.username AS deleted_by, i.gross_loss_amount
FROM incidents i
LEFT JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users r ON r.id = i.reported_by
LEFT JOIN users a ON a.id = i.assigned_to
LEFT JOIN users d ON d.id = i.deleted_by
ORDER BY i.created_at DESC;

-- ----------------------------------------------------------------
-- B. Routing evaluation (SQL to find the first matching rule for an incident)
--    This returns the routing rule and the intended assignee (user) based on rule.
-- ----------------------------------------------------------------

-- Example: find matching rule for the 'Retail IT Outage' incident
SELECT i.id AS incident_id, i.title,
       ir.id AS matched_rule_id, ir.description AS matched_description,
       ir.priority, ir.predicate,
       ir.route_to_role_id, ir.route_to_bu_id,
       u.id AS matched_user_id, u.username AS matched_user
FROM incidents i
LEFT JOIN LATERAL (
    SELECT ir.*
    FROM incident_routing_rules ir
    WHERE ir.active = TRUE
      AND (
        -- min_amount condition
        (
          (ir.predicate ? 'min_amount')
          AND ((ir.predicate->>'min_amount')::numeric <= COALESCE(i.gross_loss_amount,0))
        )
        -- OR basel_event_type (+ optional bu) condition
        OR (
          (ir.predicate ? 'basel_event_type_id')
          AND ( (ir.predicate->>'basel_event_type_id')::int = COALESCE(i.basel_event_type_id,0) )
          AND (
              NOT (ir.predicate ? 'business_unit_id')
              OR ((ir.predicate->>'business_unit_id')::int = COALESCE(i.business_unit_id,0))
          )
        )
      )
    ORDER BY ir.priority ASC
    LIMIT 1
) ir ON TRUE
LEFT JOIN LATERAL (
    -- pick one user who belongs to route_to_bu_id and/or route_to_role_id
    SELECT u2.id, u2.username
    FROM users u2
    WHERE (ir.route_to_role_id IS NULL OR u2.role_id = ir.route_to_role_id)
      AND (ir.route_to_bu_id IS NULL OR u2.business_unit_id = ir.route_to_bu_id)
    LIMIT 1
) u ON TRUE
WHERE i.title = 'Retail IT Outage';

-- ----------------------------------------------------------------
-- C. Submit an incident (DRAFT -> PENDING_REVIEW)
--    - compute review_due_at from sla_config
--    - evaluate routing rules to set assigned_to (first matching rule by priority)
--    - default: if no rule matched, assign to reporter's manager
--    - set audit.user_id so incident_audit records 'changed_by'
-- ----------------------------------------------------------------

-- verify incident's data before applying any changes
-- check incident_audit table as well with 'select *'
SELECT i.id, i.title, i.status_id, s.code AS status_code, i.assigned_to, u.username AS assigned_username, i.review_due_at
FROM incidents i
JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.title = 'Retail IT Outage';

-- Submit 'Retail IT Outage' as Alice

-- set audit user
-- SELECT id::text FROM users WHERE username='alice_emp'; -- returned 7
-- SET audit.user_id = '7';

-- this works only in transaction mode! 
-- You have to put "set_config" and subsequent UPDATE within BEGIN; ... COMMIT;
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='alice_emp'), true);

UPDATE incidents i
SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'),
    review_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='review_days') || ' days')::interval,
    assigned_to = COALESCE(
      (
        SELECT u.id
        FROM incident_routing_rules ir
        JOIN users u ON ( (ir.route_to_role_id IS NULL OR u.role_id = ir.route_to_role_id)
                         AND (ir.route_to_bu_id IS NULL OR u.business_unit_id = ir.route_to_bu_id) )
        WHERE ir.active = TRUE
          AND (
            (ir.predicate ? 'min_amount' AND (ir.predicate->>'min_amount')::numeric <= COALESCE(i.gross_loss_amount,0))
            OR (ir.predicate ? 'basel_event_type_id' AND (ir.predicate->>'basel_event_type_id')::int = COALESCE(i.basel_event_type_id,0)
              AND (NOT (ir.predicate ? 'business_unit_id') OR (ir.predicate->>'business_unit_id')::int = COALESCE(i.business_unit_id,0))
            )
          )
        ORDER BY ir.priority ASC
        LIMIT 1
      ),
      -- fallback: reporter's manager
      (SELECT manager_id FROM users WHERE id = i.reported_by)
    )
WHERE i.title = 'Retail IT Outage'
  AND (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW') IS NOT NULL;

COMMIT;

-- Verify assigned_to after submit
SELECT i.id, i.title, i.status_id, s.code AS status_code, i.assigned_to, u.username AS assigned_username, i.review_due_at
FROM incidents i
JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.title = 'Retail IT Outage';

-- ----------------------------------------------------------------
-- D. Manager review -> APPROVE (PENDING_REVIEW -> PENDING_VALIDATION)
-- !!! WRONG !!! Incident should go to InfoSec according to custom routing!
--    Manager Bob approves Retail IT Outage. Set validation_due_at.
-- ----------------------------------------------------------------

-- use select from above to check incident's status

-- Apply this instead of below section 
-- InfoSec approves -> PENDING_VALIDATION
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='eve_infosec'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'),
    validation_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='validation_days') || ' days')::interval,
    assigned_to = (SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name='Risk Officer') LIMIT 1)
WHERE title = 'Retail IT Outage'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW');
COMMIT;

-- BEGIN;
-- -- set audit user to manager (bob_mgr)
-- SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='bob_mgr'), true);

-- UPDATE incidents
-- SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'),
--     validation_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='validation_days') || ' days')::interval,
--     -- set assigned_to to an ORM (simple approach: pick any Risk Officer user)
--     assigned_to = (SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name='Risk Officer') LIMIT 1)
-- WHERE title = 'Retail IT Outage'
--   AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW');
-- COMMIT;

-- Check incident audit entries for this incident
SELECT id, incident_id, operation_type, changed_by, changed_at
FROM incident_audit
WHERE incident_id = (SELECT id FROM incidents WHERE title='Retail IT Outage')
ORDER BY changed_at;

-- ----------------------------------------------------------------
-- E. ORM validates (PENDING_VALIDATION -> VALIDATED)
--    Carried out by Carol (Risk Officer)
-- ----------------------------------------------------------------

-- use select from above to check incident's status

BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='carol_orm'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='VALIDATED'),
    validated_by = (SELECT id FROM users WHERE username='carol_orm'),
    validated_at = now()
WHERE title = 'Retail IT Outage'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION');

COMMIT;

-- Check that incident_audit has a sequence of entries (INSERT + UPDATEs)
SELECT id, incident_id, operation_type, changed_by, changed_at, old_data->>'status_id' AS old_status, new_data->>'status_id' AS new_status
FROM incident_audit
WHERE incident_id = (SELECT id FROM incidents WHERE title = 'Retail IT Outage')
ORDER BY changed_at;

-- ----------------------------------------------------------------
-- F. Full lifecycle example: Large Trading Loss (material > $1M)
--    This one will exercise routing to Group ORM and go through all states: submit -> manager -> ORM validate -> close
-- ----------------------------------------------------------------

-- check current status
SELECT i.id, i.title, i.status_id, s.code AS status_code, i.assigned_to, u.username AS assigned_username, i.review_due_at
FROM incidents i
JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.title = 'Large Trading Loss';

-- Submit Large Trading Loss (reported by Henry)
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='henry_wh_emp'), true);

UPDATE incidents i
SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW'),
    review_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='review_days') || ' days')::interval,
    assigned_to = COALESCE(
      (
        SELECT u.id
        FROM incident_routing_rules ir
        JOIN users u ON ( (ir.route_to_role_id IS NULL OR u.role_id = ir.route_to_role_id)
                         AND (ir.route_to_bu_id IS NULL OR u.business_unit_id = ir.route_to_bu_id) )
        WHERE ir.active = TRUE
          AND (ir.predicate ? 'min_amount' AND (ir.predicate->>'min_amount')::numeric <= COALESCE(i.gross_loss_amount,0))
        ORDER BY ir.priority ASC
        LIMIT 1
      ),
      (SELECT manager_id FROM users WHERE id = i.reported_by)
    )
WHERE i.title = 'Large Trading Loss';
COMMIT;

-- Verify assignment (should be assigned to a Group ORM user)
SELECT i.id, i.title, s.code AS status, i.assigned_to, u.username AS assigned_to_username
FROM incidents i
JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.title = 'Large Trading Loss';

-- -- Manager (wh_mgr) approves -> PENDING_VALIDATION
-- SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='wh_mgr'), true);

-- UPDATE incidents
-- SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'),
--     validation_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='validation_days') || ' days')::interval,
--     assigned_to = (SELECT id FROM users WHERE role_id = (SELECT id FROM roles WHERE name='Group ORM') LIMIT 1)
-- WHERE title = 'Large Trading Loss'
--   AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW');

-- ORM (Group ORM user) approves PENDING_REVIEW -> PENDING_VALIDATION
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='greg_grouporm'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION'),
    validation_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='validation_days') || ' days')::interval
WHERE title = 'Large Trading Loss'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW');
COMMIT;

-- ORM (Group ORM user) validates -> VALIDATED
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='greg_grouporm'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='VALIDATED'),
    validated_by = (SELECT id FROM users WHERE username='greg_grouporm'),
    validated_at = now(),
    assigned_to = NULL
WHERE title = 'Large Trading Loss'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION');
COMMIT;

-- ORM closes -> CLOSED
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='greg_grouporm'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='CLOSED'),
    closed_by = (SELECT id FROM users WHERE username='greg_grouporm'),
    closed_at = now()
WHERE title = 'Large Trading Loss'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='VALIDATED');
COMMIT;

-- View audit trail for Large Trading Loss
SELECT id, incident_id, operation_type, changed_by, changed_at
FROM incident_audit
WHERE incident_id = (SELECT id FROM incidents WHERE title = 'Large Trading Loss')
ORDER BY changed_at;

-- ----------------------------------------------------------------
-- G. Manager returns an incident to DRAFT (PENDING_REVIEW -> DRAFT)
--    For 'Reconciliation Error' example: manager returns it to creator and we recompute draft_due_at
-- ----------------------------------------------------------------

-- check incident status first.
SELECT i.id, i.title, i.status_id, s.code AS status_code, i.assigned_to, 
    u.username AS assigned_username, i.draft_due_at, i.review_due_at 
FROM incidents i
JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.title = 'Reconciliation Error';
-- OR more compact select from below.

-- Manager (wh_mgr) returns 'Reconciliation Error' to DRAFT with comment (simulated via an update)
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='wh_mgr'), true);

UPDATE incidents
SET status_id = (SELECT id FROM incident_status_ref WHERE code='DRAFT'),
    draft_due_at = now() + ((SELECT value_int FROM sla_config WHERE key='draft_days') || ' days')::interval,
    assigned_to = reported_by  -- assign back to author
WHERE title = 'Reconciliation Error'
  AND status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW');
COMMIT;

-- Confirm the incident is back in DRAFT and draft_due_at recomputed
SELECT id, title, (SELECT code FROM incident_status_ref s WHERE s.id = incidents.status_id) AS status_code, draft_due_at, assigned_to
FROM incidents
WHERE title = 'Reconciliation Error';

-- ----------------------------------------------------------------
-- H. Overdue detection queries (SLA)
--    1) Incidents overdue in DRAFT (creator reminder)
--    2) Incidents overdue in PENDING_REVIEW (manager reminder)
--    3) Incidents overdue in PENDING_VALIDATION (ORM reminder)
-- ----------------------------------------------------------------

-- 1) DRAFT overdue
SELECT i.id, i.title, u.username AS reporter, i.draft_due_at
FROM incidents i
JOIN users u ON u.id = i.reported_by
WHERE i.status_id = (SELECT id FROM incident_status_ref WHERE code='DRAFT')
  AND i.draft_due_at < now()
ORDER BY i.draft_due_at;

-- 2) PENDING_REVIEW overdue
SELECT i.id, i.title, u.username AS assigned_manager, i.review_due_at
FROM incidents i
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_REVIEW')
  AND i.review_due_at < now();

-- 3) PENDING_VALIDATION overdue
SELECT i.id, i.title, u.username AS assigned_orm, i.validation_due_at
FROM incidents i
LEFT JOIN users u ON u.id = i.assigned_to
WHERE i.status_id = (SELECT id FROM incident_status_ref WHERE code='PENDING_VALIDATION')
  AND i.validation_due_at < now();

-- ----------------------------------------------------------------
-- I. Verify routing for all incidents (show which rule matched)
-- ----------------------------------------------------------------
SELECT i.id, i.title, i.gross_loss_amount, i.basel_event_type_id, i.business_unit_id,
       (SELECT description FROM incident_routing_rules ir WHERE ir.id = (
            SELECT id FROM incident_routing_rules ir2
            WHERE ir2.active = TRUE
              AND (
                 (ir2.predicate ? 'min_amount' AND (ir2.predicate->>'min_amount')::numeric <= COALESCE(i.gross_loss_amount,0))
                 OR (ir2.predicate ? 'basel_event_type_id' AND (ir2.predicate->>'basel_event_type_id')::int = COALESCE(i.basel_event_type_id,0)
                     AND (NOT (ir2.predicate ? 'business_unit_id') OR (ir2.predicate->>'business_unit_id')::int = COALESCE(i.business_unit_id,0))
                 )
              )
            ORDER BY ir2.priority ASC LIMIT 1
       )) AS matched_rule_description
FROM incidents i
ORDER BY i.created_at DESC;

-- ----------------------------------------------------------------
-- J. Soft delete test: soft-delete an incident and verify active_incidents view hides it
-- ----------------------------------------------------------------

-- Soft-delete 'Credit Card Fraud' (this will trigger your soft_delete_trigger)
BEGIN;
SELECT set_config('audit.user_id', (SELECT id::text FROM users WHERE username='alice_emp'), true);

DELETE FROM incidents WHERE title = 'Credit Card Fraud';
COMMIT;

-- Confirm it's not in the active view but still exists in incidents
SELECT id, title, deleted_at, deleted_by FROM incidents WHERE title = 'Credit Card Fraud';
SELECT * FROM active_incidents WHERE title = 'Credit Card Fraud';

-- Check incident_audit for DELETE entry
SELECT id, incident_id, operation_type, changed_by, changed_at
FROM incident_audit
WHERE incident_id = (SELECT id FROM incidents WHERE title='Credit Card Fraud')
ORDER BY changed_at;

-- ----------------------------------------------------------------
-- K. Index / EXPLAIN examples (note: on a small data set planner may prefer seq scan)
-- ----------------------------------------------------------------

EXPLAIN ANALYZE
SELECT kri_id, period_start, period_end, value
FROM kri_measurements
WHERE kri_id = (SELECT id FROM key_risk_indicators WHERE name='System Downtime Hours')
  AND period_start >= '2025-07-01' AND period_end <= '2025-07-31';

-- KRI breaches (partial index will help on big tables; on small dataset may still use seq scan)
EXPLAIN ANALYZE
SELECT k.name, m.value, m.threshold_status
FROM kri_measurements m
JOIN key_risk_indicators k ON m.kri_id = k.id
WHERE m.threshold_status <> 'Green';

-- ----------------------------------------------------------------
-- L. Useful selects for interactive inspection
-- ----------------------------------------------------------------
-- All incidents with statuses and assigned_to username
SELECT i.id, i.title, s.code AS status, r.username AS reported_by, a.username AS assigned_to, 
    d.username AS deleted_by, i.gross_loss_amount
FROM incidents i
LEFT JOIN incident_status_ref s ON s.id = i.status_id
LEFT JOIN users r ON r.id = i.reported_by
LEFT JOIN users a ON a.id = i.assigned_to
LEFT JOIN users d ON d.id = i.deleted_by
ORDER BY i.created_at DESC;
