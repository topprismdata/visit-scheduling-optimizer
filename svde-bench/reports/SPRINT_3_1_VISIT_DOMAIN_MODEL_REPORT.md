# SVDE-Bench v0.3 — Sprint 3.1 Visit Scheduling Domain Model Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** Visit Scheduling Domain Decision Model (`domains/visit/`)  
**Status:** **APPROVED (Gate 11 & Gate 13 Compatibility Verified)**  

---

## 1. Executive Summary

Sprint 3.1 established the complete **Visit Scheduling Domain Decision Model** (`domains/visit/`), formalizing relationship-driven, cadence-based, and competency-matched field sales decision scenarios.

- **Primary Goal Achieved:** Created all 6 required domain specification artifacts, strictly following the domain abstraction model proven in Delivery.
- **Relational Continuity Modeled:** Introduced `relationships.yaml` to explicitly govern territory assignments, account ownership continuity, and cadence obligations.
- **Zero Framework Contamination:** Verified that Visit decision templates synthesize into cases that 100% validate against the existing `SchemaValidator` and execute through `FullPipelineRunner` with **0 lines of code changed** in `tools/case_generator/`.

---

## 2. Visit Domain Artifacts Inventory

```
svde-bench/domains/visit/
├── entities.yaml          # Sales Reps (Specialist/Senior/Junior), Accounts (Strategic/Core/Dev), Visit Demands
├── relationships.yaml     # Territory Assignment, Account Ownership, Cadence Obligation, Relationship Memory
├── patterns.yaml          # 5 Core Decision Patterns (V1 Cadence SLA, V2 Skill Match, V3 Territory Balance, V4 Absence Handoff, V5 Relationship Memory)
├── constraints.yaml       # Hard (Skill Match, Daily Hours, SLA Locks), Soft (Cadence Gap, Mileage), Preferences (Continuity)
├── failure_taxonomy.yaml  # FT_SEM_01 Cadence Drift, FT_CON_01 Skill Mismatch, FT_TRD_01 Workload Imbalance, FT_RUN_01 Handoff Disruption, FT_MEM_01 Tactical Ignorance
└── scenario_templates.yaml# Standardized scenario generation templates for V1-V5 patterns
```

---

## 3. Five Core Visit Decision Patterns Overview

1. **`PATTERN-V1-VISIT-CADENCE-SLA`** (Cadence vs Compression): Bi-weekly account SLA spacing vs travel compression temptation.
2. **`PATTERN-V2-SKILL-TIER-MATCHING`** (Competency Allocation): Strategic clinical accounts requiring certified Specialist reps vs junior proximity assignment.
3. **`PATTERN-V3-TERRITORY-WORKLOAD-BALANCE`** (Workload Equity): Dense territory rep burnout vs peripheral rep surplus and boundary re-balancing.
4. **`PATTERN-V4-DYNAMIC-ABSENCE-HANDOFF`** (Absence Handoff): Sudden rep sick leave and surgical stand-in absorption without schedule perturbation.
5. **`PATTERN-V5-RELATIONSHIP-MEMORY-TRANSFER`** (Relationship Memory): Long-term client gatekeeper preference exploitation, rejection, and context override.

---

## 4. Verification & Regression Metrics

- **Domain Model Tests:** `tools/case_generator/tests/test_visit_domain_model.py` (3/3 tests **PASS**).
- **Full Repository Regression:** **92/92 tests PASS** (9.87s runtime, 100% clean regression).
- **Gate 11 (Domain Model Freeze)**: **PASS** ✅
- **Gate 13 (Pipeline Portability)**: **PASS** ✅
