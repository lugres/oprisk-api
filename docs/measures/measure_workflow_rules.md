# Measures Workflow & Business Rules

This document defines the core business logic that governs the lifecycle of a `Measure` (corrective action).

## 1. Measure State Machine

The measure workflow follows a strict, four-stage, role-based state machine designed to ensure actions are completed and independently verified.

* [cite_start]**`OPEN`:** Measure identified but not yet started. [cite: 14]
* [cite_start]**`IN_PROGRESS`:** Work on the measure is actively underway. [cite: 15]
* [cite_start]**`PENDING_REVIEW`:** Measure implementation completed by the responsible user and is now awaiting verification from a Risk Officer. [cite: 16]
* [cite_start]**`COMPLETED`:** Measure has been successfully implemented and verified. [cite: 17]
* **`CANCELLED`:** Measure is no longer needed or was rejected. [cite_start]This is a terminal state. [cite: 18]

The primary "happy path" workflow is:
[cite_start]**`OPEN` → `IN_PROGRESS` → `PENDING_REVIEW` → `COMPLETED`** [cite: 6]

---

## 2. State Transition Rules

[cite_start]Transitions are controlled by dedicated API endpoints, each with specific role-based permissions and logic. [cite: 2, 7-12]

| Action | From Status | To Status | Authorized Role(s) |
| :--- | :--- | :--- | :--- |
| `start_progress` | `OPEN` | `IN_PROGRESS` | `responsible` user, `responsible`'s Manager |
| `submit_for_review`| `IN_PROGRESS` | `PENDING_REVIEW`| `responsible` user, `responsible`'s Manager |
| `return_to_progress`| `PENDING_REVIEW` | `IN_PROGRESS` | `Risk Officer` |
| `complete` | `PENDING_REVIEW` | `COMPLETED` | `Risk Officer` |
| `cancel` | `IN_PROGRESS`, `PENDING_REVIEW` | `CANCELLED` | `Risk Officer` |
| `DELETE` | `OPEN` | (n/a - hard delete) | `created_by` user, `responsible`'s Manager |

---

## 3. Dynamic Data Validation & Security

The system enforces data integrity and governance through dynamic validation and field-level security.

### 3.1. Dynamic Field Validation (State Transitions)

To ensure an audit trail, certain state transitions require a payload.

* **`submit_for_review`:** Requires an `{"evidence": "..."}` payload. [cite_start]The text is timestamped and appended to the measure's `notes` field. [cite: 2]
* [cite_start]**`return_to_progress`:** Requires a `{"reason": "..."}` payload, which is logged to the `notes` field. [cite: 2]
* [cite_start]**`complete`:** Requires a `{"closure_comment": "..."}` payload, which is saved to the measure's `closure_comment` field. [cite: 2]
* [cite_start]**`cancel`:** Requires a `{"reason": "..."}` payload, which is logged to the `notes` field. [cite: 2]
* [cite_start]**`add_comment`:** Requires a `{"comment": "..."}` payload, which is logged to the `notes` field. [cite: 2, 21-22]

### 3.2. Dynamic Field-Level Security (PATCH)

To protect the integrity of a measure once it is in-flight, field editability is dynamic.

* **Status: `OPEN`**
  * `responsible` user (or their Manager) can edit `description`, `deadline`, `responsible`.
* **Status: `IN_PROGRESS`**
  * `responsible` user can edit the `description`.
  * The `deadline` is **LOCKED** for the responsible user.
  * [cite_start]Only a `Risk Officer` can modify the `deadline` of an `IN_PROGRESS` measure. [cite: 2]
* **Status: `PENDING_REVIEW`, `COMPLETED`, `CANCELLED`**
  * All fields are **LOCKED** and become read-only.

---

## 4. Overdue Logic (SLA)

The system **does not** use an `OVERDUE` status. "Overdue" is a computed property, not an explicit state.

A background job (e.g., Celery Beat) will be responsible for querying for measures that are past their deadline and still active.

**Query for Overdue Measures:**
```sql
SELECT id FROM measures
WHERE status_id IN (SELECT id FROM measure_status_ref WHERE code IN ('OPEN', 'IN_PROGRESS'))
  AND deadline < NOW();
```
For each measure found, the job will create a `Notification` record with `event_type='MEASURE_OVERDUE'` to be processed by the notification queue.