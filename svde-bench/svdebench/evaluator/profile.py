"""
svdebench.evaluator.profile — Four-Dimensional Decision Intelligence Profile v0.1 (Sprint 3.5 Frozen)
Aggregates four-dimensional evaluation results into a unified profile.
Strictly prohibited from compressing multi-dimensional profiles into a single scalar score.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from svdebench.evaluator.semantic import SemanticEvaluationResult
from svdebench.evaluator.models import (
    FeasibilityEvaluationResult,
    RuntimeEvaluationResult,
    MemoryEvaluationResult,
)

class DecisionIntelligenceProfile(BaseModel):
    case_id: str = Field(..., description="Unique case identifier")
    agent_name: str = Field(..., description="Name of the evaluated decision agent")
    semantic_result: Optional[SemanticEvaluationResult] = Field(default=None, description="Dimension 1: Semantic Correctness")
    feasibility_result: Optional[FeasibilityEvaluationResult] = Field(default=None, description="Dimension 2: Execution Feasibility")
    runtime_result: Optional[RuntimeEvaluationResult] = Field(default=None, description="Dimension 3: Runtime Adaptability")
    memory_result: Optional[MemoryEvaluationResult] = Field(default=None, description="Dimension 4: Decision Memory Governance")
    overall_summary: Dict[str, Any] = Field(default_factory=dict, description="Structured dimensional overview (No single scalar score)")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_evaluators(
        cls,
        case_id: str,
        agent_name: str,
        semantic_res: Optional[SemanticEvaluationResult] = None,
        feasibility_res: Optional[FeasibilityEvaluationResult] = None,
        runtime_res: Optional[RuntimeEvaluationResult] = None,
        memory_res: Optional[MemoryEvaluationResult] = None,
    ) -> DecisionIntelligenceProfile:
        summary = {
            "semantic_pass": semantic_res.overall_pass if semantic_res else None,
            "feasibility_status": feasibility_res.feasibility_status if feasibility_res else None,
            "commitment_survival_rate": runtime_res.commitment_survival_rate if runtime_res else None,
            "memory_promotion_status": memory_res.promotion_status if memory_res else None,
            "all_mandatory_passed": (
                (semantic_res.overall_pass if semantic_res else True) and
                (feasibility_res.overall_pass if feasibility_res else True) and
                (runtime_res.overall_pass if runtime_res else True) and
                (memory_res.overall_pass if memory_res else True)
            )
        }
        return cls(
            case_id=case_id,
            agent_name=agent_name,
            semantic_result=semantic_res,
            feasibility_result=feasibility_res,
            runtime_result=runtime_res,
            memory_result=memory_res,
            overall_summary=summary
        )
