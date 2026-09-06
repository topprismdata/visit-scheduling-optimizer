"""
svdebench.core.schema — Core Data Models & Schemas (Placeholder implementation for Sprint 0)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DecisionCase(BaseModel):
    """
    Standardized benchmark input case.
    Strictly contains no gold solutions or private evaluation metrics.
    """
    id: str = Field(..., description="Unique case identifier")
    domain: str = Field(..., description="Decision domain name")
    intent: Dict[str, Any] = Field(default_factory=dict, description="Business intent parameters")
    world_state: Dict[str, Any] = Field(default_factory=dict, description="Initial physical environment state")
    contract: Dict[str, Any] = Field(default_factory=dict, description="Semantic constraints and invariants")
    runtime_events: List[Dict[str, Any]] = Field(default_factory=list, description="Event stream sequence")

class DecisionArtifact(BaseModel):
    """
    Standardized decision agent output.
    Must not contain agent internal memory/reasoning dumps, only explicit decision outputs.
    """
    case_id: str = Field(..., description="Corresponding case id")
    status: str = Field(..., description="FEASIBLE | INFEASIBLE")
    decision: Dict[str, Any] = Field(default_factory=dict, description="Executable decision allocations")
    trace: Dict[str, Any] = Field(default_factory=dict, description="Causal decision explanation")
    memory_update: Optional[Dict[str, Any]] = Field(default=None, description="Proposed candidate memory patch")
