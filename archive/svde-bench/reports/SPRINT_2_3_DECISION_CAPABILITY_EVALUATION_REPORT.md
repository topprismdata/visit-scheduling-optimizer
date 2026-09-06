# SVDE-Bench v0.2 — Sprint 2.3 Decision Capability Evaluation Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Evaluation Target:** 3 Baseline Agents × 10 Delivery Cases (D01–D10) = 30 Decision Profiles  
**Status:** **APPROVED (Measurable Capability Separation Verified)**  

---

## 1. Executive Summary

Sprint 2.3 evaluated 3 distinct baseline decision agent archetypes across the 10 extended Delivery Decision Cases (D01–D10) to determine if SVDE-Bench provides **measurable, multi-dimensional separation of decision intelligence**:

1. **Baseline A (`PureSolverAgent`)**: Mathematical objective maximizer (CVRP cost heuristic) ignoring business commitments.
2. **Baseline B (`SemanticAwareAgent`)**: Ingests business contracts, strictly honoring VIP and time-window locks.
3. **Baseline C (`FullDecisionAgent`)**: Comprehensive decision agent (Semantic + Runtime adaptation + Memory evolution).

---

## 2. 30-Profile Evaluation Matrix

| Case ID | Pattern / Dilemma | Oracle Status | PureSolverAgent | SemanticAwareAgent | FullDecisionAgent |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D01** | D1: Fixed Fleet Cost vs VIP SLA | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D02** | D1: Extreme Capacity Deficit | `INFEASIBLE` | **Grade F** (INFEASIBLE) | **Grade F** (INFEASIBLE) | **Grade F** (INFEASIBLE) |
| **D03** | D2: Vehicle Breakdown Rerouting | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D04** | D2: Emergency Order Injection | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D05** | D3: Overtime Fleet Deployment | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D06** | D3: Tiered SLA Deferral Under Jam | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D07** | D4: Refrigerated Compartment Strain| `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D08** | D4: Cargo Chemical-Food Isolation | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D09** | D5: Episodic Memory Exploitation | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |
| **D10** | D5: Stale Memory Invalidation | `OPTIMAL` | **Grade F** (Sem: 0.0, Run: 0.0) | **Grade A** (Sem: 1.0, Run: 1.0) | **Grade A** (Mem: 0.99, PROMOTED) |

---

## 3. Dimensional Separation Analysis

### 3.1 Semantic Dimension Separation (`Solution Feasibility ≠ Decision Feasibility`)
- **`PureSolverAgent`** dropped or postponed locked VIP commitments to minimize heuristic distance $\rightarrow$ **Semantic Accuracy = 0.0**, Grade **F**.
- **`SemanticAwareAgent`** & **`FullDecisionAgent`** ingested the semantic contracts and preserved all commitments on active fleet $\rightarrow$ **Semantic Accuracy = 1.0**, Grade **A** (on feasible cases).

### 3.2 Runtime Adaptation Dimension Separation
- Commitment survival rate for `PureSolverAgent` is **0.0** due to dropped commitments.
- For `SemanticAwareAgent` and `FullDecisionAgent`, commitment survival is **1.0**.

### 3.3 Memory Dimension Separation
- `PureSolverAgent` and `SemanticAwareAgent` do not generate memory patches (`NONE_REQUIRED`).
- `FullDecisionAgent` extracts structured episodic memory patches across all episodes, achieving **Memory Score = 0.99** and passing all 5 gates (`MP-G1` through `MP-G5`) to reach **`PROMOTED`** status.

---

## 4. Key Takeaways & Conclusion

1. **SVDE-Bench measures Decision Intelligence, not just Solver Speed**: Clear bifurcation between pure mathematical optimization and semantic contract honoring.
2. **Oracle Grounding Preserved**: Infeasible problems (D02) are truthfully flagged by Oracle as `INFEASIBLE` without artificial tampering.
3. **Regression Status**: 84/84 tests **PASS** (100%).
