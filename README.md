# Operational Risk Management (ORM) Platform API

This repository contains the backend API for a custom-built [Operational Risk Management (ORM)](https://jfrog.com/learn/devsecops/operational-risk-management/) platform. Developed with Django and Django Rest Framework, this system provides a robust, secure, and maintainable foundation for managing the complete operational risk lifecycle: Incidents (Loss Events), Risks, Controls, Measures, and Key Risk Indicators (KRIs).

In simple terms, **Incidents** module tracks "*what went wrong and why*" and **Measures** define "*how we fix it*", "_who is responsible_" and "_when it will be completed_". 
The **Risks** module describes "_what could potentially go wrong_" and links the elements together.
**Controls** specify "_how we prevent those potential issues_", while **KRIs** consistently measure "_room's temperature_" - early signals indicating that risk levels are rising.

This project is built on a modular monolithic Django DRF backend, following **Domain-Driven Design** principles and emphasizing a clean **Service Layer architecture** within each module to separate complex business logic from the interface. This layered design ensures the platform is testable, maintainable, and can be extended to future modules, such as Risks or Controls, with clarity. Additionally, this approach minimizes dependency on Django REST Framework, allowing for the portability of service and domain layers to other frameworks or shift to microservices if needed.

This project is based on [Oprisk database project](https://github.com/lugres/oprisk-database) - a structured relational database that enables risk managers to record and analyze incidents (loss events), define and assess risks, manage controls and mitigation measures, and monitor key risk indicators (KRIs).

## Project Scope & Core Entities

This platform is designed to be the single source of truth for all operational risk activities.

### Planned Modules

The architecture is designed to support the progressive addition of all core ORM entities:
* **Incidents:** A system for registering and processing operational risk incidents (loss events), which features an advanced, role-based workflow. ✔️
* **Risks:** A central register of operational risks, with inherent/residual assessments. ✔️
* **Controls:** A library of controls to mitigate risks. ✔️
* **Measures:** A log of corrective actions, with deadlines and owners, linked to Incidents or Risks. ✔️
* **Key Risk Indicators (KRIs):** A system for monitoring metrics against defined thresholds. 🔜
* **Linkage:** Full many-to-many relationships between entities (e.g., `incident_risk`, `risk_control`). ✔️

Here’s a simplified entity relationship diagram with the main actors, their actions, and their interconnections:
![ER Diagram](diagram.png)

### ⛈️ ⚡️ 🔍 Incidents Management Module

The Incidents module serves as the organization's system of records for operational loss events (incidents), providing a rigorous, auditable path from initial discovery to final regulatory reporting. It is built on a **Data-Driven Workflow Engine** that enforces a strict separation of duties between **Employees** (Reporting), **Managers** (Review), and **Risk Officers** (Validation). Key capabilities include:
* **5-Stage State Machine:** A formal, role-based lifecycle (`DRAFT` -> `PENDING_REVIEW` -> `PENDING_VALIDATION` -> `VALIDATED` -> `CLOSED`) ensures every loss event undergoes hierarchical analysis and data enrichment.
* **Hybrid Taxonomy:** Simplifies data entry for front-line staff using easy to understand "Simplified Event Types" (e.g., "Fraud", "IT / Data / Cyber") that automatically map to complex regulatory **Basel Event Types** for regulatory reporting.
* **Intelligent Notification Routing:** A predicate-based rules engine that dynamically triggers async notifications for high-impact or specific risk-type incidents to specialized teams (e.g., alerting Fraud team immediately once Fraud incident is registered) without disrupting the baseline workflow (employee → manager → risk team).
* **Dynamic Data Governance:** Field-level security and requirement rules are configuration-driven, enforcing progressive data disclosure (e.g., financial impact data is required for Validation but optional for Drafts) and locking sensitive fields based on the incident's status and user role.
* **SLA Management:** Automated calculation of due dates (draft_due_at, review_due_at) ensures timely processing of loss events.

### ⚙️ ➡ ✅ = ☔️ Measures Module (Corrective Actions)

This module manages the lifecycle of corrective and preventive actions. Measures can be linked to Incidents and Risks to track remediation. 
* It features its own auditable, four-stage workflow (`OPEN` → `IN_PROGRESS` → `PENDING_REVIEW` → `COMPLETED`), ensuring that actions are verified by a Risk Officer before closure. 
* The API provides dedicated endpoints for state transitions, linking, and logging evidence, with dynamic permissions that lock key fields (like deadline) once work is in progress.

### ⚠️ ⚡️ 🔍 Risks Module (RCSA)

The Risks module implements a robust **Risk and Control Self-Assessment (RCSA)** engine, serving as the central register for operational risks. It features a strict **4-state workflow** (`DRAFT` → `ASSESSED` → `ACTIVE` → `RETIRED`) that enforces segregation of duties between **Managers** (Risk Owners) and **Risk Officers** (Validators). Key capabilities include:
* **Workflow Engine:** Explicit validation checkpoints where Risk Officers must approve inherent/residual scores and Basel classifications before a risk becomes Active.
* **Dual Taxonomy:** Supports simplified internal risk categories mapped to regulatory **Basel Event Types**.
* **Contextual Logic:** Dynamic field-level security that locks specific fields based on the risk's current status and the user's role.
* **Scoring Engine:** Automated calculation of Inherent and Residual risk scores based on Likelihood × Impact matrices.
* **Interconnectivity:** Bi-directional linking with **Incidents** (realized risks), **Measures** (corrective risk mitigations) and **Controls** (preventive mitigations, to be developed).

### 🛡️ Controls Module

This module serves as a centralized repository for the organization's defense mechanisms. It is built on a "Library" architecture rather than a transactional workflow, focusing on reusability and standardization.
* **Centralized Library**: A single source of truth for preventive, detective, and corrective controls, avoiding duplication across business units.
* **Segregation of Duties**: Only **Risk Officers** can create or modify the library, while **Managers** consume controls to mitigate their specific risks.
* **Integrity Logic**: Enforces strict dependency rules—controls cannot be deactivated or deleted if they are currently linked to any active risks.
* **Integration**: Provides the foundational "Defense" layer for the RCSA process, allowing controls to be linked to Risks with specific mitigation notes.

## Key Technical Features - Incidents Module

* **Multi-Stage Incident Workflow:** A state machine that manages an incident's progression (e.g., `DRAFT` -> `PENDING_REVIEW` -> `PENDING_VALIDATION` -> `VALIDATED` -> `CLOSED`).
* **Role-Based State Transitions:** A data-driven ruleset (`AllowedTransition` model) that defines *which* role (e.g., Manager, Risk Officer) can perform *which* transition.
* **Dynamic SLA Calculation:** Automatic calculation and recalculation of `..._due_at` timestamps (e.g., `review_due_at`, `validation_due_at`) every time an incident enters a new state, with old timers being cleared.
* **Dynamic Field Validation:** A data-driven ruleset (`IncidentRequiredField` model) that enforces progressive data completeness. An incident cannot be "submitted" without filling in all fields required for the "pending review" state.
* **Dynamic Field-Level Security:** A dynamic serializer (`IncidentUpdateSerializer`) that implements progressive disclosure. Based on the user's role and the incident's current status, fields are dynamically made `read_only` to prevent unauthorized edits.
* **Asynchronous Notification Routing:** A flexible routing engine that triggers asynchronous notifications to specialist teams (e.g., Fraud, IT) based on incident data, *without* interrupting the primary ownership workflow.
* **Unified Permission Architecture:** A 3-layer security model (Data Segregation, Action Authorization, and Domain Rule Validation) for defense-in-depth.

## 3-Layer Architectural Pattern (Incidents Module example)

This project strictly follows a 3-layer architectural pattern to manage complexity:

1.  **Interface Layer (Views):** Thin `ViewSet` is responsible for HTTP handling, authentication, and permission checks.
2.  **Application Layer (Services):** Orchestrates business tasks. This is where multiple components are coordinated (e.g., "submit an incident" means *validating fields*, *running workflow*, *setting SLA*, and *assigning a user*).
3.  **Domain Layer (Workflow):** Pure, isolated Python modules that contain the core business rules (e.g., `is_transition_allowed?`).

This separation ensures that complex business logic is not coupled to the Django framework or the HTTP interface, making it highly maintainable and testable.

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

## Documentation

For a deeper dive into the system's design and business rules, please see the following documents:

* **[Project Architecture (explained based on Incidents module)](./docs/architecture.md)**: A detailed breakdown of the 3-layer architectural pattern, permission models, and notification system.

### Documentation - Incidents module

* **[Incidents Workflow Rules](./docs/incident_workflow_rules.md)**: A complete specification of the incident state machine, SLA logic, and dynamic field rules.
* **[Incidents API Contracts](./docs/incident_api_contracts.md)**: High-level documentation for the main Incidents API endpoints and workflow actions.
* **[Business Requirements Document (BRD) for the Incidents module](./docs/business_requirements_documents/incidents_design_specs_detailed.md)**: Describes functional, technical, and architectural requirements for the Incidents module, as well as an analysis of some architectural options considered.

### Documentation - Measures module

* **[Measures Workflow Rules](./docs/measure_workflow_rules.md)**: A complete specification of the measure state machine, SLA logic, and dynamic field rules.
* **[Measures API Contracts](./docs/measure_api_contracts.md)**: High-level documentation for the main Measures API endpoints and workflow actions.
* **[Architecture Decision Record (ADR) document for permission enforcement strategy in Measures](./docs/architectural_decision_records/001_adr_measures_permissions.md)**: Outlines how a robust permission enforcement mechanism is implemented in the Measures module within Service-Layer Gateway Pattern, and explains why DRF-native permission classes were not used.

### Documentation - Risks module

* **[Risks Workflow Rules](./docs/risks_workflow_rules.md)**: A complete specification of the risk state machine, SLA logic, and dynamic field rules.
* **[Risks API Contracts](./docs/risks_api_contracts.md)**: High-level documentation for the main Risks API endpoints and workflow actions.
* **[Business Requirements Document (BRD) for the Risks module](./docs/business_requirements_documents/risk_workflow_design_specs.md)**: Presents an analysis of different options considered for a Risk workflow model, and explains what was finally selected and why.

### Documentation - Controls module

* **[Controls Workflow Rules](./docs/controls_workflow_rules.md)**: A complete specification of the business logic and lifecycle rules for controls (no state machine - a library of assets).
* **[Controls API Contracts](./docs/controls_api_contracts.md)**: High-level documentation for the main Controls API endpoints (linking is in Risks).
* **[Business Requirements Document (BRD) for the Controls module, detailed analysis](./docs/business_requirements_documents/controls_design_specs_detailed.md)**: Presents an analysis of different options considered for the Controls app, including code organization, workflows, data models, and explains what was finally selected and why.
* **[Business Requirements Document (BRD) for the Controls module, Executive Summary](./docs/business_requirements_documents/controls_design_specs_exec_summary.md)**: Presents a clear development path to follow for the Controls app; based on the detailed analysis of pros and cons in the previous BRD.