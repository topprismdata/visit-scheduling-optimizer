"""
svdebench.oracle.cpsat.solver — Independent CP-SAT Solver Execution v0.1
Solves mathematical reference model and produces an OracleReference artifact.
"""
from __future__ import annotations
import time
from ortools.sat.python import cp_model
from svdebench.core.case import DecisionCase
from svdebench.oracle.base import ExactOracle
from svdebench.oracle.models import OracleReference
from svdebench.oracle.cpsat.model import CPSATModelBuilder

class CPSATExactOracle(ExactOracle):
    def __init__(self, time_limit_sec: float = 300.0, random_seed: int = 42):
        self.time_limit_sec = time_limit_sec
        self.random_seed = random_seed

    def solve(self, case: DecisionCase) -> OracleReference:
        builder = CPSATModelBuilder(case)
        model, meta = builder.build_delivery_model()
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_sec
        solver.parameters.random_seed = self.random_seed
        solver.parameters.num_search_workers = 4
        
        t0 = time.time()
        st = solver.Solve(model)
        wall_time = round(time.time() - t0, 3)
        
        if st == cp_model.OPTIMAL:
            status = "OPTIMAL"
            feasibility = "FEASIBLE"
            obj_val = solver.ObjectiveValue()
        elif st == cp_model.FEASIBLE:
            status = "FEASIBLE"
            feasibility = "FEASIBLE"
            obj_val = solver.ObjectiveValue()
        elif st == cp_model.INFEASIBLE:
            status = "INFEASIBLE"
            feasibility = "INFEASIBLE"
            obj_val = None
        else:
            status = "MODEL_INVALID"
            feasibility = "INFEASIBLE"
            obj_val = None

        return OracleReference(
            case_id=case.metadata.id,
            feasibility_status=feasibility,
            objective_value=float(obj_val) if obj_val is not None else None,
            constraint_summary={
                "capacity_constraints": "SATISFIED" if feasibility == "FEASIBLE" else "VIOLATED",
                "cold_chain_constraints": "SATISFIED" if feasibility == "FEASIBLE" else "VIOLATED",
                "commitment_constraints": "SATISFIED" if feasibility == "FEASIBLE" else "VIOLATED"
            },
            solution_metadata={
                "solver": "OR-Tools CP-SAT (Independent)",
                "wall_time_sec": wall_time,
                "best_bound": float(solver.BestObjectiveBound()) if status in ("OPTIMAL", "FEASIBLE") else None,
                "num_variables": meta.get("num_variables", 0),
                "num_branches": solver.NumBranches(),
                "num_conflicts": solver.NumConflicts()
            },
            solver_status=status
        )
