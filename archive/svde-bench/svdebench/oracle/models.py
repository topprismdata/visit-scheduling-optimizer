"""
svdebench.oracle.models — Oracle Reference Data Models v0.1 (Sprint 4 Frozen)
Represents independent mathematical gold references.
Strictly prohibited from containing agent decision recommendations or action advice.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class OracleReference(BaseModel):
    case_id: str = Field(..., description="Corresponding case id")
    feasibility_status: str = Field(..., description="FEASIBLE | INFEASIBLE")
    objective_value: Optional[float] = Field(default=None, description="Exact mathematical optimal objective value")
    constraint_summary: Dict[str, Any] = Field(default_factory=dict, description="Mathematical constraint status breakdown")
    solution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Solver statistics (e.g. wall_time, best_bound, num_nodes)")
    solver_status: str = Field(..., description="OPTIMAL | FEASIBLE | INFEASIBLE | MODEL_INVALID")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
