"""
domain.rules.capacity_rule
~~~~~~~~~~~~~~~~~~~~~~~~~~
Business rule enforcing daily visit count limits and total working time capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from domain.entities import CostBreakdown


@dataclass(frozen=True)
class DayCapacityAuditResult:
    """单日容量与工时合规审计结果"""

    day_index: int
    visit_count: int
    max_visit_limit: int
    total_time_min: float
    max_time_limit_min: float
    count_compliant: bool
    time_compliant: bool
    is_compliant: bool
    violation_message: str | None = None


class DailyCapacityRule:
    """
    单日容量与工作时长合规规则 (Daily Capacity Rule)

    硬约束：
      1. 单日拜访客户数量 <= max_visits (默认 6 家)
      2. 单日总耗时 (在途+在店+停靠) <= max_time_min (默认 540 分钟 = 9小时)
    """

    @staticmethod
    def audit(
        daily_breakdowns: Sequence[CostBreakdown],
        max_visits_per_day: int = 6,
        max_time_min_per_day: float = 540.0,
    ) -> tuple[bool, list[DayCapacityAuditResult]]:
        """
        对排班的每日工时与容量进行白盒审计

        Returns:
            (all_passed, audit_results)
        """
        results: list[DayCapacityAuditResult] = []
        all_passed = True

        for d, bd in enumerate(daily_breakdowns):
            v_count = len(bd.route_sequence)
            t_min = bd.total_time_min

            c_passed = v_count <= max_visits_per_day
            # 允许 1e-4 的浮点容差
            t_passed = t_min <= max_time_min_per_day + 1e-4
            day_passed = c_passed and t_passed

            if not day_passed:
                all_passed = False
                reasons = []
                if not c_passed:
                    reasons.append(f"门店数超标: {v_count} > {max_visits_per_day}")
                if not t_passed:
                    reasons.append(f"工时超标: {t_min:.1f}min > {max_time_min_per_day}min")
                msg = f"第 {d} 天容量违规: " + "; ".join(reasons)
            else:
                msg = None

            results.append(
                DayCapacityAuditResult(
                    day_index=d,
                    visit_count=v_count,
                    max_visit_limit=max_visits_per_day,
                    total_time_min=t_min,
                    max_time_limit_min=max_time_min_per_day,
                    count_compliant=c_passed,
                    time_compliant=t_passed,
                    is_compliant=day_passed,
                    violation_message=msg,
                )
            )

        return all_passed, results
