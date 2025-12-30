# Controls API Contracts

This document outlines the API contracts for the **Controls (Mitigation)** module. These endpoints manage the central library of hierarchical controls. Note that linking controls to risks is handled via the **Risks API**.

## Authentication

All endpoints require Token-based authentication: `Authorization: Token <your_auth_token>`

---

## Core Endpoints (CRUD)

### `POST /api/controls/`

**Action:** Creates a new control in the library (STANDARD or LOCAL).

**Permissions:** 
* **Group Risk Officer**: Can create both STANDARD and LOCAL controls
* **BU Risk Officer**: Can create LOCAL controls only (in their BU)
* **Others**: Forbidden

**Request Body (STANDARD Control):**
```json
{
  "title": "Background Check - Employees & Third Parties",
  "description": "All employees and third-party contractors must undergo background screening before access is granted.",
  "control_type": "PREVENTIVE",
  "control_nature": "MANUAL",
  "frequency": "AD_HOC",
  "control_level": "STANDARD",
  "effectiveness": 4,
  "reference_doc": "https://intranet/policies/hr-001",
  "owner": 5
  // Note: business_unit and parent_control must be NULL/omitted for STANDARD
}
```

**Request Body (LOCAL Control):**
```json
{
  "title": "Finance Automated Background Check via Vendor X",
  "description": "Finance department uses Vendor X's automated platform for background checks. Results reviewed by HR within 48 hours.",
  "control_type": "PREVENTIVE",
  "control_nature": "HYBRID",
  "frequency": "AD_HOC",
  "control_level": "LOCAL",
  "parent_control": 1,  // Required: Reference to STANDARD parent
  "business_unit": 2,   // Required: Finance BU
  "effectiveness": 4,
  "reference_doc": "https://intranet/finance/procedures/bg-check",
  "owner": 8
}
```

**Validation:**
* Fails if BU Risk Officer attempts to create STANDARD control (403 Forbidden)
* Fails if `control_level=LOCAL` but `parent_control` or `business_unit` missing (400 Bad Request)
* Fails if `control_level=STANDARD` but `parent_control` or `business_unit` provided (400 Bad Request)
* Parent control must exist and be STANDARD level
* Business unit must exist if provided

**Response (201 Created):**
```json
{
  "id": 10,
  "title": "Finance Automated Background Check via Vendor X",
  "description": "Finance department uses Vendor X's automated platform...",
  "control_type": "PREVENTIVE",
  "control_nature": "HYBRID",
  "frequency": "AD_HOC",
  "control_level": "LOCAL",
  "parent_control": {
    "id": 1,
    "title": "Background Check - Employees & Third Parties",
    "control_level": "STANDARD"
  },
  "business_unit": {
    "id": 2,
    "name": "Finance"
  },
  "effectiveness": 4,
  "reference_doc": "https://intranet/finance/procedures/bg-check",
  "owner": {
    "id": 8,
    "full_name": "Jane Smith"
  },
  "is_active": true,
  "created_by": {
    "id": 3,
    "full_name": "John Doe"
  },
  "created_at": "2025-12-30T10:30:00Z",
  "updated_at": "2025-12-30T10:30:00Z",
  "permissions": {
    "can_edit": true,
    "can_deactivate": true
  },
  "linked_risks_count": 0,
  "active_risks_count": 0,
  "child_controls": []  // Empty for LOCAL controls; populated for STANDARD
}
```

---

### `GET /api/controls/`

**Action:** Lists controls visible to the authenticated user.

**Permissions:** Any authenticated user.

**Query Logic:**
* **Group Risk Officer**: Sees ALL controls (STANDARD + LOCAL, all BUs, Active/Inactive)
* **BU Risk Officer**: Sees ALL STANDARD controls + LOCAL controls in their BU (Active/Inactive)
* **Manager/Employee**: Sees ACTIVE STANDARD controls + ACTIVE LOCAL controls in their BU + any controls linked to their risks

