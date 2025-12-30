# Incident Workflow & Business Rules

This document defines the core business logic that governs the incident lifecycle, from data collection to state transitions.

---

## 1. Incident State Machine

The incident workflow follows a strict, role-based state machine. An incident can only move between states via an authorized transition.

* **DRAFT:** The initial state. Editable only by the creator.
* **PENDING_REVIEW:** Submitted by the creator and awaiting manager approval.
* **PENDING_VALIDATION:** Reviewed by a Manager and awaiting Risk Officer validation.
* **VALIDATED:** Validated by a Risk Officer. Data is considered final.
* **CLOSED:** The incident record is complete and locked.

---

## 2. State Transition Rules

Transitions are controlled by the `AllowedTransition` model, which maps a `(from_status, to_status)` pair to an authorized `Role`.

| Action | From Status | To Status | Authorized Role |
| :--- | :--- | :--- | :--- |
| `submit` | `DRAFT` | `PENDING_REVIEW` | Employee |
| `review` | `PENDING_REVIEW` | `PENDING_VALIDATION` | Manager |
| `validate` | `PENDING_VALIDATION` | `VALIDATED` | Risk Officer |
| `close` | `VALIDATED` | `CLOSED` | Risk Officer |
| `return_to_draft` | `PENDING_REVIEW` | `DRAFT` | Manager |
| `return_to_review` | `PENDING_VALIDATION`| `PENDING_REVIEW` | Risk Officer |

---

## 3. SLA Calculation Logic

SLA timers (`..._due_at` fields) are managed to reflect the current state. This allows a background job to find all incidents that are "stuck" in their current state.

The logic is as follows:

1.  **On `create` (-> DRAFT):**
    * **SET** `draft_due_at = now() + sla_config.draft_days`
2.  **On `submit` (-> PENDING_REVIEW):**
    * **CLEAR** `draft_due_at = NULL`
    * **SET** `review_due_at = now() + sla_config.review_days`
3.  **On `review` (-> PENDING_VALIDATION):**
    * **CLEAR** `review_due_at = NULL`
    * **SET** `validation_due_at = now() + sla_config.validation_days`
4.  **On `validate` (-> VALIDATED):**
    * **CLEAR** `validation_due_at = NULL`
5.  **On `return_to_draft` (-> DRAFT):**
    * **CLEAR** `review_due_at = NULL`
    * **SET** `draft_due_at = now() + sla_config.draft_days` (timer restarts)
6.  **On `return_to_review` (-> PENDING_REVIEW):**
    * **CLEAR** `validation_due_at = NULL`
    * **SET** `review_due_at = now() + sla_config.review_days` (timer restarts)

---

## 4. Dynamic Data Validation & Security

To ensure data quality and security, the platform uses two data-driven systems.

### 4.1. Dynamic Field Validation (State Transitions)

* **Purpose:** Enforces data completeness *before* a state transition can occur.
* **Model:** `IncidentRequiredField`
* **Logic:** Before a service (e.g., `review_incident`) can execute, it runs `_validate_required_fields` to check that all fields required for the *target* state (`PENDING_VALIDATION`) are filled in.
* **Example:** A Manager cannot `review` (move to `PENDING_VALIDATION`) an incident until the `gross_loss_amount` and `product` fields are set.

### 4.2. Dynamic Field-Level Security (PATCH)

* **Purpose:** Enforces "progressive disclosure" by preventing users from editing fields that are not relevant to their role or the incident's current status.
* **Model:** `IncidentEditableField`
* **Logic:** The `IncidentUpdateSerializer` dynamically queries this model based on the user's role and the incident's status. Any field *not* in the "allowed" list for that specific context is made `read_only=True` for that `PATCH` request.
* **Example:**
    * An `Employee` can `PATCH` the `title` of an incident in `DRAFT`.
    * Once the incident is `PENDING_VALIDATION`, the `title` field becomes `read_only` for the `Employee`.
    * A `Risk Officer` can then `PATCH` the `basel_event_type` (a field the `Employee` could never edit).