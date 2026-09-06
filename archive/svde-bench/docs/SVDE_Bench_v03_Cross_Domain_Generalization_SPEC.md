# SVDE-Bench v0.3 — Cross-Domain Generalization & Multi-Domain Evaluation Specification
**Document ID:** SVDE-BENCH-V03-DESIGN-SPEC-V1.0  
**Date:** 2026-08-24  
**Classification:** Governed Architectural & Methodological Specification  
**Status:** **PROPOSED & GOVERNED (Design Sprint Phase — Zero Code Changes)**  

---

## 1. Project Motivation & Core Objective

SVDE-Bench v0.2 demonstrated that **Decision Intelligence** can be rigorously and continuously evaluated within a single business domain (`Delivery`, D01–D10). 

**The primary objective of SVDE-Bench v0.3 is to establish and prove Cross-Domain Generalization:**
> To empirically prove that the **Decision Compiler Pattern**, **Pattern-Driven Synthesis Framework**, and **Memory Governance Lifecycle** are domain-invariant, transferring seamlessly across distinct enterprise decision typologies without structural redesign.

---

## 2. v0.3 Phased Execution Strategy

To mitigate the risk of shallow modeling across multiple domains simultaneously, v0.3 is partitioned into two sequential phases:

```
                            SVDE-Bench v0.3
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
Phase v0.3-A: Temporal-Relational Extension      Phase v0.3-B: Spatial-Strategic Extension
Target: Visit Scheduling (V01-V10)               Target: Warehouse Slotting (W01-W10)
Focus: Multi-week Cadence, Skills, Territory     Focus: Spatial Contention, SKU Movement
                                                 (Channel Strategy deferred to v0.4)
```

---

## 3. Visit Scheduling Domain Model Design (Phase v0.3-A Blueprint)

The Visit Scheduling domain introduces temporal cadences, human resource skill hierarchies, and relationship-driven customer frequencies that differ fundamentally from point-to-point delivery.

### 3.1 Five Core Visit Decision Patterns (V1–V5)

| Pattern ID | Pattern Name | Decision Dilemma / Tradeoff | Primary Failure Mode |
| :--- | :--- | :--- | :--- |
| **PATTERN-V1-VISIT-CADENCE-SLA** | Periodic Cadence & Multi-Week SLA Compliance | High-value accounts require fixed visit intervals (e.g. bi-weekly). Reps tempted to compress visits into single week to save mileage, violating SLA cadence. | `FT_SEM_CADENCE_DRIFT` |
| **PATTERN-V2-SKILL-TIER-MATCHING** | Account Complexity vs Rep Competency Allocation | Key medical/corporate accounts require Certified Specialist reps. Assigning junior reps saves transit time but fails service compliance. | `FT_CON_SKILL_MISMATCH` |
| **PATTERN-V3-TERRITORY-WORKLOAD-BALANCE** | Multi-Resource Boundary Balance vs Travel Overhead | Rigid sales territory boundaries cause rep burnout in dense zones while peripheral reps are under-utilized. Boundary re-balancing vs relationship continuity. | `FT_TRD_WORKLOAD_SKEW` |
| **PATTERN-V4-DYNAMIC-ABSENCE-HANDOFF** | Unplanned Rep Absence & Temporary Route Handoff | Sales rep falls ill mid-cycle. Stand-in rep must execute critical visits without violating account historical preferences or route feasibility. | `FT_RUN_HANDOFF_DISRUPTION` |
| **PATTERN-V5-RELATIONSHIP-MEMORY-TRANSFER** | Account Preference & Historical Friction Exploitation | Long-term account has strict preferred manager meeting windows and unwritten gatekeeper protocols documented in episodic memory. | `FT_MEM_TACTICAL_IGNORANCE` |

### 3.2 Visit Entity & Constraint Model

