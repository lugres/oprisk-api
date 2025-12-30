# Controls Module Business Requirements Document

**Document Type:** Business Requirements Document  
**Project:** Operational Risk Management Platform - Controls Module  
**Version:** 1.0  
**Date:** November 29, 2025  
**Author:** [Your Name/Team]  
**Status:** Draft - Pending Approval

---

## Executive Summary

### Purpose
This document defines the business requirements for the Controls module in the Operational Risk Management platform. Controls are policies, procedures, or mechanisms designed to prevent or detect operational risks before they materialize into loss events.

### Decision Summary
**Selected Architecture:** Separate Controls App with Phased Implementation

**Key Rationale:**
- Aligns with industry-standard GRC (Governance, Risk, Compliance) system architecture
- Maintains clean separation of concerns consistent with existing modules (incidents, measures, risks)
- Establishes controls as reusable infrastructure accessible across multiple risk domains
- Enables future extensibility for control testing, deficiency tracking, and attestation workflows
- Follows Django best practices where apps represent distinct domain concepts

### Scope for MVP (Phase 1)
**In Scope:**
- Control library (centralized catalog of controls)
- Basic control attributes (name, description, type, frequency, effectiveness design rating)
- Many-to-many linkage between risks and controls
- CRUD operations for controls (Risk Officer role)
- Control assignment to risks during RCSA workflow
- Read-only control visibility for Managers and Employees

**Out of Scope (Future Phases):**
- Control testing schedules and evidence management
- Operating effectiveness assessments (Phase 2)
- Control deficiency tracking and remediation
- Control attestation workflows
- Control-to-compliance-requirement mappings
- Automated control monitoring and alerting

