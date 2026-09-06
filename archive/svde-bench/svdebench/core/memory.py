"""
svdebench.core.memory — Decision Memory Artifact Schema v0.1 (Sprint 1B Frozen)
Strictly pure data models and schema validation.
No Vector DB, no embedding, no search/retrieval algorithms.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

class MemoryClass(str, Enum):
    EPISODE = "EPISODE"
    CONSTRAINT_EVOLUTION = "CONSTRAINT_EVOLUTION"
    OUTCOME = "OUTCOME"
    ASSUMPTION = "ASSUMPTION"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    CAUSAL_DEPENDENCY = "CAUSAL_DEPENDENCY"

class MemoryLifecycleState(str, Enum):
    CANDIDATE = "CANDIDATE"
    EVALUATING = "EVALUATING"
    VALIDATED = "VALIDATED"
    PROMOTED = "PROMOTED"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"

class MemoryContext(BaseModel):
    applicable_scope: List[str] = Field(..., description="Applicable decision scopes or domains")
    preconditions: Dict[str, Any] = Field(..., description="Environmental/state preconditions (No Context, No Memory)")
    invalidation_conditions: Optional[str] = Field(default=None, description="Conditions under which memory expires/fails")

class MemoryTrigger(BaseModel):
    event_type: str = Field(..., description="Triggering event type")
    variation_classification: Optional[str] = Field(default=None, description="DATA_VARIATION | SEMANTIC_VARIATION")

class MemoryOutcomeEvaluation(BaseModel):
    predicted_outcome: Optional[Any] = Field(default=None, description="Expected objective/benchmark")
    realized_outcome: Optional[Any] = Field(default=None, description="Actual realized outcome")
    variance: Optional[str] = Field(default=None, description="Variance delta percentage or explanation")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score [0.0, 1.0]")

class MemorySourceEvidence(BaseModel):
    trace_id: Optional[str] = Field(default=None, description="Source decision trace id")
    case_id: Optional[str] = Field(default=None, description="Source decision case id")
    evidence_reference: Optional[str] = Field(default=None, description="Reference report or research proof")

class MemoryObject(BaseModel):
    memory_id: str = Field(..., description="Unique memory identifier (e.g. DMEM-DOM4-001)")
    memory_class: MemoryClass = Field(..., description="Memory classification category")
    decision_domain: str = Field(..., description="Originating decision domain")
    context: MemoryContext = Field(..., description="Contextual boundary (No Context, No Memory)")
    trigger: Optional[MemoryTrigger] = Field(default=None, description="Triggering mechanism")
    semantic_recommendation: Dict[str, Any] = Field(..., description="Semantic layer guidance (Never solver variables)")
    outcome_evaluation: Optional[MemoryOutcomeEvaluation] = Field(default=None, description="Outcome evaluation details")
    lifecycle: MemoryLifecycleState = Field(default=MemoryLifecycleState.CANDIDATE, description="Lifecycle state")
    source_evidence: Optional[MemorySourceEvidence] = Field(default=None, description="Provenance evidence link")
    expiration_date: Optional[str] = Field(default=None, description="Expiration date for memory aging")
    superseded_by: Optional[str] = Field(default=None, description="Pointer to superseding memory id")

    @model_validator(mode="after")
    def validate_memory_integrity(self) -> MemoryObject:
        # Rule 1: memory_id 不为空
        if not self.memory_id or not self.memory_id.strip():
            raise ValueError("Rule 1 Violation: memory_id cannot be empty")

        # Rule 3: PROMOTED Memory 必须完备具备 context, source_evidence, outcome_evaluation
        if self.lifecycle == MemoryLifecycleState.PROMOTED:
            if not self.source_evidence:
                raise ValueError("Rule 3 Violation: PROMOTED memory must specify 'source_evidence'")
            if not self.outcome_evaluation:
                raise ValueError("Rule 3 Violation: PROMOTED memory must specify 'outcome_evaluation'")

        # Rule 4: semantic_recommendation 严禁注入求解器底层变量 (Reuse Meaning, Not Exact Plan)
        rec_str = str(self.semantic_recommendation).lower()
        forbidden_solver_keywords = [
            "solver_variable", "set_solver_var", "x[", "f2_x", "o_x_", "variable_value",
            "coefficient_", "solver_option", "add_var", "primal_solution"
        ]
        for kw in forbidden_solver_keywords:
            if kw in rec_str:
                raise ValueError(f"Rule 4 Violation (The Semantic Impact Law): semantic_recommendation contains forbidden solver keyword '{kw}'. Memory must influence Semantic Layer, not Solver Layer.")

        return self

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryObject:
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
