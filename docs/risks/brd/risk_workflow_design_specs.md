# Risk Workflow Design Specification

**Document Type:** Workflow Design Specification  
**Project:** Operational Risk Management Platform - Risks Module  
**Version:** 1.0  
**Date:** November 24, 2025
**Author:** [Your Name/Team]  
**Status:** Approved

---

## Executive Summary

### Purpose
This document analyzes workflow state machine options for the Risk entity lifecycle in the Operational Risk Management platform and documents the selected design approach.

### Decision Summary
**Selected Workflow:** 4-State Workflow (`DRAFT → ASSESSED → ACTIVE → RETIRED`)

**Key Rationale:**
- Provides explicit validation step between risk assessment and activation
- Balances simplicity for MVP development with operational requirements
- Supports both workshop-based RCSA processes (external) and ad-hoc risk identification (in-app)
- Maintains clear separation of concerns between risk identification, scoring, validation, and monitoring phases

### Alternatives Considered
1. **4-State Workflow** (DRAFT → ASSESSED → ACTIVE → RETIRED) - **SELECTED**
2. **6-State Workflow** (DRAFT → UNDER_REVIEW → ASSESSED → ACTIVE → UNDER_REASSESSMENT → RETIRED) - Rejected as over-engineered
3. **3-State Workflow** (DRAFT → ACTIVE → RETIRED) - Rejected as oversimplified

### Out of Scope for MVP
**RCSA Campaign Management:** The analysis also evaluated implementing full Risk and Control Self-Assessment (RCSA) campaign orchestration within the application. This was **deferred** as the process will be managed externally through workshops, spreadsheets, and email workflows, with results entered into the risk register post-consolidation.

---