**Query Parameters (Filtering):**
* `is_active`: Boolean (`true`/`false`) - Filter by active status
* `control_level`: `STANDARD` or `LOCAL` - Filter by hierarchy level
* `control_type`: `PREVENTIVE`, `DETECTIVE`, `CORRECTIVE` - Filter by control type
* `control_nature`: `MANUAL`, `AUTOMATED`, `HYBRID` - Filter by automation level
* `business_unit`: ID - Filter by business unit (LOCAL controls only)
* `parent_control`: ID - Filter by parent control (LOCAL controls only)
* `search`: Text - Search in title and description (case-insensitive)

**Example Request:**
```
GET /api/controls/?control_level=STANDARD&is_active=true&search=background
```

**Response (200 OK):**
```json
{
  "count": 45,
  "next": "https://api.example.com/api/controls/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Background Check - Employees & Third Parties",
      "control_type": "PREVENTIVE",
      "control_nature": "MANUAL",
      "frequency": "AD_HOC",
      "control_level": "STANDARD",
      "parent_control": null,
      "business_unit": null,
      "effectiveness": 4,
      "is_active": true,
      "owner": {
        "id": 5,
        "full_name": "Alice Johnson"
      },
      "linked_risks_count": 0,  // STANDARD controls not linkable
      "child_controls_count": 3  // Number of LOCAL implementations
    },
    {
      "id": 10,
      "title": "Finance Automated Background Check via Vendor X",
      "control_type": "PREVENTIVE",
      "control_nature": "HYBRID",
      "frequency": "AD_HOC",
      "control_level": "LOCAL",
      "parent_control": {
        "id": 1,
        "title": "Background Check - Employees & Third Parties"
      },
      "business_unit": {
        "id": 2,
        "name": "Finance"
      },
      "effectiveness": 4,
      "is_active": true,
      "owner": {
        "id": 8,
        "full_name": "Jane Smith"
      },
      "linked_risks_count": 5,
      "active_risks_count": 3
    }
  ]
}
```

---

### `GET /api/controls/{id}/`

**Action:** Retrieves a single control with full details.

**Permissions:** Any authenticated user (subject to visibility rules).

**Response (200 OK) - STANDARD Control:**
```json
{
  "id": 1,
  "title": "Background Check - Employees & Third Parties",
  "description": "All employees and third-party contractors must undergo background screening before access is granted.",
  "control_type": "PREVENTIVE",
  "control_nature": "MANUAL",
  "frequency": "AD_HOC",
  "control_level": "STANDARD",
  "parent_control": null,
  "business_unit": null,
  "effectiveness": 4,
  "reference_doc": "https://intranet/policies/hr-001",
  "owner": {
    "id": 5,
    "full_name": "Alice Johnson",
    "email": "alice.johnson@example.com"
  },
  "is_active": true,
  "created_by": {
    "id": 2,
    "full_name": "Bob Williams"
  },
  "created_at": "2025-11-29T14:20:00Z",
  "updated_at": "2025-12-15T09:45:00Z",
  "permissions": {
    "can_edit": true,      // Group RO: true, BU RO: false
    "can_deactivate": true // Group RO: true, BU RO: false
  },
  "linked_risks_count": 0,  // STANDARD controls cannot be linked
  "active_risks_count": 0,
  "child_controls": [
    {
      "id": 10,
      "title": "Finance Automated Background Check via Vendor X",
      "control_level": "LOCAL",
      "business_unit": {
        "id": 2,
        "name": "Finance"
      },
      "is_active": true
    },
    {
      "id": 15,
      "title": "IT Manual Background Check Process",
      "control_level": "LOCAL",
      "business_unit": {
        "id": 3,
        "name": "IT"
      },
      "is_active": true
    }
  ],
  "inheritance_chain": [
    {
      "id": 1,
      "title": "Background Check - Employees & Third Parties",
      "control_level": "STANDARD"
    }
  ]
}
```

