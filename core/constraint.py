# -*- coding: utf-8 -*-
"""Constraint definitions. 可配置, 换场景不改算法.
- FrequencyConstraint: 每店月总次数 = 计划频次
- WeekdayLock: 每店锁定星期几 (可选)
- CapacityLimit: 每日店数上限 (可选)
- ServiceTime: 每日总服务时长约束 (可选, 需服务时长数据)
"""
from dataclasses import dataclass
from typing import Dict, Callable


@dataclass
class Constraints:
    freq: Dict[str, int]                       # 每店 {编码: 次数}
    weekday_lock: Dict[str, set] | None = None  # 每店 {编码: {0-4}} 允许的星期
    capacity: Dict[str, int] | None = None      # 每日 {日期: 最大店数}
    service_duration: Dict[str, float] | None = None  # 每店 {编码: 分钟}
    max_daily_minutes: float | None = None      # 每日最长工作分钟

    def check_freq_ok(self, days: dict, codes: list) -> bool:
        """每店总次数 == 计划频次."""
        cnt = {c: 0 for c in codes}
        for seq in days.values():
            for si in seq:
                cnt[codes[si]] += 1
        return all(cnt.get(c, 0) == self.freq.get(c, 0) for c in self.freq)

    def check_weekday_ok(self, days: dict, codes: list, date_weekday: Callable) -> bool:
        """店只在允许的星期几出现."""
        if not self.weekday_lock:
            return True
        for dd, seq in days.items():
            wd = date_weekday(dd)
            for si in seq:
                c = codes[si]
                allowed = self.weekday_lock.get(c)
                if allowed and wd not in allowed:
                    return False
        return True

    def check_capacity_ok(self, days: dict, max_daily: int | None = None, min_daily: int | None = None) -> bool:
        """验证单日门店数落在 [min_daily, max_daily] 业务走廊内."""
        for seq in days.values():
            n = len(seq)
            if max_daily is not None and max_daily > 0 and n > max_daily:
                return False
            if min_daily is not None and min_daily > 0 and n < min_daily:
                return False
        if not self.capacity:
            return True
        for dd, seq in days.items():
            cap = self.capacity.get(str(dd))
            if cap is not None and len(seq) > cap:
                return False
        return True

    def all_ok(self, days: dict, codes: list, date_weekday: Callable) -> dict:
        return {
            "freq": self.check_freq_ok(days, codes),
            "weekday": self.check_weekday_ok(days, codes, date_weekday),
            "capacity": self.check_capacity_ok(days),
        }
