"""
domain.rules.frequency_rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Business rule checking that every customer is visited exactly their required frequency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from domain.entities import Customer


@dataclass(frozen=True)
class FrequencyAuditResult:
    """客户频次合规审计结果"""

    customer_id: int
    customer_code: str
    customer_name: str
    required_frequency: int
    actual_visit_count: int
    is_compliant: bool
    assigned_days: list[int]
    violation_message: str | None = None


class FrequencyRule:
    """
    拜访频次合规规则 (Visit Frequency Rule)
    
    硬约束：在规划周期内，客户 c 的总拜访次数必须严格等于 required_frequency。
    """

    @staticmethod
    def audit(
        customers: Sequence[Customer],
        daily_customer_ids: Sequence[Sequence[int]],
    ) -> tuple[bool, list[FrequencyAuditResult]]:
        """
        对排班结果进行全量客户频次合规审计

        Args:
            customers: 客户全集
            daily_customer_ids: 每日安排的客户 ID 列表 (长度为 T)

        Returns:
            (all_passed, audit_results)
        """
        assigned_map: dict[int, list[int]] = {c.id: [] for c in customers}
        for d, day_list in enumerate(daily_customer_ids):
            for cid in day_list:
                if cid in assigned_map:
                    assigned_map[cid].append(d)

        results: list[FrequencyAuditResult] = []
        all_passed = True

        for c in customers:
            days = assigned_map.get(c.id, [])
            actual_count = len(days)
            passed = actual_count == c.frequency

            if not passed:
                all_passed = False
                msg = f"频次违规：要求 {c.frequency} 次/周期，实际安排 {actual_count} 次 (安排在第 {days} 天)"
            else:
                msg = None

            results.append(
                FrequencyAuditResult(
                    customer_id=c.id,
                    customer_code=c.code,
                    customer_name=c.name,
                    required_frequency=c.frequency,
                    actual_visit_count=actual_count,
                    is_compliant=passed,
                    assigned_days=days,
                    violation_message=msg,
                )
            )

        return all_passed, results
