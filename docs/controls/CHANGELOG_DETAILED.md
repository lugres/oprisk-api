# Controls Module - Detailed Changelog

This document provides detailed implementation notes for the Controls module.  
For project-wide changes, see the [main CHANGELOG.md](../../CHANGELOG.md).

---

## [2.0.5] - Hierarchical Control Model - December 30, 2025

### Overview
Major architectural refactoring from flat BU-restricted controls to hierarchical STANDARD/LOCAL model with parent-child inheritance.

### 🚨 BREAKING CHANGES

#### Data Model Changes
1. **Added Fields:**
   - `control_level`: CharField with choices [`STANDARD`, `LOCAL`], default `STANDARD`
   - `parent_control`: ForeignKey to self (nullable, PROTECT on delete)

2. **Modified Fields:**
   - `business_unit`: Now nullable (NULL for STANDARD, required for LOCAL)

3. **Validation Rules (Model.clean()):**
   - Rule 1: STANDARD controls cannot have parent_control
   - Rule 2: LOCAL controls must have parent_control
   - Rule 3: LOCAL controls must have business_unit
   - Rule 4: STANDARD controls cannot have business_unit
   - Rule 5: Circular parent-child relationships prevented

#### API Changes

**Responses (All Endpoints):**
- Added `control_level` field to all Control serializers
- Added `parent_control` field (nested object with id, title, level)
- Added `child_controls` list (for STANDARD controls showing LOCAL implementations)
- Added `inheritance_chain` array (full parent→child path)

**Request Bodies:**
- POST/PATCH now accept `control_level` field
- POST/PATCH now accept `parent_control` field (required for LOCAL)
- Validation enforces hierarchical rules

**Filtering:**
- Added `?control_level=STANDARD` query parameter
- Added `?control_level=LOCAL` query parameter

#### Permission Changes

**Before (v1.0):**
- Risk Officer: Create/edit any control in their BU
- Manager/Employee: Read-only

**After (v2.0):**
- **Group Risk Officer** (RO in "Risk Management" BU):
  - Create/edit STANDARD controls (org-wide)
  - Create/edit LOCAL controls (any BU)
- **BU Risk Officer** (RO in other BUs):
  - View STANDARD controls (read-only)
  - Create/edit LOCAL controls in their BU only
- **Manager/Employee**:
  - View STANDARD controls
  - View LOCAL controls in their BU or linked to their risks

#### Visibility Changes

**Before (v1.0):**
- Controls BU-segregated (Finance cannot see IT controls)

**After (v2.0):**
- STANDARD controls: Visible to ALL users across ALL BUs
- LOCAL controls: BU-restricted (Finance sees Finance LOCAL only)

#### Risk-Control Linking Changes

**Before (v1.0):**
- Any active control could be linked to a risk

**After (v2.0):**
- **Only LOCAL controls** can be linked to risks
- STANDARD controls are NOT linkable
- Error message guides users to create LOCAL implementation

### ✨ New Features

#### 1. Hierarchical Control Architecture

**STANDARD Controls (Parent):**
- Organization-wide policies/objectives
- Managed by Group Risk Officers
- No Business Unit assignment
- Examples: "Background Check - Employees & Third Parties", "Dual Authorization - High Value Transactions"

**LOCAL Controls (Child):**
- BU-specific implementations of STANDARD controls
- Managed by BU Risk Officers
- Must reference a STANDARD parent
- Examples: "Finance Dual Signature Implementation", "IT Background Check via Vendor X"

#### 2. Control Inheritance Methods

Added to Control model:
```python
def get_inheritance_chain(self) -> List[Control]:
    """Returns full chain from root STANDARD to this control."""

def get_all_children(self) -> List[Control]:
    """Returns all descendant controls (LOCAL implementations)."""
```

#### 3. Linkability Validation

Added domain logic:
```python
# controls/workflows.py
class ControlBusinessLogic:
    @staticmethod
    def is_control_linkable(control_level: str, is_active: bool) -> bool:
        """Only LOCAL, ACTIVE controls are linkable."""
        return control_level == "LOCAL" and is_active
```

#### 4. Enhanced Serializer Context

