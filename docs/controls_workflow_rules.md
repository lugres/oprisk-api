# Controls Workflow & Business Rules

This document defines the business logic and lifecycle rules for the **Controls** module. Unlike Risks or Incidents, Controls do not follow a complex state machine; they function as a **Library** of reusable assets.

## 1. Control Lifecycle

The Control entity has a simple binary state designed to preserve historical data while maintaining a clean library for current operations.

* **`ACTIVE` (`is_active=True`):** The control is operational and available for use. It can be linked to new risks.
* **`INACTIVE` (`is_active=False`):** The control is deprecated or no longer in use. It is hidden from standard views but preserved for audit trails. It cannot be linked to new risks.

---

## 2. Permission Model (Segregation of Duties)

Access to the Control Library is strictly governed to ensure standardization.

| Role | Action | Permissions |
| :--- | :--- | :--- |
| **Risk Officer** | **Create/Edit** | ✅ **Allowed.** Full control over the library content (Description, Type, Effectiveness). |
| **Risk Officer** | **Deactivate** | ✅ **Allowed**, but conditional (see *Validation Rules*). |
| **Risk Officer** | **View** | ✅ **All.** Can see both Active and Inactive controls. |
| **Manager** | **Create/Edit** | ❌ **Denied.** Managers cannot modify the library. |
| **Manager** | **View** | ✅ **Restricted.** Can only see Active controls, or Inactive controls specifically linked to their Risks. |
| **Employee** | **Create/Edit** | ❌ **Denied.** |
| **Employee** | **View** | ✅ **Restricted.** Same as Manager. |

---

## 3. Data Visibility & Segregation

The system enforces visibility rules to keep the library manageable while respecting organizational boundaries.

* **Risk Officer:** Views **ALL** controls within their Business Unit (Active & Inactive) to manage the library.
* **Manager / Employee:**
    1.  Views **Active** controls within their Business Unit.
    2.  Views any control (even from other BUs) if it is linked to a Risk they own or that belongs to their BU (Contextual Visibility).

---

## 4. Validation & Integrity Rules

To protect the integrity of the Risk Register, the system enforces strict dependency rules.

### 4.1. Deactivation Logic
A control cannot be turned off if it is currently relied upon for risk mitigation.

* **Rule:** A Control cannot be set to `INACTIVE` if it is linked to any Risk in the `ACTIVE` state.
* **Resolution:** The Risk Officer must first unlink the control from the active risks or retire the risks before deactivating the control.

### 4.2. Deletion Logic
* **Rule:** Hard deletion of Controls is **strictly forbidden** via the API to preserve the audit trail of past risk assessments.
* **Resolution:** Users must use the Deactivation workflow instead.

---

## 5. Risk-Control Integration

The interaction between Risks and Controls is governed by the RCSA workflow (managed in the Risks app).

* **Linking:**
    * **Pre-condition:** Control must be `ACTIVE`.
    * **Pre-condition:** Risk must **not** be `RETIRED`.
    * **Duplicate Check:** A control cannot be linked to the same risk twice.

* **Unlinking:**
    * **Pre-condition:** Risk must **not** be `RETIRED`.
    * **Constraint:** An `ACTIVE` risk cannot unlink its *last* control. It must always have at least one control remaining to justify its residual score.