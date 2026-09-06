"""
domain.rules.gap_rule
~~~~~~~~~~~~~~~~~~~~~
Business rule enforcing minimum spacing (gap) between recurring visits to the same customer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from domain.entities import Customer


@dataclass(frozen=True)
class GapAuditResult:
    """客户两次拜访间隔审计结果"""

    customer_id: int
    customer_code: str
    customer_name: str
    frequency: int
    required_min_gap_days: int
    actual_visit_days: list[int]
    actual_gaps: list[int]
    is_compliant: bool
    violation_message: str | None = None


class IntervalGapRule:
    """
    重复拜访最小间隔规则 (Inter-Visit Gap Rule)

    对于频次 >= 2 的客户，任意两次拜访之间必须相隔至少 Δ_i 天。
    理论公式：Δ_i = ⌊horizon_days / (frequency + 1)⌋
    例如：在 20 天周期中，频次 2 的客户间隔至少 6 天；频次 4 的客户间隔至少 4 天。
    """

    @staticmethod
    def calculate_min_gap(frequency: int, horizon_days: int) -> int:
        """计算理论最小间隔天数"""
        if frequency <= 1:
            return 0
        return max(1, horizon_days // (frequency + 1))

    @classmethod
    def audit(
        cls,
        customers: Sequence[Customer],
        daily_customer_ids: Sequence[Sequence[int]],
        horizon_days: int = 20,
    ) -> tuple[bool, list[GapAuditResult]]:
        """
        对所有多次拜访客户进行间隔合规审计

        Returns:
            (all_passed, audit_results)
        """
        assigned_map: dict[int, list[int]] = {c.id: [] for c in customers}
        for d, day_list in enumerate(daily_customer_ids):
            for cid in day_list:
                if cid in assigned_map:
                    assigned_map[cid].append(d)

        results: list[GapAuditResult] = []
        all_passed = True

        for c in customers:
            if c.frequency <= 1:
                continue

            days = sorted(assigned_map.get(c.id, []))
            min_gap = cls.calculate_min_gap(c.frequency, horizon_days)
            gaps = [days[k + 1] - days[k] for k in range(len(days) - 1)]

            passed = True
            msg = None

            # 检查是否有任意相邻两次拜访间隔小于 min_gap
            for gap in gaps:
                if gap < min_gap:
                    passed = False
                    all_passed = False
                    msg = (
                        f"间隔违规：要求最小间隔 >= {min_gap} 天，"
                        f"实际拜访安排在第 {days} 天 (存在过短间隔 {gap} 天)"
                    )
                    break

            results.append(
                GapAuditResult(
                    customer_id=c.id,
                    customer_code=c.code,
                    customer_name=c.name,
                    frequency=c.frequency,
                    required_min_gap_days=min_gap,
                    actual_visit_days=days,
                    actual_gaps=gaps,
                    is_compliant=passed,
                    violation_message=msg,
                )
            )

        return all_passed, results
