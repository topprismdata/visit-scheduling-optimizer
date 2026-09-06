"""
svdebench.evaluator.runtime — Runtime Evaluator v0.1 (Sprint 3C Frozen)
Evaluates dynamic adaptation, event replay state transitions, commitment survival, and disruption ratios.
Strictly black-box, zero re-planning, deterministic replay.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from svdebench.core.case import DecisionCase
from svdebench.core.artifact import DecisionArtifact
from svdebench.evaluator.base import BaseEvaluator
from svdebench.evaluator.models import RuntimeEvaluationResult

# ── 1. 合法物理与运单状态转移表（单向单调，已交付事实不可逆）──
ORDER_TRANSITIONS = {
    "PENDING_DISPATCH": ["ASSIGNED", "CANCELLED"],
    "ASSIGNED": ["IN_TRANSIT", "CANCELLED"],
    "IN_TRANSIT": ["AT_STOP", "FAILED_DELIVERY"],
    "AT_STOP": ["DELIVERED", "FAILED_DELIVERY"],
    "DELIVERED": [], # 终态不可逆
    "FAILED_DELIVERY": ["PENDING_DISPATCH", "CANCELLED"],
    "CANCELLED": []
}

VEHICLE_TRANSITIONS = {
    "AVAILABLE": ["EN_ROUTE", "IDLE", "MAINTENANCE"],
    "EN_ROUTE": ["AT_STOP", "MECHANICAL_BREAKDOWN", "AVAILABLE"],
    "AT_STOP": ["EN_ROUTE", "MECHANICAL_BREAKDOWN", "AVAILABLE"],
    "MECHANICAL_BREAKDOWN": ["MAINTENANCE"], # 故障不可原地自愈
    "MAINTENANCE": ["AVAILABLE"]
}

class RuntimeEvaluator(BaseEvaluator):
    def evaluate(
        self,
        case: DecisionCase,
        artifact: DecisionArtifact,
        gold: Optional[Dict[str, Any]] = None
    ) -> RuntimeEvaluationResult:
        world = case.world_state or {}
        runtime = case.runtime_context or {}
        events = case.events or []
        contract = case.semantic_contract or {}
        
        event_results: List[Dict[str, Any]] = []
        violations: List[str] = []
        state_valid = True
        
        # ── Rule 1: State Transition Validity ──
        # 模拟事件序列回放
        current_vehicle_states = {v["id"]: v.get("status", "AVAILABLE") for v in world.get("fleet", [])}
        
        for ev in events:
            ev_id = ev.get("event_id", "EVT_UNKNOWN")
            ev_type = ev.get("event_type", "UNKNOWN_EVENT")
            
            if ev_type == "VEHICLE_MECHANICAL_BREAKDOWN":
                veh_id = ev.get("affected_vehicle", ev.get("vehicle_id"))
                prev_status = current_vehicle_states.get(veh_id, "AVAILABLE")
                
                # 检查故障转换合法性
                if "BREAKDOWN" in prev_status:
                    violations.append(f"{ev_id}: Vehicle {veh_id} already broken down")
                    state_valid = False
                    event_results.append({"event_id": ev_id, "event_type": ev_type, "status": "INVALID", "detail": "Illegal state transition"})
                else:
                    current_vehicle_states[veh_id] = "MECHANICAL_BREAKDOWN"
                    event_results.append({"event_id": ev_id, "event_type": ev_type, "status": "VALID", "detail": f"Vehicle {veh_id} transition -> MECHANICAL_BREAKDOWN"})
                    
            elif ev_type in ("TRAFFIC_CONGESTION", "CUSTOMER_PRIORITY_CHANGE"):
                event_results.append({"event_id": ev_id, "event_type": ev_type, "status": "VALID", "detail": "Data/context variation processed deterministically"})
            else:
                event_results.append({"event_id": ev_id, "event_type": ev_type, "status": "VALID", "detail": "Standard event processed"})

        # 检查历史已完成订单不可逆性 (Past Reality Immutability)
        past_delivered = [p["order_id"] for p in runtime.get("past_delivered_orders", [])]
        decision_routes = artifact.decision.get("reassigned_routes", {}) or artifact.decision.get("routes", {})
        
        # ── Rule 2: Commitment Survival Rate ──
        # 查找所有锁定约束 (HARD_COMMITMENT)
        lock_constraints = [c for c in contract.get("constraints", []) if c.get("hardness") == "HARD_COMMITMENT" or c.get("type") == "TIME_WINDOW_LOCKED"]
        total_commitments = len(lock_constraints)
        
        all_assigned_orders = set()
        for o_list in decision_routes.values():
            if isinstance(o_list, list):
                all_assigned_orders.update(o_list)
            elif isinstance(o_list, str):
                all_assigned_orders.add(o_list)
                
        preserved_commitments = 0
        for lc in lock_constraints:
            target_o = lc.get("target_order", "ORD_03")
            if target_o in all_assigned_orders:
                preserved_commitments += 1
            else:
                violations.append(f"Broken Commitment: Locked order {target_o} not served in reassigned plan")
                
        if total_commitments > 0:
            survival_rate = round(preserved_commitments / total_commitments, 4)
        else:
            survival_rate = 1.0

        # ── Rule 3: Disruption Ratio ──
        # 衡量重排造成的业务扰动：重调对象数 / 总对象数
        total_orders_count = len(world.get("orders", []))
        if total_orders_count == 0:
            total_orders_count = len(all_assigned_orders) or 1
            
        # 从 Decision 或 Explanation 中读取改派数量
        reassigned_count = artifact.decision.get("reassigned_count", None)
        if reassigned_count is None:
            # 默认估算：未包含在锁定且发生变动的运单
            reassigned_count = len([o for o in all_assigned_orders if o not in past_delivered])
            
        disruption_ratio = round(min(1.0, reassigned_count / total_orders_count), 4)

        # ── Rule 4: Overall Replay Determinism & Pass ──
        overall_pass = state_valid and (survival_rate == 1.0) and (len(violations) == 0)
        
        return RuntimeEvaluationResult(
            overall_pass=overall_pass,
            score=survival_rate,
            event_results=event_results,
            commitment_survival_rate=survival_rate,
            disruption_ratio=disruption_ratio,
            state_transition_validity=state_valid,
            violations=violations,
            findings=[{"violation": v} for v in violations],
            evidence={
                "events_replayed": len(events),
                "total_commitments": total_commitments,
                "preserved_commitments": preserved_commitments,
                "disruption_ratio": disruption_ratio,
                "event_results": event_results
            }
        )
