# SVDE Core Framework — Sprint 6.3 Decision Structures & Capability Composition Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** First-Class Decision Structures (`Assignment` vs `Routing`) & Multi-Step Capability Composition  
**Status:** **APPROVED (Structural Invariants & Pipeline Composition Verified, 15 Core Tests + 121 Bench Tests Passing)**  

---

## 1. Executive Summary

Sprint 6.3 resolved the **Flat-Bag Coercion Problem** and introduced **Multi-Step Capability Composition**:

1. **First-Class Decision Structures (`svde/contracts/decision_structures.py`)**:
   - `AssignmentDecisionStructure`: Native discrete allocation modeling ($resources, tasks, contention, commitments$).
   - `RoutingDecisionStructure`: Native network routing modeling ($nodes, edge\_matrix, depot\_ids, time\_windows, sequence\_locks$).
   - Completely eliminated the anti-pattern of coercing VRP/TSP stops into pseudo Resource-Task assignment bags.
2. **Structural DecisionSpec Integration**:
   - `DecisionSpec` explicitly carries `decision_class`, `decision_structure`, and `required_capabilities`.
3. **Multi-Step Capability Pipeline Composition**:
   - `DecisionPlan` now structures an ordered list of `CapabilityStep` items (`[Step 1: Solve -> Step 2: Semantic Verification]`).
   - `RuntimeOrchestrator` executes capability pipelines in strict deterministic order, recording per-step execution traces.
4. **Dynamic Routing Capability Execution**:
   - Demonstrated that a newly registered `sequential_routing` capability (`MockSequentialVRPNewtonCapability`) compiles, plans, and executes cleanly **without a single line of Core modification**.

---

## 2. Invariant Verification Matrix

| Architecture Contract Invariant | Verification Method | Status |
| :--- | :--- | :--- |
| **Invariant 1: Native Routing Structure Compilation** | `test_routing_decision_structure_compilation`: Routing request compiles into `RoutingDecisionStructure` with nodes, edge matrix, and sequence locks (No Resource/Task coercion). | **PASS** ✅ |
| **Invariant 2: Unsupported Routing Fails Closed** | `test_unsupported_routing_capability_fails_closed`: Unfulfilled routing capability raises `UnsupportedCapabilityError`. | **PASS** ✅ |
| **Invariant 3: Dynamic Capability Pipeline Execution** | `test_dynamically_registered_routing_capability_executes_pipeline`: Registers `sequential_routing` and executes 2-step pipeline (`Solve -> Verify`) with per-step trace. | **PASS** ✅ |
| **Invariant 4: Assignment Backward Compatibility** | `test_assignment_decision_structure_backward_compatibility`: Classic assignment requests compile and execute seamlessly. | **PASS** ✅ |

---

## 3. Regression & Test Suite Status

- **SVDE Core Architecture Tests**: `svde/tests/` (**15/15 tests PASS** in 0.11s).
- **SVDE-Bench Regression Suite**: `svde-bench/` (**121/121 tests PASS** in 9.06s).
- **Public API**: Unchanged (`artifact = svde.decide(request)`).
