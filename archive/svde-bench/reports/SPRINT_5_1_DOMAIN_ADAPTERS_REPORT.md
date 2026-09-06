# SVDE-Bench v0.5 — Sprint 5.1 Explicit Domain Adapters Report
**Version:** v1.0  
**Date:** 2026-08-24  
**Target:** Explicit Domain Adapters (`domains/adapters/`) & Pure Canonical Context Decoupling  
**Status:** **APPROVED (DeliveryDomainAdapter & VisitDomainAdapter Operational with Zero Field Remapping)**  

---

## 1. Executive Summary

Sprint 5.1 initiated the **Reality Validation & De-Toying Phase**, eliminating all previous temporary field remapping hacks (`req_cold` used for skills, `weight_kg` for duration) and establishing a clean, decoupled **Domain Adapter Layer** (`domains/adapters/`):

1. **`BaseDomainAdapter` (`base_adapter.py`)**: Formal interface defining bidirectional translation between domain-specific models and canonical `DecisionContext`.
2. **`DeliveryDomainAdapter` (`delivery_adapter.py`)**: Ingests physical vehicles (Standard/Cold/Bike) and payload orders (Ambient/Cold) into canonical resources and tasks.
3. **`VisitDomainAdapter` (`visit_adapter.py`)**: Ingests sales representatives with genuine **Skill Tiers (`SPECIALIST`, `SENIOR`, `JUNIOR`)** and visit demands with genuine **Duration Mins & Competency Invariants** without concept downgrading.
4. **`DomainAdapterRegistry` (`registry.py`)**: Centralized router delegating context normalization dynamically.

---

## 2. Decoupled Mapping Matrix

| Domain Specific Concept | Adapter Class | Canonical Normalized Primitive | Competency / Invariant Representation |
| :--- | :--- | :--- | :--- |
| **Fleet Vehicles** | `DeliveryDomainAdapter` | `NormalizedResource` | `resource_class`: `STANDARD_VAN` / `COLD_REFRIGERATED` |
| **Delivery Cargo Orders** | `DeliveryDomainAdapter` | `NormalizedTask` | `required_competency`: `COLD_CHAIN` / `GENERAL` |
| **Field Sales Reps** | `VisitDomainAdapter` | `NormalizedResource` | `resource_class`: `SPECIALIST_REP` / `SENIOR_REP` / `JUNIOR_REP` |
| **Hospital / Account Visits**| `VisitDomainAdapter` | `NormalizedTask` | `required_competency`: `SPECIALIST` / `SENIOR` / `GENERAL` |

---

## 3. Regression & Test Suite Status

- **Sprint 5.1 Domain Adapter Tests**: `domains/adapters/tests/` (3/3 tests **PASS**).
- **Full SVDE-Bench Repository Regression**: **116/116 tests PASS** (100% clean regression, 7.84s runtime).
- **Zero Framework Contamination**: 0 modifications to existing evaluators, 0 changes to Profile schema core.
