# API Contracts & Endpoints

This document outlines the API contracts for the **Incident Management** module, which is the first and most developed component of the ORM platform.

Future modules (Risks, Controls, Measures) will have their own API contracts.

## Authentication

All endpoints require Token-based authentication. The token must be provided in the `Authorization` header:

`Authorization: Token <your_auth_token>`

---

## Core Endpoints (CRUD)

These endpoints provide standard Create, Read, Update, and Delete functionality, governed by the [Dynamic Field-Level Security](./incident_workflow_rules.md#42-dynamic-field-level-security-patch) rules.

* **`GET /api/incidents/incidents/`**
    * Lists all incidents visible to the authenticated user, based on their role (Layer 1 Security).
* **`POST /api/incidents/incidents/`**
    * Creates a new incident. The incident is created in the `DRAFT` state, and `draft_due_at` is set.
* **`GET /api/incidents/incidents/{id}/`**
    * Retrieves a single incident.
* **`PATCH /api/incidents/incidents/{id}/`**
    * Updates an incident. The fields available for editing are dynamically controlled by the `IncidentEditableField` configuration, based on the incident's status and the user's role.

---

## Workflow Action Endpoints

These are the primary endpoints for managing the incident lifecycle. They are all `POST` requests that trigger a specific business service.

### `POST /api/incidents/incidents/{id}/submit/`

* **Action:** Moves an incident from `DRAFT` to `PENDING_REVIEW`.
* **Permissions:** `IsIncidentCreator` (only the creator can submit).
* **Validations:**
    * Fails if any fields required for `PENDING_REVIEW` (e.g., `simplified_event_type`) are missing.
* **Side Effects:**
    * Clears `draft_due_at` timer.
    * Sets `review_due_at` timer.
    * Assigns the incident to the creator's manager (or a custom route).

### `POST /api/incidents/incidents/{id}/review/`

* **Action:** Moves an incident from `PENDING_REVIEW` to `PENDING_VALIDATION`.
* **Permissions:** `IsIncidentManager` (only the creator's manager can review).
* **Validations:**
    * Fails if any fields required for `PENDING_VALIDATION` (e.g., `product`) are missing.
* **Side Effects:**
    * Clears `review_due_at` timer.
    * Sets `validation_due_at` timer.
    * Assigns the incident to a `Risk Officer`.
    * Triggers the **Notification Routing** engine based on simplified event type (can be moved to 'submit' later).

### `POST /api/incidents/incidents/{id}/validate/`

* **Action:** Moves an incident from `PENDING_VALIDATION` to `VALIDATED`.
* **Permissions:** `IsRoleRiskOfficer` (only Risk Officers can validate).
* **Validations:**
    * Fails if any fields required for `VALIDATED` (e.g., `basel_event_type`, `net_loss_amount`) are missing.
* **Side Effects:**
    * Clears `validation_due_at` timer.
    * Sets `validated_by` and `validated_at` timestamps.
    * Triggers the **Notification Routing** engine based on Basel event type (an option).

### `POST /api/incidents/incidents/{id}/close/`

* **Action:** Moves an incident from `VALIDATED` to `CLOSED`.
* **Permissions:** `IsRoleRiskOfficer`.
* **Side Effects:**
    * Sets `closed_by` and `closed_at` timestamps.
    * (In future: locks the incident from all edits).

### `POST /api/incidents/incidents/{id}/return_to_draft/`

* **Action:** Returns an incident from `PENDING_REVIEW` to `DRAFT`.
* **Permissions:** `IsRoleManager`.
* **Request Body:** Requires a `reason` field: `{"reason": "string"}`.
* **Side Effects:**
    * Clears `review_due_at` timer.
    * Resets `draft_due_at` timer.
    * Logs the `reason` to the incident's `notes`.

### `POST /api/incidents/incidents/{id}/return_to_review/`

* **Action:** Returns an incident from `PENDING_VALIDATION` to `PENDING_REVIEW`.
* **Permissions:** `IsRoleRiskOfficer`.
* **Request Body:** Requires a `reason` field: `{"reason": "string"}`.
* **Side Effects:**
    * Clears `validation_due_at` timer.
    * Resets `review_due_at` timer.
    * Logs the `reason` to the incident's `notes`.

---

## Notification Routing

The system uses custom, data-driven incident routing for **awareness**, not ownership.

Current logic:

* When a Manager `reviews` an incident, the `review_incident` service calls the routing engine (`evaluate_routing_for_incident`).
* This engine checks the incident's `simplified_event_type` against `IncidentRoutingRule`s.
* If a match is found (e.g., "Fraud"), a new `Notification` record is created in the database queue with `status='queued'` and `recipient_role='Fraud Team'`.
* This *does not* change the `assigned_to` field, which correctly points to the Risk Officer for the next workflow step.
* An asynchronous (Celery) worker is responsible for processing this queue.