**Response (200 OK) - LOCAL Control:**
```json
{
  "id": 10,
  "title": "Finance Automated Background Check via Vendor X",
  "description": "Finance department uses Vendor X's automated platform for background checks. Results reviewed by HR within 48 hours.",
  "control_type": "PREVENTIVE",
  "control_nature": "HYBRID",
  "frequency": "AD_HOC",
  "control_level": "LOCAL",
  "parent_control": {
    "id": 1,
    "title": "Background Check - Employees & Third Parties",
    "control_level": "STANDARD",
    "effectiveness": 4
  },
  "business_unit": {
    "id": 2,
    "name": "Finance",
    "code": "FIN"
  },
  "effectiveness": 4,
  "reference_doc": "https://intranet/finance/procedures/bg-check",
  "owner": {
    "id": 8,
    "full_name": "Jane Smith",
    "email": "jane.smith@example.com"
  },
  "is_active": true,
  "created_by": {
    "id": 3,
    "full_name": "John Doe"
  },
  "created_at": "2025-12-30T10:30:00Z",
  "updated_at": "2025-12-30T10:30:00Z",
  "permissions": {
    "can_edit": true,      // Group RO: true, BU RO in Finance: true, others: false
    "can_deactivate": true // Same as can_edit
  },
  "linked_risks_count": 5,
  "active_risks_count": 3,
  "child_controls": [],  // LOCAL controls don't have children
  "inheritance_chain": [
    {
      "id": 1,
      "title": "Background Check - Employees & Third Parties",
      "control_level": "STANDARD"
    },
    {
      "id": 10,
      "title": "Finance Automated Background Check via Vendor X",
      "control_level": "LOCAL"
    }
  ]
}
```

**Response Context Includes:**
* `permissions`: Computed based on user's role and control ownership
* `linked_risks_count`: Total number of risks using this control
* `active_risks_count`: Number of ACTIVE risks using this control
* `child_controls`: List of LOCAL implementations (STANDARD only)
* `inheritance_chain`: Full hierarchy from root to current control

---

### `PATCH /api/controls/{id}/`

**Action:** Updates control attributes.

**Permissions:** 
* **Group Risk Officer**: Can edit all controls
* **BU Risk Officer**: Can edit LOCAL controls in their BU only
* **Others**: Forbidden

**Editable Fields:**
* `title`, `description`, `effectiveness`, `reference_doc`, `owner`, `frequency`, `control_type`, `control_nature`, `is_active`

**Structural Fields (IMMUTABLE):**
* `control_level`: Cannot change STANDARD ↔ LOCAL
* `parent_control`: Cannot reassign parent
* `business_unit`: Cannot change BU ownership

**Request Body:**
```json
{
  "description": "Updated procedure: Finance now uses Vendor Y platform with 24-hour SLA.",
  "effectiveness": 5,
  "reference_doc": "https://intranet/finance/procedures/bg-check-v2"
}
```

**Validation:**
* Fails if attempting to modify structural fields (400 Bad Request with clear error message)
* If setting `is_active=false`, checks for dependencies (linked to ACTIVE risks) → 400 Bad Request if found
* BU Risk Officer attempting to edit STANDARD control → 403 Forbidden
* BU Risk Officer attempting to edit LOCAL control in another BU → 403 Forbidden

**Response (200 OK):** Same structure as GET detail, with updated fields.

**Error Response (400 Bad Request - Structural Field):**
```json
{
  "error": "Cannot modify structural fields",
  "detail": "The following fields cannot be modified after creation: control_level, parent_control, business_unit. To change these, deactivate this control and create a new one.",
  "immutable_fields": ["control_level", "parent_control", "business_unit"]
}
```

