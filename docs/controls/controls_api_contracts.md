# Controls API Contracts

This document outlines the API contracts for the **Controls (Mitigation)** module. These endpoints manage the central library of controls. Note that linking controls to risks is handled via the **Risks API**.

## Authentication

All endpoints require Token-based authentication: `Authorization: Token <your_auth_token>`

---

## Core Endpoints (CRUD)

* **`POST /api/controls/`**
  * **Action:** Creates a new control in the library.
  * **Permissions:** `Risk Officer` only.
  * **Default Behavior:** The control is created as `ACTIVE` (`is_active=True`) by default unless specified otherwise.
  * **Validation:** Fails if the user is a Manager or Employee.
  * **Response Context:** Includes computed permissions and usage metadata.

* **`GET /api/controls/`**
  * **Action:** Lists controls visible to the authenticated user.
  * **Permissions:** Any authenticated user.
  * **Query Logic:**
      * **Risk Officer:** Sees all controls (Active/Inactive) in their Business Unit.
      * **Manager/Employee:** Sees `ACTIVE` controls in their Business Unit + any controls linked to their risks.
  * **Query Parameters (Filtering):**
      * `is_active`: Boolean (`true`/`false`).
      * `control_type`: `PREVENTIVE`, `DETECTIVE`, `CORRECTIVE`.
      * `control_nature`: `MANUAL`, `AUTOMATED`, `HYBRID`.
      * `business_unit`: ID of the business unit.
      * `search`: Text search on title and description.

* **`GET /api/controls/{id}/`**
  * **Action:** Retrieves a single control.
  * **Response Context:** Includes computed permissions and usage metadata:
      * `permissions`: `{"can_edit": bool, "can_deactivate": bool}`.
      * `linked_risks_count`: Total number of risks using this control.
      * `active_risks_count`: Number of `ACTIVE` risks using this control.

* **`PATCH /api/controls/{id}/`**
  * **Action:** Updates control attributes (Description, Effectiveness, Frequency).
  * **Permissions:** `Risk Officer` only.
  * **Validation (Deactivation):** If setting `is_active=False`, the system checks for dependencies. The request **fails (400 Bad Request)** if the control is linked to any `ACTIVE` risks.
  * **Response Context:** Includes computed permissions and usage metadata.

* **`DELETE /api/controls/{id}/`**
  * **Action:** Hard delete.
  * **Permissions:** **None.**
  * **Behavior:** Always returns `403 Forbidden` with a message instructing to use Deactivation (`PATCH is_active=False`) instead.

---

## Field Reference

### Control Types
* `PREVENTIVE`: Stops errors or irregularities from occurring.
* `DETECTIVE`: Identifies errors or irregularities after they occur.
* `CORRECTIVE`: Remedial action taken to correct an error. Mostly covered by Measures module, should be avoided.

### Control Nature
* `MANUAL`: Performed entirely by humans.
* `AUTOMATED`: Performed entirely by systems.
* `HYBRID`: IT-Dependent Manual.

### Effectiveness
* **Scale:** 1 (Ineffective) to 5 (Highly Effective).
* **Scope:** Represents **Design Effectiveness** (how well the control *should* work in theory). Operational effectiveness is deferred for later, once business decides to start control testing process.