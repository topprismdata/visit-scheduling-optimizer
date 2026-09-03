"""
svdebench.evaluator.feasibility — Feasibility Evaluator v0.1 (Sprint 3B Frozen)
Evaluates physical capacity, hard constraints, and mathematical feasibility.
Provides Oracle Comparison Interface for objective gap benchmarking.
Strictly decoupled from SemanticEvaluator, zero solver generation code.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from svdebench.core.case import DecisionCase
from svdebench.core.artifact import DecisionArtifact
from svdebench.evaluator.base import BaseEvaluator
from svdebench.evaluator.models import FeasibilityEvaluationResult

class FeasibilityEvaluator(BaseEvaluator):
    def evaluate(
        self,
        case: DecisionCase,
        artifact: DecisionArtifact,
        gold: Optional[Dict[str, Any]] = None
    ) -> FeasibilityEvaluationResult:
        world = case.world_state or {}
        fleet = {v["id"]: v for v in world.get("fleet", [])}
        orders = {o["id"]: o for o in world.get("orders", [])}
        
        decision_routes = artifact.decision.get("reassigned_routes", {}) or artifact.decision.get("routes", {})
        
        constraint_results: List[Dict[str, Any]] = []
        violations: List[str] = []
        
        # ── Rule 1 & 2: Physical Capacity & Vehicle Load Limits ──
        for v_id, o_list in decision_routes.items():
            veh = fleet.get(v_id)
            if not veh:
                violations.append(f"Unknown vehicle {v_id} assigned in route")
                continue
                
            cap_limit = veh.get("capacity_kg", float("inf"))
            total_load = sum(orders[o]["weight_kg"] for o in o_list if o in orders)
            
            if total_load <= cap_limit:
                constraint_results.append({
                    "type": "VEHICLE_CAPACITY",
                    "entity": v_id,
                    "actual_load_kg": total_load,
                    "capacity_limit_kg": cap_limit,
                    "status": "SATISFIED"
                })
            else:
                violations.append(f"Vehicle {v_id} overloaded: {total_load}kg > {cap_limit}kg")
                constraint_results.append({
                    "type": "VEHICLE_CAPACITY",
                    "entity": v_id,
                    "actual_load_kg": total_load,
                    "capacity_limit_kg": cap_limit,
                    "status": "VIOLATED"
                })
                
        # ── Rule 2: Hard Time Window Feasibility Check (if arrival times present) ──
        arrival_times = artifact.decision.get("arrival_times", {})
        for o_id, arr_t in arrival_times.items():
            if o_id in orders:
                tw_e = orders[o_id].get("tw_early", 0)
                tw_l = orders[o_id].get("tw_late", float("inf"))
                if arr_t < tw_e or arr_t > tw_l:
                    violations.append(f"Order {o_id} arrival time {arr_t} out of window [{tw_e}, {tw_l}]")
                    constraint_results.append({
                        "type": "TIME_WINDOW",
                        "entity": o_id,
                        "arrival_time": arr_t,
                        "window": [tw_e, tw_l],
                        "status": "VIOLATED"
                    })
                else:
                    constraint_results.append({
                        "type": "TIME_WINDOW",
                        "entity": o_id,
                        "arrival_time": arr_t,
                        "window": [tw_e, tw_l],
                        "status": "SATISFIED"
                    })

        # ── Rule 3: Oracle Comparison Interface ──
        oracle_comp = None
        obj_gap = None
        if gold and "oracle_solution" in gold:
            oracle_sol = gold["oracle_solution"]
            oracle_obj = float(oracle_sol.get("objective", 0.0))
            candidate_cost = float(artifact.decision.get("total_additional_cost", artifact.decision.get("cost", 0.0)))
            
            if oracle_obj > 0:
                obj_gap = round(abs(candidate_cost - oracle_obj) / oracle_obj, 4)
            else:
                obj_gap = 0.0
                
            oracle_comp = {
                "oracle_status": oracle_sol.get("status", "OPTIMAL"),
                "oracle_objective": oracle_obj,
                "candidate_cost": candidate_cost,
                "objective_gap": obj_gap,
                "oracle_feasible": oracle_sol.get("feasible", True)
            }
            
        overall_pass = (len(violations) == 0)
        feas_status = "FEASIBLE" if overall_pass else "INFEASIBLE"
        
        return FeasibilityEvaluationResult(
            overall_pass=overall_pass,
            score=1.0 if overall_pass else 0.0,
            feasibility_status=feas_status,
            constraint_results=constraint_results,
            objective_gap=obj_gap,
            oracle_comparison=oracle_comp,
            violations=violations,
            findings=[{"violation": v} for v in violations],
            evidence={
                "decision_routes": decision_routes,
                "violations_count": len(violations),
                "oracle_comparison": oracle_comp
            }
        )
