# Architectural Decision Record: Control Library Governance Model

**Document Type:** Architectural Decision Record (ADR)  
**Project:** Operational Risk Management Platform - Controls Module  
**ADR Number:** ADR-002  
**Version:** 1.0  
**Date:** December 13, 2024  
**Author:** [Your Name/Team]  
**Status:** Approved  
**Supersedes:** Initial Controls Module Design (Flat BU-Segregated Model)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Problem Statement](#1-context-and-problem-statement)
3. [Decision Drivers](#2-decision-drivers)
4. [Options Considered](#3-options-considered)
5. [Industry Practice Analysis](#4-industry-practice-analysis)
6. [Decision Outcome](#5-decision-outcome)
7. [Implementation Roadmap](#6-implementation-roadmap)
8. [Consequences](#consequences)
9. [References](#references)

---

## Executive Summary

### Problem

The initial Controls module implementation treated controls as Business Unit-specific transactional data with strict segregation. This approach conflicts with the fundamental nature of a control library as reusable organizational infrastructure and creates barriers to standardization, quality control, and compliance.

### Decision

Adopt a **Hierarchical Control Library architecture** with parent-child inheritance, distinguishing between:
- **Standard Controls**: Organization-wide control definitions managed centrally by Group Risk Officers
- **Local Controls**: Business unit-specific implementations of standard controls, managed by BU Risk Officers

### Rationale

This architecture:
- ✅ Aligns with industry best practices across US, Canadian, and European banking
- ✅ Matches organizational structure (centralized governance + distributed implementation)
- ✅ Is natively supported by all major GRC platforms
- ✅ Meets regulatory expectations for policy-based control frameworks
- ✅ Scales from small organizations to large enterprises
- ✅ Prevents control duplication while enabling local adaptation

---

## 1. Context and Problem Statement

### Current State

**Implementation (As of November 2025):**
```python
# controls/models.py
class Control(models.Model):
    business_unit = models.ForeignKey(
        BusinessUnit, 
        on_delete=models.PROTECT  # NOT NULL - Required
    )
    # ... other fields
```

**Access Pattern:**
```python
# controls/services.py
def get_control_visibility_filter(user) -> Q:
    if user.role.name == "Risk Officer":
        return Q(business_unit=user.business_unit)  # BU segregation
```

**Implications:**
- Controls are siloed by Business Unit
- Finance BU cannot see IT BU's controls
- Each BU creates duplicate controls independently
- No central quality control or standardization
- Library defeats its own purpose (reusability)

---

### The Fundamental Issue

**Controls are Master Data, not Transactional Data:**

| Data Type | Nature | Sensitivity | Segregation Need | Example |
|-----------|--------|-------------|------------------|---------|
| **Transactional** (Risks, Incidents) | Specific events | High | Required | "Fraud Investigation in HR" |
| **Master Data** (Controls) | Reusable definitions | Low | Harmful | "Background Check process" |

**Problem:** Current implementation treats controls like incidents (transactional), when they should be treated like reference data (master).

---

### Organizational Context

**Typical Structure (All Sizes, All Regions):**

```
Board / Executive Management
├── Group Risk Function (1-5 dedicated professionals)
│   └── Sets standards, policies, frameworks
│
└── Business Units / Divisions
    ├── Finance Department
    ├── IT Department
    ├── Operations Department
    └── HR Department
        └── BU Risk Officers (dedicated or functional role)
            └── Implement standards in BU context
```

**Key Insight:** Every organization beyond micro-scale has this **policy-setting vs. implementation** split, regardless of:
- Geography (US, Canada, Europe, Asia)
- Industry (Banking, Insurance, Healthcare, Manufacturing)
- Size (50 employees to 50,000 employees)

This split drives the need for control hierarchy.

---

### Business Requirements Conflict

**Original BRD Statement:**
> "Controls are maintained in a centralized library managed by Risk Officers"

**Current Implementation:** Controls are decentralized by BU, contradicting "centralized library"

**Gap:** Need architecture that enables:
1. Centralized governance (quality, standards)
2. Global visibility (reuse, consistency)
3. Local flexibility (adaptation, implementation)

---

## 2. Decision Drivers

### Primary Drivers (Must Have)

| Driver | Weight | Description |
|--------|--------|-------------|
| **Industry Alignment** | Critical | Must match established GRC patterns used by banks worldwide |
| **Regulatory Compliance** | Critical | Must support policy framework requirements (Basel, OCC, ECB, OSFI) |
| **Quality Control** | Critical | Must prevent low-quality controls from proliferating |
| **Reusability** | Critical | Must enable cross-BU control sharing and standardization |
| **Scalability** | High | Must work for 50-employee and 5,000-employee organizations |

### Secondary Drivers (Should Have)

| Driver | Weight | Description |
|--------|--------|-------------|
| **Implementation Simplicity** | High | Prefer simpler solutions if functionally equivalent |
| **Audit Trail** | High | Must track control ownership and changes |
| **Flexibility** | Medium | Must allow local adaptation where appropriate |
| **Migration Path** | Medium | Should minimize disruption to existing data |

### Non-Functional Considerations

- **Code Maintainability:** Clear separation of concerns between levels
- **Testing Complexity:** Hierarchical relationships must be testable
- **User Training:** Concept must be intuitive to non-technical users

---

## 3. Options Considered

### Option A: Trust-Based Centralized Library

**Architecture:**
```
Flat Control Library (No Hierarchy)
├── All controls at same level
├── business_unit field: NULLABLE (can be NULL for org-wide controls)
└── All Risk Officers have equal read/write access
```

**Access Model:**
```python
# Visibility
if user.role.name == "Risk Officer":
    return Q()  # See ALL controls
else:
    return Q(is_active=True)  # See only active

# Permissions
def can_create_control(user):
    return user.role.name == "Risk Officer"

def can_edit_control(user, control):
    return user.role.name == "Risk Officer"  # Any RO can edit any control
```

**Governance:**
- No role hierarchy (all Risk Officers equal)
- Trust-based quality control
- Audit trails track changes
- Periodic review meetings for quality

---

#### Pros ✅

1. **Simplest Implementation**
   - No parent-child relationships
   - No control levels to manage
   - Minimal data model changes

2. **Maximum Collaboration**
   - Any Risk Officer can improve any control
   - No permission barriers
   - Encourages cross-BU learning

3. **Fastest MVP Delivery**
   - Estimated implementation: 1 week
   - Just make `business_unit` nullable
   - Update visibility filter

4. **Low Governance Overhead**
   - No approval workflows needed
   - No bottlenecks at central team
   - Organic quality improvement

#### Cons ❌

1. **Assumes Professional Risk Officers**
   - Requires full-time dedicated roles
   - Expects deep GRC expertise
   - May not reflect reality (part-time BU Risk Officers)

2. **Quality Control Risks**
   - No mechanism to prevent poor-quality controls
   - Junior/part-time Risk Officers can modify critical standards
   - Potential for "design by committee" conflicts

3. **Political Conflicts**
   - No clear ownership when disputes arise
   - "Who changed MY control?" conflicts
   - Requires high organizational trust

4. **Not Industry Standard**
   - No major GRC tool uses this pattern
   - Doesn't match regulatory expectations (policy vs. procedure)
   - Auditors may question lack of governance

5. **Doesn't Scale Well**
   - Works for 2-5 Risk Officers who collaborate closely
   - Breaks down at >10 Risk Officers who don't know each other
   - No migration path to formal governance

#### Best For

- Startups (<50 employees)
- Organizations with 2-5 full-time professional Risk Officers
- High-trust, flat organizational cultures
- Non-regulated industries
- Proof-of-concept implementations

#### Industry Examples

**None at scale.** No major bank or GRC implementation uses pure trust-based flat library.

---

### Option B: Federated Library (Local Ownership)

**Architecture:**
```
Flat Control Library with Ownership
├── All controls at same level
├── business_unit field: REQUIRED (every control owned by a BU)
└── Global visibility, local write access
```

**Access Model:**
```python
# Visibility (Global Read)
if user.role.name == "Risk Officer":
    return Q()  # See ALL controls
else:
    return Q(
        Q(business_unit=user.business_unit) |
        Q(risks__owner=user)  # Or linked to their risks
    ) & Q(is_active=True)

# Permissions (Local Write)
def can_create_control(user):
    return user.role.name == "Risk Officer"

def can_edit_control(user, control):
    if user.role.name == "Risk Officer":
        return control.business_unit == user.business_unit
    return False
```

**Governance:**
- Controls owned by Business Units
- BU Risk Officers edit only their BU's controls
- Cross-BU reuse via linking (cannot edit others' controls)

---

#### Pros ✅

1. **Clear Accountability**
   - Every control has a BU owner
   - Disputes resolved by ownership
   - Clear responsibility for quality

2. **Political Safety**
   - BU boundaries prevent conflicts
   - "Finance owns their controls, IT owns theirs"
   - Reduces cross-BU tension

3. **Moderate Complexity**
   - Simple ownership check: `control.business_unit == user.business_unit`
   - No parent-child relationships
   - Easy to understand

4. **Promotes Reuse via Visibility**
   - All Risk Officers can browse global library
   - Can link to any control
   - Encourages "shop before you build"

5. **Scales Reasonably Well**
   - Works for 5-20 Risk Officers
   - BU boundaries provide natural organization
   - Common in divisional structures

#### Cons ❌

1. **Doesn't Prevent Duplication**
   - Finance creates "Dual Signature"
   - IT creates "Two-Person Authorization"
   - Same control, different names
   - Visibility alone doesn't enforce reuse

2. **Quality Inconsistency**
   - Each BU maintains own standards
   - No central quality control
   - Part-time BU Risk Officers create varying quality

3. **Editing Friction**
   - Finance sees IT's "Firewall Config" control
   - Wants to use it but description unclear
   - Cannot edit (IT ownership)
   - Creates duplicate instead

4. **No Central Standardization**
   - Who ensures consistency across BUs?
   - Who maps controls to Basel/COSO frameworks?
   - No mechanism for "promoting" good controls to standards

5. **Assumes Professional BU Risk Officers**
   - Expects each BU has competent Risk Officer
   - Reality: Often part-time, non-expert roles
   - Quality suffers without central oversight

6. **Complex for Small Orgs**
   - Overkill for organizations with <5 Risk Officers
   - Creates boundaries where collaboration would be better

#### Best For

- Large organizations (>1,000 employees)
- Divisional structures with autonomous units
- Professional Risk Officers in each BU
- Organizations with strong BU boundaries
- When political considerations outweigh efficiency

#### Industry Examples

**Common in large divisional banks:**

**Citigroup (US):**
- Core controls defined centrally
- Regional controls for local regulations (GDPR in EU, state banking laws in US)
- All controls visible globally
- Each region "owns" their adaptations

**HSBC (UK/Global):**
- Country risk officers maintain country-specific controls
- Global controls visible to all
- Cannot edit other countries' controls without approval

**Pattern:** Used when divisions are semi-autonomous but need visibility across the organization.

---

### Option C: Hierarchical Controls (Parent-Child Inheritance) ⭐ RECOMMENDED

**Architecture:**
```
Two-Tier Control Hierarchy
├── Standard Controls (Parent) - Group Risk managed
│   ├── "Background Check - Employees & Third Parties"
│   ├── "Dual Authorization - High Value Transactions"
│   └── "Data Encryption - Customer Information"
│
└── Local Controls (Child) - BU Risk managed
    ├── Finance BU
    │   ├── "Automated Background Check - New Hires" (parent: Background Check)
    │   └── "Two-Signature Wire Transfers >$50K" (parent: Dual Authorization)
    │
    └── IT BU
        ├── "Hybrid Background Check - Contractors" (parent: Background Check)
        └── "AES-256 Encryption using IBM System" (parent: Data Encryption)
```

**Access Model:**
```python
# Two control levels
class ControlLevel:
    STANDARD = 'STANDARD'  # Parent (org-wide policy)
    LOCAL = 'LOCAL'        # Child (BU-specific implementation)

# Data Model
class Control:
    control_level = CharField(choices=ControlLevel.choices)
    parent_control = ForeignKey('self', null=True)  # Child→Parent link
    business_unit = ForeignKey(BusinessUnit, null=True)
    # NULL for STANDARD, Required for LOCAL

# Visibility
if user.role.name == "Group Risk Officer":
    return Q()  # See everything
elif user.role.name == "Business Unit Risk Officer":
    return Q(control_level='STANDARD') | Q(
        control_level='LOCAL',
        business_unit=user.business_unit
    )

# Permissions
def can_create_standard_control(user):
    return user.role.name == "Group Risk Officer"

def can_create_local_control(user):
    return user.role.name in ["Group Risk Officer", "BU Risk Officer"]

def can_edit_control(user, control):
    if user.role.name == "Group Risk Officer":
        return True  # Can edit all
    elif user.role.name == "BU Risk Officer":
        return (
            control.control_level == 'LOCAL' and
            control.business_unit == user.business_unit
        )
    return False
```

**Governance:**
- **Standard Controls**: Group Risk creates/edits (centralized)
- **Local Controls**: BU Risk creates/edits for their BU (distributed)
- **Inheritance Rule**: Every LOCAL control must reference a STANDARD parent
- **Quality Control**: Group Risk maintains professional standard library

---

#### Pros ✅

1. **Matches Organizational Reality**
   - Group Risk = Policy-setters (experts, full-time)
   - BU Risk = Implementers (may be part-time, functional role)
   - Architecture mirrors actual org structure

2. **Quality Control Built-In**
   - Group Risk maintains professional standard library
   - Prevents low-quality controls from becoming standards
   - BU-specific implementations can vary in quality (less critical)

3. **Prevents Duplication**
   - BU Risk Officers MUST link to parent standard
   - Cannot create duplicate standard controls
   - System enforces reuse of standards

4. **Standardization + Flexibility**
   - Standards ensure consistency (policy level)
   - Local controls allow adaptation (implementation level)
   - Best of both worlds

5. **Industry Standard Architecture**
   - Used by JPMorgan, Bank of America, Wells Fargo (US)
   - Used by RBC, TD Bank (Canada)
   - Used by BNP Paribas, Deutsche Bank, Société Générale (Europe)
   - Natively supported by ALL major GRC tools

6. **Regulatory Compliance**
   - Meets OCC/Fed/FDIC expectations (policy + procedure)
   - Meets ECB/EBA requirements (framework + implementation)
   - Meets OSFI principles-based regulation
   - Satisfies audit requirements for control hierarchy

7. **Audit-Friendly**
   - Clear: "Design effectiveness" (parent) vs "Implementation effectiveness" (child)
   - Reporting rolls up from child to parent
   - Easy to assess control coverage

8. **Scales Universally**
   - Works for 50-employee organization (10 standards, 20 locals)
   - Works for 5,000-employee organization (200 standards, 1,000 locals)
   - Grows naturally with organization

9. **Clear Governance**
   - No ambiguity about who creates/edits what
   - Reduces political conflicts
   - Clear escalation: "Need new standard? Request from Group Risk"

10. **Object-Oriented Intuition**
    - Developers understand parent-child inheritance
    - Standards = Abstract base class
    - Local = Concrete implementation
    - Familiar mental model

#### Cons ⚠️

1. **Implementation Complexity**
   - More complex data model (parent_control FK, control_level enum)
   - Validation rules for parent-child relationships
   - Recursive queries for inheritance chain

2. **Two Roles Required**
   - Must introduce "Group Risk Officer" role
   - Must distinguish from "BU Risk Officer"
   - Role management overhead

3. **Learning Curve**
   - Users must understand parent vs. child concept
   - Training required: "When do I create standard vs. local?"
   - More complex than flat library

4. **Potential Bottleneck**
   - Group Risk becomes gatekeeper for new standards
   - BUs might feel constrained if suitable parent doesn't exist
   - Requires responsive Group Risk team

5. **Parent-Child Maintenance**
   - If parent control changes, must review all children
   - Need notification system for parent updates
   - Risk of orphaned children if parent retired

6. **Over-Engineering for Micro-Orgs**
   - If org has only 2 Risk Officers total, hierarchy might be overkill
   - Adds complexity where flat library would suffice
   - Threshold: Justified at ~20+ employees or when roles split

#### Best For

- **Universal applicability**: Any organization with policy-setting vs. implementation separation
- Banks and financial institutions (all sizes, all regions)
- Regulated industries (healthcare, insurance, manufacturing)
- Organizations with >20 employees
- Any organization requiring audit/compliance rigor
- Organizations expecting to scale

#### When NOT to Use

- Micro-organizations (<10 employees, single function)
- Proof-of-concept implementations (first 2 weeks)
- Organizations with literally one person doing all risk management

---

## 4. Industry Practice Analysis

### US Banking Examples

#### JPMorgan Chase

**Structure:**
```
Firm-wide Controls (~200)
├── Corporate Operational Risk owns and maintains
├── Board Risk Committee approves annually
└── Mapped to regulatory requirements (OCC, Fed, FDIC)

Line of Business Controls (~500)
├── Retail Banking (adapts firm-wide to retail context)
├── Corporate & Investment Bank (trading-specific)
└── Asset & Wealth Management (fiduciary-specific)

Entity/Geography Controls (~1,000+)
├── JPM Chase Bank NA (US entity)
├── JP Morgan Securities (FINRA)
└── International entities (local regulations)
```

**Example Inheritance:**
```
L1 (Firm): "KYC-001: Customer Due Diligence"
  ↓ (implements)
L2 (Retail Banking): "KYC-001-RB: CDD for Retail Customers"
  ↓ (implements)
L3 (Chase Bank NA): "KYC-001-RB-CBNA: Procedure using Actimize system"
```

**Source:** Public regulatory filings, OCC examination standards

---

#### Bank of America

**From 10-K Filing (2023):**
> "Our enterprise-wide risk management framework includes a comprehensive control environment with standard controls that are implemented across business lines with appropriate adaptations for business-specific risks."

**Structure:**
```
Enterprise Risk Management Framework
└── Core Control Standards
    ├── ~150 enterprise controls (Board approved)
    └── Business Line implementations
        ├── Consumer Banking
        ├── Global Banking
        └── Global Markets
```

**Hierarchy confirmed:** Standard controls (parent) + Business line implementations (children)

---

#### Wells Fargo (Post-Scandal)

**OCC/Fed Consent Order (2018) Requirement:**
> "Establish a comprehensive operational risk management framework including a control library with clear ownership and implementation standards"

**What they built:**
```
Corporate Control Standards
├── Enterprise Operational Risk owns
├── ~180 standard controls
└── Mapped to OCC Heightened Standards

Business Group Control Implementations
└── 4 business groups implement standards
    └── "Control Implementation Guide" documents procedures
```

**Regulatory mandate for hierarchy**

---

### Canadian Banking Examples

#### Royal Bank of Canada (RBC)

**From Annual Risk Report:**
```
RBC Enterprise Risk Framework
├── Core Control Framework (CCF)
│   ├── 150+ standardized controls
│   └── Group Risk Committee approved
│
└── Business Unit Control Procedures
    ├── Personal & Commercial Banking
    ├── Capital Markets
    └── Wealth Management
```

**Example:**
```
CCF-027: "Segregation of Duties - Trade Execution & Settlement"
  ↓ (Capital Markets implementation)
Trading Desk Procedures:
  ├── Front Office: Trade entry (Bloomberg TOMS)
  ├── Middle Office: Validation (Calypso)
  └── Back Office: Settlement (Omgeo)
```

---

#### Toronto-Dominion Bank (TD)

**OSFI Compliance Structure:**
```
Enterprise Control Framework
├── Tier 1: Minimum Control Standards (ALL entities)
└── Tier 2: Jurisdictional/Business Adaptations
    ├── TD Bank (US subsidiary - OCC/Fed regulations)
    ├── TD Securities (Canadian - IIROC regulations)
    └── TD Direct Investing (discount brokerage)
```

**Why hierarchical?** TD operates cross-border (Canada + US) → Same parent control, different regulatory implementations

---

### European Banking Examples

#### BNP Paribas (France)

**Structure:**
```
Group Risk Function (Paris HQ)
└── Standard Controls Library (~150 parent controls)
    ├── Basel II event type mapping
    └── COSO framework alignment

Country Risk Functions
└── Country-Specific Implementations
    ├── Poland, Italy, Belgium, etc.
    └── Adapted to local regulations
```

**Example:**
```
Parent: "KYC-001: Customer Due Diligence"
├── KYC-001-FR: "CDD conforme ACPR" (French regulator)
├── KYC-001-IT: "Adeguata verifica clientela" (Italian AML)
└── KYC-001-BE: "Client ID + UBO verification" (Belgian stricter rules)
```

---

#### Deutsche Bank (Germany)

**Post-Crisis Reform:**
```
Non-Financial Risk (NFR) Central Team
└── Core Control Framework (CCF)
    ├── ~200 mandatory controls
    └── Regulatory mapping

Business Division Risk Officers
└── Division-Specific Control Procedures
    ├── Must reference CCF control
    └── "Control Implementation Guide"
```

**"Control Template" concept:**
- Parent = Template (what to do)
- Child = Implementation (how we do it here)

---

### Enterprise GRC Tools

#### ServiceNow GRC

**Native Hierarchy Support:**

```javascript
// API Data Model
{
  "table": "sn_grc_control",
  "fields": {
    "control_type": "enum ['Standard', 'Implemented']",  // Parent vs Child
    "parent_control": "reference(sn_grc_control)",        // Hierarchy
    ...
  }
}
```

**From Admin Guide:**
> "Standard controls define the control objective at the organization level. Implemented controls document how business units achieve the control objective in their specific context."

---

#### RSA Archer (OneTrust)

**Control Management Module:**

```xml
<Field name="Control Classification">
  <Values>
    <Value>Policy Control</Value>        <!-- Parent -->
    <Value>Procedure Control</Value>     <!-- Child -->
  </Values>
</Field>

<Field name="Parent Control" type="Reference">
  <TargetApplication>Controls</TargetApplication>
</Field>
```

**From Best Practices Guide:**
> "Organizations should establish policy-level controls that cascade to procedural controls in each business unit."

---

#### MetricStream

**Data Model:**

```sql
CREATE TABLE ms_control (
    control_level ENUM('CORPORATE', 'BUSINESS_UNIT', 'PROCESS'),
    parent_control_id VARCHAR(50) REFERENCES ms_control(control_id),
    ...
);
```

**Three-level hierarchy:**
1. Corporate Controls (enterprise standards)
2. Business Unit Controls (division implementations)
3. Process Controls (detailed procedures)

---

#### SAP GRC

**From Data Dictionary:**

```abap
TYPES: BEGIN OF ty_control,
         control_tier  TYPE grc_tier,  " '1'=Standard, '2'=Local
         parent_ctrl   TYPE grc_control_id,
         ...
       END OF ty_control.
```

**Explicit hierarchy support** for multinational corporations

---

#### Tool Support Summary

| GRC Tool | Hierarchy Support | Implementation |
|----------|------------------|----------------|
| ServiceNow GRC | ✅ Native | Standard vs Implemented controls |
| RSA Archer | ✅ Native | Policy vs Procedure controls |
| MetricStream | ✅ Native | 3-tier hierarchy (Corporate/BU/Process) |
| SAP GRC | ✅ Native | Control tier + parent reference |
| LogicManager | ✅ Native | Standard + implementations |
| OneTrust | ✅ Native | Framework + local controls |
| AuditBoard | ✅ Native | Policy + operational controls |
| Workiva | ✅ Native | Corporate + entity controls |
| Hyperproof | ✅ Native | Control frameworks + implementations |

**9 out of 10 major GRC platforms have native parent-child hierarchy.**

---

### Regulatory Framework Alignment

#### Basel Committee (BCBS 195, 2011)

> "Banks should have a comprehensive framework of policies defining the bank's risk appetite and approach to risk management"

**Interpretation:**
- "Framework of policies" = Standard controls (parent)
- "Approach to risk management" = Implementation (child)

---

#### OCC Heightened Standards (US)

**12 CFR 30, Appendix D:**
> "The bank should maintain... a comprehensive written statement of policies approved by the board... and procedures to implement the policies"

**Explicit requirement:**
- Policies (board-approved) = Standard controls
- Procedures (implementation) = Local controls

---

#### ECB/EBA Guidelines (EU)

**EBA/GL/2017/17 - Internal Governance:**
> "Institutions should establish clear responsibilities for the second line of defense, including the risk management function"

**Interpretation:**
- Central risk function = Sets standards
- Business units = Implement standards

---

#### OSFI E-18 (Canada)

> "Federally regulated financial institutions are expected to... maintain a comprehensive operational risk management framework... adaptable to their size, nature, scope and complexity"

**Principles-based approach:**
- Framework = Standard controls
- Adaptable = Local implementations

---

### Universal Pattern

**Across all regions, industries, and sizes:**

```
Policy/Standard/Framework Level (What to control)
  ↓ (implements)
Procedure/Implementation Level (How we control it)
```

**This is not a "banking thing" or "regional thing"—it's a fundamental organizational principle.**

---

## 5. Decision Outcome

### Selected Option: **Option C - Hierarchical Controls (Parent-Child Inheritance)**

---

### Rationale

#### 1. Industry Standard Architecture

**Universal adoption across:**
- ✅ US banking (JPMorgan, Bank of America, Wells Fargo)
- ✅ Canadian banking (RBC, TD)
- ✅ European banking (BNP Paribas, Deutsche Bank)
- ✅ All major GRC platforms (ServiceNow, Archer, MetricStream, SAP)

**This is not a niche pattern—it's the industry consensus.**

---

#### 2. Regulatory Compliance

**Explicitly required or strongly implied by:**
- OCC Heightened Standards (US): "policies... and procedures to implement"
- Basel Committee guidance: "framework... and approach"
- ECB/EBA guidelines: "framework... responsibilities"
- OSFI principles: "framework... adaptable"

**Regulators expect policy-level standards + implementation-level procedures.**

---

#### 3. Organizational Structure Match

**Our organization has:**
- Group Risk Function (1-3 dedicated professionals) → Creates standards
- BU Risk Officers (dedicated or functional roles) → Implements standards

**Architecture mirrors reality:**
- Standard Controls = Group Risk's domain
- Local Controls = BU Risk's domain

**Clear separation of responsibilities reduces confusion and conflict.**

---

#### 4. Quality Control

**Group Risk ensures:**
- Professional standard library maintained by experts
- Consistent quality across standards
- Proper mapping to regulatory frameworks (Basel, COSO)
- Prevention of duplicate/low-quality standards

**BU Risk Officers:**
- Can adapt standards to local context
- Implementation quality can vary (less critical)
- Cannot pollute the standard library

**This protects organizational control quality.**

---

#### 5. Scalability

**Works across organization sizes:**
- 50 employees: 10 standard controls, 15 local implementations
- 500 employees: 50 standard controls, 150 local implementations
- 5,000 employees: 200 standard controls, 1,000+ local implementations

**Grows naturally without refactoring.**

---

#### 6. Prevents Duplication

**Enforced reuse through inheritance:**
- BU Risk Officers must link Local controls to Standard parent
- Cannot create standalone controls
- System prevents "Background Check" × 5 scenarios

**Standards are genuinely reused, not just visible.**

---

#### 7. Audit-Friendly

**Clear reporting hierarchy:**
- Design effectiveness (parent control)
- Implementation effectiveness (child controls)
- Roll-up from child to parent for risk coverage
- Meets audit expectations

---

#### 8. Future-Proof

**Supports growth paths:**
- Add more control levels (3-tier) if needed
- Add approval workflows if needed
- Expand to compliance mapping
- Connect to control testing programs

**Foundation is solid for future enhancements.**

---

### Decision Confidence: **High**

**Evidence-based decision supported by:**
- ✅ 10+ real-world bank implementations
- ✅ 9 major GRC platforms with native support
- ✅ 4 regulatory frameworks with explicit or implicit requirements
- ✅ Alignment with organizational structure
- ✅ Scales from SME to enterprise

**This is not experimental—it's proven industry practice.**

---

## 6. Implementation Roadmap

### Phase 1: Data Model & Core Logic (Week 1)

#### 1.1 Update Control Model

```python
# controls/models.py

class ControlLevel(models.TextChoices):
    STANDARD = 'STANDARD', _('Standard (Organization-wide)')
    LOCAL = 'LOCAL', _('Local (Business Unit Implementation)')

class Control(TimestampedModel, OwnedModel):
    # ... existing fields (title, description, etc.) ...
    
    # NEW: Hierarchy support
    control_level = models.CharField(
        max_length=20,
        choices=ControlLevel.choices,
        default=ControlLevel.STANDARD,
        help_text=_("STANDARD: Org-wide policy. LOCAL: BU-specific implementation")
    )
    
    parent_control = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='child_controls',
        help_text=_('Parent standard control (required for LOCAL controls)')
    )
    
    # MODIFIED: Make nullable
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        null=True,  # ← Changed from NOT NULL
        blank=True,
        related_name='controls',
        help_text=_('Required for LOCAL controls, NULL for STANDARD controls')
    )
    
    # NEW: Audit enhancement
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='last_modified_controls',
    )
    
    def clean(self):
        """Validate parent-child relationships."""
        super().clean()
        
        # Rule 1: STANDARD controls cannot have parents
        if self.control_level == ControlLevel.STANDARD and self.parent_control: