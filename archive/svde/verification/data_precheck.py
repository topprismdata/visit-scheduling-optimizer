"""SVDE Core Real-Data Precheck Validator.

Pre-flight data validation rules before running offline replay or shadow-mode decisions:
1. Entity ID uniqueness & non-emptiness.
2. Capacity & demand unit/type validity (non-negative numeric).
3. Time-window structural validity (tw_early <= tw_late).
4. Distance/edge-matrix completeness for routing (all node pairs must be connected or have numeric DEFAULT).
5. Explicit depot presence for sequential routing.
6. Ban on implicit fallback travel times.
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from svde.contracts import DecisionRequest, CompilationError


@dataclass
class PrecheckFinding:
    severity: str  # "ERROR" | "WARNING"
    field: str
    message: str


@dataclass
class PrecheckReport:
    is_valid: bool
    findings: List[PrecheckFinding] = field(default_factory=list)
    checked_entity_count: int = 0
    checked_edge_count: int = 0

    @property
    def errors(self) -> List[PrecheckFinding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def warnings(self) -> List[PrecheckFinding]:
        return [f for f in self.findings if f.severity == "WARNING"]


class DataPrecheckValidator:
    """Pre-flight validator for real enterprise historical/shadow dataset ingestion."""

    def validate(self, request: DecisionRequest) -> PrecheckReport:
        findings: List[PrecheckFinding] = []
        world = request.world_state or {}
        entities = world.get("entities", {})
        fleet = world.get("fleet", entities.get("vehicles", []))
        orders = world.get("orders", entities.get("orders", []))
        stops = world.get("stops", [])

        # 1. Check Resource IDs & Capacity Numeric Non-Negativity
        seen_res_ids: Set[str] = set()
        for idx, r in enumerate(fleet):
            r_id = r.get("id")
            if not r_id or not str(r_id).strip():
                findings.append(PrecheckFinding("ERROR", f"fleet[{idx}].id", "Resource ID must be non-empty string"))
            elif str(r_id) in seen_res_ids:
                findings.append(PrecheckFinding("ERROR", f"fleet[{idx}].id", f"Duplicate resource ID '{r_id}'"))
            seen_res_ids.add(str(r_id))

            cap = r.get("capacity_kg", r.get("capacity", r.get("max_daily_minutes")))
            if cap is not None:
                if not isinstance(cap, (int, float)) or isinstance(cap, bool) or cap < 0:
                    findings.append(PrecheckFinding("ERROR", f"fleet[{idx}].capacity", f"Capacity must be non-negative numeric, got {cap}"))

        # 2. Check Order/Task IDs, Demand & Time-Windows
        seen_task_ids: Set[str] = set()
        for idx, o in enumerate(orders):
            o_id = o.get("id")
            if not o_id or not str(o_id).strip():
                findings.append(PrecheckFinding("ERROR", f"orders[{idx}].id", "Order/Task ID must be non-empty string"))
            elif str(o_id) in seen_task_ids:
                findings.append(PrecheckFinding("ERROR", f"orders[{idx}].id", f"Duplicate task ID '{o_id}'"))
            seen_task_ids.add(str(o_id))

            dmd = o.get("weight_kg", o.get("demand", o.get("duration_mins")))
            if dmd is not None:
                if not isinstance(dmd, (int, float)) or isinstance(dmd, bool) or dmd < 0:
                    findings.append(PrecheckFinding("ERROR", f"orders[{idx}].demand", f"Demand must be non-negative numeric, got {dmd}"))

            tw_e = o.get("tw_early")
            tw_l = o.get("tw_late")
            if tw_e is not None and tw_l is not None:
                if tw_e > tw_l:
                    findings.append(PrecheckFinding("ERROR", f"orders[{idx}].time_window", f"Invalid time window: tw_early ({tw_e}) > tw_late ({tw_l})"))

        # 3. Routing Edge Matrix & Depot Validation (Gap 2 Hardening)
        edge_matrix = world.get("distance_matrix", world.get("edge_matrix", {}))
        edge_count = 0
        is_routing_domain = bool(stops or request.domain in ("city_routing", "sequential_routing"))

        if is_routing_domain:
            # Check Depot Presence
            has_depot = any(s.get("is_depot") or "DEPOT" in str(s.get("id", "")).upper() for s in stops)
            if not has_depot and not any("DEPOT" in str(r_id).upper() for r_id in seen_res_ids):
                findings.append(PrecheckFinding("ERROR", "world_state.stops", "Sequential routing requires at least one explicit depot stop"))

            # Check Edge Matrix Completeness
            if not edge_matrix:
                findings.append(PrecheckFinding("ERROR", "world_state.edge_matrix", "Missing edge_matrix: routing datasets must supply explicit distance/time matrix (no implicit default travel time)"))
            else:
                has_default_fallback = False
                if "DEFAULT" in edge_matrix:
                    row_def = edge_matrix["DEFAULT"]
                    if not isinstance(row_def, (int, float)) or isinstance(row_def, bool):
                        findings.append(PrecheckFinding("ERROR", "edge_matrix.DEFAULT", f"DEFAULT fallback cost must be numeric, got {type(row_def).__name__}"))
                    else:
                        has_default_fallback = True

                # Validate matrix row formatting
                for src_k, row in edge_matrix.items():
                    if src_k == "DEFAULT":
                        continue
                    if not isinstance(row, dict):
                        findings.append(PrecheckFinding("ERROR", f"edge_matrix[{src_k}]", "Each origin in edge_matrix must map to a destination dict"))
                    else:
                        for dst_k, cost in row.items():
                            edge_count += 1
                            if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                                findings.append(PrecheckFinding("ERROR", f"edge_matrix[{src_k}][{dst_k}]", f"Edge weight must be non-negative numeric, got {cost}"))

                # Check all stop pairs connectivity if no DEFAULT fallback is provided
                if not has_default_fallback and stops:
                    stop_ids = [s.get("id") for s in stops if s.get("id")]
                    for u in stop_ids:
                        if u not in edge_matrix:
                            findings.append(PrecheckFinding("ERROR", f"edge_matrix[{u}]", f"Missing distance matrix row for stop '{u}'"))
                        else:
                            for v in stop_ids:
                                if u != v and v not in edge_matrix[u]:
                                    findings.append(PrecheckFinding("ERROR", f"edge_matrix[{u}][{v}]", f"Missing edge connectivity from '{u}' to '{v}' in distance matrix"))

        is_valid = len([f for f in findings if f.severity == "ERROR"]) == 0
        return PrecheckReport(
            is_valid=is_valid,
            findings=findings,
            checked_entity_count=len(seen_res_ids) + len(seen_task_ids),
            checked_edge_count=edge_count
        )
