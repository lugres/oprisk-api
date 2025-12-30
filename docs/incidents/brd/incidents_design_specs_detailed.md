# Incidents Module Business Requirements Document

**Document Type:** Business Requirements Document  
**Project:** Operational Risk Management Platform - Incidents Module  
**Version:** 2.0 (Implementation & Architecture Aligned)  
**Date:** December 10, 2025  
**Status:** Implementation Complete  

---

## Executive Summary

### Purpose
This document defines the functional, technical, and architectural requirements for the **Incidents (Loss Data)** module. This module serves as the foundation for the Operational Risk Management (ORM) framework, enabling the organization to capture, validate, and quantify operational loss events.

### Decision Summary
**Selected Architecture:** * **Workflow:** 5-Stage Validation (`DRAFT` → `PENDING_REVIEW` → `PENDING_VALIDATION` → `VALIDATED` → `CLOSED`) to enforce a "Four-Eyes" review principle.
* **Routing:** Database-driven Predicate Engine (JSON rules) rather than hard-coded logic.
* **Taxonomy:** Domain-Specific implementation (`SimplifiedEventType` resides in `incidents` app) rather than a generic reference model.

**Key Rationale:**
The architecture prioritizes **Configuration over Hard-Coding**. By implementing validation rules (`IncidentRequiredField`), field security (`IncidentEditableField`), and routing logic (`IncidentRoutingRule`) as database models, the system allows the Risk Department to adapt governance rules without requiring engineering deployment cycles.

