# SVDE Sales Visit Ontology — v0.3 FROZEN
**Document ID:** SVDE-SALES-VISIT-ONTOLOGY-V0.3-FROZEN
**Date:** 2026-08-24
**Status:** FROZEN (per v1.1 §5.3 5-state lifecycle, post-6-GAP business arbitration)
**Framework Basis:** SVDE_ONTOLOGY_ENGINEERING_FRAMEWORK_COMPONENT_SPEC_v1.1

---

## 0. Freeze Provenance

| Field | Value |
| :--- | :--- |
| `frozen_at` | 2026-08-24T12:00:00Z |
| `frozen_by` | Business Owner (本人签署) + Project Architect |
| `frozen_state_progression` | EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW → **BUSINESS_APPROVED** → **FROZEN** |
| `evidence_level` | PRODUCT_FACT (Salesforce, OR Group) + DOMAIN_PRACTICE (Woodburn, Zoltners) + MATHEMATICAL_THEORY (Ahuja, Hillier) + DESIGN_INFERENCE (Dawson) |
| `archival_path` | prism-ontology/provenance/v0.3-freeze-manifest.ttl |

---

## 1. Business Objects (FROZEN, 12 entities)

### Identity Layer
1. `Customer` (tier, commercial_value, location, required_cadence_class)
2. `Resource` (rep_id, type, base_location, weekly_capacity_minutes)

### Policy Layer
3. `VisitPolicy` (customer_id, cadence_spec_id, weekly_availability, time_window, min/max_interval_days)
4. `CadenceSpec` (visits_per_week, visits_per_month, tolerance_days)
5. `OwnershipPolicy` (customer_id, rep_id, is_locked, tenure_months)
6. `EligibilityPolicy` (rep_id, allowed_customer_tiers, excluded_customer_ids)
7. `SubstitutionPolicy` (customer_id, primary_rep_id, substitute_rep_ids)
8. `ObjectiveProfile` (priority_levels, distance_metric, **customer_facing_time** [v0.3新增], **stability_penalty** [v0.3新增], forbidden_tradeoffs, deferral_cost)

### Event Layer
9. `VisitDemand` (customer_id, policy_id, requested_window)
10. `PlannedVisit` (customer_id, date, rep_id, time_window, is_locked, frequency_compliance, status)
11. `ActualVisit` (customer_id, date, rep_id, actual_arrival, actual_departure, status)
12. `Commitment` (customer_id, rep_id, date, time_window, lifecycle_state ∈ {PROPOSED, APPROVED, LOCKED, EXECUTED, MISSED, CANCELLED}, source)

### Measurement Layer
13. `TravelCostMatrix` (source, matrix, captured_at, confidence)
14. `TravelCostEstimate` (route_id, total_distance_km, total_in_transit_min, model_used)
15. `DeferralPolicy` (customer_id, allowed_deferral_days, requires_approval, business_cost_per_day [可选字段])

### Plan Layer
16. `ResourceDayProfile` (rep_id, date, total_capacity_minutes, available_minutes)
17. `PlanningHorizon` (id, start_date, end_date, working_days, timezone, planning_cycle)
18. `RouteStop` (id, planned_visit_id, planned_arrival, service_duration, sequence_idx)
19. `RoutePlan` (id, target_date, rep_id, sequence[RouteStop], depot_id, total_distance_km, total_in_transit_min)

---

## 2. Decisions Layers (FROZEN)

```
TERRITORY_ALIGNMENT    → TerritoryAssignmentPlan
  input: Customer, OwnershipPolicy, EligibilityPolicy, Resource
  constraint: locked_ownership_preserved

PERIODIC_COVERAGE      → PeriodicVisitPlan
  input: VisitDemand, CadenceSpec, PlanningHorizon, Commitment
  constraint: frequency_min_interval_preserved, locked_commitments_preserved

DAILY_ROUTE_SEQUENCING → DailyRoutePlan
  input: PlannedVisit[], TravelCostMatrix, ResourceDayProfile, Commitment
  constraint: customer_set_FIXED, time_window_preserved, depot_closure

ROLLING_REPLAN         → RollingReplanProposal
  input: ExistingCommitment, ExecutionSignal, VisitDemand

DISTANCE_TIME_TRADEOFF → TradeoffAssessment
  constraint: forbid_relaxing_locked
```

---

## 3. Forbidden Folds (Anti-Promotion Rules, FROZEN)

| Object | Must NOT be folded into | Why |
| :--- | :--- | :--- |
| `Customer` | `Task` / `RouteStop` | Different identity layer |
| `PlannedVisit` / `ActualVisit` | `RouteStop` | Different lifecycle stage |
| `RoutePlan` | `DecisionArtifact.decision` | Different abstraction |
| `VisitPolicy` | `COMMITTED_TASK` | Different policy/data layer |
| `Commitment` | "soft preference" | Hard locked commitment |
| `BusinessPolicy` | "SolverParameter" | Different governance layer |
| Algorithm concept (Column Generation, LNS, Tabu, Simplex, Big-M) | Business Object | Internal to Capability only |
| Channel hierarchy (Kotler 4P) | Sales visit ontology | Different domain |
| Sales force incentive | Sales visit ontology | Different scope |
| **Any SOP-related object** (SOPPolicy / CustomerSOPBinding) | **Permanently rejected** | GAP-6 = C closed by business |

---

## 4. Objective Priority (FROZEN, Lexicographic)

```
Level 0: Hard constraints (frequency, locked, window, ownership, capacity)
Level 1: Business value / unfulfilled-cost minimization
Level 2: In-transit time / distance / customer-facing-time
Level 3: Plan stability / disruption cost
Level 4: Secondary preferences
```

Priority Rules (machine-verifiable):
- `DistanceMinimization.subordinateTo(CoverageCompliance)` → distance cannot override frequency
- `DistanceMinimization.mustNotOverride(CommitmentLock)` → distance cannot move locked commitments
- `DistanceMinimization.cannotReduce(CadenceSpec.min_interval_days)` → distance cannot compress intervals
- `DailyRouteOptimization.requires(FixedVisitSet)` → daily route needs fixed visits
- `PeriodicVisitPlanning.requires(PlanningHorizon)` → periodic needs horizon

---

## 5. GAP Arbitration Outcome (FROZEN)

| GAP | Decision | Frozen Field |
| :--- | :--- | :--- |
| GAP-1 Product/SKU | BUSINESS_APPROVED | (not entered into v0.3) |
| GAP-2 Subsidiary/Region/Zone | BUSINESS_APPROVED | (not entered into v0.3) |
| GAP-3 ApprovalRequest | 否 (走 SOP) | (not entered into v0.3) |
| GAP-4 TimeDeviation | BUSINESS_APPROVED | (not entered into v0.3) |
| GAP-5 BusinessCostPerDay | 否 (可选字段) | `DeferralPolicy.business_cost_per_day` 设为 optional |
| GAP-6 CustomerOpRequirement | **PERMANENTLY_CLOSED** | 永不入本体 |

---

## 6. Frozen State

```
FROZEN at 2026-08-24 by Business Owner + Project Architect
All future changes MUST go through v1.1 §8 OntologyChangeRequest
Agent 不得自行解冻或修改
```

---

## 7. Downstream Action Trigger

v0.3 FROZEN → 触发 `prism-ontology` Phase 0 独立骨架启动（per SVDE_ONTOLOGY_ENGINEERING_FRAMEWORK_COMPONENT_SPEC_v1.1 §9）
