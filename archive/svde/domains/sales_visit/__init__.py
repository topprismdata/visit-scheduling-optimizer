"""SVDE Sales Visit Domain Input Contracts.

Domain-level input entities for Sales Visit decision problems.
These mirror A01/A05 reference architecture and prevent flattening customers into
generic COMMITTED_TASK. Each entity carries business semantics that must NOT be lost
during domain → canonical translation.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class Customer:
    """A retail/medical account that must be visited under a VisitPolicy."""
    id: str
    name: str
    location: Dict[str, float]                 # {"lat":..., "lon":...}
    commercial_value: float = 0.0              # monthly revenue / priority score
    tier: str = "STANDARD"                      # STRATEGIC | CORE | DEVELOPMENT
    visit_policy_id: str = ""


@dataclass
class VisitPolicy:
    """Per-customer cadence + window + override rules."""
    customer_id: str
    cadence_spec_id: str
    weekly_availability: List[str] = field(default_factory=list)  # ["Mon","Tue","Wed","Thu","Fri"]
    preferred_time_window: List[int] = field(default_factory=list) # [earliest, latest] in minutes
    min_interval_days: int = 0
    max_interval_days: int = 30
    locked_visit_days: List[str] = field(default_factory=list)   # forced days (e.g. VIP Tue AM)


@dataclass
class CadenceSpec:
    """Specifies the desired visit frequency (per week / per month)."""
    id: str
    customer_id: str
    visits_per_week: int = 1
    visits_per_month: int = 4
    tolerance_days: int = 1                     # acceptable jitter


@dataclass
class WeeklyAvailability:
    """Which weekdays a rep works and their daily capacity (in minutes)."""
    rep_id: str
    working_days: List[str] = field(default_factory=list)         # ["Mon","Tue","Wed","Thu","Fri"]
    daily_capacity_minutes: int = 480
    base_location: Dict[str, float] = field(default_factory=dict)


@dataclass
class OwnershipPolicy:
    """Customer-to-rep ownership. Can be locked (cannot change) or floating (can rebalance)."""
    customer_id: str
    rep_id: str
    is_locked: bool = False                    # if True, TerritoryAlignment MUST NOT move this customer
    tenure_months: int = 0


@dataclass
class ExistingCommitment:
    """A visit that is already promised/contractually locked and CANNOT be moved."""
    id: str
    customer_id: str
    rep_id: str
    date: str                                   # YYYY-MM-DD
    time_window: List[int] = field(default_factory=list)
    is_hard: bool = True


@dataclass
class ResourceDayProfile:
    """Per-day per-rep workload capacity and shift window."""
    rep_id: str
    date: str
    total_capacity_minutes: int = 480
    committed_minutes: int = 0
    available_minutes: int = 480


@dataclass
class ObservedTravelCost:
    """Real-world observed travel cost matrix between nodes."""
    source: str                                 # "OSRM", "MANUAL", "STRAIGHT_LINE"
    matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)  # node_id -> node_id -> minutes
    captured_at: str = ""


@dataclass
class ObjectivePolicy:
    """Hierarchical objective for any Sales Visit decision problem."""
    priority_levels: List[str] = field(default_factory=lambda: [
        "Hard constraints (cadence, locked, window, ownership, capacity)",
        "Maximize commercial value covered",
        "Minimize in-transit time / distance",
        "Stabilize plan (minimize deviation)",
    ])
    deprioritize_distance: bool = True         # never trade SLA for distance
    forbid_relaxing_locked: bool = True        # NEVER downgrade locked commitments