## Table of Contents
1. [Problem Statement](#1-problem-statement)
2. [Background & Context](#2-background--context)
3. [Evaluation Criteria](#3-evaluation-criteria)
4. [Workflow Options Analysis](#4-workflow-options-analysis)
5. [RCSA Campaign Management Analysis](#5-rcsa-campaign-management-analysis)
6. [Decision & Recommendation](#6-decision--recommendation)
7. [Implementation Guidelines](#7-implementation-guidelines)
8. [Appendix: Role Definitions](#appendix-role-definitions)

---

## 1. Problem Statement

### Business Need
The Operational Risk Management platform requires a clear, manageable workflow for risk records that:
- Distinguishes between draft/work-in-progress risks and validated/active risks
- Enforces review and approval by Risk Officers before risks become active in the register
- Supports both structured RCSA processes and ad-hoc risk identification
- Enables periodic reassessment of existing risks
- Provides audit trail of risk status transitions

### Challenge
The workflow must balance:
- **Simplicity** - MVP timeline constraints require lean implementation
- **Rigor** - Operational risk management requires proper validation and approval
- **Flexibility** - Must accommodate multiple entry methods (workshops, ad-hoc identification)
- **Compliance** - Must support regulatory requirements for risk assessment documentation

### Success Criteria
The selected workflow will:
1. Be implementable within MVP timeline (2-3 weeks)
2. Clearly separate Manager assessment from Risk Officer validation
3. Support annual RCSA cycles without requiring in-app campaign management
4. Provide clear visibility into pending reviews and approvals
5. Enable risk score updates through reassessment process

---

## 2. Background & Context

### Risk Entity Overview
A **Risk** represents a potential for loss resulting from inadequate or failed internal processes, people, systems, or external events. Each risk includes:

- **Identification:** Title, description, categorization (internal + Basel II event types)
- **Context:** Links to Business Units, Processes, Products
- **Assessment:** Inherent risk (pre-control) and Residual risk (post-control) scores
- **Relationships:** Links to Incidents (realizations), Controls (mitigations), Measures (action plans)

### Key Roles
- **Manager:** Business unit owner who identifies and assesses inherent risks in their domain
- **Risk Officer:** Central risk management professional who validates assessments, determines residual risk, and approves risks for the register
- **Employee:** Limited read-only access; may propose risks to their manager

### RCSA Process Context
Organizations typically conduct Risk and Control Self-Assessment (RCSA) on annual or quarterly cycles through:
1. Workshops with business unit managers
2. Spreadsheet-based questionnaires distributed via email
3. Manual consolidation by Risk Officers
4. Entry of validated risks into the risk register

**Key Decision:** For MVP, RCSA campaign orchestration (questionnaire distribution, response collection, duplicate consolidation) will remain external to the application. The risk register will serve as the system of record for validated risks post-RCSA.

---

## 3. Evaluation Criteria

Workflow options were evaluated against the following criteria:

### Primary Criteria (Must Have)
| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Validation Enforced** | Critical | Risk Officer approval required before risk becomes active |
| **Role Separation** | Critical | Clear distinction between Manager assessment and Risk Officer validation |
| **MVP Feasibility** | Critical | Implementable within 2-3 week timeline with < 3 models |
| **Audit Trail** | High | Ability to track who assessed, who approved, when |

### Secondary Criteria (Should Have)
| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Flexibility** | High | Supports both workshop-based and ad-hoc risk entry |
| **Reassessment Support** | Medium | Enables periodic review without workflow duplication |
| **User Clarity** | Medium | States are intuitive to non-technical users |
| **Future Extensibility** | Low | Can evolve to support campaign management if needed |

### Non-Functional Considerations
- **Code Maintainability:** Fewer states = simpler business logic
- **Testing Complexity:** Fewer transitions = fewer test cases
- **User Training:** Simpler workflow = faster adoption

---

## 4. Workflow Options Analysis

### Option 1: 4-State Workflow (SELECTED)

#### States
```
DRAFT → ASSESSED → ACTIVE → RETIRED
```

#### State Definitions

**DRAFT** - Risk identified but not yet scored
- **Who Creates:** Manager or Risk Officer
- **Required Fields:** Title, description, risk category (simplified internal risk taxonomy), context (business unit/process), owner
- **Optional Fields:** Inherent likelihood/impact (Manager can begin scoring)
- **Transitions To:** ASSESSED (Manager submits) or ACTIVE (Risk Officer direct approval for workshop results)

**ASSESSED** - Risk scored, awaiting validation
- **Who Transitions:** Manager submits for review
- **Required Fields:** All DRAFT fields + inherent likelihood/impact with justification
- **Risk Officer Actions:** 
  - Add residual likelihood/impact
  - Selects Basel event type based on simplified internal risk taxonomy, system checks that Basel type belongs to one of the types mapped by the internal risk_category
  - Link controls and measures
  - Approve → ACTIVE
  - Reject → back to DRAFT (with comments)
- **Transitions To:** ACTIVE (approved) or DRAFT (rejected)

**ACTIVE** - Risk validated and live in register
- **Who Transitions:** Risk Officer after validation
- **Complete Fields:** All inherent + residual scores, controls, measures
- **Ongoing Activities:** 
  - Link incidents as they occur
  - Update measures
  - Monitor through dashboards
- **Transitions To:** ASSESSED (reassessment requested) or RETIRED

**RETIRED** - Risk no longer applicable
- **Who Transitions:** Risk Officer
- **Required:** Retirement reason documented
- **State:** Read-only, maintained for historical record
- **Transitions To:** None (terminal state)

#### Workflow Diagram
```
┌─────────┐
│  DRAFT  │ ← Risk Officer can send back for revision
└────┬────┘
     │ Manager submits OR Risk Officer approves directly
     ▼
┌──────────┐
│ ASSESSED │
└────┬─────┘
     │ Risk Officer approves
     ▼
┌─────────┐ ← Risk Officer requests reassessment
│ ACTIVE  │ ──────────────────────┐
└────┬────┘                       │
     │                             │
     │ Risk Officer retires        │ Loops back to
     ▼                             │ ASSESSED
┌─────────┐                       │
│ RETIRED │                       │
└─────────┘ ◄─────────────────────┘
```

#### Pros
✅ **Clear validation checkpoint:** ASSESSED state creates explicit queue for Risk Officer review  
✅ **Flexible entry methods:** Supports both workshop (direct DRAFT→ACTIVE) and ad-hoc (DRAFT→ASSESSED→ACTIVE)  
✅ **Simple to implement:** 4 states, ~6 transitions, single model  
✅ **Intuitive naming:** Business users understand "assessed" vs "active"  
✅ **Handles reassessment:** Reuses ASSESSED state for periodic reviews  
✅ **Audit-friendly:** Submitted_at/validated_at timestamps track approval process  
✅ **MVP-appropriate:** Estimated 1-2 weeks implementation time

#### Cons
⚠️ **Less prescriptive:** Doesn't explicitly separate "Manager scoring" from "Risk Officer validation" as distinct states  
⚠️ **Reassessment ambiguity:** Active → Assessed transition could be confusing (looks like going backward)  
⚠️ **No in-progress visibility:** Can't distinguish "Manager is working on it" from "Manager abandoned it" within DRAFT

#### Evaluation Scoring
| Criterion | Score | Notes |
|-----------|-------|-------|
| Validation Enforced | ✅ Excellent | ASSESSED state blocks activation until approval |
| Role Separation | ✅ Good | DRAFT=Manager, ASSESSED=transition, ACTIVE=approved |
| MVP Feasibility | ✅ Excellent | 1 model, 4 states, 6 transitions |
| Audit Trail | ✅ Excellent | submitted_at, validated_at, validated_by fields |
| Flexibility | ✅ Excellent | Supports workshop + ad-hoc equally well |
| Reassessment Support | ⚠️ Good | Works but transition direction is counterintuitive |
| User Clarity | ✅ Good | States are self-explanatory |

---

### Option 2: 6-State Workflow

#### States
```
DRAFT → UNDER_REVIEW → ASSESSED → ACTIVE → UNDER_REASSESSMENT → RETIRED
```

#### State Definitions

**DRAFT** - Risk Officer creates skeleton  
**UNDER_REVIEW** - Manager assessing inherent risk  
**ASSESSED** - Risk Officer validating + setting residual risk  
**ACTIVE** - Live in register  
**UNDER_REASSESSMENT** - Annual review cycle triggered  
**RETIRED** - No longer relevant

#### Workflow Diagram
```
┌─────────┐
│  DRAFT  │
└────┬────┘
     │ Risk Officer assigns to Manager
     ▼
┌──────────────┐
│ UNDER_REVIEW │
└──────┬───────┘
       │ Manager submits assessment
       ▼
┌──────────┐
│ ASSESSED │
└────┬─────┘
     │ Risk Officer approves
     ▼
┌─────────┐ ◄──────────────────┐
│ ACTIVE  │                     │
└────┬────┘                     │
     │                           │
     │ Trigger: Annual cycle,    │ Manager reassesses
     │ incident, control failure │
     ▼                           │
┌───────────────────┐           │
│ UNDER_REASSESSMENT│───────────┘
└─────────┬─────────┘
          │ Manager updates, submits
          ▼
     (back to ASSESSED)
```

#### Pros
✅ **Explicitly separates roles:** UNDER_REVIEW (Manager) vs ASSESSED (Risk Officer) are distinct  
✅ **Formal reassessment:** UNDER_REASSESSMENT state makes annual cycles explicit  
✅ **Clearer handoffs:** Each state change represents a role handoff  
✅ **Aligns with formal RCSA:** Matches structured assessment process documentation

#### Cons
❌ **Over-engineered for MVP:** 6 states, ~10 transitions, estimated 3-4+ weeks implementation  
❌ **Assumes in-app campaigns:** Designed for orchestrating RCSA cycles within the system  
❌ **Rigid workflow:** Forces linear progression even for simple cases  
❌ **Redundant states:** UNDER_REVIEW vs DRAFT is splitting hairs; UNDER_REASSESSMENT vs ASSESSED is duplicate logic  
❌ **Poor workshop fit:** Risk Officer creating DRAFT then assigning doesn't match workshop reality  
❌ **Complex testing:** Significantly more state transitions to test  
❌ **User confusion:** "Why is my risk 'under review' vs 'assessed'?" requires explanation

#### Evaluation Scoring
| Criterion | Score | Notes |
|-----------|-------|-------|
| Validation Enforced | ✅ Excellent | Multiple validation checkpoints |
| Role Separation | ✅ Excellent | Each role has dedicated states |
| MVP Feasibility | ❌ Poor | 3-4+ weeks, complex state machine |
| Audit Trail | ✅ Excellent | Detailed tracking at each phase |
| Flexibility | ❌ Poor | Designed for campaign orchestration only |
| Reassessment Support | ✅ Excellent | Dedicated UNDER_REASSESSMENT state |
| User Clarity | ⚠️ Fair | Requires training to understand distinctions |

---

### Option 3: 3-State Workflow

#### States
```
DRAFT → ACTIVE → RETIRED
```

#### State Definitions

**DRAFT** - Risk being worked on (anyone can create/edit)  
**ACTIVE** - Approved by Risk Officer  
**RETIRED** - No longer relevant

#### Workflow Diagram
```
┌─────────┐
│  DRAFT  │ ← Risk Officer can send back
└────┬────┘
     │ Risk Officer approves
     ▼
┌─────────┐
│ ACTIVE  │
└────┬────┘
     │ Risk Officer retires
     ▼
┌─────────┐
│ RETIRED │
└─────────┘
```

#### Pros
✅ **Minimalist:** Only 3 states, ~4 transitions, extremely simple to implement  
✅ **Fast development:** < 1 week implementation  
✅ **Flexible:** Doesn't prescribe who does what, when  
✅ **Easy to understand:** No ambiguity about states

#### Cons
❌ **No validation visibility:** Can't distinguish "submitted for review" from "still being drafted"  
❌ **No approval queue:** Risk Officer can't see "risks awaiting my validation"  
❌ **Implicit process:** Assessment and validation are not captured in workflow  
❌ **Poor audit trail:** Timestamps only show created/activated, not submitted-for-review  
❌ **Manager uncertainty:** "Did my assessment get submitted? Is Risk Officer reviewing it?"  
❌ **Loses key distinction:** Between "scored but not validated" and "validated and monitoring"

#### Evaluation Scoring
| Criterion | Score | Notes |
|-----------|-------|-------|
| Validation Enforced | ⚠️ Fair | Technically enforced but not visible in workflow |
| Role Separation | ❌ Poor | Roles are implicit, not reflected in states |
| MVP Feasibility | ✅ Excellent | Simplest possible implementation |
| Audit Trail | ⚠️ Fair | Basic timestamps only |
| Flexibility | ✅ Excellent | Maximum flexibility |
| Reassessment Support | ⚠️ Fair | Works but no distinct reassessment state |
| User Clarity | ⚠️ Fair | Too simple - users want more visibility |

---

## 5. RCSA Campaign Management Analysis

### Scope Evaluated
The analysis also considered implementing full RCSA campaign orchestration, including:

**Campaign Management Features:**
- RCSA cycle planning (annual/quarterly campaigns)
- Participant assignment by business unit/process
- Risk identification phase (managers propose risks)
- Consolidation phase (Risk Officer removes duplicates, merges proposals)
- Assessment phase (managers score consolidated risks)
- Validation phase (Risk Officer approves assessments)
- Progress tracking (who has submitted, who is overdue)
- Automated email reminders and notifications

**Estimated Complexity:**
- **Models:** 5-7 additional models (RCSACampaign, RCSAParticipant, RCSARiskProposal, RCSANotification, etc.)
- **Workflow Logic:** Complex state machines for campaign phases and proposal statuses
- **UI Components:** Campaign dashboard, participant management, proposal consolidation interface, duplicate detection
- **Development Time:** 3-4 weeks of additional development
- **Testing Complexity:** Significantly increased due to multiple interacting workflows

### Decision: Defer Campaign Management

**Rationale for Exclusion from MVP:**

1. **RCSA is Inherently Human-Centric**
   - Risk identification benefits from face-to-face workshops and brainstorming
   - Consolidation requires human judgment to identify true duplicates vs similar risks
   - Email/spreadsheet workflows are familiar and work well for periodic exercises
   - Forcing process into rigid system workflow may reduce effectiveness

2. **The Register is the Value, Not the Process**
   - Core value proposition: centralized, queryable risk register with linkages
   - The *process* of discovering risks doesn't need to be in-system
   - Organizations already have RCSA processes that work for them
   - System should support existing processes, not replace them

3. **Significant Development Overhead**
   - Campaign management represents 50%+ additional development time
   - Complex features with uncertain ROI for MVP validation
   - Risk of building features that don't match actual user workflows
   - Maintenance burden for rarely-used complex workflows

4. **Viable External Process**
   - Risk Officer exports current register to Excel template
   - Workshops conducted with managers using familiar tools
   - Results consolidated manually in spreadsheet
   - Risk Officer enters validated risks into system post-workshop
   - This workflow is proven and requires no system changes

5. **Future Extensibility Preserved**
   - Decision is reversible: can add campaign features in Phase 2
   - MVP will validate whether users want in-app campaign management
   - User feedback post-MVP will inform campaign feature requirements
   - Current design doesn't preclude future campaign functionality

### Hybrid Approach for MVP

**In-App:** Risk register with CRUD, workflow, relationships, reporting  
**External:** RCSA campaign planning, questionnaires, consolidation  
**Integration Point:** CSV/Excel import for bulk risk creation post-workshop

**Benefits:**
- Delivers core value (risk register) quickly
- Respects existing organizational processes
- Reduces MVP scope by 40-50%
- Allows user feedback to shape future campaign features

---

## 6. Decision & Recommendation

### Selected Workflow: 4-State (Option 1)

**Recommendation:** Implement the 4-state workflow (`DRAFT → ASSESSED → ACTIVE → RETIRED`) for the Risk entity lifecycle.

### Justification

#### Meets All Primary Criteria
| Criterion | Assessment |
|-----------|------------|
| **Validation Enforced** | ✅ ASSESSED state creates explicit approval checkpoint |
| **Role Separation** | ✅ Clear handoff from Manager (DRAFT/ASSESSED) to Risk Officer (ACTIVE) |
| **MVP Feasibility** | ✅ Single model, 4 states, implementable in 1-2 weeks |
| **Audit Trail** | ✅ submitted_at, validated_at, validated_by fields capture approval process |

#### Balances Simplicity and Rigor
- **Not Too Simple:** Unlike 3-state, explicitly captures validation step
- **Not Too Complex:** Unlike 6-state, avoids over-engineering for unneeded campaign orchestration
- **Goldilocks Zone:** Sufficient structure for operational risk management without excessive overhead

#### Supports Both Entry Methods
**Workshop-Based RCSA (Bulk Entry):**
```
Risk Officer creates risk in DRAFT
  → Risk Officer fills all scores (inherent + residual)
  → Risk Officer transitions directly to ACTIVE
(Skips ASSESSED since Risk Officer is both assessor and validator)
```

**Ad-Hoc Risk Identification:**
```
Manager creates risk in DRAFT
  → Manager adds inherent scores
  → Manager submits → ASSESSED
  → Risk Officer reviews, adds residual scores
  → Risk Officer approves → ACTIVE
```

#### Future-Proof
- Can add campaign management later without changing core workflow
- ASSESSED state can be reused for reassessments without new states
- Simple enough to explain to users, complex enough to be useful

### Implementation Priority: High
This workflow is foundational for the Risks module and should be implemented in Phase 1 (MVP Sprint 1).

---

## 7. Implementation Guidelines

### Technical Implementation

#### Risk Model
```python
class RiskStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    ASSESSED = 'ASSESSED', 'Assessed (Pending Validation)'
    ACTIVE = 'ACTIVE', 'Active'
    RETIRED = 'RETIRED', 'Retired'

class Risk(models.Model):
    # Identification
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # ... other fields (category, context, scores, etc.) ...
    
    # Workflow
    status = models.CharField(
        max_length=20,
        choices=RiskStatus.choices,
        default=RiskStatus.DRAFT
    )
    
    # Audit trail
    submitted_for_review_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(User, null=True, related_name='submitted_risks')
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(User, null=True, related_name='validated_risks')
    retirement_reason = models.TextField(blank=True)
```

#### Allowed Transitions
```python
ALLOWED_TRANSITIONS = {
    RiskStatus.DRAFT: {
        RiskStatus.ASSESSED: ['manager', 'risk_officer'],  # Submit for review
        RiskStatus.ACTIVE: ['risk_officer'],  # Direct approval (workshop case)
    },
    RiskStatus.ASSESSED: {
        RiskStatus.ACTIVE: ['risk_officer'],  # Approve
        RiskStatus.DRAFT: ['risk_officer'],   # Send back for revision
        RiskStatus.RETIRED: ['risk_officer'],  # Retire without activation
    },
    RiskStatus.ACTIVE: {
        RiskStatus.ASSESSED: ['risk_officer'],  # Request reassessment
        RiskStatus.RETIRED: ['risk_officer'],   # Retire
    },
    RiskStatus.RETIRED: {},  # Terminal state
}
```

### Field Requirements by Status

| Field | DRAFT | ASSESSED | ACTIVE | RETIRED |
|-------|-------|----------|--------|---------|
| Title, Description, Internal Category | Required | Required | Required | Required |
| Basel Category | Optional | Optional | Required | Required |
| Context (BU, Process, Product) | Required | Required | Required | Required |
| Owner | Required | Required | Required | Required |
| Inherent Likelihood/Impact | Optional | **Required** | Required | Required |
| Inherent Justification | Optional | **Required** | Required | Required |
| Residual Likelihood/Impact | - | Optional | **Required** | Required |
| Residual Justification | - | Optional | **Required** | Required |
| Controls Linked | Optional | Optional | **Required** | Required |
| Measures Linked | Optional | Optional | Optional | Optional |
| Retirement Reason | - | - | - | **Required** |

### API Endpoints (preliminary)

**State Transition Endpoints:**
```
POST /api/risks/{id}/submit/           # DRAFT → ASSESSED
POST /api/risks/{id}/approve/          # ASSESSED → ACTIVE
POST /api/risks/{id}/send_back/        # ASSESSED → DRAFT
POST /api/risks/{id}/request_reassessment/  # ACTIVE → ASSESSED
POST /api/risks/{id}/retire/           # ACTIVE/ASSESSED → RETIRED
```

**Queryset Filters for UI:**
```
GET /api/risks/?status=ASSESSED&assigned_to_me=true
  → Risk Officer's "Pending My Validation" queue

GET /api/risks/?status=DRAFT&owner=current_user
  → Manager's "My Draft Risks"

GET /api/risks/?status=ACTIVE&next_review_date__lte=today
  → Risks due for reassessment
```

### User Interface Considerations

**Manager Perspective:**
- DRAFT risks show "Submit for Review" button when inherent scores are complete
- ASSESSED risks show "Awaiting Risk Officer Validation" badge (read-only)
- ACTIVE risks show "Request Reassessment" button (available to owner only)

**Risk Officer Perspective:**
- Dashboard widget: "X Risks Awaiting Validation" with link to filtered list
- ASSESSED risks show validation form with residual score inputs and Approve/Send Back buttons
- Can transition risks directly from DRAFT to ACTIVE (for workshop-based entry)

### Validation Rules

**Submission (DRAFT → ASSESSED):**
- Inherent likelihood and impact must be set (1-5)
- Inherent justification must be provided (min 20 characters)
- Internal risk category must be assigned (per risk_category)
- Owner must be assigned

**Approval (ASSESSED → ACTIVE):**
- Residual likelihood and impact must be set (1-5)
- Residual score must be ≤ inherent score (controls can't increase risk)
- Basel category must be assigned, belongs to one of the types mapped by the risk_category
- At least one control must be linked
- Residual justification must be provided

**Retirement:**
- Retirement reason must be documented (min 20 characters)
- State change is irreversible (no transitions out of RETIRED)

### Notifications

**Email/in-app notifications Triggers:**
- Manager submits DRAFT → ASSESSED: Notify Risk Officer
- Risk Officer sends back ASSESSED → DRAFT: Notify Manager (original submitter)
- Risk Officer approves ASSESSED → ACTIVE: Notify Manager (owner)
- Risk Officer requests reassessment ACTIVE → ASSESSED: Notify Manager (owner)

---

## Appendix: Role Definitions

### Manager
**Definition:** Business unit leader or process owner responsible for identifying and assessing risks within their domain.

**Permissions:**
- Create risks in DRAFT status
- Edit risks they own (while in DRAFT or ASSESSED)
- Submit risks for validation (DRAFT → ASSESSED)
- Link incidents to risks they own
- Add measures to risks they own
- View all risks related to their business unit/process

**Responsibilities:**
- Identify operational risks in their area
- Assess inherent risk scores (likelihood × impact before controls)
- Provide justification for risk scores
- Monitor active risks and link incidents as they occur
- Propose measures to mitigate risks
- Participate in periodic risk reassessments

### Risk Officer
**Definition:** Central operational risk management professional who validates risk assessments, maintains the risk register, and ensures consistency across the organization.

**Permissions:**
- All Manager permissions, plus:
- Validate and approve risks (ASSESSED → ACTIVE)
- Send risks back for revision (ASSESSED → DRAFT)
- Set residual risk scores
- Set Basel category
- Request reassessment of active risks (ACTIVE → ASSESSED)
- Retire risks (ACTIVE → RETIRED)
- Bulk import risks from RCSA workshops
- Edit any risk regardless of owner
- Access all risks across all business units

**Responsibilities:**
- Review and validate risk assessments submitted by Managers
- Determine residual risk scores (likelihood × impact after controls)
- Ensure consistency in risk scoring across business units
- Maintain risk register data quality (no duplicates, proper categorization)
- Coordinate RCSA processes (planning, consolidation, validation)
- Link controls to risks
- Generate risk reports for senior management
- Monitor risk trends and escalate high-risk areas

### Employee
**Definition:** General bank employee with read-only access to the risk register.

**Permissions:**
- View risks related to their business unit
- View public risk reports and dashboards
- Suggest new risks to their Manager (via email/chat, not in-app)

**Responsibilities:**
- Report risk-related observations to their Manager
- Participate in RCSA workshops when invited
- Follow risk mitigation procedures

---

## Document Control

### Version History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-24 | [Your Name] | Initial document; workflow analysis and decision |

### Approvals
| Role | Name | Signature | Date |
|------|------|-----------|------|
| Business Analyst | [Name] | | |
| Technical Lead | [Name] | | |
| Product Owner | [Name] | | |

### Related Documents
- `incidents_workflow_spec.md` - Incident entity workflow design
- `measures_workflow_spec.md` - Measure entity workflow design
- `risk_api_specification.yaml` - Risk API endpoints (OpenAPI spec)
- `risk_data_model.md` - Database schema for Risk entity

---

**End of Document**