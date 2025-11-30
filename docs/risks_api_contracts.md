# Risks API Contracts

This document outlines the API contracts for the **Risks (RCSA)** module. These endpoints allow for the full lifecycle management of risks, from identification and assessment to validation, monitoring, and retirement.

## Authentication

All endpoints require Token-based authentication: `Authorization: Token <your_auth_token>`

---

## Core Endpoints (CRUD)

* **`POST /api/risks/`**
  * **Action:** Creates a new risk.
  * **Permissions:** `Manager`, `Risk Officer`.
  * **Side Effects:** The risk is created in the `DRAFT` state. The `created_by` user is set to the requestor.
  * **Validation:** Fails if the `owner` does not belong to the selected `business_unit`.

* **`GET /api/risks/`**
  * **Action:** Lists all risks visible to the authenticated user.
  * **Permissions:** Any authenticated user (visibility restricted by role).
  * **Query Logic:** The queryset is filtered based on the user's role:
      1.  **Risk Officer:** Sees all risks in their Business Unit.
      2.  **Manager:** Sees all risks in their Business Unit.
      3.  **Employee:** Sees all risks in their Business Unit.
  * **Query Parameters (Filtering):** 
    * `status`: Comma-separated list (e.g., `?status=ACTIVE,RETIRED`)
    * `risk_category`: ID of internal category
    * `business_unit`: ID of business unit
    * `owner`: User ID or `me` (e.g., `?owner=me`)
    * `inherent_score__gte`: Integer (1-25)
    * `search`: Text search on title/description

* **`GET /api/risks/{id}/`**
  * **Action:** Retrieves a single risk.
  * **Permissions:** Any user who is allowed to see the risk in the `GET` list.
  * **Response Data:** Includes computed fields (`inherent_risk_score`, `residual_risk_score`), counts (`incident_count`, `measure_count`), and contextual workflow data (`available_transitions`, `permissions`).

* **`PATCH /api/risks/{id}/`**
  * **Action:** Updates the details of a risk.
  * **Permissions:** Dynamically controlled by status and role (see Workflow Rules).
      * **`DRAFT` status:** `Manager` and `Risk Officer` can edit identity and inherent scores.
      * **`ASSESSED` status:** `Risk Officer` can edit residual scores and classification. `Manager` is read-only.
      * **`ACTIVE` / `RETIRED` status:** Read-only.

* **`DELETE /api/risks/{id}/`**
  * **Action:** Permanently deletes a risk.
  * **Permissions:** `created_by` user or `Risk Officer`.
  * **Validation:** Fails if the risk's status is **not** `DRAFT`.

---

## Workflow Action Endpoints

These endpoints are used to move a risk through its state machine.

* **`POST /api/risks/{id}/submit-for-review/`**
  * **Action:** Moves status from `DRAFT` to `ASSESSED`.
  * **Permissions:** `Manager`, `Risk Officer`.
  * **Validation:** Fails if `inherent_likelihood`, `inherent_impact`, or `risk_category` are missing.
  * **Side Effects:** Updates `submitted_for_review_at` and `submitted_by`.

* **`POST /api/risks/{id}/approve/`**
  * **Action:** Moves status from `ASSESSED` (or `DRAFT`) to `ACTIVE`.
  * **Permissions:** `Risk Officer`.
  * **Validation:** Fails if `residual_likelihood`, `residual_impact`, or `basel_event_type` are missing. Fails if `residual_risk_score` > `inherent_risk_score`. Fails if `basel_event_type` is not valid for the `risk_category`.
  * **Side Effects:** Updates `validated_at` and `validated_by`.

* **`POST /api/risks/{id}/send-back/`**
  * **Action:** Moves status from `ASSESSED` back to `DRAFT`.
  * **Permissions:** `Risk Officer`.
  * **Request Body:** `{"reason": "Inherent impact justification is insufficient."}`
  * **Side Effects:** The `reason` is logged to the `notes` field.

* **`POST /api/risks/{id}/request-reassessment/`**
  * **Action:** Moves status from `ACTIVE` back to `ASSESSED`.
  * **Permissions:** `Risk Officer`.
  * **Side Effects:** Updates `submitted_for_review_at`.

* **`POST /api/risks/{id}/retire/`**
  * **Action:** Moves status from `ACTIVE` or `ASSESSED` to `RETIRED`.
  * **Permissions:** `Risk Officer`.
  * **Request Body:** `{"reason": "Process decommissioned."}`
  * **Side Effects:** The `reason` is saved to the `retirement_reason` field.

* **`POST /api/risks/{id}/add-comment/`**
  * **Action:** Appends a timestamped comment to the risk's `notes` field.
  * **Permissions:** Participants (Owner, Creator, Risk Officer, Managers).
  * **Request Body:** `{"comment": "Discussed in Q3 committee."}`

---

## Linking Endpoints

These endpoints manage the many-to-many relationships between risks and other entities.

* **`POST /api/risks/{id}/link-to-incident/`**
  * **Action:** Creates a link between the risk and an incident.
  * **Permissions:** `Manager`, `Risk Officer` (via write access).
  * **Request Body:** `{"incident_id": 123}`
  * **Validation:** Fails if the risk is `RETIRED`. Fails if the link already exists.

* **`POST /api/risks/{id}/unlink-from-incident/`**
  * **Action:** Removes a link between the risk and an incident.
  * **Permissions:** `Manager`, `Risk Officer`.
  * **Request Body:** `{"incident_id": 123}`
  * **Validation:** Fails if the link does not exist.

* **`POST /api/risks/{id}/link-to-measure/`**
  * **Action:** Creates a link between the risk and a measure.
  * **Permissions:** `Manager`, `Risk Officer`.
  * **Request Body:** `{"measure_id": 456}`
  * **Validation:** Fails if the risk is `RETIRED`. Fails if the link already exists.

* **`POST /api/risks/{id}/unlink-from-measure/`**
  * **Action:** Removes a link between the risk and a measure.
  * **Permissions:** `Manager`, `Risk Officer`.
  * **Request Body:** `{"measure_id": 456}`
  * **Validation:** Fails if the link does not exist.