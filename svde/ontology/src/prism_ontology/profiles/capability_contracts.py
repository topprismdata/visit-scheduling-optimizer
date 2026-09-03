"""Capability Contract Definitions for Sales Visit v0.3 (Phase 4).

Per v1.1 §9 Phase 4: only define and validate the 3 Sales Visit capability contracts.
No implementation. No solver integration. Just contracts.

Capabilities:
- TerritoryAlignmentCapability
- PeriodicVisitPlanningCapability
- DailyRouteOptimizationCapability

All 3 marked as PLANNED (not IMPLEMENTED) per v1.1 honesty gate.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from prism_ontology.reference.store import ObjectLayer, DecisionLevel


class CapabilityStatus(str, Enum):
    """Honesty gate: capabilities must be honestly reported as PLANNED until implemented."""
    PLANNED = "PLANNED"
    REGISTERED = "REGISTERED"
    IMPLEMENTED = "IMPLEMENTED"


@dataclass
class CapabilityContract:
    """Formal contract for a Sales Visit capability.

    Each capability declares:
    - Which decision level it serves
    - Which ReferenceObjects it consumes
    - Which hard constraints it must enforce
    - Which guarantees it provides
    - Which priority rules it must respect
    - Its current status (PLANNED / REGISTERED / IMPLEMENTED)
    """
    capability_id: str
    decision_level: DecisionLevel
    input_objects: List[str]  # ReferenceObject ids
    output_type: str          # e.g. "TerritoryAssignmentPlan", "PeriodicVisitPlan", "DailyRoutePlan"
    hard_constraints: List[str] = field(default_factory=list)
    guarantees: List[str] = field(default_factory=list)
    priority_rules_respected: List[str] = field(default_factory=list)
    status: CapabilityStatus = CapabilityStatus.PLANNED
    evidence_sources: List[str] = field(default_factory=list)
    version: str = "0.1.0-draft"


# ============================================================================
# 1. TerritoryAlignmentCapability
# ============================================================================

TERRITORY_ALIGNMENT_CONTRACT = CapabilityContract(
    capability_id="capability.territory_alignment",
    decision_level=DecisionLevel.TERRITORY_ALIGNMENT,
    input_objects=[
        "Customer",
        "OwnershipPolicy",
        "EligibilityPolicy",
        "Resource",
        "SubstitutionPolicy",
    ],
    output_type="TerritoryAssignmentPlan",
    hard_constraints=[
        "every_customer_assigned_exactly_once",
        "rep_weekly_load_must_not_exceed_capacity",
        "locked_ownership_must_be_preserved (OwnershipPolicy.is_locked == True)",
    ],
    guarantees=[
        "all_customers_assigned_to_exactly_one_rep",
        "no_rep_load_exceeds_capacity",
        "respects_locked_ownership_assignments",
        "respects_eligibility_constraints",
    ],
    priority_rules_respected=[
        "PR-001 (DistanceMinimization.subordinateTo(CoverageCompliance)) — coverage over distance",
        "PR-002 (DistanceMinimization.mustNotOverride(CommitmentLock)) — locked commitments cannot be relaxed",
    ],
    status=CapabilityStatus.PLANNED,
    evidence_sources=[
        "REF-012 (Zoltners: territory assignment is independent decision layer)",
        "REF-014 (Shanahan: strategic/tactical/operational time-scale separation)",
        "REF-005 (Van Loon: strategic vs operational planning)",
        "REF-002 (Salesforce: Service Goals and SLAs)",
    ],
)


# ============================================================================
# 2. PeriodicVisitPlanningCapability
# ============================================================================

PERIODIC_VISIT_PLANNING_CONTRACT = CapabilityContract(
    capability_id="capability.periodic_visit_planning",
    decision_level=DecisionLevel.PERIODIC_COVERAGE,
    input_objects=[
        "VisitDemand",
        "CadenceSpec",
        "PlanningHorizon",
        "Commitment",
        "ResourceDayProfile",
        "Customer",
        "OwnershipPolicy",
    ],
    output_type="PeriodicVisitPlan",
    hard_constraints=[
        "each_customer_visited_at_cadence (CadenceSpec)",
        "visits_on_allowed_weekdays_and_windows (VisitPolicy.weekly_availability)",
        "existing_locked_commitments_preserved (Commitment.lifecycle_state == LOCKED)",
        "rep_daily_workload_within_capacity (ResourceDayProfile.available_minutes)",
        "min_interval_days_respected (CadenceSpec.min_interval_days)",
    ],
    guarantees=[
        "all_customers_covered_in_planning_horizon",
        "frequency_compliance_per_customer",
        "weekday_pattern_aligned",
        "respects_locked_commitments",
    ],
    priority_rules_respected=[
        "PR-001 (coverage before distance)",
        "PR-002 (locked commitments)",
        "PR-003 (min_interval_days preserved)",
        "PR-005 (PlanningHorizon required)",
    ],
    status=CapabilityStatus.PLANNED,
    evidence_sources=[
        "REF-001 (OR Group: service frequency rules)",
        "REF-PTV-001 (PTV xCluster: assignmentRules + week rhythms + weekday patterns)",
        "REF-002 (Salesforce: Service Goals cadence)",
    ],
)


# ============================================================================
# 3. DailyRouteOptimizationCapability
# ============================================================================

DAILY_ROUTE_OPTIMIZATION_CONTRACT = CapabilityContract(
    capability_id="capability.daily_route_optimization",
    decision_level=DecisionLevel.DAILY_ROUTE_SEQUENCING,
    input_objects=[
        "PlannedVisit",
        "TravelCostMatrix",
        "ResourceDayProfile",
        "Commitment",
        "ObjectiveProfile",
    ],
    output_type="DailyRoutePlan",
    hard_constraints=[
        "customer_set_must_be_FIXED (cannot change set of PlannedVisit)",
        "locked_visit_order_must_be_preserved (if any)",
        "every_customer_served_within_time_window (PlannedVisit.time_window)",
        "route_must_start_and_end_at_depot",
        "max_daily_work_minutes_must_not_be_exceeded (ResourceDayProfile)",
        "every_edge_in_route_must_be_in_TravelCostMatrix (no implicit defaults)",
    ],
    guarantees=[
        "feasible_route_within_horizon",
        "time_windows_preserved",
        "capacity_bounds_respected",
        "depot_closure_start_end",
    ],
    priority_rules_respected=[
        "PR-001 (DistanceMinimization subordinate to CoverageCompliance)",
        "PR-002 (DistanceMinimization mustNotOverride CommitmentLock)",
        "PR-004 (DailyRouteOptimization requires FixedVisitSet)",
    ],
    status=CapabilityStatus.PLANNED,
    evidence_sources=[
        "REF-016 (PTV xTour: VRP formulation + multi-depot + capacity + time windows)",
        "REF-007 (Toth & Vigo: hard time windows cannot be relaxed)",
        "REF-008 (Langevin: rolling re-plan + disruption cost)",
    ],
)


# ============================================================================
# Registry
# ============================================================================

ALL_CAPABILITY_CONTRACTS: List[CapabilityContract] = [
    TERRITORY_ALIGNMENT_CONTRACT,
    PERIODIC_VISIT_PLANNING_CONTRACT,
    DAILY_ROUTE_OPTIMIZATION_CONTRACT,
]


class CapabilityRegistry:
    """Honest capability contract registry. All Sales Visit caps start as PLANNED."""

    def __init__(self):
        self._contracts: Dict[str, CapabilityContract] = {
            c.capability_id: c for c in ALL_CAPABILITY_CONTRACTS
        }

    def get(self, capability_id: str) -> Optional[CapabilityContract]:
        return self._contracts.get(capability_id)

    def get_by_decision_level(self, decision_level: DecisionLevel) -> List[CapabilityContract]:
        return [c for c in self._contracts.values() if c.decision_level == decision_level]

    def all(self) -> List[CapabilityContract]:
        return list(self._contracts.values())

    def all_planned(self) -> List[CapabilityContract]:
        """List all capabilities still in PLANNED state (v1.1 honesty gate)."""
        return [c for c in self._contracts.values() if c.status == CapabilityStatus.PLANNED]

    def all_ids(self) -> List[str]:
        return sorted(self._contracts.keys())

    def summary(self) -> Dict[str, Any]:
        return {
            "total_capabilities": len(self._contracts),
            "all_planned": len(self.all_planned()),
            "any_implemented": any(c.status == CapabilityStatus.IMPLEMENTED for c in self._contracts.values()),
            "by_decision_level": {
                level.value: [c.capability_id for c in self.get_by_decision_level(level)]
                for level in DecisionLevel
            },
        }
