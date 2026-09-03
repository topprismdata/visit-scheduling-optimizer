# SVDE-Bench v0.4 — Sprint 4.1 Principle Runtime Integration Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** Integration of Governed Decision Principles into Runtime Decision Pipeline  
**Status:** **APPROVED (PrincipleStore, PrincipleMatcher & GovernedPrincipleDecisionAgent Operational)**  

---

## 1. Executive Summary

Sprint 4.1 evolved SVDE-Bench from an evaluation and offline mining testbed into an **executable Decision Runtime**, implementing three core software components:

1. **`PrincipleStore` (`tools/decision_runtime/principle_store.py`)**: File-backed, versioned repository managing promoted decision principles with explicit invalidation boundaries, evidence traces, and precedence tiers.
2. **`PrincipleMatcher` (`tools/decision_runtime/principle_matcher.py`)**: Real-time context feature extractor and boundary checker that matches `DecisionCase` instances to applicable principles and ranks them by precedence tier ($Tier 3 \succ Tier 2 \succ Tier 1$).
3. **`GovernedPrincipleDecisionAgent` (`tools/decision_runtime/governed_principle_agent.py`)**: Operational decision agent that ingests matching governed principles to synthesize decisions while resisting negative transfer.

---

## 2. Head-to-Head Runtime Comparison (D10 & V10 Negative Transfer Cases)

| Test Case | Operational Dilemma | PureSolverAgent | RawEpisodeMemoryAgent | GovernedPrincipleDecisionAgent |
| :--- | :--- | :--- | :--- | :--- |
| **D10** (Delivery) | Reopened Bridge (Outdated Detour) | Grade F (Sem: 0.0) | **Grade F (Sem: 0.0, Poisoned)** | **Grade A (Sem: 1.0, Negative Transfer Resisted)** |
| **V10** (Visit) | Management Shift (Friday Open) | Grade F (Sem: 0.0) | **Grade F (Sem: 0.0, Poisoned)** | **Grade A (Sem: 1.0, Negative Transfer Resisted)** |

---

## 3. Key Architectural Deliverables

```
svde-bench/
├── tools/
│   ├── decision_runtime/
│   │   ├── __init__.py
│   │   ├── principle_store.py          # Versioned principle repository
│   │   ├── principle_matcher.py        # Context-feature & boundary matcher
│   │   ├── governed_principle_agent.py # Runtime Principle-Guided Decision Agent
│   │   └── tests/
│   │       └── test_runtime_integration.py # Runtime validation & negative transfer tests
│   └── case_generator/                 # Offline synthesis & evaluation tooling (v0.1-v0.3)
```

---

## 4. Regression & Verification Metrics

- **Sprint 4.1 Runtime Tests**: `tools/decision_runtime/tests/` (3/3 tests **PASS**).
- **Full Repository Regression**: **105/105 tests PASS** (100% clean regression, 25.60s runtime).
- **Zero Framework Contamination**: 0 modifications to existing evaluators, 0 changes to Profile schema core.
