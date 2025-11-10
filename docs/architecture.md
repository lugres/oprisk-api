# Project Architecture

This document outlines the high-level architecture of the ORM platform, focusing on the tech stack, separation of concerns, and permission model.

## 1. High-Level System Design

The platform is designed as a **monolithic Django backend** providing a RESTful API. This approach was chosen to simplify development, testing, and iteration for the MVP. A planned **React frontend** will consume this API.

* **Backend:** Django & Django Rest Framework (DRF);
* **Database:** PostgreSQL as the single source of truth;
* **Asynchronous Tasks:** Celery with a Redis broker (planned);
* **Deployment:** The entire stack is containerized with Docker.

This layered, modular monolith provides a clear path for future scaling, allowing well-defined components to be potentially extracted into microservices if needed.

## 2. The 3-Layer Architectural Pattern

To manage complex business logic, the application is divided into three distinct layers.

!

### 2.1. Interface Layer (Views / `views.py`)

* **Responsibility:** Handles HTTP requests and responses.
* **Components:** Django Rest Framework `ViewSet`s.
* **Logic:** This layer is intentionally "thin." It is only responsible for:
    * Authenticating the user.
    * Running coarse-grained permission checks (Layer 2 Security).
    * Deserializing request data.
    * Calling a single function in the Service Layer.
    * Serializing the response.
* **Rule:** This layer **never** contains business logic.

### 2.2. Application Layer (Services / `services.py`)

* **Responsibility:** Orchestrates a single business use case or "task."
* **Components:** Functions (e.g., `review_incident(...)`).
* **Logic:** This layer contains no core business rules but coordinates all the pieces needed to fulfill a request. A typical function will:
    1.  **Validate:** Check required fields for the action (`_validate_required_fields`).
    2.  **Authorize:** Call the Domain Layer to check business rules (`validate_transition`).
    3.  **Execute:** Perform the state change and apply all side-effects (e.g., set new status, calculate new SLA, `incident.save()`).
    4.  **Notify:** Trigger any parallel workflows (e.g., create a `Notification` record).
* **Rule:** This layer is the *only* layer that should talk to both the Interface and Domain layers.

### 2.3. Domain Layer (Workflow / `workflow.py`)

* **Responsibility:** Contains the pure, isolated business rules of the organization.
* **Components:** Pure Python functions (e.g., `validate_transition(...)`).
* **Logic:** This layer is "Django-unaware." It knows nothing about databases or HTTP. It simply accepts Python data (like `from_status`, `to_status`, `role_name`) and returns a result or raises a business exception (e.t., `InvalidTransitionError`).
* **Rule:** This layer *never* imports from Django models or views.

---

## 3. Asynchronous Notification System

The notification system is designed as a robust, asynchronous queue to avoid blocking the main API.

1.  **`Notification` (The "Event"):** When a service function needs to send an alert (e.g., `review_incident` triggers a route to the Fraud team), it creates a *single* `Notification` row in the database. This row has `status='queued'` and defines *what* happened (`entity_id`, `event_type`) and *who* it's intended for (`recipient_role`).
2.  **`UserNotification` (The "Inbox"):** A separate Celery task (planned) reads this queue. It "fans out" the single `Notification` event by creating multiple `UserNotification` rows — one for each user who belongs to the `recipient_role`. This table tracks the `is_read` state for each individual user, powering the "red bell" UI.
3.  **Delivery (Planned):** A second set of Celery tasks will handle the actual delivery (Email, Slack) based on the `Notification` record's `method` and user preferences, tracking `attempts` and `last_error`.

This "queue-and-fan-out" model ensures that API requests are fast and that notifications are processed reliably in the background.

---

## 4. The Unified Permission Architecture

Security is applied in three distinct layers, providing defense-in-depth.

### Layer 1: Data Segregation (What can you *see*?)

* **Where:** `get_queryset()` in the `ViewSet`.
* **Purpose:** This is the foundational layer that defines the *universe of objects* a user is allowed to interact with. It's a data-scoping mechanism, not an action-authorization one.
* **Example:** "A Manager can see their own incidents + incidents from their direct reports. A Risk Officer sees all incidents in their Business Unit."

### Layer 2: Action Authorization (What can you *try* to do?)

* **Where:** `permission_classes` on the `ViewSet` or `@action` decorator.
* **Purpose:** This is the "gatekeeper" for a specific endpoint. It performs fast, coarse-grained checks on the user's *identity* or *role*.
* **Example:** `permission_classes=[IsAuthenticated, IsRoleRiskOfficer]` on the `validate` action. This check happens *before* any other logic runs.

### Layer 3: Domain Rule Authorization (Is this specific action *valid*?)

* **Where:** Inside the **Service Layer** (e.g., `validate_transition(...)`).
* **Purpose:** This is the final, fine-grained check. After passing Layers 1 & 2, this layer confirms if the action is valid according to specific **business rules** and the object's **current state**.
* **Example:** "A Manager (Role) is trying to `submit` (Action) their own incident (Object). Layers 1 & 2 pass. But the domain rule states only the 'Employee' role can perform the 'DRAFT' -> 'PENDING_REVIEW' transition. The request is denied."