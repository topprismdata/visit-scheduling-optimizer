"""DynamicPlanningPolicy — Phase 2 扩展：价值评分 + 动态权重 + 稳定性预算。

设计依据: docs/phase2_design.md §一 (动态价值模型 / 动态优先级 / 情景比较)。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping

from .policy import PlanningPolicy


@dataclass(frozen=True)
class DynamicPlanningPolicy:
    """Phase 2 扩展策略 — 在 PlanningPolicy 基础上增加价值与稳定性维度。

    字段分三层:
    - 基础约束: 继承 PlanningPolicy 的硬约束（频次/间隔/日容量/工时）
    - 价值层: value_scores + priority_weights，驱动加权求解
    - 稳定性层: stability_budget + change_penalty + freeze 规则，控制变更幅度
    """
    base: PlanningPolicy
    value_scores: Mapping[int, float]         # customer_idx → [0,1]
    value_confidence: Mapping[int, float]     # customer_idx → [0,1]
    priority_weights: Mapping[str, float] = field(default_factory=lambda: {
        "value_coverage": 1.0,
        "travel_workload": 1.0,
        "plan_stability": 0.5,
        "workload_equity": 0.5,
    })
    stability_budget_max_customers_changed: int = 8
    change_penalty_coefficient: float = 5.0   # 分钟/次变更惩罚
    freeze_committed_visits: bool = True
    opportunity_threshold: float = 0.0        # 高于此值视为"高机会客户"

    def __post_init__(self):
        if not self.value_scores:
            raise ValueError("value_scores 不能为空")
        for c, s in self.value_scores.items():
            if not (0.0 <= s <= 1.0):
                raise ValueError(f"value_scores[{c}] 必须在 [0,1], 实际 {s}")
        if not (0.0 <= self.opportunity_threshold <= 1.0):
            raise ValueError(f"opportunity_threshold 必须在 [0,1], 实际 {self.opportunity_threshold}")
        if any(w < 0.0 for w in self.priority_weights.values()):
            raise ValueError("priority_weights 权重必须 >= 0")

    # ------------------------------------------------------------------
    def effective_value_weight(self) -> float:
        """加权求解器的 value_weight = value_coverage 权重 × 平均值 confidence。"""
        if not self.value_confidence:
            return 0.0
        avg_conf = sum(self.value_confidence.values()) / len(self.value_confidence)
        return self.priority_weights["value_coverage"] * avg_conf

    def high_opportunity_customers(self) -> set[int]:
        """返回超过 opportunity_threshold 的客户 id 集合。"""
        return {c for c, s in self.value_scores.items()
                if s >= self.opportunity_threshold}

    def summary(self) -> dict:
        return {
            **self.base.summary(),
            "n_scored_customers": len(self.value_scores),
            "avg_value_score": (
                sum(self.value_scores.values()) / len(self.value_scores)
                if self.value_scores else 0.0
            ),
            "priority_weights": dict(self.priority_weights),
            "stability_budget": self.stability_budget_max_customers_changed,
            "change_penalty": self.change_penalty_coefficient,
            "opportunity_threshold": self.opportunity_threshold,
        }