---

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Business Context](#2-business-context)
3. [Architectural Options Analysis](#3-architectural-options-analysis)
4. [Domain Model](#4-domain-model)
5. [Control Effectiveness Philosophy](#5-control-effectiveness-philosophy)
6. [Module Placement Decision](#6-module-placement-decision)
7. [Functional Requirements](#7-functional-requirements)
8. [Data Model Specifications](#8-data-model-specifications)
9. [Integration with Risk Module](#9-integration-with-risk-module)
10. [User Roles and Permissions](#10-user-roles-and-permissions)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Appendix: Industry Standards Alignment](#appendix-industry-standards-alignment)

---

## 1. Problem Statement

### Business Need
Organizations require a structured approach to manage operational risk controls:

- **Centralized Control Library:** Maintain a single source of truth for all operational controls across the organization
- **Risk Mitigation Documentation:** Clearly document which controls mitigate which risks to demonstrate risk management rigor
- **Residual Risk Calculation:** Enable accurate residual risk assessment based on control effectiveness
- **Regulatory Compliance:** Support Basel II/III requirements for documenting control environments
- **Audit Trail:** Provide auditors with visibility into control design and risk-control mappings
- **Control Reusability:** Avoid duplicating control documentation across different risks and business units

### Current Situation
The platform currently has:
- **Risks Module:** Potential losses are documented and scored (inherent risk)
- **Incidents Module:** Actual loss events are tracked and analyzed
- **Measures Module:** Corrective and preventive actions are managed

**Gap:** No systematic way to document the **preventive/detective mechanisms** (controls) that reduce inherent risk to residual risk levels.

### Success Criteria
The Controls module will:
1. Provide a centralized control library accessible to all risk stakeholders
2. Enable Risk Officers to link controls to risks during RCSA approval workflow
3. Support calculation of residual risk based on control presence and effectiveness
4. Maintain consistency with industry operational risk management frameworks (COSO, Basel, ISO 31000)
5. Be implementable within 2-week MVP timeline as a focused, well-scoped module
6. Serve as foundation for future control testing and attestation features

---

## 2. Business Context

### What is a Control?

**Definition:** A control is a policy, procedure, practice, or organizational structure designed to provide reasonable assurance that business objectives will be achieved and undesired events will be prevented or detected and corrected.

**Characteristics:**
- **Embedded in Business Processes:** Controls are part of day-to-day operations, not one-off actions
- **Preventive or Detective:** Controls either stop risks from occurring or detect them quickly when they do
- **Ongoing:** Controls operate continuously or on regular schedules (daily, monthly, etc.)
- **Designed:** Controls have inherent design characteristics (manual vs. automated, frequency, etc.)

### Controls vs. Measures vs. Incidents

| Dimension | Control | Measure | Incident |
|-----------|---------|---------|----------|
| **Nature** | Preventive/Detective mechanism | Corrective/Preventive action | Loss event (realized risk) |
| **Lifecycle** | Ongoing, embedded in process | Time-bound project with start/end | One-time occurrence |
| **Timing** | Operates before/during risk | Created after incident or during risk review | Already happened |
| **Example** | "Dual signature required for payments > $5K" | "Implement dual signature by Q2" | "Unauthorized payment of $50K" |
| **Status** | Active / Inactive | Open / In Progress / Completed | Draft / Confirmed / Closed |
| **Ownership** | Control Owner (operates daily) | Measure Owner (delivers action) | Incident Owner (investigates) |

**Key Relationships:**
- **Controls → Risks:** Controls **mitigate** risks (many-to-many: one control can address multiple risks; one risk requires multiple controls)
- **Measures → Risks:** Measures are created to **strengthen controls** or **reduce risks** identified during assessments
- **Measures → Controls:** A measure might **implement** or **improve** a control (e.g., "Implement segregation of duties control by Q3")
- **Incidents → Risks:** Incidents are **realizations** of risks that materialized despite controls
- **Incidents → Controls:** Incidents may reveal **control failures** or **gaps** that need remediation

### RCSA (Risk and Control Self-Assessment) Process

Controls are integral to the RCSA workflow:

```
1. Identify Risk
   ↓
2. Assess Inherent Risk (likelihood × impact WITHOUT controls)
   ↓
3. Identify Existing Controls
   ↓
4. Assess Control Effectiveness
   ↓
5. Calculate Residual Risk (likelihood × impact AFTER controls)
   ↓
6. Approve Risk for Register (if residual risk is acceptable)
   ↓
7. Create Measures (if residual risk too high or control gaps identified)
```

**BRD Reference Point:** Per the Risk Workflow Design Specification (Section 7, Field Requirements):
- **ASSESSED → ACTIVE transition** requires: "At least one control must be linked"
- Risk Officer links controls during the validation phase before approving a risk

### Industry Standards Context

**COSO Framework (Committee of Sponsoring Organizations):**
- Controls are one of the five components of internal control
- Emphasizes control environment, risk assessment, control activities, information & communication, monitoring

**Basel II/III (Banking Regulation):**
- Requires banks to identify operational risks and document control environments
- Links capital requirements to quality of risk management and controls

**ISO 31000 (Risk Management Standard):**
- Controls are "risk treatments" that modify risk levels
- Distinguishes between risk identification, assessment, and treatment (controls)

**Three Lines of Defense Model:**
- **1st Line:** Business units own and operate controls
- **2nd Line:** Risk management validates control design and monitors effectiveness
- **3rd Line:** Internal audit provides independent assurance on controls

---

## 3. Architectural Options Analysis

### Overview
Three architectural approaches were evaluated for implementing controls functionality:

1. **Separate Controls App** (Recommended)
2. Controls within Risks App
3. Controls within Measures App

### Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Conceptual Clarity** | Critical | Does the structure match domain concepts? |
| **Industry Alignment** | Critical | Does it match how enterprise GRC systems are built? |
| **Scalability** | High | Can it grow to support control testing, deficiencies, attestation? |
| **Code Maintainability** | High | Clear boundaries, easy to navigate |
| **MVP Feasibility** | High | Can it be delivered within 2-week timeline? |
| **Reusability** | Medium | Can controls be used beyond just risks? |
| **Team Workflow** | Medium | Clear ownership, minimal merge conflicts |

### Option 1: Separate Controls App ✅ RECOMMENDED

**Structure:**
```
controls/
├── models.py           # Control, ControlType enums
├── serializers.py      # Control CRUD serializers
├── views.py            # Control API endpoints
├── services.py         # Control business logic
├── filters.py          # Control filtering/search
├── tests/
│   └── test_api.py     # Control functionality tests
└── migrations/
```

**Pros:**
- ✅ **Industry Standard:** Matches RSA Archer, ServiceNow GRC, MetricStream, IBM OpenPages architecture
- ✅ **Clean Separation:** Controls are distinct domain concept separate from risks, incidents, measures
- ✅ **Scalability:** Easy to add control testing, deficiencies, attestation in future
- ✅ **Reusability:** Control library can be referenced from multiple contexts (risks, processes, compliance)
- ✅ **Team Organization:** Different developers can own different apps, clear code review boundaries
- ✅ **Testing Isolation:** Control tests don't bloat risk test suite

**Cons:**
- ⚠️ Initial implementation appears lightweight (~10 fields for MVP)
- ⚠️ Cross-app imports required (`from controls.models import Control`)
- ⚠️ Migration dependencies between apps need management

**Alignment with Existing Architecture:**
The platform has already established the pattern of separate apps for distinct domain concepts:
- `incidents/` - What happened (loss events)
- `measures/` - What we're doing about it (actions)
- `risks/` - What could happen (potential losses)
- `controls/` - What prevents it (mitigations) ← Natural fit

**Industry Practice:** ⭐⭐⭐⭐⭐ (5/5)
This is exactly how mature GRC systems structure controls functionality.

---

### Option 2: Controls Within Risks App ⚠️ ACCEPTABLE FOR MVP

**Structure:**
```
risks/
├── models.py           # Risk, RiskCategory, Control, RiskControl
├── serializers.py      # Risk + Control serializers
├── views.py            # Risk + Control endpoints
└── ...
```

**Pros:**
- ✅ **RCSA Alignment:** Controls are assessed together with risks in workshops
- ✅ **Simplified Imports:** No cross-app dependencies
- ✅ **Transaction Simplicity:** Risk + Control operations in same app naturally
- ✅ **MVP Speed:** Faster initial development, less boilerplate

**Cons:**
- ❌ **Risks App Becomes "God Object":** Violates Single Responsibility Principle
- ❌ **Limited Reusability:** Controls tightly coupled to risks, hard to reuse elsewhere
- ❌ **Namespace Pollution:** `from risks.models import Control` is semantically confusing
- ❌ **Future Refactoring Pain:** Extracting controls later = breaking change
- ❌ **Doesn't Match Control Nature:** Controls are reusable infrastructure, not risk metadata

**Industry Practice:** ⭐⭐⭐ (3/5)
Common in spreadsheet-based RCSA and small systems, rare in enterprise platforms.

**Verdict:** Works short-term but creates technical debt. Not recommended even for MVP.

---

### Option 3: Controls Within Measures App ❌ NOT RECOMMENDED

**Structure:**
```
measures/
├── models.py           # Measure, Control (conceptual grouping as "mitigations")
└── ...
```

**Fundamental Flaw - Conceptual Mismatch:**

Controls and Measures are **fundamentally different** in operational risk management:

| Dimension | Control | Measure |
|-----------|---------|---------|
| **Nature** | Preventive/Detective | Corrective/Reactive |
| **Timing** | Continuous, ongoing | Time-bound, project-based |
| **Purpose** | Prevent/detect risks | Fix what went wrong or strengthen defenses |
| **Lifecycle** | Active/Inactive (state) | Open→In Progress→Completed (workflow) |
| **Example** | "Daily reconciliation" | "Implement reconciliation process by Q2" |
| **Relationship** | Measure may CREATE a control | Control exists independently |

**Why This Violates Industry Standards:**

**COSO Framework:**
- Controls = Component of Internal Control System (infrastructure)
- Corrective Actions = Management Response to Deficiencies (projects)

**Basel II/III:**
- Controls = Part of Risk Mitigation Framework (permanent)
- Action Plans = Management Actions post-incident (temporary)

**ISO 31000:**
- Controls = Risk Treatment Measures (ongoing state)
- Actions = Implementation Plans (time-bound projects)

**Three Lines of Defense:**
- 1st Line: Owns and operates **controls** daily
- 2nd Line: Monitors **controls**, tracks **measures** for remediation
- 3rd Line: Audits **controls**, validates **measure** completion

**Data Model Issues:**
- Measures have: `status`, `due_date`, `completion_date`, `priority`
- Controls have: `effectiveness_rating`, `frequency`, `control_type`, `is_automated`
- These attributes don't overlap - forcing them together creates messy nullable fields

**Industry Practice:** ⭐ (1/5)
Cannot find examples of enterprise systems that conflate controls with measures.

**Verdict:** Architecturally incorrect. Would confuse users and auditors.

---

### Comparative Summary

| Criterion | Separate App | Within Risks | Within Measures |
|-----------|-------------|--------------|-----------------|
| **Conceptual Clarity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Industry Alignment** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **MVP Speed** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Code Maintainability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Reusability** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ |

**Decision:** Proceed with **Option 1 - Separate Controls App**

---

## 4. Domain Model

### Core Entities

#### Control
**Definition:** A policy, procedure, or mechanism designed to prevent or detect operational risks.

**Key Attributes:**
- **Identity:** Name, description
- **Classification:** Control type (preventive/detective/corrective), frequency (continuous/daily/monthly/etc.)
- **Design:** Is automated?, effectiveness design rating
- **Context:** Business process, control owner
- **Status:** Is active?
- **Documentation:** Reference document link

**Lifecycle:** Controls don't have complex workflows. They are either:
- **Active:** Currently operating in business processes
- **Inactive:** No longer in use (deprecated, replaced, or discontinued)

#### RiskControl (Link Table)
**Definition:** The many-to-many relationship between a Risk and a Control, documenting which controls mitigate which risks.

**Key Attributes:**
- Risk reference
- Control reference
- Mitigation notes (how this control specifically addresses this risk)
- Linked by (user who created the mapping)
- Linked at (timestamp)

**Future Extension (Phase 2):**
- Operating effectiveness rating
- Last tested date
- Test results
- Remediation measure link (if control is deficient)

---

## 5. Control Effectiveness Philosophy

### Two Types of Effectiveness

Industry frameworks (COSO, Basel, ISO 31000) distinguish between:

**1. Design Effectiveness (Inherent)**
- **Question:** "How effective SHOULD this control be if operated properly?"
- **Rating Scale:** 1 (Poorly designed) to 5 (Well designed)
- **Assessed By:** Control design expert, Risk Officer
- **Example:** "Dual signature for payments > $5K" = 4/5 (strong design)

**2. Operating Effectiveness (Actual)**
- **Question:** "How effective IS this control in practice?"
- **Rating Scale:** 1 (Not working) to 5 (Fully effective)
- **Assessed By:** Control testing, internal audit, monitoring
- **Example:** Same dual signature control = 2/5 (many exceptions found during testing)

### MVP Approach: Design Effectiveness Only

**Phase 1 Decision:** Store only **design effectiveness** on the Control entity.

**Rationale:**
- Sufficient for initial RCSA workflow and residual risk calculation
- Keeps data model simple for MVP
- Risk Officers can assign controls to risks based on design effectiveness
- Avoids complexity of control testing infrastructure (not in MVP scope)

**Data Model (Phase 1):**
```python
class Control(models.Model):
    effectiveness = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Design effectiveness rating (1-5)"
    )
```

**Future Evolution (Phase 2):** Add operating effectiveness to the link table when control testing is implemented:

```python
class RiskControlAssessment(models.Model):  # Renamed from RiskControl
    effectiveness_operating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Operating effectiveness for this risk (1-5)"
    )
    last_tested = models.DateField(null=True, blank=True)
    test_results = models.TextField(blank=True)
```

### Why Not Contextual Effectiveness? (Rejected Alternative)

**Scenario Presented:** "Dual signature control is effective (5/5) for 'Petty Cash Theft' but weak (2/5) for 'CEO Fraud' because executives can override it."

**Analysis:** This scenario indicates **poor control design**, not contextual variation.

**Proper Approach:** Design specific controls for specific risk profiles:
- ✅ "Dual signature - Routine payments" (for junior staff fraud) → Effectiveness: 4/5
- ✅ "Board approval - Executive transactions" (for executive fraud) → Effectiveness: 4/5
- ❌ Generic "Dual signature" control with varying effectiveness → Poor practice

**Industry Principle:** If a control's effectiveness varies wildly by risk, either:
1. Control is too generic (wrong level of abstraction)
2. Control has design flaws
3. Multiple controls are needed (defense in depth)

**Auditor Expectation:** Controls should have **consistent inherent effectiveness**. Variations should occur in **operating effectiveness** (how well it's implemented), not design.

**Conclusion:** Effectiveness belongs on Control entity (design), with future option to add operating effectiveness on link table (testing results).

---

## 6. Module Placement Decision

### RiskControl Link Table: Where Should It Live?

Two options were evaluated:

**Option A: In Controls App**
- Control owns the relationship
- API: `POST /api/controls/{id}/link-to-risk/`
- Perspective: "This control addresses which risks?"

**Option B: In Risks App** ✅ RECOMMENDED
- Risk owns the relationship
- API: `POST /api/risks/{id}/link-to-control/`
- Perspective: "This risk is mitigated by which controls?"

**Decision: Option B (Risks App)**

**Rationale:**
1. **Workflow Alignment:** Risk Officer links controls TO risks during RCSA approval workflow
2. **Query Pattern:** More common to ask "What controls mitigate Risk X?" than "What risks does Control Y address?"
3. **Permission Model:** Linking happens during risk validation, which is risk-centric
4. **Consistency:** Matches existing pattern (`IncidentRisk` and `RiskMeasure` are in `risks/models.py`)

**Implementation:**
```python
# controls/models.py
class Control(models.Model):
    # ... control attributes ...
    pass

# risks/models.py
class Risk(models.Model):
    controls = models.ManyToManyField(
        'controls.Control',
        through='RiskControl',
        related_name='risks',
        blank=True
    )

class RiskControl(models.Model):
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE)
    control = models.ForeignKey('controls.Control', on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    linked_by = models.ForeignKey(User, on_delete=models.PROTECT)
    linked_at = models.DateTimeField(auto_now_add=True)
```

**API Structure:**
```
GET  /api/controls/                      # List controls (library)
POST /api/controls/                      # Create control (Risk Officer)
GET  /api/controls/{id}/                 # Control detail
PUT  /api/controls/{id}/                 # Update control

POST /api/risks/{id}/link-to-control/    # Link control to risk
POST /api/risks/{id}/unlink-from-control/ # Unlink control from risk
GET  /api/risks/{id}/controls/           # List controls for a risk
```

---

## 7. Functional Requirements

### FR-1: Control Library Management

**FR-1.1: Create Control**
- **Actor:** Risk Officer
- **Preconditions:** User has Risk Officer role
- **Input:** Name, description, control type, frequency, business process (optional), control owner, is_automated flag, effectiveness rating, reference document (optional)
- **Process:**
  1. Risk Officer accesses control library
  2. Clicks "Create New Control"
  3. Fills in control details
  4. Saves control
- **Output:** New control added to library with status "Active"
- **Validation:**
  - Name is required (max 255 characters)
  - Description is required
  - Control type must be valid choice (PREVENTIVE/DETECTIVE/CORRECTIVE)
  - Frequency must be valid choice
  - Control owner must exist and be active user
  - Effectiveness rating must be 1-5 if provided

**FR-1.2: View Control Library**
- **Actor:** Risk Officer, Manager, Employee
- **Preconditions:** User is authenticated
- **Process:** User accesses `/api/controls/` endpoint
- **Output:** Paginated list of controls with:
  - ID, name, control type, frequency, effectiveness, is_active status
  - Filter options: control type, business process, is_active, is_automated
  - Search: by name or description
- **Permissions:**
  - Risk Officer: View all controls
  - Manager: View active controls only
  - Employee: View active controls only

**FR-1.3: View Control Detail**
- **Actor:** Risk Officer, Manager, Employee
- **Process:** User accesses `/api/controls/{id}/` endpoint
- **Output:** Full control details including:
  - All attributes
  - List of risks this control is mapped to (with risk titles and IDs)
  - Control owner information
  - Created by and created at timestamps
- **Permissions:** Same as FR-1.2

**FR-1.4: Update Control**
- **Actor:** Risk Officer
- **Preconditions:** Control exists
- **Process:**
  1. Risk Officer opens control detail
  2. Edits control attributes
  3. Saves changes
- **Validation:** Same as FR-1.1
- **Business Rules:**
  - Cannot change control if it's linked to ACTIVE risks (must unlink first)
  - Can update description, effectiveness, reference docs at any time
  - Changes to control effectiveness don't automatically recalculate residual risk (manual reassessment required)

**FR-1.5: Deactivate Control**
- **Actor:** Risk Officer
- **Preconditions:** Control exists, control is not linked to any ACTIVE risks
- **Process:**
  1. Risk Officer opens control detail
  2. Clicks "Deactivate Control"
  3. Confirms action
- **Output:** Control status changed to inactive
- **Business Rules:**
  - Cannot deactivate control if linked to ACTIVE risks
  - Inactive controls remain in database for audit trail
  - Inactive controls hidden from control library by default (filter to show)

---

### FR-2: Risk-Control Linkage

**FR-2.1: Link Control to Risk**
- **Actor:** Risk Officer
- **Preconditions:**
  - Risk exists in DRAFT or ASSESSED status
  - Control exists and is active
  - User has Risk Officer role
- **Process:**
  1. Risk Officer opens risk in ASSESSED status
  2. In "Controls" section, clicks "Link Control"
  3. Searches/selects control from library
  4. Optionally adds mitigation notes ("How does this control address this risk?")
  5. Saves link
- **Output:** Control linked to risk, visible in risk detail view
- **Validation:**
  - Control must be active
  - Cannot link same control twice to same risk
  - Cannot link controls to RETIRED risks
- **API:** `POST /api/risks/{risk_id}/link-to-control/`
  - Payload: `{"control_id": 123, "notes": "Optional mitigation notes"}`

**FR-2.2: View Controls Linked to Risk**
- **Actor:** Risk Officer, Manager (if they own the risk), Employee (read-only)
- **Process:** User views risk detail page
- **Output:** "Controls" section shows:
  - List of linked controls with names and effectiveness ratings
  - Mitigation notes for each control
  - Who linked the control and when
- **Calculation:** System displays residual risk score considering control effectiveness

**FR-2.3: Unlink Control from Risk**
- **Actor:** Risk Officer
- **Preconditions:** Control is linked to risk, risk is not RETIRED
- **Process:**
  1. Risk Officer opens risk detail
  2. In Controls section, clicks "Unlink" next to control
  3. Confirms action
- **Output:** Link removed, control remains in library
- **Business Rules:**
  - Can unlink controls from DRAFT or ASSESSED risks freely
  - Can unlink controls from ACTIVE risks (triggers warning: "This may affect residual risk. Consider reassessment.")
  - Cannot unlink if it would leave risk with zero controls and risk is ACTIVE (must have at least one control per BRD requirement)

---

### FR-3: RCSA Workflow Integration

**FR-3.1: Control Requirement for Risk Approval**
- **Context:** Risk Officer approving risk (ASSESSED → ACTIVE transition)
- **Business Rule:** Per Risk Workflow BRD Section 7:
  - "At least one control must be linked" before risk can be approved to ACTIVE status
- **Validation:** System checks `risk.controls.count() >= 1`
- **Error Message:** "Cannot approve risk: At least one control must be linked. Please link controls before approval."

**FR-3.2: Control Effectiveness in Residual Risk Calculation**
- **Context:** Risk Officer calculates residual risk after linking controls
- **Current Approach (MVP):**
  - Residual likelihood and impact are **manually entered** by Risk Officer
  - Control effectiveness is **considered qualitatively** by Risk Officer when determining residual scores
  - System does not auto-calculate residual risk based on controls (future enhancement)
- **Display:** Risk detail page shows:
  - Inherent risk score (likelihood × impact)
  - Linked controls with effectiveness ratings
  - Residual risk score (manually assessed)
  - Visual indicator if residual > inherent (validation error)

**FR-3.3: Control Linking Workflow**
Typical RCSA workflow integration:
```
1. Manager: Create risk in DRAFT, assess inherent risk
2. Manager: Submit risk → ASSESSED
3. Risk Officer: Review risk
4. Risk Officer: Link controls from library (FR-2.1)
5. Risk Officer: Assess residual risk considering control effectiveness
6. Risk Officer: Approve → ACTIVE (validation ensures controls linked)
```

---

### FR-4: Reporting and Visibility

**FR-4.1: Risk-Control Matrix Report**
- **Actor:** Risk Officer
- **Output:** Report showing:
  - Rows: Risks (with inherent and residual scores)
  - Columns: Controls (with effectiveness ratings)
  - Cells: ✓ if control is linked to risk
- **Purpose:** Identify control coverage gaps, risks with insufficient controls

**FR-4.2: Control Coverage Metrics**
- **Actor:** Risk Officer
- **Metrics:**
  - Total number of controls in library
  - Number of active controls
  - Average control effectiveness rating
  - Number of risks with 0 controls (gap analysis)
  - Number of risks with < 3 controls (weak coverage)
  - Most frequently used controls (linked to most risks)

**FR-4.3: Control Detail - Linked Risks View**
- **Actor:** Risk Officer
- **Context:** Viewing control detail
- **Output:** List of all risks this control is mapped to
- **Purpose:** Understand control impact, plan control testing priorities

---

## 8. Data Model Specifications

### Control Entity

```python
class ControlType(models.TextChoices):
    PREVENTIVE = 'PREVENTIVE', 'Preventive'
    DETECTIVE = 'DETECTIVE', 'Detective'
    CORRECTIVE = 'CORRECTIVE', 'Corrective'

class ControlFrequency(models.TextChoices):
    CONTINUOUS = 'CONTINUOUS', 'Continuous'
    DAILY = 'DAILY', 'Daily'
    WEEKLY = 'WEEKLY', 'Weekly'
    MONTHLY = 'MONTHLY', 'Monthly'
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    ANNUALLY = 'ANNUALLY', 'Annually'
    AD_HOC = 'AD_HOC', 'Ad Hoc'

class Control(TimestampedModel):
    # Identity
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Classification
    control_type = models.CharField(
        max_length=20,
        choices=ControlType.choices,
        default=ControlType.PREVENTIVE
    )
    frequency = models.CharField(
        max_length=20,
        choices=ControlFrequency.choices,
        help_text="How often this control is performed"
    )
    
    # Design Characteristics
    is_automated = models.BooleanField(
        default=False,
        help_text="Is this control automated or manual?"
    )
    effectiveness = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Design effectiveness rating (1-5)"
    )
    
    # Documentation
    reference_doc = models.CharField(
        max_length=255,
        blank=True,
        help_text="Link to control procedure document"
    )
    
    # Context
    business_process = models.ForeignKey(
        'references.BusinessProcess',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    # Ownership
    control_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_controls',
        help_text="Person responsible for operating this control"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_controls'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
```

### RiskControl Link Entity (in risks/models.py)

```python
class RiskControl(models.Model):
    risk = models.ForeignKey('Risk', on_delete=models.CASCADE)
    control = models.ForeignKey('controls.Control', on_delete=models.PROTECT)
    
    # Context
    notes = models.TextField(
        blank=True,
        help_text="How this control mitigates this specific risk"
    )
    
    # Audit Trail
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    linked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('risk', 'control')
        verbose_name = "Risk-Control Link"
```

### Field Requirements

| Field |

Nullability | Default | Validation |
|-------|---------|---------|------------|
| name | NOT NULL | - | Max 255 chars |
| description | NOT NULL | - | Free text |
| control_type | NOT NULL | PREVENTIVE | Must be valid choice |
| frequency | NOT NULL | - | Must be valid choice |
| is_automated | NOT NULL | False | Boolean |
| effectiveness | NULL | NULL | 1-5 if provided |
| reference_doc | NULL | '' | Max 255 chars |
| business_process | NULL | NULL | Must exist if provided |
| control_owner | NOT NULL | - | Must be active user |
| created_by | NOT NULL | Current user | System-managed |
| is_active | NOT NULL | True | Boolean |

---

## 9. Integration with Risk Module

### Risk Model Updates

```python
# risks/models.py
class Risk(TimestampedModel, OwnedModel):
    # ... existing fields ...
    
    # M2M Relationship
    controls = models.ManyToManyField(
        'controls.Control',
        through='RiskControl',
        related_name='risks',
        blank=True
    )
```

### Risk Workflow Integration Points

**1. Risk Approval Validation (ASSESSED → ACTIVE)**
- Add validation in `risks/services.py::approve()`:
```python
@transaction.atomic
def approve(*, risk: Risk, user: User) -> Risk:
    # ... existing validations ...
    
    # NEW: Control linkage validation
    if risk.controls.count() == 0:
        raise RiskTransitionError(
            "At least one control must be linked before approval."
        )
    
    # ... rest of approval logic ...
```

**2. Risk Detail Serializer Enhancement**
- Add control information to risk detail response:
```python
# risks/serializers.py
class RiskDetailSerializer(serializers.ModelSerializer):
    # ... existing fields ...
    
    linked_controls = serializers.SerializerMethodField()
    control_count = serializers.IntegerField(
        source='controls.count',
        read_only=True
    )
    
    def get_linked_controls(self, obj):
        return ControlListSerializer(
            obj.controls.filter(is_active=True),
            many=True
        ).data
```

**3. Risk List Filtering**
- Add control-based filters to risk queryset:
```python
# risks/filters.py
class RiskFilter(django_filters.FilterSet):
    # ... existing filters ...
    
    has_controls = django_filters.BooleanFilter(
        method='filter_has_controls'
    )
    control_effectiveness__gte = django_filters.NumberFilter(
        method='filter_control_effectiveness'
    )
    
    def filter_has_controls(self, queryset, name, value):
        if value:
            return queryset.filter(controls__isnull=False).distinct()
        return queryset.filter(controls__isnull=True)
```

---

## 10. User Roles and Permissions

### Risk Officer

**Permissions:**
- ✅ Create controls in library
- ✅ Update control attributes
- ✅ Deactivate controls (if not linked to ACTIVE risks)
- ✅ View all controls (active and inactive)
- ✅ Link controls to risks during ASSESSED → ACTIVE approval
- ✅ Unlink controls from risks (with warnings if ACTIVE)
- ✅ Export control library

**Responsibilities:**
- Maintain centralized control library
- Ensure control descriptions are clear and accurate
- Assess control design effectiveness ratings
- Map controls to risks during RCSA validation
- Ensure adequate control coverage for all risks
- Generate control coverage reports

### Manager

**Permissions:**
- ❌ Cannot create/edit controls (library managed centrally by Risk Officers)
- ✅ View active controls in library (read-only)
- ✅ View controls linked to risks they own
- ✅ Suggest new controls to Risk Officer (via email/chat, not in-app)

**Responsibilities:**
- Review controls linked to their risks
- Inform Risk Officer if controls are not operating effectively
- Participate in RCSA workshops where controls are discussed
- Operate controls in their business unit (as control owners)

### Employee

**Permissions:**
- ❌ Cannot create/edit controls
- ✅ View active controls (read-only)
- ✅ View controls linked to risks in their business unit

**Responsibilities:**
- Understand controls that apply to their work
- Follow control procedures
- Report control failures or bypasses to Manager

---

## 11. Implementation Roadmap

### Phase 1: MVP (Weeks 1-2) - CURRENT SCOPE

**Goal:** Establish control library and basic risk-control linkage to support RCSA workflow.

**Deliverables:**
- ✅ Controls app scaffold (models, serializers, views, tests)
- ✅ Control CRUD API endpoints
- ✅ RiskControl link model in risks app
- ✅ Link/unlink control actions on Risk API
- ✅ Risk approval validation (requires controls)
- ✅ Basic control filtering and search
- ✅ Control list in risk detail response
- ✅ Control count in risk list response

**Out of Scope:**
- ❌ Control testing workflows
- ❌ Operating effectiveness tracking
- ❌ Control deficiency management
- ❌ Automated residual risk calculation

**Success Metrics:**
- Risk Officers can create controls in library
- Risk Officers can link controls to risks during approval
- Risk approval blocked if no controls linked
- Control library visible to all roles

---

### Phase 2: Control Testing & Operating Effectiveness (Future)

**Goal:** Track how well controls are actually performing in practice.

**New Features:**
- Control testing schedule (who tests, when, how often)
- Test evidence upload (documents, screenshots)
- Operating effectiveness rating per risk-control link
- Control deficiency tracking (when operating effectiveness < design)
- Automated linkage: Deficiency → Measure creation
- Control testing status dashboard

**Data Model Changes:**
```python
# Rename RiskControl → RiskControlAssessment
class RiskControlAssessment(models.Model):
    # ... existing fields ...
    
    # NEW: Operating effectiveness
    effectiveness_operating = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    last_tested = models.DateField(null=True, blank=True)
    tested_by = models.ForeignKey(User, null=True, ...)
    test_results = models.TextField(blank=True)
    
    # NEW: Deficiency tracking
    remediation_measure = models.ForeignKey(
        'measures.Measure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
```

---

### Phase 3: Advanced Control Management (Future)

**Goal:** Enterprise-grade control governance.

**New Features:**
- Control attestation workflows (control owners certify effectiveness quarterly)
- Control framework mappings (SOX, COSO, ISO 31000 categories)
- Control-to-compliance-requirement links
- Control change management (version history, approval for changes)
- Automated control monitoring integration (API hooks to monitoring tools)
- Control effectiveness trending over time
- Predictive analytics (risk of control failure)

---

## 12. Non-Functional Requirements

### NFR-1: Performance
- Control library list: Load < 500ms for 1000 controls
- Risk detail with 10 controls: Load < 300ms
- Control search: Results within 200ms

### NFR-2: Data Integrity
- Control deletion prohibited if linked to ACTIVE risks (use deactivate instead)
- Referential integrity enforced: RiskControl.control → Control (PROTECT on delete)
- Orphaned links cleaned up if risk is deleted (CASCADE on risk deletion)

### NFR-3: Audit Trail
- All control creations/updates logged with user and timestamp
- All control linkages logged (who linked, when)
- Control status changes (active/inactive) logged

### NFR-4: Usability
- Control library filterable by type, process, active status, automated flag
- Control search by name or description (full-text)
- Control selection UI: Typeahead search in risk detail page

### NFR-5: Scalability
- Support 5000+ controls in library
- Support 50+ controls per risk
- Efficient many-to-many queries with prefetch_related

---

## Appendix: Industry Standards Alignment

### COSO Framework Alignment

**COSO Component: Control Activities**
- "Actions established through policies and procedures that help ensure management's directives are carried out"
- Our Control entity represents these "control activities"
- RiskControl linkage documents which controls address which risks

**COSO Principles:**
- Principle 10: Selects and develops control activities
- Principle 11: Selects and develops general controls over technology
- Principle 12: Deploys through policies and procedures

Our implementation supports these principles by:
- Centralized control library (Principle 10)
- is_automated flag distinguishes IT controls (Principle 11)
- reference_doc links to policies/procedures (Principle 12)

### Basel II/III Operational Risk Framework

**Basel Requirement:** Banks must identify operational risks and maintain documentation of control environment.

Our implementation provides:
- ✅ Control library as evidence of control environment
- ✅ Risk-control mapping demonstrates mitigation strategies
- ✅ Control effectiveness ratings support capital calculation models
- ✅ Audit trail for regulatory examination

### ISO 31000:2018 Risk Management

**ISO 31000 Section 6.4.6: Risk Treatment**
- "Risk treatment involves selecting and implementing options for addressing risk"
- Controls are "risk treatment measures"

Our implementation aligns:
- Control library = catalog of available risk treatments
- RiskControl links = selected treatments for specific risks
- Control effectiveness = treatment efficacy assessment

### Three Lines of Defense Model

**1st Line (Business Units):**
- Control owners operate controls daily
- Managers ensure controls are followed

**2nd Line (Risk Management):**
- Risk Officers maintain control library
- Risk Officers validate control design
- Risk Officers monitor control effectiveness (Phase 2)

**3rd Line (Internal Audit):**
- Auditors review control documentation
- Auditors test control operating effectiveness
- Auditors validate risk-control mappings

Our data model supports all three lines:
- control_owner field = 1st Line accountability
- created_by, is_active = 2nd Line management
- Test results fields (Phase 2) = 3rd Line validation

---

## Document Control

### Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-27 | [Your Name] | Initial BRD based on architectural analysis |

### Approvals
| Role | Name | Signature | Date |
|------|------|-----------|------|
| Business Analyst | [Name] | | |
| Technical Lead | [Name] | | |
| Product Owner | [Name] | | |
| Risk Officer (Stakeholder) | [Name] | | |

### Related Documents
- `risk_workflow_design_specs.md` - Risk entity workflow (references control linkage requirement)
- `incidents_workflow_spec.md` - Incident entity workflow
- `measures_workflow_spec.md` - Measure entity workflow
- `controls_data_model.md` - Detailed database schema (to be created)
- `controls_api_specification.yaml` - API endpoints (to be created)

---

**End of Document**