"""SVDE Core Sales Visit Capability Contracts.

Three-tier Decision Capability Contracts for Sales Visit domain:
1. TerritoryAlignmentCapability
2. PeriodicVisitPlanningCapability
3. DailyRouteOptimizationCapability

Each contract strictly defines:
- Input structure
- Output structure
- Hard constraints (non-negotiable)
- Optimization objective
- Acceptable approximation bounds
- Output evidence
- Unsupported scenarios
- Validation metrics
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from svde.contracts.decision_structures import BaseDecisionStructure, DecisionClass


class SalesVisitCapabilityStatus(str, Enum):
    """Capability availability status — honesty gate (no fabrication allowed)."""
    IMPLEMENTED = "IMPLEMENTED"
    REGISTERED = "REGISTERED"
    PLANNED = "PLANNED"        # Contract frozen, implementation pending
    NOT_REGISTERED = "NOT_REGISTERED"


class SalesVisitCapabilityType(str, Enum):
    TERRITORY_ALIGNMENT = "territory_alignment"
    PERIODIC_VISIT_PLANNING = "periodic_visit_planning"
    DAILY_ROUTE_OPTIMIZATION = "daily_route_optimization"


# ===========================================================================
# 1. TerritoryAlignmentCapability
# ===========================================================================
@dataclass
class TerritoryAlignmentInputs:
    """Inputs: customer-rep ownership + sales value + workload capacity."""
    customers: List[Dict[str, Any]]           # id, location, commercial_value
    sales_reps: List[Dict[str, Any]]           # id, base_location, weekly_capacity_minutes
    historical_assignments: Optional[List[Dict[str, Any]]] = None  # prior period ownership


@dataclass
class TerritoryAlignmentOutputs:
    """Outputs: rep-to-customer assignment + workload balance metrics."""
    assignments: Dict[str, List[str]]         # rep_id -> [customer_ids]
    workload_minutes_per_rep: Dict[str, float]
    coverage_violations: List[str]            # customers with no assigned rep
    unbalance_score: float                    # 0.0 = perfectly balanced


@dataclass
class TerritoryAlignmentContract:
    """Aligns customers to sales reps based on territory, capacity, and value."""
    capability_name: str = "territory_alignment"
    supported_decision_classes: List[DecisionClass] = field(
        default_factory=lambda: [DecisionClass.DISCRETE_ASSIGNMENT]
    )
    required_structure_type: type = None      # Set in post_init

    def __post_init__(self):
        self.required_structure_type = TerritoryAlignmentStructure

    # Hard constraints (non-negotiable, must be satisfied)
    hard_constraints: List[str] = field(default_factory=lambda: [
        "Every customer must be assigned to exactly one sales rep",
        "Rep weekly workload must not exceed capacity",
        "Locked ownership assignments (if any) must be preserved"
    ])

    # Optimization objective (Lexicographic, Level 1 > Level 2 > ...)
    optimization_objective: str = (
        "Level 0: Hard constraints must be satisfied. "
        "Level 1: Maximize total commercial value covered. "
        "Level 2: Minimize rep workload imbalance (max-min ratio). "
        "Level 3: Minimize customer-rep reassignments vs historical baseline."
    )

    # Acceptable approximation bounds
    approximation_bounds: Dict[str, float] = field(default_factory=lambda: {
        "max_optimality_gap_pct": 5.0,        # ≤5% gap from optimal acceptable
        "max_solver_runtime_sec": 120.0,
    })

    # Output evidence (must include in DecisionArtifact)
    output_evidence: List[str] = field(default_factory=lambda: [
        "Per-customer assignment with rep_id",
        "Workload utilization per rep (min:max ratio)",
        "List of unassigned customers (if any)",
        "Number of customers reassigned vs historical baseline"
    ])

    # Explicitly forbidden behaviors
    unsupported_scenarios: List[str] = field(default_factory=lambda: [
        "Single-day route ordering (use DailyRouteOptimizationCapability)",
        "Multi-week visit frequency planning (use PeriodicVisitPlanningCapability)",
        "Changing locked customer-rep ownership (FAIL CLOSED if requested)"
    ])

    # Validation metrics
    validation_metrics: List[str] = field(default_factory=lambda: [
        "coverage_pct = (assigned_customers / total_customers) * 100",
        "workload_imbalance = max(utilization) - min(utilization)",
        "ownership_change_pct = (reassigned / total) * 100"
    ])


@dataclass
class TerritoryAlignmentStructure(BaseDecisionStructure):
    """Decision structure for territory alignment problems."""
    customers: List[Dict[str, Any]] = field(default_factory=list)
    sales_reps: List[Dict[str, Any]] = field(default_factory=list)
    historical_assignments: Optional[List[Dict[str, Any]]] = None

    @property
    def structure_type(self) -> DecisionClass:
        return DecisionClass.DISCRETE_ASSIGNMENT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_type": self.structure_type.value,
            "customer_count": len(self.customers),
            "rep_count": len(self.sales_reps),
            "has_historical_baseline": self.historical_assignments is not None,
        }


# ===========================================================================
# 2. PeriodicVisitPlanningCapability
# ===========================================================================
@dataclass
class PeriodicVisitPlanningInputs:
    """Inputs: 4-week plan with frequency + weekday + window + locked commitments."""
    customers: List[Dict[str, Any]]            # id, weekly_availability, visit_duration_mins
    planning_horizon_weeks: int = 4
    working_days: List[str] = None             # e.g. ["Mon","Tue","Wed","Thu","Fri"]
    cadence_specs: Optional[List[Dict[str, Any]]] = None
    existing_commitments: Optional[List[Dict[str, Any]]] = None
    representative_day_profiles: Optional[List[Dict[str, Any]]] = None
    objective_policy: Optional[Dict[str, Any]] = None


@dataclass
class PeriodicVisitPlanningOutputs:
    """Outputs: weekly per-customer visit plan (date, rep_id)."""
    weekly_plan: Dict[int, Dict[str, List[Dict[str, Any]]]]
    # week_idx -> {"YYYY-MM-DD": [{"customer_id":..., "rep_id":..., "duration_mins":...}]}
    frequency_violations: List[str]
    weekday_violations: List[str]
    coverage_breach: List[str]


@dataclass
class PeriodicVisitPlanningContract:
    capability_name: str = "periodic_visit_planning"
    supported_decision_classes: List[DecisionClass] = field(
        default_factory=lambda: [DecisionClass.PERIODIC_SCHEDULING]
    )
    required_structure_type: type = None

    def __post_init__(self):
        self.required_structure_type = PeriodicVisitPlanningStructure

    hard_constraints: List[str] = field(default_factory=lambda: [
        "Each customer must be visited at the exact cadence specified (within tolerance)",
        "Visit must occur on customer's allowed weekdays and within time window",
        "Existing commitments (locked visits) must be preserved",
        "Rep daily workload must not exceed daily capacity profile"
    ])

    optimization_objective: str = (
        "Level 0: Hard constraints must be satisfied. "
        "Level 1: Maximize cadence compliance rate. "
        "Level 2: Minimize cross-week visit clustering (regularity). "
        "Level 3: Minimize representative workload imbalance across planning period."
    )

    approximation_bounds: Dict[str, float] = field(default_factory=lambda: {
        "max_optimality_gap_pct": 8.0,
        "max_solver_runtime_sec": 300.0,
    })

    output_evidence: List[str] = field(default_factory=lambda: [
        "Full 4-week per-day per-customer visit plan",
        "Cadence compliance rate (%)",
        "Cross-week visit regularity score",
        "List of customers failing cadence/timing"
    ])

    unsupported_scenarios: List[str] = field(default_factory=lambda: [
        "Single-day route ordering (use DailyRouteOptimizationCapability)",
        "Changing rep-to-customer ownership (use TerritoryAlignmentCapability)"
    ])

    validation_metrics: List[str] = field(default_factory=lambda: [
        "cadence_compliance_pct",
        "weekday_alignment_pct",
        "representative_load_balance_std"
    ])


@dataclass
class PeriodicVisitPlanningStructure(BaseDecisionStructure):
    planning_horizon_weeks: int = 4
    working_days: List[str] = field(default_factory=list)
    cadence_specs: List[Dict[str, Any]] = field(default_factory=list)
    existing_commitments: List[Dict[str, Any]] = field(default_factory=list)
    customers: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def structure_type(self) -> DecisionClass:
        return DecisionClass.PERIODIC_SCHEDULING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_type": self.structure_type.value,
            "horizon_weeks": self.planning_horizon_weeks,
            "working_days": self.working_days,
            "customer_count": len(self.customers),
            "locked_commitments": len(self.existing_commitments),
        }


# ===========================================================================
# 3. DailyRouteOptimizationCapability
# ===========================================================================
@dataclass
class DailyRouteOptimizationInputs:
    """Inputs: fixed customer set for one day + coordinates + time windows."""
    target_date: str                            # YYYY-MM-DD
    rep_id: str
    depot_location: Dict[str, float]           # {"lat":..., "lon":...}
    customer_set: List[Dict[str, Any]]         # id, lat, lon, time_window_earliest, time_window_latest, service_duration_mins
    distance_matrix: Dict[str, Dict[str, float]]  # node_id -> node_id -> minutes
    locked_visit_order: List[str] = None       # nodes that cannot be reordered
    max_daily_work_minutes: int = 480
    serviced_route_subclass: str = "VEHICLE_ROUTING"  # VRP/TSP variation


@dataclass
class DailyRouteOptimizationOutputs:
    """Outputs: route sequence + metrics + diff vs baseline."""
    route_sequence: List[str]                  # node_ids in order
    depot_id: str
    total_distance_km: float
    total_travel_minutes: float
    total_service_minutes: float
    total_wait_minutes: float                   # wait for time windows
    total_work_minutes: float                   # travel + service + wait
    constraint_audit: Dict[str, Any]           # feasibility per constraint
    diff_vs_baseline: Dict[str, float] = field(default_factory=dict)


@dataclass
class DailyRouteOptimizationContract:
    """Optimizes single-day visit order for a fixed customer set under strict time-window + locked-node constraints."""
    capability_name: str = "daily_route_optimization"
    supported_decision_classes: List[DecisionClass] = field(
        default_factory=lambda: [DecisionClass.SEQUENTIAL_ROUTING]
    )
    required_structure_type: type = None

    def __post_init__(self):
        self.required_structure_type = DailyRouteOptimizationStructure

    hard_constraints: List[str] = field(default_factory=lambda: [
        "Customer set is FIXED — no add, no remove, no rep change",
        "Locked visit order (if any) is preserved exactly",
        "Every customer must be served within its time window (arrival <= tw_late)",
        "Service duration per customer must be respected",
        "Route must start and end at depot",
        "Max daily work minutes must not be exceeded"
    ])

    optimization_objective: str = (
        "Level 0: Hard constraints must be satisfied. "
        "Level 1: Maximize on-customer face-time utilization. "
        "Level 2: Minimize total in-transit minutes. "
        "Level 3: Minimize total km. "
        "Level 4: Stabilize route (minimize deviation from baseline)."
    )

    approximation_bounds: Dict[str, float] = field(default_factory=lambda: {
        "max_optimality_gap_pct": 5.0,
        "max_solver_runtime_sec": 60.0,
        "max_deviation_from_baseline_pct": 15.0,
    })

    output_evidence: List[str] = field(default_factory=lambda: [
        "Full ordered route sequence (depot -> ... -> depot)",
        "Per-segment travel time, service time, wait time",
        "Time-window feasibility audit per stop",
        "Diff vs baseline route (km, minutes, sequence changes)"
    ])

    unsupported_scenarios: List[str] = field(default_factory=lambda: [
        "Changing customer set (use TerritoryAlignmentCapability first)",
        "Changing visit cadence or weekly plan (use PeriodicVisitPlanningCapability)",
        "Changing rep-to-customer ownership (use TerritoryAlignmentCapability)",
        "Solving without explicit distance matrix (no implicit defaults)"
    ])

    validation_metrics: List[str] = field(default_factory=lambda: [
        "time_window_violation_count",
        "max_daily_work_minutes_utilization",
        "depot_start_end_closure",
        "route_deviation_pct_from_baseline"
    ])


@dataclass
class DailyRouteOptimizationStructure(BaseDecisionStructure):
    target_date: str = ""
    rep_id: str = ""
    depot_location: Dict[str, float] = field(default_factory=dict)
    customer_set: List[Dict[str, Any]] = field(default_factory=list)
    distance_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    locked_visit_order: List[str] = field(default_factory=list)
    max_daily_work_minutes: int = 480

    @property
    def structure_type(self) -> DecisionClass:
        return DecisionClass.SEQUENTIAL_ROUTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_type": self.structure_type.value,
            "target_date": self.target_date,
            "rep_id": self.rep_id,
            "customer_count": len(self.customer_set),
            "locked_count": len(self.locked_visit_order),
            "matrix_rows": len(self.distance_matrix),
        }
