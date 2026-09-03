"""增量重算与锁定管理 (Phase 2 深化 + Phase 3 rolling_horizon 前置)。

- LockManager: 管理锁定客户/日期/拜访
- ChangeBudget: 稳定性预算
- incremental_replan: 受锁约束的局部求解入口
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence

from .planning import PlanVersion, PlannedVisit


@dataclass(frozen=True)
class LockedVisit:
    """不可移动的已锁定拜访记录。"""
    customer_id: str
    planned_date: date
    reason: str = "MANAGER_LOCKED"


class LockManager:
    """锁定管理 — 跟踪当前计划版本中被锁定的客户/日期组合。"""

    def __init__(self):
        self._locks: dict[tuple[str, date], LockedVisit] = {}

    def lock(self, customer_id: str, planned_date: date, reason: str = "MANAGER_LOCKED") -> None:
        key = (customer_id, planned_date)
        self._locks[key] = LockedVisit(customer_id, planned_date, reason)

    def unlock(self, customer_id: str, planned_date: date) -> None:
        self._locks.pop((customer_id, planned_date), None)

    def is_locked(self, customer_id: str, planned_date: date) -> bool:
        return (customer_id, planned_date) in self._locks

    @property
    def locked_visits(self) -> list[LockedVisit]:
        return list(self._locks.values())

    def __len__(self):
        return len(self._locks)


@dataclass(frozen=True)
class ChangeBudget:
    """稳定性预算 — 限制每轮重算的变化幅度。

    Fields:
        max_customers_changed: 每轮最多改变的客户数
        max_visit_changes: 每轮最多改变的拜访条数
        near_execution_penalty_days: 距执行日 <= N 天的变更受惩罚
        penalty_coefficient: 变更惩罚系数 (分钟/次)
    """
    max_customers_changed: int = 8
    max_visit_changes: int = 15
    near_execution_penalty_days: int = 3
    penalty_coefficient: float = 5.0

    def is_within_budget(self, old_plan: Sequence[PlannedVisit], new_plan: Sequence[PlannedVisit]) -> bool:
        """对比新旧计划，检查变更是否在预算内。"""
        old_map = {(v.customer_id, v.planned_date): v for v in old_plan}
        new_map = {(v.customer_id, v.planned_date): v for v in new_plan}

        changed_customers = set()
        changed_visits = 0

        all_keys = set(old_map.keys()) | set(new_map.keys())
        for key in all_keys:
            if key not in old_map or key not in new_map:
                changed_visits += 1
                changed_customers.add(key[0])
            elif old_map[key].sequence != new_map[key].sequence:
                changed_visits += 1

        if changed_customers and changed_customers.__len__() > self.max_customers_changed:
            return False
        if changed_visits > self.max_visit_changes:
            return False
        return True


def incremental_replan(
    existing_plan: PlanVersion,
    existing_visits: list[PlannedVisit],
    locks: LockManager | None = None,
    change_budget: ChangeBudget | None = None,
) -> "IncrementalReplanResult":
    """基于已有计划和锁定列表生成增量的新版本计划框架。

    当前实现: 标记被锁定的 PlannedVisit 并保留; 非锁定的由上游 SolverAdapter 重算。
    """
    if existing_plan.status == "published":
        new_version = existing_plan.version + 1
    else:
        raise ValueError(
            f"仅 published 计划可以增量重算, 当前 status={existing_plan.status!r}"
        )
    if locks is None:
        locks = LockManager()

    locked_visits_list = []
    unlocked_visits_list = []
    for v in existing_visits:
        if locks.is_locked(v.customer_id, v.planned_date) or v.is_locked:
            locked_visits_list.append(v)
        else:
            unlocked_visits_list.append(v)

    return IncrementalReplanResult(
        parent_plan=existing_plan,
        locked_count=len(locked_visits_list),
        unlocked_for_solver=unlocked_visits_list,
        new_version=new_version,
        plan_id=f"{existing_plan.plan_id}@v{new_version}",
    )


@dataclass(frozen=True)
class IncrementalReplanResult:
    """增量重算的中间结果 — locked 保留 + 待求解列表 + 新版本标识。"""
    parent_plan: PlanVersion
    locked_count: int
    unlocked_for_solver: list[PlannedVisit]
    new_version: int
    plan_id: str