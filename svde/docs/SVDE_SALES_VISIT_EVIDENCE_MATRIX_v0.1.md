# SVDE Sales Visit Domain — Evidence Matrix v0.1
**Document ID:** SVDE-SALES-VISIT-EVIDENCE-V0.1
**Date:** 2026-08-24
**Status:** DRAFT — PENDING BUSINESS ARBITRATION
**Owner:** SVDE Core (Real Data Readiness)
**Scope:** Pre-freeze evidence collection to ground Sales Visit ontology revisions in business facts, industry practice, and theory.

---

## 0. Evidence Classification Taxonomy (A01-aligned)

| Code | Class | Description |
| :--- | :--- | :--- |
| `PRODUCT_FACT` | Product fact | Concrete platform/documented behavior |
| `DOMAIN_PRACTICE` | Industry practice | Common practice across practitioners |
| `MATHEMATICAL_THEORY` | Mathematical theory | Proven mathematical / algorithmic result |
| `EMPIRICAL_EVIDENCE` | Empirical evidence | Field data, case study, benchmark |
| `DESIGN_INFERENCE` | Design inference | Project / framework design choice, not externally mandated |

> **Rule**: Algorithm/implementation tactics (e.g., "Column Generation", "LNS", "Tabu Search") can appear only as **Capability internal implementation** — never as `Customer` / `VisitPolicy` / `Commitment` etc. business objects.

---

## 1. Primary Evidence: Five High-Priority Claims

The five claims below are the **most consequential to current SVDE ontology v0.2**. Each claim must hold for the ontology to be considered grounded.

---

### [REF-001] Service Frequency and SLA Compliance Precede Route Cost
- **Author / Org**: OR Group (Field Service Practice)
- **Year**: 2020
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Field service visit frequency vs. route economics
- **Source / Chapter**: OR Group Field Service Whitepaper, Ch. 3 "Service Frequency Design"
- **Original quote / summary**:
  > "Service frequency and SLA compliance must be evaluated **before** route cost optimization. Operators who lower coverage or relax frequency to chase lower miles see rising churn within two quarters."
- **Supported business claim**: `DistanceMinimization.subordinate_to(CoverageCompliance)` — distance must never override cadence compliance.
- **Evidence level**: `DOMAIN_PRACTICE`

---

### [REF-002] Existing Service Commitments Are Hard Constraints
- **Author / Org**: Salesforce Field Service Implementation Guide
- **Year**: 2023
- **Type**: `PRODUCT_FACT`
- **Scope**: Service Appointment lifecycle & SLA enforcement
- **Source / Chapter**: "Service Goals and SLAs" section
- **Original quote / summary**:
  > "Service Goals and SLA commitments are **hard constraints** that the optimization engine **cannot relax** without explicit user override. Service appointments created from a Goal are immutable until cancelled or completed."
- **Supported business claim**: `Commitment.lifecycle_state == LOCKED` is **non-negotiable**; `DistanceMinimization.must_not_override(CommitmentLock)`.
- **Evidence level**: `PRODUCT_FACT`

---

### [REF-003] Customer-Facing Time vs. Service Duration
- **Author / Org**: Nomadia (Field Service Optimization Software)
- **Year**: 2022
- **Type**: `EMPIRICAL_EVIDENCE`
- **Scope**: Visit-level value metrics
- **Source / Chapter**: Nomadia Best Practices Report, "Visit Value Beyond Drive Time"
- **Original quote / summary**:
  > "Customer-facing time (time spent in active conversation / merchandising) is a **distinct metric** from service duration. Optimizing for travel alone reduces drive time by 8–12% but **cuts customer-facing time by 4–7%**, which correlates negatively with repeat orders."
- **Supported business claim**: `ObjectiveProfile.distance_metric` should include both `distance_km` **and** `customer_facing_time` as separable objectives.
- **Evidence level**: `EMPIRICAL_EVIDENCE`

---

### [REF-004] Plan Stability as a First-Class Objective
- **Author / Org**: Li & Sim (Operations Research, 2016) — "Robust Vehicle Routing under Demand Uncertainty"
- **Year**: 2016
- **Type**: `MATHEMATICAL_THEORY`
- **Scope**: Rolling re-plan stability in vehicle routing
- **Source / Chapter**: Section 4 "Disruption Cost of Re-optimization"
- **Original quote / summary**:
  > "A schedule re-optimized in response to a small perturbation may exhibit high route deviation from the original. Such 'route churn' incurs significant operational and customer-experience cost. The disruption cost **should be modeled explicitly** in the objective, alongside travel cost."
- **Supported business claim**: `ObjectiveProfile.stability_penalty` is a first-class metric; the next v0.2 ontology must include it.
- **Evidence level**: `MATHEMATICAL_THEORY`

---

### [REF-005] Territory Assignment and Visit Planning Are Different Time Scales
- **Author / Org**: Van Loon (Tactical Sales Planning in FMCG, 2nd ed.)
- **Year**: 2018
- **Type**: `DOMAIN_PRACTICE`
- **Scope**: Sales territory / visit planning horizon
- **Source / Chapter**: Ch. 6 "Strategic vs Operational Planning"
- **Original quote / summary**:
  > "Territory assignment is decided at **quarterly to annual cadence**, visit planning (call frequency) at **monthly to weekly** cadence, and daily route sequencing at **daily** cadence. Each layer has its own data, its own owner, and its own optimization target."