**Error Response (400 Bad Request - Deactivation Blocked):**
```json
{
  "error": "Cannot deactivate control",
  "detail": "This control is linked to 3 ACTIVE risks. Unlink the control from these risks before deactivating.",
  "active_risks": [
    {"id": 15, "title": "Fraud - Unauthorized Hiring"},
    {"id": 22, "title": "Compliance - Background Check Failure"},
    {"id": 30, "title": "HR Process - Inadequate Screening"}
  ]
}
```

---

### `DELETE /api/controls/{id}/`

**Action:** Hard delete (FORBIDDEN).

**Permissions:** None.

**Behavior:** Always returns `403 Forbidden` with instructional message.

**Response (403 Forbidden):**
```json
{
  "error": "Deletion forbidden",
  "detail": "Hard deletion of controls is not allowed to preserve audit trail. Use PATCH to set is_active=false instead.",
  "alternative_action": "PATCH /api/controls/{id}/ with {\"is_active\": false}"
}
```

---

## Risk-Control Linkage Endpoints

These endpoints are in the **Risks API** but are documented here for completeness.

### `POST /api/risks/{risk_id}/link-to-control/`

**Action:** Links a LOCAL control to a risk.

**Permissions:** Risk Officer only.

**Request Body:**
```json
{
  "control_id": 10,
  "notes": "This control mitigates the risk of hiring individuals with fraudulent credentials by verifying employment history and criminal records."
}
```

**Validation:**
* Control must exist and be ACTIVE
* Control must be LOCAL level (STANDARD controls cannot be linked)
* Control cannot already be linked to this risk
* Risk cannot be RETIRED

**Response (200 OK):**
```json
{
  "message": "Control linked successfully",
  "risk_control": {
    "control": {
      "id": 10,
      "title": "Finance Automated Background Check via Vendor X",
      "control_level": "LOCAL",
      "effectiveness": 4
    },
    "notes": "This control mitigates the risk of hiring...",
    "linked_by": {
      "id": 3,
      "full_name": "John Doe"
    },
    "linked_at": "2025-12-30T14:22:00Z"
  }
}
```

**Error Response (400 Bad Request - STANDARD Control):**
```json
{
  "error": "Cannot link STANDARD control",
  "detail": "STANDARD controls are organization-wide policies and cannot be linked to risks. Please create a LOCAL implementation of this control in your business unit, or select an existing LOCAL control.",
  "parent_control": {
    "id": 1,
    "title": "Background Check - Employees & Third Parties"
  },
  "suggestion": "Create a LOCAL control with parent_control=1 in your business unit"
}
```

---

### `POST /api/risks/{risk_id}/unlink-from-control/`

**Action:** Unlinks a control from a risk.

**Permissions:** Risk Officer only.

**Request Body:**
```json
{
  "control_id": 10
}
```

**Validation:**
* Control must be linked to this risk
* Risk cannot be RETIRED
* Cannot unlink last control from ACTIVE risk (must have at least one)

**Response (200 OK):**
```json
{
  "message": "Control unlinked successfully"
}
```

---

## Field Reference

### Control Types
* `PREVENTIVE`: Stops errors or irregularities from occurring before they happen.
* `DETECTIVE`: Identifies errors or irregularities after they occur but before significant impact.
* `CORRECTIVE`: Remedial action taken to correct an error (mostly covered by Measures module, use sparingly).

### Control Nature
* `MANUAL`: Performed entirely by humans without IT system dependency.
* `AUTOMATED`: Performed entirely by systems without human intervention.
* `HYBRID`: IT-Dependent Manual - requires both system and human action.

### Control Level (NEW)
* `STANDARD`: Organization-wide policy or control objective. Defines WHAT needs to be controlled. Cannot be linked to risks. Visible to all users. Managed by Group Risk Officers.
* `LOCAL`: Business unit-specific implementation of a STANDARD control. Defines HOW it's controlled in practice. Can be linked to risks. BU-restricted visibility. Managed by BU Risk Officers.

