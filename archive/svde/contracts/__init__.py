"""SVDE Core Contracts.

Defines the single source of truth for domain-neutral data contracts:
- Canonical Enums: DecisionClass, FeasibilityStatus
- Normalized Entities: NormalizedEntity, NormalizedResource, NormalizedTask
- Exceptions: SVDEError, UnsupportedDomainError, UnsupportedCapabilityError, CompilationError
- Decision Structures: BaseDecisionStructure, AssignmentDecisionStructure, RoutingDecisionStructure, RoutingNode, RoutingEdge
- Capability Contracts: CapabilityContract, CapabilityStepTrace, PipelineExecutionAudit
- Decision Pipeline Objects: DecisionRequest, DecisionContext, DecisionSpec, CapabilityStep, DecisionPlan, DecisionResult, DecisionEvidence, DecisionArtifact
"""
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import hashlib
import json
from svde.contracts.exceptions import SVDEError, UnsupportedDomainError, UnsupportedCapabilityError, CompilationError


class DecisionClass(str, Enum):
    """Canonical decision paradigm classification."""
    DISCRETE_ASSIGNMENT = "discrete_assignment"
    SEQUENTIAL_ROUTING = "sequential_routing"
    PERIODIC_SCHEDULING = "periodic_scheduling"
    RESOURCE_ALLOCATION = "resource_allocation"
    SPATIAL_SLOTTING = "spatial_slotting"
    POLICY_SELECTION = "policy_selection"
    PREDICTIVE_SIMULATION = "predictive_simulation"
    RULE_EVALUATION = "rule_evaluation"
    HUMAN_REVIEW = "human_review"


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass
class NormalizedEntity:
    """Canonical representation of any decision entity."""
    entity_id: str
    entity_type: str  # "EXECUTION_RESOURCE", "COMMITTED_TASK", "LOCATION_SLOT", etc.
    attributes: Dict[str, Any] = field(default_factory=dict)
    capacity: Optional[float] = None
    demand: Optional[float] = None
    is_active: bool = True
    is_locked: bool = False
    required_competencies: List[str] = field(default_factory=list)
    provided_competencies: List[str] = field(default_factory=list)
    time_window: Optional[List[int]] = None


NormalizedResource = NormalizedEntity
NormalizedTask = NormalizedEntity


class BaseDecisionStructure(ABC):
    """Abstract interface for canonical decision problem structures."""
    @property
    @abstractmethod
    def structure_type(self) -> DecisionClass:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass


@dataclass
class AssignmentDecisionStructure(BaseDecisionStructure):
    """Canonical structure for discrete resource-to-task assignment problems."""
    resources: List[NormalizedEntity] = field(default_factory=list)
    tasks: List[NormalizedEntity] = field(default_factory=list)
    contention_ratio: float = 0.0
    has_hard_commitments: bool = False
    has_competency_constraints: bool = False

    @property
    def structure_type(self) -> DecisionClass:
        return DecisionClass.DISCRETE_ASSIGNMENT

    @property
    def resource_count(self) -> int:
        return len(self.resources)

    @property
    def task_count(self) -> int:
        return len(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_type": self.structure_type.value,
            "resource_count": self.resource_count,
            "task_count": self.task_count,
            "contention_ratio": self.contention_ratio,
            "has_hard_commitments": self.has_hard_commitments,
            "has_competency_constraints": self.has_competency_constraints,
        }


@dataclass
class RoutingNode:
    node_id: str
    node_type: str  # "DEPOT", "CUSTOMER_STOP", "CHARGING_STATION"
    location_coords: List[float] = field(default_factory=lambda: [0.0, 0.0])
    service_duration: float = 0.0
    time_window: Optional[List[int]] = None
    is_locked_window: bool = False


@dataclass
class RoutingEdge:
    origin_id: str
    destination_id: str
    travel_time: float
    travel_distance: float


