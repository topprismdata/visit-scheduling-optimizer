"""
svdebench.core.case — DecisionCase Data Model v0.1 (Sprint 0.6 Frozen)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

class CaseMetadata(BaseModel):
    id: str = Field(..., description="Unique case identifier")
    domain: str = Field(..., description="Decision domain name (e.g. delivery, warehouse, channel, visit)")
    name: Optional[str] = Field(default="", description="Descriptive case name")
    created_at: Optional[str] = Field(default="2026-08-22", description="Creation timestamp")
    tags: List[str] = Field(default_factory=list, description="Taxonomy tags")

class DecisionCase(BaseModel):
    metadata: CaseMetadata = Field(..., description="Case metadata")
    intent: Dict[str, Any] = Field(default_factory=dict, description="Business intent and objectives")
    world_state: Dict[str, Any] = Field(default_factory=dict, description="Physical and environment state")
    semantic_contract: Dict[str, Any] = Field(default_factory=dict, description="Semantic constraints and invariants")
    runtime_context: Optional[Dict[str, Any]] = Field(default=None, description="Dynamic state snapshot and past immutable facts")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Dynamic event stream sequence")

    @model_validator(mode="after")
    def validate_dynamic_context(self) -> DecisionCase:
        if self.events and not self.runtime_context:
            raise ValueError("Dynamic cases containing 'events' must provide a non-null 'runtime_context'")
        return self

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecisionCase:
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
