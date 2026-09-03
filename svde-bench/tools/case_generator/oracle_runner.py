"""Oracle Runner Adapter for SVDE-Bench v0.2.

Provides a unified invocation interface for solving benchmark cases using the
existing CPSATExactOracle solver backend.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import time
import yaml

from svdebench.oracle.cpsat import CPSATExactOracle
from svdebench.core import DecisionCase


class OracleResult:
    def __init__(
        self,
        status: str,
        objective: float,
        solution: Dict[str, Any],
        runtime_sec: float,
        case_id: str,
        raw_output: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.objective = objective
        self.solution = solution
        self.runtime_sec = runtime_sec
        self.case_id = case_id
        self.raw_output = raw_output or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "objective": self.objective,
            "solution": self.solution,
            "runtime_sec": self.runtime_sec,
            "case_id": self.case_id,
        }


class OracleRunner:
    def __init__(self, timeout_sec: int = 300):
        self.timeout_sec = timeout_sec
        self._oracle = CPSATExactOracle(time_limit_sec=timeout_sec)

    def run_case(self, case: DecisionCase) -> OracleResult:
        t0 = time.perf_counter()
        cid = case.metadata.id
        try:
            ref = self._oracle.solve(case)
            t1 = time.perf_counter()
            raw_dict = ref.to_dict() if hasattr(ref, "to_dict") else ref.__dict__
            return OracleResult(
                status=raw_dict.get("solver_status", raw_dict.get("feasibility_status", "UNKNOWN")),
                objective=float(raw_dict.get("objective_value") or 0.0),
                solution=raw_dict.get("solution_metadata", {}),
                runtime_sec=round(t1 - t0, 4),
                case_id=cid,
                raw_output=raw_dict,
            )
        except Exception as e:
            t1 = time.perf_counter()
            return OracleResult(
                status="ERROR",
                objective=0.0,
                solution={"error": str(e)},
                runtime_sec=round(t1 - t0, 4),
                case_id=cid,
            )

    def run_directory(self, case_dir: Path) -> OracleResult:
        """Adapts a multi-file case directory to a single DecisionCase object for solving."""
        meta_file = case_dir / "metadata.yaml"
        world_file = case_dir / "world_state.yaml"
        intent_file = case_dir / "intent.yaml"
        constraints_file = case_dir / "constraints.yaml"
        
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
        with open(world_file, "r", encoding="utf-8") as f:
            world = yaml.safe_load(f) or {}
        with open(intent_file, "r", encoding="utf-8") as f:
            intent = yaml.safe_load(f) or {}
        with open(constraints_file, "r", encoding="utf-8") as f:
            constraints = yaml.safe_load(f) or {}

        cid = meta.get("case_id") or meta.get("id") or case_dir.name
        
        # Normalize world_state: support Layer 1 'entities.vehicles' as 'fleet' for evaluators
        entities = world.get("entities", {})
        fleet = entities.get("vehicles", world.get("fleet", []))
        orders = entities.get("orders", world.get("orders", []))
        depot = world.get("depot", [0, 0])

        normalized_world = {
            "depot": depot,
            "fleet": fleet,
            "orders": orders,
            "entities": entities,
            "relationships": world.get("relationships", {}),
        }

        # Normalize constraints
        hard_list = constraints.get("hard", [])
        soft_list = constraints.get("soft", [])
        combined_constraints = hard_list + soft_list if isinstance(hard_list, list) else constraints

        combined_dict = {
            "metadata": {
                "id": cid,
                "domain": meta.get("domain", "delivery"),
                "name": meta.get("title", ""),
                "created_at": meta.get("created_at", "2026-08-24"),
                "tags": meta.get("tags", []),
            },
            "intent": intent,
            "world_state": normalized_world,
            "semantic_contract": {"constraints": combined_constraints},
        }
        case = DecisionCase.from_dict(combined_dict)
        return self.run_case(case)
