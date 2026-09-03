"""
svdebench.evaluator.models — Unified Evaluation Result Models v0.1 (Sprint 3.5 Complete Suite)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class BaseEvaluationResult(BaseModel):
    evaluator_name: str = Field(..., description="Name of the evaluator")
    overall_pass: bool = Field(..., description="High-level boolean pass/fail status")
    score: float = Field(default=1.0, ge=0.0, le=1.0, description="Normalized score [0.0, 1.0]")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Structured finding details")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Audit evidence and explanations")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class FeasibilityEvaluationResult(BaseEvaluationResult):
    evaluator_name: str = Field(default="FeasibilityEvaluator")
    feasibility_status: str = Field(..., description="FEASIBLE | INFEASIBLE")
    constraint_results: List[Dict[str, Any]] = Field(default_factory=list, description="Per-constraint physical checks")
    objective_gap: Optional[float] = Field(default=None, description="Gap against oracle objective (if oracle provided)")
    oracle_comparison: Optional[Dict[str, Any]] = Field(default=None, description="Oracle reference comparison details")
    violations: List[str] = Field(default_factory=list, description="Physical capacity or hard math violations")

class RuntimeEvaluationResult(BaseEvaluationResult):
    evaluator_name: str = Field(default="RuntimeEvaluator")
    event_results: List[Dict[str, Any]] = Field(default_factory=list, description="Per-event replay evaluation status")
    commitment_survival_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Ratio of preserved commitments [0.0, 1.0]")
    disruption_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of reallocated objects over total objects [0.0, 1.0]")
    state_transition_validity: bool = Field(default=True, description="Whether all runtime state transitions were valid and monotonic")
    violations: List[str] = Field(default_factory=list, description="State transition or broken commitment violations")

class MemoryEvaluationResult(BaseEvaluationResult):
    evaluator_name: str = Field(default="MemoryEvaluator")
    promotion_status: str = Field(..., description="PROMOTED | VALIDATED | REJECTED | CANDIDATE")
    lifecycle_validation: bool = Field(default=True, description="Whether memory lifecycle state is valid")
    evidence_sufficiency: bool = Field(default=True, description="Whether memory has sufficient trace/outcome proof")
    context_boundary_check: bool = Field(default=True, description="Whether context scope and preconditions are bounded")
    contradiction_check: bool = Field(default=True, description="Whether memory is free from direct knowledge conflict")
    false_memory_probability: float = Field(default=0.0, ge=0.0, le=1.0, description="Probability score of false memory/over-generalization [0.0, 1.0]")
    violations: List[str] = Field(default_factory=list, description="MDVL gate rejections or boundary violations")
