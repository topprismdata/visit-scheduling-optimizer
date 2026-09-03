"""Decision Context Abstraction for SVDE-Bench v0.5 Runtime.

Provides a unified, de-grounded representation of operational reality,
delegating domain-specific ingestion to explicit Domain Adapters.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from svdebench.core import DecisionCase


@dataclass
class NormalizedResource:
    resource_id: str
    resource_class: str  # e.g., STANDARD_VAN, COLD_REFRIGERATED, SPECIALIST_REP, SENIOR_REP
    capacity_limit: float
    status: str  # AVAILABLE, BROKEN_DOWN, ON_LEAVE, SICK_LEAVE
    is_active: bool


@dataclass
class NormalizedTask:
    task_id: str
    demand_quantity: float
    is_locked: bool
    is_vip: bool
    required_competency: str  # GENERAL, COLD_CHAIN, SPECIALIST, SENIOR
    time_window: Optional[List[int]] = None


@dataclass
class DecisionContext:
    case_id: str
    domain: str
    primary_objective: str
    resources: List[NormalizedResource] = field(default_factory=list)
    tasks: List[NormalizedTask] = field(default_factory=list)
    resource_contention_ratio: float = 0.0
    has_hard_commitments: bool = False
    has_competency_constraints: bool = False
    has_resource_failure: bool = False
    active_resource_count: int = 0
    total_active_capacity: float = 0.0
    total_task_demand: float = 0.0
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_decision_case(cls, case: DecisionCase) -> "DecisionContext":
        """Delegates case translation to the registered DomainAdapter."""
        from domains.adapters.registry import ADAPTER_REGISTRY
        dom = case.metadata.domain if hasattr(case.metadata, "domain") else "delivery"
        adapter = ADAPTER_REGISTRY.get_adapter(dom)
        return adapter.to_decision_context(case)