@dataclass
class RoutingDecisionStructure(BaseDecisionStructure):
    """Canonical structure for sequential routing and TSP/VRP network problems."""
    nodes: List[RoutingNode] = field(default_factory=list)
    edge_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    depot_ids: List[str] = field(default_factory=list)
    max_travel_time_per_route: Optional[float] = None
    has_sequence_locks: bool = False

    @property
    def structure_type(self) -> DecisionClass:
        return DecisionClass.SEQUENTIAL_ROUTING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structure_type": self.structure_type.value,
            "node_count": len(self.nodes),
            "depot_ids": self.depot_ids,
            "has_edge_matrix": len(self.edge_matrix) > 0,
            "has_sequence_locks": self.has_sequence_locks,
        }


@dataclass
class CapabilityContract:
    """Formal interface contract defining a capability's input structure, output guarantees, and invariants."""
    capability_name: str
    supported_decision_classes: List[DecisionClass]
    required_structure_type: Type[BaseDecisionStructure]
    guarantees: List[str] = field(default_factory=list)
    evidence_types_emitted: List[str] = field(default_factory=list)


@dataclass
class CapabilityStepTrace:
    """Granular per-step execution trace capturing input/output integrity hashes and runtime metrics."""
    step_id: str
    capability_name: str
    status: str
    input_hash: str
    output_hash: str
    objective_value: float
    principles_applied: List[str] = field(default_factory=list)
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    raw_step_trace: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def compute_hash(data: Any) -> str:
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
        except Exception:
            serialized = str(data)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()[:12]


@dataclass
class PipelineExecutionAudit:
    """Complete audit envelope for multi-step capability execution pipelines."""
    plan_id: str
    total_steps_executed: int
    step_traces: List[CapabilityStepTrace] = field(default_factory=list)
    pipeline_status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "total_steps_executed": self.total_steps_executed,
            "pipeline_status": self.pipeline_status,
            "step_traces": [
                {
                    "step_id": t.step_id,
                    "capability": t.capability_name,
                    "status": t.status,
                    "input_hash": t.input_hash,
                    "output_hash": t.output_hash,
                    "objective": t.objective_value,
                    "principles": t.principles_applied,
                    "metrics": t.execution_metrics,
                    "trace": t.raw_step_trace,
                }
                for t in self.step_traces
            ]
        }


@dataclass
class DecisionRequest:
    """Incoming business decision request."""
    request_id: str
    domain: str
    intent: Dict[str, Any]
    world_state: Dict[str, Any]
    semantic_contract: Dict[str, Any] = field(default_factory=dict)
    runtime_context: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionContext:
    """Domain-neutral, generalized decision context."""
    request_id: str
    domain: str
    primary_objective: str
    decision_classes: List[DecisionClass] = field(default_factory=lambda: [DecisionClass.DISCRETE_ASSIGNMENT])
    entities: List[NormalizedEntity] = field(default_factory=list)
    structure: Optional[BaseDecisionStructure] = None
    
    invariants: List[Dict[str, Any]] = field(default_factory=list)
    contention_ratio: float = 0.0
    has_hard_commitments: bool = False
    has_competency_constraints: bool = False
    has_resource_failure: bool = False
    raw_world_state: Dict[str, Any] = field(default_factory=dict)

    @property
    def resources(self) -> List[NormalizedEntity]:
        return [e for e in self.entities if e.entity_type == "EXECUTION_RESOURCE"]

    @property
    def tasks(self) -> List[NormalizedEntity]:
        return [e for e in self.entities if e.entity_type == "COMMITTED_TASK"]

    @property
    def active_resource_count(self) -> int:
        return sum(1 for r in self.resources if r.is_active)

    @property
    def total_active_capacity(self) -> float:
        return sum(r.capacity or 0.0 for r in self.resources if r.is_active)

    @property
    def total_task_demand(self) -> float:
        return sum(t.demand or 0.0 for t in self.tasks)

    @property
    def resource_contention_ratio(self) -> float:
        return self.contention_ratio


@dataclass
class DecisionSpec:
    spec_id: str
    domain: str
    context: DecisionContext
    decision_class: DecisionClass = DecisionClass.DISCRETE_ASSIGNMENT
    decision_structure: Optional[BaseDecisionStructure] = None
    required_capabilities: List[str] = field(default_factory=lambda: ["discrete_assignment"])
    hard_invariants: List[Dict[str, Any]] = field(default_factory=list)
    soft_preferences: List[Dict[str, Any]] = field(default_factory=list)
    governing_principles: List[Dict[str, Any]] = field(default_factory=list)
    objective_formulation: str = "lexicographic_invariants_then_commitments_then_efficiency"


