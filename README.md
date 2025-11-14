# Operational Risk Management (ORM) Platform API

This repository contains the backend API for a custom-built Operational Risk Management (ORM) platform. Developed with Django and Django Rest Framework, this system provides a robust, secure, and maintainable foundation for managing the complete operational risk lifecycle: Incidents (Loss Events), Risks, Controls, Measures, and Key Risk Indicators (KRIs).

The current development focus is on the **Incident Management** module, which features an advanced, role-based workflow.

This project is built on a monolithic Django DRF backend, emphasizing a clean **Service Layer architecture** to separate complex business logic from the interface. This layered design ensures the platform is testable, maintainable, and can be extended to future modules (like Risks or Controls) with clarity.

This project is based on [Oprisk database project](https://github.com/lugres/oprisk-database) - a structured relational database that enables risk managers to record and analyze incidents (loss events), define and assess risks, manage controls and mitigation measures, and monitor key risk indicators (KRIs).

## Project Scope & Core Entities

This platform is designed to be the single source of truth for all operational risk activities.

### Incident Management

The first-built module manages the complete lifecycle of operational risk events. Its logic is governed by a sophisticated workflow engine that includes:
* A role-based, multi-stage state machine (e.g., `DRAFT` -> `PENDING_REVIEW` -> `VALIDATION`).
* Data-driven rules for transitions, required fields, and field-level editability.
* Automatic, state-based SLA timer calculation.
* Asynchronous, rule-based notification routing for awareness (e.g., alerting the Fraud team immediately once Fraud incident is registered).

### Measures & Corrective Actions (In Development)
This module manages the lifecycle of corrective and preventive actions. Measures can be linked to Incidents (and later, Risks) to track remediation. 
* It features its own auditable, four-stage workflow (OPEN → IN_PROGRESS → PENDING_REVIEW → COMPLETED), ensuring that actions are verified by a Risk Officer before closure. 
* The API provides dedicated endpoints for state transitions, linking, and logging evidence, with dynamic permissions that lock key fields (like deadline) once work is in progress.

### Planned Modules (Future Work)

The architecture is designed to support the progressive addition of all core ORM entities:
* **Risks:** A central register of operational risks, with inherent/residual assessments.
* **Controls:** A library of controls to mitigate risks.
* **Measures:** A log of corrective actions, with deadlines and owners, linked to Incidents or Risks.
* **Key Risk Indicators (KRIs):** A system for monitoring metrics against defined thresholds.
* **Linkage:** Full many-to-many relationships between all entities (e.g., `incident_risk`, `risk_control`).

## Key Features (Incident Module)

* **Multi-Stage Incident Workflow:** A state machine that manages an incident's progression (e.g., `DRAFT` -> `PENDING_REVIEW` -> `PENDING_VALIDATION` -> `VALIDATED` -> `CLOSED`).
* **Role-Based State Transitions:** A data-driven ruleset (`AllowedTransition` model) that defines *which* role (e.g., Manager, Risk Officer) can perform *which* transition.
* **Dynamic SLA Calculation:** Automatic calculation and recalculation of `..._due_at` timestamps (e.g., `review_due_at`, `validation_due_at`) every time an incident enters a new state, with old timers being cleared.
* **Dynamic Field Validation:** A data-driven ruleset (`IncidentRequiredField` model) that enforces progressive data completeness. An incident cannot be "submitted" without filling in all fields required for the "pending review" state.
* **Dynamic Field-Level Security:** A dynamic serializer (`IncidentUpdateSerializer`) that implements progressive disclosure. Based on the user's role and the incident's current status, fields are dynamically made `read_only` to prevent unauthorized edits.
* **Asynchronous Notification Routing:** A flexible routing engine that triggers asynchronous notifications to specialist teams (e.g., Fraud, IT) based on incident data, *without* interrupting the primary ownership workflow.
* **Unified Permission Architecture:** A 3-layer security model (Data Segregation, Action Authorization, and Domain Rule Validation) for defense-in-depth.

## Tech Stack & Architecture

This project is a monolithic Django application, containerized with Docker, and designed for a clean separation of concerns.

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend API** | Django, Django Rest Framework (DRF) | Serves a robust, secure, and versioned API. |
| **Database** | PostgreSQL | The single source of truth for all ORM data. |
| **Async Tasks** | Celery & Redis | For handling asynchronous tasks like sending email/Slack notifications and running scheduled SLA checks. |
| **Frontend (Planned)** | React + Tailwind | A responsive web client. (Mobile with React Native planned for future). |
| **Deployment** | Docker | Containerized for consistent development, testing, and production environments. |
| **CI/CD** | GitHub Actions | For automated linting and running the test suite on every push. |

## 3-Layer Architectural Pattern (Incident Module example)

This project strictly follows a 3-layer architectural pattern to manage complexity:

1.  **Interface Layer (Views):** Thin `ViewSet`s responsible for HTTP handling, authentication, and permission checks.
2.  **Application Layer (Services):** Orchestrates business tasks. This is where multiple components are coordinated (e.g., "submit an incident" means *validating fields*, *running workflow*, *setting SLA*, and *assigning a user*).
3.  **Domain Layer (Workflow):** Pure, isolated Python modules that contain the core business rules (e.g., `is_transition_allowed?`).

This separation ensures that complex business logic is not coupled to the Django framework or the HTTP interface, making it highly maintainable and testable.

## Documentation

For a deeper dive into the system's design and business rules, please see the following documents:

* **[Project Architecture](./docs/architecture.md)**: A detailed breakdown of the 3-layer architectural pattern, permission models, and notification system.
* **[Incident Workflow Rules](./docs/incident_workflow_rules.md)**: A complete specification of the incident state machine, SLA logic, and dynamic field rules.
* **[Incident API Contracts](./docs/incident_api_contracts.md)**: High-level documentation for the main Incident API endpoints and workflow actions.
* **[Measure Workflow Rules](./docs/measure_workflow_rules.md)**: A complete specification of the measure state machine, SLA logic, and dynamic field rules.
* **[Measure API Contracts](./docs/measure_api_contracts.md)**: High-level documentation for the main Measure API endpoints and workflow actions.