- **Entities**:
  - `SalesResource`: ID, Base Location, Skill Tiers (`[JUNIOR, SENIOR, SPECIALIST]`), Max Daily Working Minutes, Assigned Territories.
  - `AccountTarget`: ID, Tier (`[STRATEGIC, CORE, DEVELOPMENT]`), Service Duration (mins), Cadence Spec (`EXACT_WEEKLY`, `BI_WEEKLY`, `MONTHLY_TARGET`), Preferred Time Windows.
- **Constraints**:
  - *Hard*: Skill Tier Match, Max Working Hours, Mandatory Account Locked Day/Slot.
  - *Soft*: Territory Boundary Deviation Penalty, Inter-Visit Interval Variance.
  - *Preference*: Rep-Account Familiarity / Historical Continuity.

---

## 4. Cross-Domain Generalization & Memory Transfer Methodology

### 4.1 Cross-Domain Transfer Matrix

To evaluate whether Decision Memory generalizes beyond a single case into a cross-case or cross-domain capability, v0.3 introduces three controlled experiment axes:

```
[Experiment Axis 1: In-Domain Intra-Case]
Episode 1 (Delivery D09) ──Memory Formed──► Episode 2 (Delivery D09)  [Proven in v0.2]

[Experiment Axis 2: In-Domain Inter-Case Transfer]
Facility A (Delivery D09) ──Memory Formed──► Facility B (Delivery D01) [Target in v0.3]

[Experiment Axis 3: Cross-Domain Abstract Principle Transfer]
Delivery Disruption (D02) ──General Principle──► Rep Absence Handoff (V04) [Target in v0.3]
```

### 4.2 Negative Transfer & Invalidation Protocol

A memory generated in Domain A or Facility A must be evaluated against target domain context boundaries before admission:
1. **Context Alignment Check**: If the target scenario's preconditions do not strictly match the memory's `applicable_scope`, the memory must evaluate to **`REJECTED`** or **`PENDING`**.
2. **Contextual Override Rule**: Real-time world state telemetry always supersedes historical memory recommendations when physical or SLA invariants are at risk.

---

## 5. Evaluation Framework Expansion: Fifth Dimension (`generalization`)

To maintain strict backward compatibility with v0.2 `DecisionProfile` schema, the 5th dimension is introduced via the standard `evaluation.extensions` field:

```yaml
# Backward-compatible extension within DecisionProfile
evaluation:
  semantic:
    score: 1.0
    evidence: "..."
  feasibility:
    score: 1.0
    violations: []
  runtime:
    score: 1.0
    adaptation: "..."
  memory:
    score: 0.99
    admitted_memory: {...}
  extensions:
    generalization:
      score: 0.92
      cross_case_transfer_pass: true
      cross_domain_compatibility: "HIGH"
      negative_transfer_resisted: true
```

---

## 6. v0.3 Phased Gates & Acceptance Criteria

```
Gate 11: Visit Domain Model Freezing
         ✅ domains/visit/ (patterns, entities, constraints, failure_taxonomy, templates) complete and valid.

Gate 12: Visit Scenario Synthesis & Validation
         ✅ 10 Visit cases (V01-V10) synthesized via DecisionScenarioSynthesizer and 100% pass SchemaValidator.

Gate 13: Zero Pipeline Modification in v0.3-A
         ✅ All V01-V10 cases execute through OracleRunner, EvaluatorRunner, and ProfileBuilder with 0 changes to tools/case_generator/.

Gate 14: Cross-Domain Capability Separation
         ✅ 4-Tier Agent Continuum (Pure -> Constraint -> Semantic -> Full) produces measurable separation on V01-V10.

Gate 15: Cross-Case Memory Transfer Proof
         ✅ Episodic memory formed in V09/D09 demonstrates verified performance gain in an independent second scenario.
```

---

## 7. Conclusion & Next Step

SVDE-Bench v0.3 transitions the framework from single-domain evaluation into an enterprise-wide **Multi-Domain Decision Intelligence Benchmark**. 

**Current Action:** Design Specification is logged and frozen. Awaiting explicit user authorization to begin **Sprint 3.1: Visit Domain Modeling (`domains/visit/`)**.
