# Controls Workflow & Business Rules

This document defines the business logic and lifecycle rules for the **Controls** module. Unlike Risks or Incidents, Controls do not follow a complex state machine; they function as a **Library** of reusable assets organized in a hierarchical structure.

## 1. Control Lifecycle

The Control entity has a simple binary state designed to preserve historical data while maintaining a clean library for current operations.

* **`ACTIVE` (`is_active=True`):** The control is operational and available for use. It can be linked to new risks (if LOCAL level).
* **`INACTIVE` (`is_active=False`):** The control is deprecated or no longer in use. It is hidden from standard views but preserved for audit trails. It cannot be linked to new risks.

---

## 2. Permission Model (Hierarchical Governance)

Access to the Control Library is strictly governed based on a two-tier hierarchy that distinguishes between organizational standards and business unit implementations.

### 2.1. Control Levels

* **STANDARD Controls**: Organization-wide policies and control objectives. Serve as templates that define what needs to be controlled (e.g., "Background Check - Employees & Third Parties").
* **LOCAL Controls**: Business unit-specific implementations of STANDARD controls. Define how the control is implemented in specific contexts (e.g., "Finance Automated Background Check via Vendor X").

### 2.2. Role-Based Permissions

| Role | STANDARD Controls | LOCAL Controls | Notes |
| :--- | :--- | :--- | :--- |
| **Group Risk Officer** | **[Create/Edit]** | **[Create/Edit]** (any BU) | Full control over entire library. Typically the Risk Management or Group Risk function. |
| **BU Risk Officer** | [View Only] | **[Create/Edit]** (own BU only) | Can implement STANDARD controls in their BU context. Cannot modify STANDARD definitions. |
| **Manager** | [View Only] (Active) | [View Only] (Active, own BU or linked to their risks) | Read-only access for risk mitigation planning. |
| **Employee** | [View Only] (Active) | [View Only] (Active, own BU or linked to their risks) | Read-only access for awareness. |

### 2.3. Structural Field Restrictions

Certain fields are considered "structural" and cannot be modified after creation to maintain data integrity:

* **`control_level`**: Cannot change STANDARD -> LOCAL (would break inheritance chains)
* **`parent_control`**: Cannot reassign parent (would break risk-control mappings)
* **`business_unit`**: Cannot change BU ownership (would affect visibility and permissions)

**Rationale:** These fields define the control's position in the hierarchy and organizational boundaries. Changing them would be semantically equivalent to creating a new control.

**If changes needed:** Deactivate the existing control and create a new one with correct attributes.

---

## 3. Data Visibility & Segregation

The system enforces visibility rules based on control level and organizational boundaries.

### 3.1. STANDARD Controls (Organization-Wide)

* **Visibility**: ALL authenticated users can view STANDARD controls across the entire organization.
* **Rationale**: STANDARD controls are policies and templates meant to be reused across business units. Global visibility promotes standardization and prevents duplication.

### 3.2. LOCAL Controls (Business Unit Restricted)

* **Default Rule**: Users can only view LOCAL controls belonging to their business unit.
* **Exception (Contextual Visibility)**: Users can view LOCAL controls from other BUs if those controls are linked to risks they own or that belong to their BU.

**Example:**
* Finance BU Risk Officer creates LOCAL control "Finance Dual Signature Implementation"
* IT BU Manager CANNOT see this control (different BU, not linked to their risks)
* Finance Manager CAN see this control (same BU)
* IT Manager CAN see this control IF it's linked to a risk they own (e.g., shared operational risk)

### 3.3. Visibility Matrix

| User Role | STANDARD Controls | LOCAL Controls (Own BU) | LOCAL Controls (Other BUs) |
| :--- | :--- | :--- | :--- |
| **Group Risk Officer** | All | All | All |
| **BU Risk Officer** | All | All (own BU) | Only if linked to their risks |
| **Manager** | Active only | Active only (own BU) | Active only, if linked to their risks |
| **Employee** | Active only | Active only (own BU) | Active only, if linked to risks in their BU |

---

## 4. Validation & Integrity Rules

To protect the integrity of the hierarchical structure and Risk Register, the system enforces strict validation rules.

### 4.1. Hierarchical Validation Rules

These rules are enforced in the `Control.clean()` method and prevent invalid parent-child relationships:

**Rule 1: STANDARD controls cannot have parents**
* **Logic**: `if control_level == STANDARD and parent_control is not None → Error`
* **Rationale**: STANDARD controls are top-level policies. Allowing them to have parents would break the two-tier hierarchy.

**Rule 2: LOCAL controls must have parents**
* **Logic**: `if control_level == LOCAL and parent_control is None → Error`
* **Rationale**: LOCAL controls are implementations of STANDARD policies. Every implementation must reference its parent policy.

**Rule 3: LOCAL controls must have business units**
* **Logic**: `if control_level == LOCAL and business_unit is None → Error`
* **Rationale**: LOCAL controls are BU-specific by definition. They must be assigned to a business unit.

**Rule 4: STANDARD controls cannot have business units**
* **Logic**: `if control_level == STANDARD and business_unit is not None → Error`
* **Rationale**: STANDARD controls are organization-wide policies. Assigning them to a specific BU would contradict their purpose.

**Rule 5: Circular parent-child relationships are prevented**
* **Logic**: System checks the full inheritance chain to ensure a control doesn't reference itself as an ancestor.
* **Rationale**: Prevents infinite loops in hierarchy traversal and maintains data integrity.

### 4.2. Deactivation Logic