@dataclass
class CapabilityStep:
    """Represents an ordered execution step within a multi-capability DecisionPlan."""
    step_id: str
    capability_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionPlan:
    """Ordered pipeline of capability execution steps."""
    plan_id: str
    steps: List[CapabilityStep] = field(default_factory=list)
    selected_engine: str = "discrete_assignment"
    execution_steps: List[str] = field(default_factory=list)
    engine_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionResult:
    request_id: str
    status: str
    raw_decision: Dict[str, Any] = field(default_factory=dict)
    objective_value: float = 0.0
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    engine_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhysicalFeasibilityEvidence:
    satisfied: bool
    violations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessFeasibilityEvidence:
    satisfied: bool
    violations: List[str] = field(default_factory=list)
    commitments_honored: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticComplianceEvidence:
    satisfied: bool
    violations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionEvidence:
    """Segregated, orthogonal evidence spaces."""
    physical: PhysicalFeasibilityEvidence
    business: BusinessFeasibilityEvidence
    semantic: SemanticComplianceEvidence
    activated_principles: List[Dict[str, Any]] = field(default_factory=list)
    rejected_principles: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def hard_invariants_satisfied(self) -> bool:
        return self.physical.satisfied

    @property
    def commitments_honored(self) -> bool:
        return self.business.commitments_honored

    @property
    def solution_feasible(self) -> bool:
        return self.physical.satisfied

    @property
    def decision_feasible(self) -> bool:
        return self.physical.satisfied and self.business.satisfied

    @property
    def semantic_compliance(self) -> bool:
        return self.semantic.satisfied

    @property
    def violations(self) -> List[str]:
        return self.physical.violations + self.business.violations + self.semantic.violations

    @property
    def explanations(self) -> Dict[str, Any]:
        return {
            "physical_details": self.physical.details,
            "business_details": self.business.details,
            "semantic_details": self.semantic.details,
        }


@dataclass
class DecisionArtifact:
    request_id: str
    domain: str
    decision: Dict[str, Any]
    solution_feasible: bool
    decision_feasible: bool
    semantic_compliance: bool
    evidence: DecisionEvidence
    activated_principles: List[Dict[str, Any]] = field(default_factory=list)
    rejected_principles: List[Dict[str, Any]] = field(default_factory=list)
    execution_trace: Dict[str, Any] = field(default_factory=dict)
    unresolved_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "domain": self.domain,
            "decision": self.decision,
            "solution_feasible": self.solution_feasible,
            "decision_feasible": self.decision_feasible,
            "semantic_compliance": self.semantic_compliance,
            "activated_principles": self.activated_principles,
            "rejected_principles": self.rejected_principles,
            "evidence": {
                "physical_feasible": self.evidence.physical.satisfied,
                "business_feasible": self.evidence.business.satisfied,
                "semantic_compliant": self.evidence.semantic.satisfied,
                "violations": self.evidence.violations,
                "explanations": self.evidence.explanations,
            },
            "execution_trace": self.execution_trace,
            "unresolved_issues": self.unresolved_issues,
        }


__all__ = [
    "DecisionClass",
    "FeasibilityStatus",
    "BaseDecisionStructure",
    "AssignmentDecisionStructure",
    "RoutingDecisionStructure",
    "RoutingNode",
    "RoutingEdge",
    "CapabilityStep",
    "CapabilityContract",
    "CapabilityStepTrace",
    "PipelineExecutionAudit",
    "NormalizedEntity",
    "NormalizedResource",
    "NormalizedTask",
    "DecisionRequest",
    "DecisionContext",
    "DecisionSpec",
    "DecisionPlan",
    "DecisionResult",
    "PhysicalFeasibilityEvidence",
    "BusinessFeasibilityEvidence",
    "SemanticComplianceEvidence",
    "DecisionEvidence",
    "DecisionArtifact",
    "SVDEError",
    "UnsupportedDomainError",
    "UnsupportedCapabilityError",
    "CompilationError",
]