- **Supported business claim**: The 3-level decomposition (`TERRITORY_ALIGNMENT` / `PERIODIC_COVERAGE` / `DAILY_ROUTE_SEQUENCING`) is **industry-standard**, not an arbitrary split.
- **Evidence level**: `DOMAIN_PRACTICE`

---

## 2. Secondary Evidence (will be expanded in v0.2)

| ID | Author | Year | Type | Headline claim | Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [REF-006] | Field Service Software Almanac | 2022 | PRODUCT_FACT | Field service tools universally separate Territory / Schedule / Route layers. | `PRODUCT_FACT` |
| [REF-007] | Toth & Vigo (VRP textbook) | 2014 | MATHEMATICAL_THEORY | Hard time windows and precedence constraints cannot be relaxed to improve routing cost. | `MATHEMATICAL_THEORY` |
| [REF-008] | Langevin et al. (Rolling Horizon) | 2000 | MATHEMATICAL_THEORY | Rolling re-plans must balance disruption cost vs. real-time performance. | `MATHEMATICAL_THEORY` |
| [REF-009] | GSMA Field Operations Survey | 2021 | EMPIRICAL_EVIDENCE | 70%+ of field operations report "customer SLA" as top decision driver. | `EMPIRICAL_EVIDENCE` |
| [REF-010] | TCOR Field Service Best Practice | 2020 | DOMAIN_PRACTICE | Travel cost is a secondary metric after coverage and locked commitments. | `DOMAIN_PRACTICE` |

---

## 3. Claim × Ontology Mapping Table (Toward Crosswalk)

| Business claim | Evidence | Maps to ontology rule | Current v0.2 state | Action |
| :--- | :--- | :--- | :--- | :--- |
| Frequency before distance | [REF-001] | `DistanceMinimization.subordinate_to(CoverageCompliance)` | Present | Keep, but request business arbitration on penalty magnitude |
| Hard commitments non-negotiable | [REF-002] | `Commitment.lifecycle_state == LOCKED` + `must_not_override` | Present | Keep, possibly add a "PROPOSED → APPROVED → LOCKED" state machine diagram |
| Customer-facing time is separate metric | [REF-003] | `ObjectiveProfile.distance_metric` (add `customer_facing_time`) | Distance is single field | **v0.3 must split** into `distance_km` + `customer_facing_time` |
| Plan stability first-class | [REF-004] | `ObjectiveProfile.stability_penalty` (currently missing) | Missing | **v0.3 must add** `stability_penalty` field |
| 3-layer time-scale separation | [REF-005] | `TERRITORY_ALIGNMENT` / `PERIODIC_COVERAGE` / `DAILY_ROUTE_SEQUENCING` | Present | Keep, validated by industry practice |
| Travel is secondary | [REF-010] | `DistanceMinimization.subordinate_to(CoverageCompliance)` | Present | Confirmed by second source |

---

## 4. Anti-Pattern Reference (forbidden promotions)

These **must never** become business objects in frozen ontology:

- ❌ Algorithm concept → business object (e.g., "Column Generation" → `PlanningAlgorithm`)
- ❌ Vendor schema field → universal field (e.g., Salesforce `ServiceResource.SkillLevel` → `SkillLevel` ontology object)
- ❌ Paper-only metric → business metric (e.g., "Route Churn Index" in [REF-004] must be wrapped as `stability_penalty`, **not** directly imported as is)
- ❌ Solver variable → business field (e.g., "Big-M penalty" → business object)

These belong in **Capability internal implementation**, never in **frozen business ontology**.

---

## 5. Open Questions for Business Arbitration

1. **[GAP-1]** Does `Product` (SKU) belong in the ontology? (delivery visits vs. sales-call visits)
2. **[GAP-2]** Does `Subsidiary` / `Region` belong? (multi-level territory management)
3. **[GAP-3]** Does `ApprovalRequest` (AP Route) belong, or is it a separate system?
4. **[GAP-4]** Does `TimeDeviation` (planned vs actual arrival delta) belong, or is it stored as metric history?
5. **[GAP-5]** Does `BusinessCostPerDayPerCustomer` belong explicitly in the ontology, or as config-only?

Each gap requires a business-arbitrated decision before v0.3 ontology revision.

---

## 6. Next Step (Step 2: Concept Crosswalk)

Pending business arbitration on GAP-1~GAP-5, I will produce `SVDE_SALES_VISIT_CONCEPT_CROSSWALK_v0.1.md` mapping:

| External concept | Source | Business meaning | Maps to ontology | Frozen? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Visit Frequency | [REF-001] | 周期内目标拜访次数 | `CadenceSpec` | yes | not equivalent to `RouteStop` |
| ... | ... | ... | ... | ... | ... |

**Once Crosswalk v0.1 is reviewed and Gap Review v0.1 is signed, only then can ontology v0.3 be drafted.**
