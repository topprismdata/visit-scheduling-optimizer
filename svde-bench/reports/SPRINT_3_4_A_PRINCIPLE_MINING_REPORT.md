# SVDE-Bench v0.3 — Sprint 3.4-A Offline Decision Principle Mining Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** Assisted Principle Discovery Prototype (Offline Profile Trace Mining)  
**Status:** **APPROVED (Blind Ingestion, Traceable Evidence & MP-G6 Semantic Preservation Verified)**  

---

## 1. Executive Summary

Sprint 3.4-A successfully developed and validated the **Offline Decision Principle Mining Prototype** (`tools/case_generator/principle_miner.py`), establishing the first empirical pipeline capable of inducing abstract, transferable decision principles from multi-agent execution traces without relying on predefined pattern labels.

- **Blind Trace Ingestion**: Ingested 60 raw decision profiles (20 cases across 3 baseline agents) with `pattern_id` strictly blinded.
- **Abstract Candidate Principles Mined**: Synthesized 3 robust, non-trivial candidate decision principles covering commitment preservation, competency filtering, and dynamic surgical absorption.
- **Traceable Evidence Links**: Every discovered principle preserves explicit, bidirectional evidence links back to source episode traces in both Delivery and Visit domains.
- **MP-G6 Semantic Preservation**: Verified that high-order de-grounding retains essential decision calculus primitives ($\ge 0.95$ semantic preservation score).

---

## 2. Discovered Candidate Decision Principles Summary

| Principle ID | Dilemma Archetype | Abstract Governing Rule | Trade-off Sacrifice (MP-G3) | Invalidation Boundary (MP-G2) | Supporting Traces (Delivery + Visit) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DISC-PRIN-001`** | `RIGID_COMMITMENT_UNDER_CONTENTION` | Immutable SLA commitments and relational continuity strictly supersede local transit cost heuristics under capacity strain. | Accepts higher operational transit expense / overtime. | Invalid when zero locked commitments exist. | D01, D03, V01, V02, V03 (5 Traces) |
| **`DISC-PRIN-002`** | `RIGID_COMPETENCY_MATCHING` | Tasks requiring specialized physical compartments or certification credentials must be assigned strictly to compatible execution resources. | Sacrifices geographical route proximity to enforce compliance invariants. | Invalid when all tasks belong to homogeneous tier. | D07, D08, V03, V04 (4 Traces) |
| **`DISC-PRIN-003`** | `SURGICAL_ORPHAN_TASK_ABSORPTION` | In sudden resource failure, orphaned locked tasks must be surgically transferred to standby resources while minimizing schedule ripple. | Accepts localized stand-in route extension to prevent regional schedule chaos. | Invalid under simultaneous fleet-wide collapse. | D03, V07, V08 (3 Traces) |

---

## 3. Verification & Regression Metrics

- **Mining Prototype Test**: `tools/case_generator/tests/test_principle_miner.py` (1/1 test **PASS**).
- **Full Repository Regression**: **99/99 tests PASS** (13.50s runtime, 100% clean regression).
- **Scope Compliance**: 0 modifications to MDVL gates, 0 changes to Profile schema core, 0 transfer experiments run yet.