### Control Frequency
* `CONTINUOUS`: Ongoing, real-time (e.g., access controls, firewalls)
* `DAILY`: Performed every business day
* `WEEKLY`: Performed once per week
* `MONTHLY`: Performed once per month
* `QUARTERLY`: Performed once per quarter
* `ANNUALLY`: Performed once per year
* `AD_HOC`: Event-driven, performed as needed

### Effectiveness
* **Scale:** 1 (Ineffective) to 5 (Highly Effective)
* **Scope:** Represents **Design Effectiveness** (how well the control *should* work in theory if operated perfectly)
* **Note:** Operating effectiveness (how well it works in practice) is tracked separately during control testing (future phase)

---

## Common Use Cases

### Use Case 1: Group Risk Officer Creates STANDARD Control

**Request:**
```
POST /api/controls/
Authorization: Token abc123

{
  "title": "Dual Authorization - High Value Transactions",
  "description": "All transactions exceeding defined thresholds require approval from two authorized individuals.",
  "control_type": "PREVENTIVE",
  "control_nature": "HYBRID",
  "frequency": "CONTINUOUS",
  "control_level": "STANDARD",
  "effectiveness": 4,
  "reference_doc": "https://intranet/policies/fin-002",
  "owner": 5
}
```

**Result:** STANDARD control created, visible to all users, cannot be linked to risks.

---

### Use Case 2: BU Risk Officer Creates LOCAL Implementation

**Request:**
```
POST /api/controls/
Authorization: Token def456

{
  "title": "Finance Two-Signature Wire Transfers >$50K",
  "description": "Finance implements dual authorization via banking platform. Requires VP Finance + CFO approval for wires exceeding $50K.",
  "control_type": "PREVENTIVE",
  "control_nature": "AUTOMATED",
  "frequency": "CONTINUOUS",
  "control_level": "LOCAL",
  "parent_control": 5,  // Reference to "Dual Authorization - High Value Transactions"
  "business_unit": 2,   // Finance
  "effectiveness": 5,
  "reference_doc": "https://intranet/finance/procedures/wire-approval",
  "owner": 8
}
```

**Result:** LOCAL control created in Finance BU, inherits from STANDARD parent, can be linked to risks.

---

### Use Case 3: Risk Officer Links LOCAL Control to Risk

**Request:**
```
POST /api/risks/15/link-to-control/
Authorization: Token def456

{
  "control_id": 20,  // Finance Two-Signature Wire Transfers
  "notes": "This control prevents unauthorized wire transfers by requiring dual approval from senior finance leadership."
}
```

**Result:** Control linked to risk, appears in risk detail, contributes to residual risk justification.

---

### Use Case 4: Manager Views Controls for Their Risk

**Request:**
```
GET /api/controls/?control_level=LOCAL&business_unit=2
Authorization: Token ghi789
```

**Result:** Manager sees:
* All ACTIVE STANDARD controls (organization-wide visibility)
* All ACTIVE LOCAL controls in their BU (Finance)
* Any controls from other BUs that are linked to risks they own

---

### Use Case 5: Filtering STANDARD Controls Only

**Request:**
```
GET /api/controls/?control_level=STANDARD&is_active=true
```

**Result:** List of all active STANDARD controls (organizational policies), useful for BU Risk Officers browsing for parents when creating LOCAL controls.

---

## Migration Notes

For systems upgrading from the flat control model:

1. **Existing controls**: Should be reviewed and assigned appropriate `control_level` (STANDARD or LOCAL)
2. **Default behavior**: New `control_level` field defaults to `STANDARD` in database migration
3. **Backward compatibility**: Existing API clients must be updated to handle new fields
4. **Linking validation**: Existing risk-control links are preserved, but new links must use LOCAL controls only

---

**Document Version**: 2.0 (Hierarchical Model)  
**Last Updated**: December 30, 2025  
**See Also**: 
* [controls_workflow_rules.md](controls_workflow_rules.md) for business logic
* [CHANGELOG.md](../../../CHANGELOG.md) for implementation history