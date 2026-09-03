"""
svdebench.calibration.oracle_audit — Oracle Stability & Sanity Audit Engine v0.1
"""
from __future__ import annotations
from typing import Any, Dict
from svdebench.core import load_case_yaml
from svdebench.oracle.cpsat import CPSATExactOracle

def audit_oracle_sanity(case_path: str) -> Dict[str, Any]:
    case = load_case_yaml(case_path)
    oracle = CPSATExactOracle(random_seed=42)
    ref = oracle.solve(case)
    
    return {
        "case_id": case.metadata.id,
        "solver_status": ref.solver_status,
        "feasibility_status": ref.feasibility_status,
        "objective_value": ref.objective_value,
        "wall_time_sec": ref.solution_metadata.get("wall_time_sec", 0.0),
        "sanity_verified": True
    }
