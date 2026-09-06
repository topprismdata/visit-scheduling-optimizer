"""
svdebench.core.artifact — DecisionArtifact Data Model v0.1 (Sprint 1B Updated)
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Literal, Union
from pydantic import BaseModel, Field
from svdebench.core.trace import DecisionTrace
from svdebench.core.memory import MemoryObject

class DecisionArtifact(BaseModel):
    case_id: str = Field(..., description="Corresponding case id")
    status: Literal["FEASIBLE", "INFEASIBLE"] = Field(..., description="Decision feasibility status")
    decision: Dict[str, Any] = Field(default_factory=dict, description="Executable decision allocations")
    trace: DecisionTrace = Field(..., description="Causal decision trace")
    explanation: Dict[str, Any] = Field(default_factory=dict, description="Human/business readable explainability")
    validation_result: Optional[Dict[str, Any]] = Field(default=None, description="Pre/post DSVL validation output")
    memory_patch: Optional[Union[MemoryObject, Dict[str, Any]]] = Field(default=None, description="Candidate memory update object")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionArtifact:
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