A control cannot be turned off if it is currently relied upon for risk mitigation.

* **Rule**: A Control cannot be set to `INACTIVE` if it is linked to any Risk in the `ACTIVE` state.
* **Resolution**: The Risk Officer must first unlink the control from active risks or retire the risks before deactivating the control.
* **Applies To**: Both STANDARD and LOCAL controls (though STANDARD controls cannot be linked directly, their children might be).

### 4.3. Deletion Logic

* **Rule**: Hard deletion of Controls is **strictly forbidden** via the API to preserve the audit trail of past risk assessments.
* **Resolution**: Users must use the Deactivation workflow instead (`PATCH is_active=False`).
* **Applies To**: Both STANDARD and LOCAL controls.

---

## 5. Risk-Control Integration

The interaction between Risks and Controls is governed by the RCSA workflow (managed in the Risks app), with specific rules for hierarchical controls.

### 5.1. Linkability Rules

**Critical Rule**: Only LOCAL controls can be linked to risks. STANDARD controls are templates and cannot be linked directly.

* **STANDARD Controls**: Cannot be linked to risks. Serve as policy definitions and templates.
* **LOCAL Controls**: Can be linked to risks. Represent actual implementations that mitigate specific risks.

**Rationale**: 
* STANDARD controls define "what" needs to be controlled (policy level)
* LOCAL controls define "how" it's controlled in practice (implementation level)
* Risks are mitigated by actual implementations, not abstract policies

**User Experience**: If a user attempts to link a STANDARD control, the system provides a helpful error message:
```
"STANDARD controls cannot be linked to risks. Please create a LOCAL implementation 
of this control in your business unit, or select an existing LOCAL control."
```

### 5.2. Linking Workflow

* **Pre-condition 1**: Control must be `ACTIVE`
* **Pre-condition 2**: Control must be `LOCAL` level
* **Pre-condition 3**: Risk must **not** be `RETIRED`
* **Pre-condition 4**: If control is from another BU, user must have appropriate permissions (typically Group Risk Officer only)
* **Duplicate Check**: A control cannot be linked to the same risk twice

### 5.3. Unlinking Workflow

* **Pre-condition**: Risk must **not** be `RETIRED`
* **Constraint**: An `ACTIVE` risk cannot unlink its *last* control. It must always have at least one control remaining to justify its residual score.
* **Applies To**: LOCAL controls only (since only they can be linked)

### 5.4. Business Unit Alignment

When linking LOCAL controls to risks, the system validates business unit alignment:

* **Same BU**: Local control and risk in same BU → Always allowed (if user has permissions)
* **Different BU**: Local control from BU-A linked to risk in BU-B → Allowed but logged for audit purposes
* **Rationale**: Cross-BU linkage is sometimes necessary (shared risks, enterprise-wide initiatives) but should be tracked

---

## 6. Workflow Examples

### Example 1: Creating a STANDARD Control (Group Risk Officer)

1. **Actor**: Group Risk Officer
2. **Action**: Creates new control with `control_level=STANDARD`
3. **Required Fields**: Title, Description, Type, Nature, Frequency, Owner
4. **Optional Fields**: Effectiveness rating, Reference doc
5. **Prohibited Fields**: `business_unit` (must be NULL), `parent_control` (must be NULL)
6. **Result**: STANDARD control visible to all users across organization

### Example 2: Creating a LOCAL Control (BU Risk Officer)

1. **Actor**: BU Risk Officer (Finance)
2. **Action**: Creates new control with `control_level=LOCAL`
3. **Required Fields**: Title, Description, Type, Nature, Frequency, Owner, **parent_control** (reference to STANDARD), **business_unit** (Finance)
4. **Optional Fields**: Effectiveness rating, Reference doc
5. **Result**: LOCAL control visible to Finance BU users, implements the parent STANDARD control

### Example 3: Linking Control to Risk (Risk Officer)

1. **Actor**: Risk Officer (Finance)
2. **Context**: Reviewing risk in ASSESSED status
3. **Action**: Searches control library for relevant controls
4. **Available Controls**: 
   - All STANDARD controls (read-only, cannot link)
   - All LOCAL controls in Finance BU (can link)
   - Any LOCAL controls from other BUs linked to Finance risks (can link if permissions allow)
5. **Selection**: Selects LOCAL control "Finance Dual Signature Implementation"
6. **Validation**: System checks control is LOCAL, active, and not already linked
7. **Result**: Control linked to risk with optional mitigation notes

---

## 7. Summary of Key Changes from Original Model

For reference, here's what changed from the original flat control model:

| Aspect | Original (Flat) | Current (Hierarchical) |
| :--- | :--- | :--- |
| **Control Levels** | Single level, all controls equal | Two levels: STANDARD (parent) & LOCAL (child) |
| **Business Unit** | Required for all controls | NULL for STANDARD, Required for LOCAL |
| **Roles** | Single "Risk Officer" role | Group Risk Officer & BU Risk Officer |
| **Visibility** | BU-segregated (Finance can't see IT) | STANDARD = global, LOCAL = BU-segregated |
| **Linkability** | Any active control can be linked | Only LOCAL controls can be linked |
| **Permissions** | Risk Officer edits any control in their BU | Group RO edits all, BU RO edits LOCAL in their BU |
| **Validation** | Basic (active status, no duplicates) | 5 hierarchical integrity rules |

---

**Document Version**: 2.0 (Hierarchical Model)  
**Last Updated**: December 30, 2025  
**See Also**: [CHANGELOG.md](../../../CHANGELOG.md) for implementation history