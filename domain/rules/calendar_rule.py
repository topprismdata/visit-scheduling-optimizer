"""
domain.rules.calendar_rule
~~~~~~~~~~~~~~~~~~~~~~~~~~
Business rule checking calendar weekday availability and minimum active day requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from domain.entities import Customer


@dataclass(frozen=True)
class WeekdayAuditResult:
    """客户星期可用性合规审计结果"""

    customer_id: int
    customer_code: str
    allowed_weekdays: tuple[int, ...]
    violated_days: list[tuple[int, int]]  # [(day_index, weekday)]
    is_compliant: bool
    violation_message: str | None = None


class CalendarRule:
    """
    工作日历与星期可用性规则 (Calendar Availability Rule)

    1. 将连续工作日索引 d (0..T-1) 映射到 (周次, 星期几)
       week = d // 5 + 1
       weekday = d % 5  (0=周一 .. 4=周五)
    2. 校验客户是否仅在允许的星期接受拜访 (allowed_weekdays)
    3. 校验出勤天数是否满足最小出勤天数约束 (min_active_days)
    """

    @staticmethod
    def day_to_weekday(day_index: int) -> int:
        """工作日索引 -> 星期 (0=周一 .. 4=周五)"""
        return day_index % 5

    @staticmethod
    def day_to_week_number(day_index: int) -> int:
        """工作日索引 -> 周序号 (1..4)"""
        return (day_index // 5) + 1

    @classmethod
    def audit_customer_weekdays(
        cls,
        customers: Sequence[Customer],
        daily_customer_ids: Sequence[Sequence[int]],
    ) -> tuple[bool, list[WeekdayAuditResult]]:
        """
        审计客户是否在被允许的星期拜访
        """
        assigned_map: dict[int, list[int]] = {c.id: [] for c in customers}
        for d, day_list in enumerate(daily_customer_ids):
            for cid in day_list:
                if cid in assigned_map:
                    assigned_map[cid].append(d)

        results: list[WeekdayAuditResult] = []
        all_passed = True

        for c in customers:
            violations = []
            for d in assigned_map.get(c.id, []):
                wday = cls.day_to_weekday(d)
                if not c.is_weekday_allowed(wday):
                    violations.append((d, wday))

            passed = len(violations) == 0
            if not passed:
                all_passed = False
                w_names = ["周一", "周二", "周三", "周四", "周五"]
                v_desc = [f"第{d}天({w_names[w]})" for d, w in violations]
                msg = f"星期违例：允许星期为 {c.allowed_weekdays}，但在 {v_desc} 进行了拜访"
            else:
                msg = None

            results.append(
                WeekdayAuditResult(
                    customer_id=c.id,
                    customer_code=c.code,
                    allowed_weekdays=c.allowed_weekdays,
                    violated_days=violations,
                    is_compliant=passed,
                    violation_message=msg,
                )
            )

        return all_passed, results

    @staticmethod
    def audit_active_days(
        daily_customer_ids: Sequence[Sequence[int]],
        min_active_days: int | None = None,
    ) -> tuple[bool, int, str | None]:
        """
        审计实际出勤天数是否满足最小要求

        Returns:
            (is_compliant, actual_active_days, violation_message)
        """
        active_days = sum(1 for day in daily_customer_ids if len(day) > 0)
        if min_active_days is None:
            return True, active_days, None

        passed = active_days >= min_active_days
        msg = (
            None
            if passed
            else f"出勤天数不足：要求至少 {min_active_days} 天出勤，实际仅出勤 {active_days} 天"
        )
        return passed, active_days, msg
