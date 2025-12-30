# "OOP/Hierarchical" Model - brief summary

**"OOP/Hierarchical"** proposal addresses the specific reality of small/medium European banks where "Risk Officer" is often a "hat" worn by a business manager, not a dedicated profession.

Here is the deep analysis of proposed **Hierarchical (Parent-Child)** approach compared to the previous options.

---

## Table of Contents

1. [Analysis of "OOP/Hierarchical" Model](#1-analysis-of-oophierarchical-model)
2. [Comparison with Previous Options](#2-comparison-with-previous-options)
3. [Industry Best Practices Check](#3-industry-best-practices-check)
4. [Verdict & Recommendation](#4-verdict-and-recommendation)

---

### 1. Analysis of "OOP/Hierarchical" Model

**The Concept:**

  * **Parent Control (Class):** Abstract/General. Owned by Central Risk. (e.g., "Background Checks").
  * **Child Control (Instance):** Concrete/Specific. Owned by BU. (e.g., "HR Automated Background Check via Vendor X").
  * **Constraint:** A BU cannot create a "root" control; they must "inherit" (implement) a central one.

#### Pros

  * **✅ Guardrails for Non-Experts:** This is the biggest win. Since BU Risk Officers are "functional" (business-focused, less risk-savvy), this model **forces** them to align with a central standard. They don't have to invent control definitions; they just implement pre-defined objectives.
  * **✅ Reporting Power:** You can report on "Effectiveness of Background Checks" globally by aggregating all the Child controls linked to that Parent.
  * **✅ Audit Traceability:** Auditors can pick a Central Policy ("Must check backgrounds") and instantly see every specific implementation across the bank.

#### Cons

  * **⚠️ MVP Complexity:** It requires a recursive data structure (`parent = ForeignKey('self')`) and slightly more complex UI (picking a parent before creating).
  * **⚠️ Bottleneck Risk:** If a BU has a unique risk that *doesn't* fit a central category, they are blocked until the Central team creates the Parent.

-----

### 2. Comparison with Previous Options

| Feature | Trust-Based | Federated | Hierarchical |
| :--- | :--- | :--- | :--- |
| **Primary Philosophy** | "Remove friction; clean up later." | "Local autonomy with global read." | **"Central Standards, Local Implementation."** |
| **Trust Level** | **High.** Assumes ROs are experts who won't create "junk." | **Medium.** Assumes ROs know their domain. | **Low.** Assumes ROs are functional/busy and need guidance. |
| **Data Structure** | Flat List (Null BU for global). | Flat List (Siloed ownership). | **Tree Structure** (Parent $\to$ Child). |
| **Standardization** | Voluntary (RO *chooses* to reuse). | Weak (likely duplication). | **Enforced** (RO *must* select parent). |
| **Best Fit For...** | Mature teams / Fast MVP. | Large, autonomous divisions. | **SMBs / Low Maturity / High Regulation.** |

### 3. Industry Best Practices Check

Does "OOP" model match industry standards? **Yes, perfectly.**

In frameworks like **COSO** and **COBIT**, this is formally known as:

1.  **Control Objective ("Parent"):** "Access to systems should be restricted to authorized users." (Central/Policy Level).
2.  **Control Activity ("Child"):** "Active Directory password rotation every 90 days." (Operational Level).

Enterprise GRC tools (ServiceNow GRC, RSA Archer) use this exact model:

  * **Policy/Citation:** The rule.
  * **Control Objective:** The generic requirement.
  * **Control Instance:** The specific implementation applied to an asset/process.

### 4. Verdict and Recommendation

**Proposal to use Hierarchical control model is the superior architectural fit for this specific business context.**

The "Trust-Based" model supported earlier works for *agile software teams* or *expert risk teams*. It fails in environments where the "Risk Officer" is a busy HR Manager doing this on Friday afternoons. They will create duplicate, poorly named controls if not guided.

**Recommendation for MVP Implementation:**

You can achieve your "OOP" model without over-engineering it.

**1. Data Model Change:**
Add a self-referential Foreign Key to the `Control` model.

```python
class Control(models.Model):
    # ... existing fields ...
    
    # The "OOP" Link
    parent = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.PROTECT,
        related_name='implementations',
        help_text="The central control objective this specific control implements."
    )
    
    # Helper to distinguish types
    is_standard = models.BooleanField(
        default=False, 
        help_text="Is this a central standard/parent control?"
    )
```

**2. Permission Logic (The "Guardrail"):**

  * **Central Risk Team:** Can create controls where `is_standard=True` (Parents).
  * **BU Risk Officer:**
      * Can **only** create controls where `parent` is NOT NULL (Children).
      * Can **only** link `parent` to an existing `is_standard` control.
      * Cannot create `is_standard=True` controls.

**3. Workflow:**

1.  **Central Team** populates the library with 20-50 "Standard Controls" (Objectives).
2.  **BU Risk Officer** logs in. They see a dropdown of these Standards.
3.  They click "Implement Control" on "Background Checks".
4.  The system pre-fills the Title/Description from the parent.
5.  The RO edits it to match their specific procedure ("Manual check by Linda") and saves.

**Conclusion:**
Go with **Hierarchical approach**. It solves the "skill gap" problem in SMBs and aligns perfectly with the COSO "Objective vs. Activity" framework. It adds slight development effort (one FK + one validation rule) but saves massive cleanup effort later.