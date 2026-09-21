# -*- coding: utf-8 -*-
"""Layer Escalation 状态机 (v0.2 §6.2): L3 React → L2 Reconcile → L1 Plan/授权.

> P0-1 的正面落点: L3 不产出违约解、不自产业务事件 — 它只报数学事实
> (INFEASIBLE / violated_constraints), 由本状态机沿 SourceMap 追溯到语义
> 规则, 给出升级动作。业务事件 (MakeupDebt/SpacingDebt/ServiceException)
> 由 Orchestrator 解释, 不由 solver 发明。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from visit_math_api import SolveResult, ValidationReport, VisitPlanningInstance


class Level(str, Enum):
    NONE = "NONE"                 # 无需升级 — 解可行且通过验解
    L3_REACT = "L3_REACT"         # L3 授权包络内可修复 (未实现: 预留)
    L2_RECONCILE = "L2_RECONCILE" # L2 重编译可恢复 (滚动周期内吸收)
    L1_AUTHORIZE = "L1_AUTHORIZE" # 需要业务授权 (改走廊/合同/例外)


@dataclass(frozen=True)
class Escalation:
    """一次升级裁决: 级别 + 数学事实 + 语义追溯 + 建议动作."""

    level: Level
    violated_rule_ids: tuple          # 语义规则 ID (经 SourceMap 追溯)
    detail: tuple                     # 人话明细 (constraint_id: detail)
    action: str                       # 建议动作 (给 Orchestrator/人)
    episode_note: str = ""


# 硬约束类 → L2 可否滚动恢复的判定表 (v0.2 §2.2)
_RECONCILABLE = {"C1_OBLIGATION", "C2_CORRIDOR_MIN", "C2_CORRIDOR_MAX"}
_AUTHORIZE_ONLY = {"C3_ELIGIBILITY", "C4_FIXED_VISIT"}  # 触及合同语义, 必须 L1 授权


def escalate(
    instance: VisitPlanningInstance,
    result: SolveResult,
    report: Optional[ValidationReport] = None,
) -> Escalation:
    """根据求解结果 + 验解报告裁决升级级别 (纯函数).

    规则:
    - status INFEASIBLE 或验解有违例 → 至少 L2;
    - 违例全部可滚动吸收 (义务/走廊) → L2_RECONCILE;
    - 任一违例触及合同语义 (合法日期/核心保全) → L1_AUTHORIZE
      (solver 无权改合同语义 — v0.2 中心命题);
    - 结构违例 (C0_*) → 视为 solver bug, 同样升 L2 并在 detail 标注.
    """
    if result.status in ("OPTIMAL", "FEASIBLE") and (report is None or report.ok):
        return Escalation(Level.NONE, (), (), "直接采纳")

    violations = tuple(report.violations) if report is not None else ()
    if not violations:
        # 求解器自报 INFEASIBLE 但无验解明细 — 用实例参数生成走廊/义务事实
        return Escalation(
            Level.L2_RECONCILE, (), (f"solver: {result.termination_reason or result.status}",),
            "L2 SP Recompile: 放宽列生成预算或扩池后重解",
        )

    ids = {v.constraint_id for v in violations}
    rules = tuple(dict.fromkeys(v.semantic_rule_id for v in violations))
    detail = tuple(f"{v.constraint_id}: {v.detail}" for v in violations)

    if ids & _AUTHORIZE_ONLY:
        return Escalation(
            Level.L1_AUTHORIZE, rules, detail,
            "需业务授权: 修改合同语义/核心保护/例外授权后重新编译 "
            "(ExceptionGrant → SemanticCompiler → 新 MathIR → L3 re-solve)",
        )
    if ids & _RECONCILABLE or any(i.startswith("C0_") for i in ids):
        return Escalation(
            Level.L2_RECONCILE, rules, detail,
            "L2 SP Recompile: 滚动周期内恢复义务守恒 (MakeupDebt 吸收)",
        )
    return Escalation(
        Level.L2_RECONCILE, rules, detail, "L2 重编译 (未分类违例, 保守升级)",
    )


__all__ = ["Level", "Escalation", "escalate"]
