# Risks Workflow & Business Rules

This document defines the core business logic that governs the lifecycle of a `Risk` (RCSA entry).

## 1. Risk State Machine

The risk workflow follows a strict, four-stage, role-based state machine designed to separate assessment from validation.

* **`DRAFT`:** Risk identified and being assessed by the Manager. Inherent scores are estimated.
* **`ASSESSED`:** Assessment submitted by Manager. Locked for Manager edits. Awaiting validation and residual scoring by a Risk Officer.
* **`ACTIVE`:** Risk validated and live in the Risk Register. Subject to monitoring. Scores are locked.
* **`RETIRED`:** Risk is no longer relevant or the underlying process was decommissioned. This is a terminal state.

The primary "happy path" workflow is:
**`DRAFT` → `ASSESSED` → `ACTIVE`**

A "Workshop Mode" shortcut exists for Risk Officers:
**`DRAFT` → `ACTIVE`**

---

## 2. State Transition Rules

Transitions are controlled by dedicated API endpoints, each with specific role-based permissions and logic.

| Action | From Status | To Status | Authorized Role(s) |
| :--- | :--- | :--- | :--- |
| `submit_for_review` | `DRAFT` | `ASSESSED` | `Manager`, `Risk Officer` |
| `approve` | `ASSESSED` | `ACTIVE` | `Risk Officer` |
| `approve` (Direct) | `DRAFT` | `ACTIVE` | `Risk Officer` |
| `send_back` | `ASSESSED` | `DRAFT` | `Risk Officer` |
| `request_reassessment`| `ACTIVE` | `ASSESSED` | `Risk Officer` |
| `retire` | `ACTIVE`, `ASSESSED` | `RETIRED` | `Risk Officer` |
| `DELETE` | `DRAFT` | (n/a - hard delete) | `created_by` user, `Risk Officer` |

---

## 3. Dynamic Data Validation & Security

The system enforces data integrity and governance through dynamic validation and field-level security.

### 3.1. Dynamic Field Validation (State Transitions)

To ensure data quality, certain state transitions require specific data to be present.

* **`submit_for_review`:**
    * **Inherent Scores:** `inherent_likelihood` and `inherent_impact` must be set.
    * **Categorization:** `risk_category` must be set.
    * **Basel Type:** Validated against `risk_category` mappings if present.

* **`approve`:**
    * **Residual Scores:** `residual_likelihood` and `residual_impact` must be set.
    * **Basel Type:** `basel_event_type` must be set and valid for the selected `risk_category`.
    * **Logic Check:** `residual_risk_score` cannot exceed `inherent_risk_score`.

* **`send_back`:**
    * Requires a `{"reason": "..."}` payload, which is logged to the `notes` field.

* **`retire`:**
    * Requires a `{"reason": "..."}` payload, which is saved to the `retirement_reason` field.

* **`add_comment`:**
    * Requires a `{"comment": "..."}` payload, which is logged to the `notes` field.

### 3.2. Dynamic Field-Level Security (PATCH)

To protect the integrity of the risk register, field editability is dynamic based on status and role.

* **Status: `DRAFT`**
    * **`Manager`, `Risk Officer`:** Can edit all identification fields, context, and inherent scores.
    * **`Risk Officer`:** Can also edit residual scores (for "Workshop Mode").

* **Status: `ASSESSED`**
    * **`Manager`:** Read-only. Cannot modify data while under review.
    * **`Risk Officer`:** Can edit **Validation Fields Only** (`residual_likelihood`, `residual_impact`, `basel_event_type`, `risk_category`, `title`, `description`, `context`).

* **Status: `ACTIVE`, `RETIRED`**
    * All fields are **LOCKED** and become read-only for all users.
    * To modify an `ACTIVE` risk, a Risk Officer must first use `request_reassessment` to move it back to `ASSESSED`.

---

## 4. Reassessment Logic

The system supports periodic RCSA cycles through the Reassessment workflow.

* **Trigger:** A Risk Officer triggers a review (e.g., annual cycle or post-incident) using the `request_reassessment` action.
* **Effect:**
    1.  Status moves from `ACTIVE` to `ASSESSED`.
    2.  `submitted_for_review_at` timestamp is updated.
    3.  Fields become editable for the Risk Officer to update scores.
    4.  If the Risk Officer needs the Manager to provide input, they can then use `send_back` to move it to `DRAFT`.