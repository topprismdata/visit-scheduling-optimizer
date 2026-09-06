# SVDE-Bench v0.5 — Sprint 5.3 Real Decision Agents Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** Black-Box LLM Decision Agent & Exact CP-SAT Solver Agent (`agents/real/`)  
**Status:** **APPROVED (LLMDecisionAgent & ConstrainedSolverAgent Operational)**  

---

## 1. Executive Summary

Sprint 5.3 implemented genuine black-box reasoning agents, replacing synthetic mock behavior with true algorithmic formulation and prompt-driven inference:

1. **`LLMDecisionAgent` (`agents/real/llm_agent.py`)**: Prompts an autonomous LLM with canonical `DecisionContext` in natural and structured form, parsing the resulting JSON completion into `DecisionArtifact` with full causal rationale.
2. **`ConstrainedSolverAgent` (`agents/real/solver_agent.py`)**: Dynamically formulates and solves exact OR-Tools CP-SAT mathematical models directly from canonical `DecisionContext`, honoring multi-tier competency and commitment invariants.

---

## 2. Head-to-Head Agent Comparison

| Agent Archetype | Implementation Mechanism | Input Ingestion | Decision Synthesis | Trace Generation |
| :--- | :--- | :--- | :--- | :--- |
| **`LLMDecisionAgent`** | Prompt $\rightarrow$ Completion $\rightarrow$ JSON | Canonical `DecisionContext` | Autonomous LLM Reasoning | Detailed LLM prompt snippet & parsed reasoning |
| **`ConstrainedSolverAgent`** | Mathematical CP-SAT Model | Canonical `DecisionContext` | Exact Mathematical Solver | Exact variables, constraints & solver wall time |
| **`GovernedPrincipleDecisionAgent`** | PrincipleStore + Matcher | Canonical `DecisionContext` | Principle Precedence Arbitration | Activated/Rejected principle trace with boundaries |

---

## 3. Regression & Test Suite Status

- **Sprint 5.3 Real Agent Tests**: `agents/real/tests/` (2/2 tests **PASS**).
- **Full SVDE-Bench Repository Regression**: **120/120 tests PASS** (100% clean regression, 15.19s runtime).
- **Zero Framework Contamination**: 0 modifications to existing evaluators, 0 changes to Profile schema core.