---

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Business Context & Roles](#2-business-context--roles)
3. [Architectural Options & Decision Analysis](#3-architectural-options--decision-analysis)
4. [Workflow & Lifecycle Specification](#4-workflow--lifecycle-specification)
5. [Functional Requirements](#5-functional-requirements)
6. [Data Model Specifications](#6-data-model-specifications)
7. [Intelligent Routing & SLA](#7-intelligent-routing--sla)
8. [Integration & Segregation](#8-integration--segregation)

---

## 1. Problem Statement

### Business Need
Operational loss data is the critical input for capital modeling (Basel II/III), regulatory reporting, and risk trending. The organization currently lacks a unified system to:
* Capture loss events immediately upon discovery by front-line staff.
* Enforce a standardized, multi-layer review process to validate financial impact amounts.
* Ensure incidents are mapped to the correct regulatory categories while keeping the UI simple for employees.
* Route high-severity incidents (e.g., large fraud) to specialized teams immediately.

### Success Criteria
1.  **Data Quality:** Prevent incidents from moving to the `VALIDATED` stage if key financial data (Gross/Net Loss) is missing.
2.  **Segregation of Duties:** Prevent the Creator from validating their own incident.
3.  **Simplify Reporting:** Allow users to report incidents using terminology they understand, while maintaining regulatory compliance in the background.
4.  **Responsiveness:** Route high-risk events to Risk Officers immediately via a flexible rules engine.
5.  **Auditability and Timeliness:** Track every state change, review, and validation step with timestamps and user references.

---

## 2. Business Context, User Roles & Permissions

The application implements strict Role-Based Access Control (RBAC) augmented by Object-Level Permissions.

### 2.1. Main User Roles

* **Employee (The Reporter):** Front-line staff who discover issues. Can only create `DRAFT` incidents and submit them. No visibility into other units.
* **Permissions:**
    * **Create:** Can create new incidents in `DRAFT` status.
    * **View:** Can only view incidents *they* created.
    * **Edit:** Can edit detailed fields only while the incident is in `DRAFT`. Once submitted, they lose write access to prevent tampering.
    * **Action:** Can perform `submit` action.

* **Manager (The Reviewer):** Team leads. Responsible for operational review (`PENDING_REVIEW` → `PENDING_VALIDATION`). Can view incidents from their direct reports.
* **Permissions:**
    * **View:** Can view incidents created by themselves OR their direct reports (hierarchical visibility).
    * **Review:** Responsible for moving incidents from `PENDING_REVIEW` to `PENDING_VALIDATION`.
    * **Edit:** Can modify description and classification during the review phase to improve data quality.
    * **Return:** Can return incidents to `DRAFT` if information is insufficient.

* **Risk Officer (The Validator):** Centralized risk professionals. Responsible for taxonomy validation, financial verification, and final closure (`VALIDATED` → `CLOSED`). Can view all incidents in their Business Unit.
* **Permissions:**
    * **View:** Can view **ALL** incidents within their assigned Business Unit.
    * **Validate:** Responsible for final financial validation (`PENDING_VALIDATION` → `VALIDATED`).
    * **Close:** Responsible for final closure (`VALIDATED` → `CLOSED`).
    * **Override:** Can return incidents to `PENDING_REVIEW` if the Manager's review was inadequate.
    * **Routing:** Receives notifications for high-priority incidents via the Routing Engine.

### 2.2. The "Four-Eyes" Principle

The system is designed to enforce a specific chain of custody:
`Detector (Employee)` → `Reviewer (Manager)` → `Validator (Risk Officer)`
This ensures that no single individual can enter and finalize a loss event without oversight.

---

## 3. Architectural Options & Decision Analysis

During the design phase, several architectural approaches were evaluated. This section documents the rationale behind the selected implementations.

### Decision 1: Workflow State Machine Complexity

**Option A: 3-State Workflow (`DRAFT` → `OPEN` → `CLOSED`)**
* *Pros:* Simple to implement; fast for users.
* *Cons:* Lacks granularity. Does not distinguish between a Manager's operational review and a Risk Officer's regulatory validation.
* *Verdict:* **Rejected.**

**Option B: 5-Stage Validation Workflow (Selected)**
* *Structure:* `DRAFT` → `PENDING_REVIEW` (Manager) → `PENDING_VALIDATION` (Risk Officer) → `VALIDATED` (Final State) → `CLOSED`.
* *Pros:* * Enforces segregation of duties (Manager vs. Risk Officer).
    * Allows "Return to Draft" and "Return to Review" loops for data correction.
    * Clearly delineates "Operational Data" (Manager's scope) from "Regulatory Data" (Risk Officer's scope).
* *Verdict:* **Selected.** This model aligns with the regulatory requirement for independent validation of loss data.

### Decision 2: Simplified Taxonomy Location

**Option A: Generic Reference App**
* *Concept:* Place `SimplifiedEventTypeRef` in the `references` app alongside `Country` and `Currency`.
* *Pros:* Centralizes all lookup tables.
* *Cons:* Low cohesion. `SimplifiedEventTypeRef` is tightly coupled to the Incident creation flow and has specific mapping logic (`SimplifiedToBaselEventMap`) that is irrelevant to other modules.

**Option B: Domain-Specific Location (Selected)**
* *Concept:* Place `SimplifiedEventTypeRef` inside the `incidents` app.
* *Pros:* **High Cohesion.** The model is owned by the domain that uses it. It allows the `incidents` module to be more self-contained.
* *Verdict:* **Selected.** We prioritized domain cohesion over generic centralization.

### Decision 3: Routing Logic Implementation

**Option A: Hard-Coded Logic in Services**
* *Concept:* Write Python `if/else` statements in `services.py` (e.g., `if gross_loss > 10000: notify_fraud_team()`).
* *Pros:* Fast to write initially. Easy to unit test.
* *Cons:* **Rigid.** Changing a threshold requires a code deployment. Business users (Risk Officers) cannot adjust rules.

**Option B: Database-Driven Predicate Engine (Selected)**
* *Concept:* Create an `IncidentRoutingRule` model with a `JSONField` for predicates (e.g., `{"min_amount": 10000}`). The `routing.py` service evaluates these rules dynamically.
* *Pros:* **Flexible.** Risk Officers can create new routing rules via the Admin interface (e.g., "Route all IT Failures to the Cyber Team") without engineering support.
* *Verdict:* **Selected.** The complexity of implementation is outweighed by the operational flexibility it provides.

### Decision 4: Field-Level Governance

**Option A: Serializer Logic**
* *Concept:* Define `read_only_fields` inside `IncidentUpdateSerializer`.
* *Pros:* Standard Django REST Framework pattern.
* *Cons:* Hard to visualize the matrix of [Role x Status x Field]. Maintenance becomes difficult as the matrix grows.

**Option B: Configuration Models (Selected)**
* *Concept:* Create `IncidentRequiredField` and `IncidentEditableField` models.
* *Pros:* **Transparency.** The governance rules are data, not code. We can query "Which fields are required for Validation?" directly from the database.
* *Verdict:* **Selected.** This allows for progressive data disclosure (requiring more fields as the incident matures) to be managed dynamically.

---

## 4. Workflow & Lifecycle Specification

The Incident entity follows a rigid, 5-step state machine orchestrated by `services.py` and validated by `workflows.py`.

### State Transitions Matrix

| From Status | To Status | Action | Actor | Validation Logic (Prerequisites) |
| :--- | :--- | :--- | :--- | :--- |
| **DRAFT** | **PENDING_REVIEW** | `submit` | Creator | • SLA `draft_due_at` active.<br>• Must satisfy `IncidentRequiredField` for `PENDING_REVIEW`. |
| **PENDING_REVIEW** | **PENDING_VALIDATION** | `review` | Manager | • Actor must be Creator's Manager.<br>• Must satisfy requirements for `PENDING_VALIDATION`. |
| **PENDING_REVIEW** | **DRAFT** | `return_to_draft` | Manager | • **Reason** required (logged to notes).<br>• Resets SLA. |
| **PENDING_VALIDATION** | **VALIDATED** | `validate` | Risk Officer | • Financials (`gross_loss`, `net_loss`) must be populated.<br>• Basel Category mapped.<br>• SLA `validation_due_at` active. |
| **PENDING_VALIDATION** | **PENDING_REVIEW** | `return_to_review` | Risk Officer | • **Reason** required.<br>• Returns responsibility to Manager<br>• Resets `review_due_at` SLA. |
| **VALIDATED** | **CLOSED** | `close` | Risk Officer | • Final data check and administrative closure. |

### Visual Workflow
```mermaid
graph LR
    D[DRAFT] -->|submit| PR[PENDING_REVIEW]
    PR -->|review| PV[PENDING_VALIDATION]
    PV -->|validate| V[VALIDATED]
    V -->|close| C[CLOSED]
    PR -->|return_to_draft| D
    PV -->|return_to_review| PR
```

---

## 5. Functional Requirements

### FR-1: Incident Creation & Hybrid Taxonomy

To lower the barrier to reporting, the system abstracts complex regulatory taxonomies.

  * **Simplified Event Types:** The user selects from a list of `SimplifiedEventTypeRef` (e.g., "Fraud", "IT / Data / Cyber").
  * **Automated Mapping:** The system maintains a `SimplifiedToBaselEventMap`. On save/submit, the backend infers the `BaselEventType`.
  * **Validation:** Creation is lightweight. Only `title`, `business_unit`, and `simplified_event_type` are strictly required to save a Draft.

### FR-2: Progressive Data Disclosure

Data requirements increase as the incident matures.

  * **Draft Stage:** Focus on qualitative data ("What happened?" - title, description, etc.).
  * **Validation Stage:** Focus on quantitative data ("How much did we lose?" - loss data).
  * **Implementation:** `services.validate_incident` iterates through `IncidentRequiredField` records for the target status and raises `RequiredFieldsError` if data is missing.

### FR-3: Dynamic Field Security

To ensure data integrity, fields lock down as the incident progresses.

  * **Logic:** The `IncidentUpdateSerializer` initializes by querying `IncidentEditableField` based on the user's role and the incident's status. The `IncidentEditableField` model defines exactly which role can edit which field at which status.
  * **Behavior Example:**
      * A **Manager** can edit `gross_loss` during `PENDING_REVIEW`.
      * Once moved to `PENDING_VALIDATION`, `gross_loss` becomes **Read-Only** for the Manager and Writable only for the **Risk Officer**.
      * Once `VALIDATED`, the incident is effectively immutable (Read-Only for everyone).

### FR-4: Financial Tracking

The module must support granular loss tracking:

 * **Gross Loss:** Total estimated loss before recovery.
 * **Recovery Amount:** Amount recovered via insurance or direct recovery.
 * **Net Loss:** Calculated (Gross - Recovery).
 * **Currency Code:** ISO code for the loss amounts.
 * **Near Miss:** Boolean flag for events with zero actual loss but high potential impact.

---

## 6. Data Model Specifications

### Core Entities

#### `Incident`

The central aggregate root.

  * **Identity:** `title`, `description`, `incident_date`, `discovery_date`.
  * **Categorization:** `simplified_event_type`, `basel_event_type`.
  * **Context:** `business_unit`, `business_process`, `product`.
  * **Financials:** `gross_loss_amount`, `recovery_amount`, `net_loss_amount` (computed), `currency_code`.
  * **Workflow:** `status` (FK), `assigned_to` (User).
  * **SLA:** `draft_due_at`, `review_due_at`, `validation_due_at`.
  * **Audit:** `created_by`, `reviewed_by`, `validated_by`, `closed_by`.

#### `IncidentRoutingRule`

Defines logic for the Routing Engine.

  * `predicate`: JSONField with rules (e.g., `{"min_amount": 10000, "simplified_event_type_id": 3}`).
  * `route_to_role`: Role to notify if matched.
  * `route_to_bu`: Business Unit to notify.
  * `priority`: Integer (evaluation order).

#### `IncidentRequiredField` & `IncidentEditableField`

Configuration tables that drive the dynamic validation and security logic described in FR-2 and FR-3.

 ##### `IncidentRequiredField` - Configuration table for validation logic.
 * `status`: The status where the requirement is enforced.
 * `field_name`: The specific field on the Incident model that must be non-null.
 * `required`: Boolean.

 ##### `IncidentEditableField` - Configuration table for field-level security.
 * `status`: The status where editing is allowed.
 * `role`: The role allowed to edit.
 * `field_name`: The specific field that is writable.

### Integration Points

  * **Incident ↔ Causes:** Many-to-Many via `IncidentCause`. Tracks root causes (People, Process, System, External).
  * **Incident ↔ Risks:** Many-to-Many (`IncidentRisk`). An incident is the realization of a Risk.
  * **Incident ↔ Measures:** Many-to-Many (`IncidentMeasure`). An incident triggers corrective Measures.
  * **Incident ↔ Notifications:** The Routing Engine triggers entries in the Notifications module, to be delivered in async mode by Celery.

---

## 7. Intelligent Routing & SLA

### 7.1. Predicate-Based Routing Engine

To handle high-severity events that require immediate attention outside the standard hierarchy, the `routing.py` service implements a rules engine.

**Trigger:** Executed during the `submit` (DRAFT → PENDING_REVIEW) and/or `review` (PENDING_REVIEW → PENDING_VALIDATION) transitions. Configured only for the latter for now to minimize information noise caused by mistakenly registered incidents by Employee and not confirmed by Manager.

**Logic:**

1.  Fetch all active `IncidentRoutingRule` records ordered by priority.
2.  Evaluate `rule.predicate` against the Incident instance.
      * *Supported Predicates:* `min_amount`, `business_unit_id`, `simplified_event_type_id`, `basel_event_type_id` (switched off for now).
3.  **Match Action:** If a match is found, generate a `Notification` for the target Role/BU.
4.  **Use Case:** Ensures the Fraud Team is alerted immediately about high-value fraud, even if the incident is currently sitting in a Manager's review queue.

### 7.2. SLA Tracking

Service Level Agreements timers are calculated dynamically upon state entry.

  * **Configuration:** `SlaConfig` table stores days allowed for each stage (e.g., `draft_days=7`).
  * **Calculation:**
      * `create_incident` → sets `draft_due_at` (Now + 7 days).
      * `submit` → clears `draft_due_at`, sets `review_due_at` (Now + 5 days).
      * `review` → clears `review_due_at`, sets `validation_due_at` (Now + 10 days).
  * **Reset Logic:** If an incident is returned (`return_to_draft`), the SLA timer for that specific stage is reset to the full allowance to give the user time to fix issues.

---

## 8. Integration & Segregation

### 8.1. Data Segregation
The module enforces strict visibility rules via `get_queryset` in `views.py`:
* **Employees** see only what they created.
* **Managers** see their own creations **AND** incidents created by users who report to them (`created_by__manager=user`).
* **Risk Officers** see everything within their Business Unit (`business_unit=user.business_unit`).

### 8.2. Module Interconnectivity
The Incidents module acts as the "Realization" point for other modules:
* **Risks:** Incidents are linked to Risks to update the historical loss profile of a risk scenario.
* **Measures:** Incidents spawn Measures (corrective actions) to prevent recurrence.
* **Notifications:** The Routing Engine utilizes the Notifications module and Celery to alert stakeholders in async mode about critical incidents.

---

## Document Control

### Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-03 | [Your Name] | Initial Requirements |
| 2.0 | 2025-12-10 | [Your Name] | Updated to reflect architectural decisions (Routing Engine, 5-Stage Workflow) |

**End of Document**