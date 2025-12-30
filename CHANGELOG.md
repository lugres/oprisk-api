# Operational Risk Management Platform - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.5] - late December 2025

### 🚨 BREAKING CHANGES

#### Controls Module
- **Hierarchical Control Model**: Introduced STANDARD (org-wide) and LOCAL (BU-specific) control levels with parent-child inheritance
- **API Changes**: `control_level` and `parent_control` fields added to all Control responses
- **Linking Rules**: Only LOCAL controls can be linked to risks (STANDARD controls are not linkable)

#### Risks Module  
- **Risk-Control Linking**: Updated validation to enforce LOCAL-only control linking
- **Visibility**: STANDARD controls now visible across all Business Units

### ✨ New Features

#### Controls Module
- Group Risk Officer role can create STANDARD controls (organization-wide policies)
- BU Risk Officers can create LOCAL controls (BU-specific implementations)
- Parent-child control relationships with inheritance chains
- Hierarchical integrity validation (5 rules enforced in model.clean())

### 🔧 Changed

#### Controls Module
- Permission model: Group RO (edit all) vs BU RO (edit LOCAL in their BU)
- Visibility rules: STANDARD controls visible to all, LOCAL controls BU-restricted
- Business Unit field now nullable (NULL for STANDARD, required for LOCAL)

### 📝 Migration Notes

- Existing controls should be reviewed and potentially converted to hierarchical structure
- Group Risk team should create STANDARD controls for common policies
- BU teams create LOCAL implementations linked to STANDARD parents

**Detailed Controls Module Changelog**: See [docs/controls/CHANGELOG_DETAILED.md](docs/controls/CHANGELOG_DETAILED.md)

---

## [1.0.3] - early December 2025

### ✨ Initial Release

#### Controls Module
- Centralized control library with CRUD operations
- Control attributes: type, nature, frequency, effectiveness
- Risk-control many-to-many linkage
- Role-based permissions (Risk Officer, Manager, Employee)

#### Risks Module
- Risk register with DRAFT → ASSESSED → ACTIVE workflow
- Inherent and residual risk scoring
- Basel event type mapping

#### Measures Module
- Corrective action management
- Status tracking

#### Incidents Module
- Loss event tracking
- Multi-status workflow

---

## [0.0.8] - late November 2025

### ✨ Beta Release

#### Risks Module
- Risk register with DRAFT → ASSESSED → ACTIVE workflow
- Inherent and residual risk scoring
- Basel event type mapping

#### Measures Module
- Corrective action management
- Status tracking

#### Incidents Module
- Loss event tracking
- Multi-status workflow