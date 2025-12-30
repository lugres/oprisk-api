# Measures API Contracts

This document outlines the API contracts for the **Measures (Corrective Actions)** module. These endpoints allow for the full lifecycle management of measures, from creation and linking to execution and verification.

## Authentication

All endpoints require Token-based authentication: `Authorization: Token <your_auth_token>`

---

## Core Endpoints (CRUD)

* **`POST /api/measures/`**
  * [cite_start]**Action:** Creates a new measure. [cite: 2]
  * [cite_start]**Permissions:** `Manager`, `Risk Officer`. [cite: 2]
  * **Side Effects:** The measure is created in the `OPEN` state. The `created_by` user is set to the requestor.

* **`GET /api/measures/`**
  * **Action:** Lists all measures visible to the authenticated user.
  * **Permissions:** Any authenticated user.
  * **Query Logic:** The queryset is filtered based on the user's role. A user can see a measure if they are:
      1.  The `responsible` user.
      2.  The `created_by` user.
      3.  The Manager of the `responsible` or `created_by` user.
      4.  [cite_start]A `Risk Officer` in the same Business Unit. [cite: 2]

* **`GET /api/measures/{id}/`**
  * **Action:** Retrieves a single measure.
  * [cite_start]**Permissions:** Any user who is allowed to see the measure in the `GET` list (relies on the same `get_queryset` logic). [cite: 2]

* **`PATCH /api/measures/{id}/`**
  * **Action:** Updates the details of a measure, such as its `description` or `deadline`.
  * **Permissions:** Dynamically controlled.
      * **`OPEN` status:** `responsible` user (or Manager), `created_by` user.
      * **`IN_PROGRESS` status:** `responsible` user (or Manager) can edit `description`. [cite_start]Only a `Risk Officer` can edit the `deadline`. [cite: 2]
      * Other statuses are read-only.

* **`DELETE /api/measures/{id}/`**
  * **Action:** Permanently deletes a measure.
  * [cite_start]**Permissions:** `created_by` user (or their Manager). [cite: 2]
  * [cite_start]**Validation:** Fails if the measure's status is **not** `OPEN`. [cite: 2]

---

## Workflow Action Endpoints

These endpoints are used to move a measure through its state machine.

* **`POST /api/measures/{id}/start_progress/`**
  * [cite_start]**Action:** Moves status from `OPEN` to `IN_PROGRESS`. [cite: 8]
  * [cite_start]**Permissions:** `responsible` user or their Manager. [cite: 2]

* **`POST /api/measures/{id}/add_comment/`**
  * [cite_start]**Action:** Appends a timestamped comment to the measure's `notes` field. [cite: 21-22]
  * [cite_start]**Permissions:** `responsible` user (or Manager), `Risk Officer`. [cite: 2]
  * **Request Body:** `{"comment": "This is my progress update."}`

* **`POST /api/measures/{id}/submit_for_review/`**
  * [cite_start]**Action:** Moves status from `IN_PROGRESS` to `PENDING_REVIEW`. [cite: 9]
  * [cite_start]**Permissions:** `responsible` user or their Manager. [cite: 2]
  * **Request Body:** `{"evidence": "Completed the task. See attached server log."}`
  * [cite_start]**Side Effects:** The `evidence` text is logged to the `notes` field. [cite: 2]

* **`POST /api/measures/{id}/return_to_progress/`**
  * [cite_start]**Action:** Moves status from `PENDING_REVIEW` back to `IN_PROGRESS`. [cite: 10]
  * [cite_start]**Permissions:** `Risk Officer`. [cite: 2]
  * **Request Body:** `{"reason": "The provided evidence is insufficient."}`
  * [cite_start]**Side Effects:** The `reason` is logged to the `notes` field. [cite: 2]

* **`POST /api/measures/{id}/complete/`**
  * [cite_start]**Action:** Moves status from `PENDING_REVIEW` to `COMPLETED`. [cite: 10]
  * [cite_start]**Permissions:** `Risk Officer`. [cite: 2]
  * **Request Body:** `{"closure_comment": "Verified fix with the IT team."}`
  * [cite_start]**Side Effects:** The `closure_comment` is saved to its dedicated field. [cite: 2]

* **`POST /api/measures/{id}/cancel/`**
  * [cite_start]**Action:** Moves status to `CANCELLED`. [cite: 9, 10]
  * [cite_start]**Permissions:** `Risk Officer`. [cite: 2]
  * **Validation:** Fails if status is `OPEN`.
  * **Request Body:** `{"reason": "This measure is no longer required due to new system."}`
  * [cite_start]**Side Effects:** The `reason` is logged to the `notes` field. [cite: 2]

---

## Linking Endpoints

[cite_start]These endpoints manage the many-to-many relationship between measures and other entities. [cite: 3, 4]

* **`POST /api/measures/{id}/link-to-incident/`**
  * **Action:** Creates a link between the measure and an incident.
  * [cite_start]**Permissions:** `Risk Officer`, `Manager`, `responsible` user. [cite: 2]
  * **Request Body:** `{"incident_id": 123}`
  * **Validation:** Fails if the measure's status is `CANCELLED`. Fails if the link already exists.

* **`POST /api/measures/{id}/unlink-from-incident/`**
  * **Action:** Removes a link between the measure and an incident.
  * [cite_start]**Permissions:** `Risk Officer` user. [cite: 2]
  * **Request Body:** `{"incident_id": 123}`
  * **Validation:** Fails if the link does not exist.