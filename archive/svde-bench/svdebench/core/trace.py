"""
svdebench.core.trace — DecisionTrace Data Model v0.1
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DecisionTrace(BaseModel):
    trace_id: str = Field(..., description="Unique trace identifier")
    decision_chain: List[Dict[str, Any]] = Field(default_factory=list, description="Causal pipeline stages")
    causal_rationale: List[Dict[str, Any]] = Field(default_factory=list, description="Entity level rationales")
    constraint_provenance: Dict[str, str] = Field(default_factory=dict, description="Constraint to source mapping")