ControlDetailSerializer now includes:
- `parent_control`: Nested representation of parent STANDARD
- `child_controls`: List of LOCAL implementations (for STANDARD controls)
- `inheritance_chain`: Full hierarchy path
- Visibility-filtered child_controls (respects user's BU permissions)

### 🔧 Changed

#### Services Layer Updates

**controls/services.py:**
- Split `create_control()` into:
  - `create_standard_control()`: For Group RO, enforces STANDARD rules
  - `create_local_control()`: For BU RO, enforces LOCAL rules
- Updated `update_control()`:
  - Prevents modification of structural fields (`control_level`, `parent_control`, `business_unit`)
  - Raises explicit error if attempted
- Updated `get_control_visibility_filter()`:
  - Added STANDARD visibility (all users)
  - Added LOCAL BU-segregation

**risks/services.py:**
- Updated `validate_control_linkage()`:
  - Checks `control.is_linkable` (LOCAL + active)
  - Provides helpful error messages with suggestions
  - Validates BU alignment for LOCAL controls

#### Workflows Layer Updates

**controls/workflows.py:**
- Added `ControlBusinessLogic` class:
  - `is_control_linkable()`: Pure domain rule
  - `get_linkability_reasons()`: Explains why control not linkable
- Added role helpers:
  - `is_group_risk_officer()`: Risk Officer + Risk Management BU
  - `is_bu_risk_officer()`: Risk Officer + other BU
- Updated permissions:
  - `can_create_standard_control()`: Only Group RO
  - `can_create_local_control()`: Group RO or BU RO
  - `can_edit_control()`: Context-dependent (Group RO all, BU RO local only)

**risks/workflows.py:**
- Added `validate_bu_alignment_for_control_linking()`:
  - Pure domain function for BU alignment check
  - Returns (bool, error_message) tuple

#### Admin Interface Updates

**controls/admin.py:**
- Added "Hierarchy & Classification" fieldset
- Added `control_level` and `parent_control` to list_display
- Added `control_level` to list_filter (first filter for prominence)
- Added `parent_control` to autocomplete_fields

#### Test Suite Updates

**controls/tests/test_models.py:**
- Updated setUp to create STANDARD + LOCAL controls
- Added 10 new tests for hierarchical validation
- Added tests for `get_inheritance_chain()` and `get_all_children()`

**controls/tests/test_admin.py:**
- Updated setUp to create Group RO user
- Added tests for STANDARD control creation/editing
- Added tests for LOCAL control creation with parent
- Added 3 new validation tests (prevent invalid hierarchies)
- Added hierarchy display tests (parent/children in changelist)

**controls/tests/test_api.py:**
- Updated setUp to create hierarchical control structure
- Renamed/updated tests to reflect STANDARD vs LOCAL
- Added tests for Group RO vs BU RO permissions
- Added test for structural field immutability
- Added tests for hierarchy features (filter by level, inheritance chain)

**risks/tests/test_api.py:**
- Updated setUp to create LOCAL controls with parents
- Added test: cannot link STANDARD control to risk
- Added test: Manager cannot link controls (only RO)
- Controls properly created with `control_level=LOCAL` and `parent_control`

### 🐛 Bug Fixes

- Fixed `__str__` method f-string bug (was `"[STD] self.title"`, now `"[STD] {self.title}"`)
- Fixed `assertFormError` API compatibility in admin tests (Django version issue)
- Added missing `control_nature` field to test form submissions

### 📚 Documentation Updates

- Added ADR-002: Architectural Decision Record for hierarchical model
- Updated BRD with hierarchical model rationale
- Updated API contracts with control_level field
- Updated workflow rules with STANDARD/LOCAL distinctions
- Added this detailed CHANGELOG

### 🔄 Migration Guide

**For Administrators:**
1. Review existing controls - identify which should be STANDARD policies
2. Have Group Risk team create STANDARD controls for common policies
3. Create LOCAL controls as children of STANDARD parents
4. Update risk-control links (only LOCAL controls can be linked)

**For Developers:**
1. Database migration adds `control_level` and `parent_control` fields
2. Existing controls default to `control_level=STANDARD` (or LOCAL with BU)
3. Update any custom code that creates controls to specify level
4. Update tests that assume flat control structure

**Breaking Changes Checklist:**
- [ ] Review API clients - add `control_level` field handling
- [ ] Update control creation code - specify STANDARD or LOCAL
- [ ] Update control queries - consider STANDARD visibility
- [ ] Update linking code - validate LOCAL-only linking
- [ ] Test permission changes - Group RO vs BU RO

---

## [1.0.3] - Initial Implementation - December 10, 2025

### ✨ Initial Features

#### Core Functionality
- Control library with CRUD operations
- Control types: Preventive, Detective, Corrective
- Control nature: Manual, Automated, Hybrid
- Control frequency: Continuous, Daily, Weekly, Monthly, Quarterly, Annually, Ad-hoc
- Design effectiveness rating (1-5 scale)

#### Data Model
- Control entity with TimestampedModel and OwnedModel mixins
- Business Unit assignment (required)
- Control owner (required)
- Reference documentation links
- Active/Inactive status

#### Permissions
- Risk Officer: Full CRUD on controls in their BU
- Manager: Read-only access to active controls
- Employee: Read-only access to active controls

#### Risk Integration
- Many-to-many relationship with Risks via RiskControl link table
- Link/unlink actions on Risk API
- Control requirement for risk approval (ASSESSED → ACTIVE)
- Control count in risk detail responses

#### API Endpoints
- `GET /api/controls/` - List controls (paginated, filtered)
- `POST /api/controls/` - Create control
- `GET /api/controls/{id}/` - Control detail
- `PATCH /api/controls/{id}/` - Update control
- `DELETE /api/controls/{id}/` - Forbidden (use deactivate)
- `POST /api/risks/{id}/link-to-control/` - Link control to risk
- `POST /api/risks/{id}/unlink-from-control/` - Unlink control from risk

#### Filtering & Search
- Filter by: control_type, control_nature, business_unit, is_active
- Search by: title, description (case-insensitive)

#### Validation Rules
- Cannot deactivate control if linked to ACTIVE risks
- Cannot link inactive controls to risks
- Cannot link same control twice to same risk
- Cannot unlink last control from ACTIVE risk

---

## Version History Summary

| Version | Date | Type | Description |
|---------|------|------|-------------|
| 2.0.5 | 2025-12-30 | Major | Hierarchical control model (STANDARD/LOCAL) |
| 1.0.3 | 2025-12-10 | Major | Initial implementation |

---

## Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version (X.0.0): Incompatible API changes, breaking changes
- **MINOR** version (0.X.0): New functionality, backward-compatible
- **PATCH** version (0.0.X): Bug fixes, backward-compatible

---

## Contributing

When updating this changelog:
1. Add new entries under `[Unreleased]` section at the top
2. Use categories: Breaking Changes, New Features, Changed, Fixed, Deprecated, Removed
3. When releasing, move `[Unreleased]` to new version with date
4. Link to relevant issues/PRs where applicable
5. Keep entries concise but descriptive

---

## References

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [ADR-002: Hierarchical Control Model](./adr/002_adr_controls_Hierarchical_analysis_detailed.md)
- [Controls Module BRD](./brd/controls_design_specs_detailed.md)