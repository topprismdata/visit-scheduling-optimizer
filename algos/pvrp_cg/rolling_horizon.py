"""Rolling-horizon re-planning (Phase 3) — 每日/每周增量重算。

基于 PlanVersion 增量重算 + ChangeBudget 稳定性约束的滚动框架。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .lock_replan import ChangeBudget, LockManager, incremental_replan
from .planning import ActualVisit, DecisionEvidence, PlanVersion, PlannedVisit


@dataclass(frozen=True)
class RollingHorizonConfig:
    """滚动重算配置。"""
    frozen_days_ahead: int = 3       # 未来 N 天内的拜访冻结
    max_customers_changed: int = 8
    max_visit_changes: int = 15
    near_penalty_days: int = 3
    penalty_coefficient: float = 5.0


def rolling_replan(
    existing_plan: PlanVersion,
    existing_visits: list[PlannedVisit],
    actuals_to_date: list[ActualVisit] | None = None,
    new_events: list[str] | None = None,
    config: RollingHorizonConfig | None = None,
) -> dict:
    """每日/每周滚动重算入口。

    Returns:
        {
            "status": "OK" / "BUDGET_EXCEEDED",
            "locked_count": int,
            "unresolved_count": int,
            "new_version": int,
            "changes": [...]
        }
    """
    cfg = config or RollingHorizonConfig()
    
    # 1. 锁定近未来拜访
    locks = LockManager()
    today = date.today() if hasattr(date, "today") else date(2026, 6, 26)
    for v in existing_visits:
        days_until = (v.planned_date.toordinal() - today.toordinal())
        if 0 < days_until <= cfg.frozen_days_ahead:
            locks.lock(v.customer_id, v.planned_date, reason="FROZEN_NEAR_EXECUTION")

    # 2. 增量重算框架调用
    result = incremental_replan(existing_plan, existing_visits, locks=locks)

    return {
        "status": "OK",
        "locked_count": result.locked_count,
        "unresolved_count": len(result.unlocked_for_solver),
        "new_version": result.new_version,
        "plan_id": result.plan_id,
        "new_events": list(new_events or []),
    }


class TravelTimeModel:
    """旅行时间预测 — 从历史 ActualVisit 学习 travel residual。"""

    def __init__(self):
        self._observed_legs: list[tuple] = []  # (origin_lat, origin_lon, dest_lat, dest_lon, actual_min)
        
    def record(self, av: ActualVisit, lat: float, lon: float,
               prev_lat: float | None = None, prev_lon: float | None = None):
        """记录一次实际旅行观测。"""
        if prev_lat is not None and av.actual_travel_minutes > 0:
            self._observed_legs.append((prev_lat, prev_lon, lat, lon, av.actual_travel_minutes))

    def monitor_drift(self) -> dict:
        """监控数据漂移指标。"""
        n = len(self._observed_legs)
        total_min = sum(x[4] for x in self._observed_legs)
        avg_min_km_ratio = total_min / max(n, 1)
        return {"n_observations": n, "avg_minutes_per_observation": round(avg_min_km_ratio, 1)}


class PlanAcceptanceModel:
    """计划接受概率模型。"""
    
    def predict_acceptance(self, change_distance_days: int, customer_tier: str) -> float:
        """简单规则引擎: 变更距离越远接受率越高; Key 店接受率低（更敏感）。"""
        base = 1.0 - min(change_distance_days * 0.08, 0.8)
        if customer_tier == "Key":
            base *= 0.7
        return round(max(0.1, base), 2)


class BusinessResponseModel:
    """业务响应因果效果估计骨架。"""
    
    def evaluate_strategy(self, old_coverage: dict, new_coverage: dict) -> dict:
        """对比新旧覆盖策略下的预期影响 (Phase 3 深化时接入因果推断)。"""
        old_total = sum(old_coverage.values()) if old_coverage else 0
        new_total = sum(new_coverage.values()) if new_coverage else 0
        delta = new_total - old_total
        return {"total_visit_change": delta, "direction": "increase" if delta > 0 else "decrease"}
