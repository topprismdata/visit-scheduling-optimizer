"""SVDE Core Capability Contracts & Trace Primitives.

Defines the formal input/output contracts, guarantees, and evidence requirements
for all computational capabilities in the SVDE Decision Operating System:
- CapabilityContract (Declarative capability input/output/guarantee contract)
- CapabilityStepTrace (Granular per-capability execution trace with deterministic MD5 audit digests)
- PipelineExecutionAudit (End-to-end multi-step capability pipeline audit envelope)
"""
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field
import hashlib
import json
from svde.contracts.decision_structures import BaseDecisionStructure, DecisionClass


@dataclass
class CapabilityContract:
    """Formal interface contract defining a capability's input structure, output guarantees, and invariants."""
    capability_name: str
    supported_decision_classes: List[DecisionClass]
    required_structure_type: Type[BaseDecisionStructure]
    guarantees: List[str] = field(default_factory=list)  # e.g., ["CAPACITY_BOUND_SATISFIED", "DETERMINISTIC_EXECUTION"]
    evidence_types_emitted: List[str] = field(default_factory=list)  # e.g., ["PHYSICAL_FEASIBILITY", "SEMANTIC_COMPLIANCE"]


@dataclass
class CapabilityStepTrace:
    """Granular per-step execution trace capturing input/output integrity fingerprints and runtime metrics."""
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
        """Computes a deterministic 12-char MD5 fingerprint digest for input/output audit verification."""
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
