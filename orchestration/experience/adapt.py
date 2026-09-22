# -*- coding: utf-8 -*-
"""动态适配 (v0.4): 月中偏差出现时, 剩余周计划带着欠账重排.

老板命题: "第一周一旦偏差, 后面都会乱" → 框架不应只回顾, 应**动态适配**:
    触发(周界/欠账阈值) → Scope(REP_WEEK/REP_MONTH) → 带欠账重排剩余日
    → diff + 系统适配事件(进月循环学习) → 下月规划

v1 算法 = 确定性重基线 (可解释优先, 不上优化器):
    对每个星期几 wd (σ 锁: 只允许同星期几的剩余日):
        owed = 该 wd 上"仍有欠账/剩余义务"的店, 欠账店优先(最久欠的先排)
        按走廊 k_max 逐日填入剩余日
    排不下的欠账 → unabsorbed (升级 REP_MONTH 或人工)

为什么 v1 不用优化器: 适配的第一要求是**可解释+稳定**(业代要能看懂
"为什么我的周三多了两家"), 里程优化是第二位的 (What-if 层再做)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

import pandas as pd

SCOPE_WEEK = "REP_WEEK"
SCOPE_MONTH = "REP_MONTH"


@dataclass(frozen=True)
class AdaptResult:
    line_id: str
    as_of: str
    scope: str
    moved: tuple                 # (store, old_day, new_day)
    backlog_at_trigger: int
    backlog_recovered: int
    unabsorbed: tuple            # 排不下的欠账店
    adapted_days: Mapping        # day -> [store,...]  (剩余日新排法)
    validation_ok: Optional[bool] = None

    @property
    def recovery_rate(self) -> float:
        return self.backlog_recovered / self.backlog_at_trigger if self.backlog_at_trigger else 1.0


def adapt_plan(line_id: str, plan: pd.DataFrame, act: pd.DataFrame,
               as_of, corridor: tuple = (0, 12),
               scope: str = SCOPE_MONTH, svc_wd: Optional[Mapping] = None) -> AdaptResult:
    """plan: [customer_code, plan_day, 服务日?]; act: [customer_code, call_date].

    svc_wd: {customer_code: 服务日(1-5)}; 缺省用 plan 的 服务日 列。
    scope=REP_WEEK 时只重排 as_of 所在周的剩余日 + 欠账; REP_MONTH 重排全部剩余日。
    """
    as_of = pd.Timestamp(as_of).normalize()
    plan = plan.copy()
    plan["d"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    act = act.copy()
    act["d"] = pd.to_datetime(act["call_date"]).dt.normalize()
    wd_of = svc_wd or plan.drop_duplicates("customer_code").set_index("customer_code")["服务日"].to_dict()

    executed = set(act[act["d"] <= as_of]["customer_code"])
    planned_upto = plan[plan["d"] <= as_of]
    backlog = sorted(set(planned_upto["customer_code"]) - executed)
    future = plan[plan["d"] > as_of]

    k_min, k_max = corridor
    # 最小扰动: 未来安排原样保留, 只把欠账店插进同星期几的剩余日空位
    adapted = {}
    for d, g in future.groupby("d"):
        adapted[str(d.date())] = list(g["customer_code"])
    load = {d: len(v) for d, v in adapted.items()}
    if scope == SCOPE_WEEK:
        ok_days = {d for d in adapted
                   if as_of <= pd.Timestamp(d) <= as_of + pd.Timedelta(days=6)}
    else:
        ok_days = set(adapted)
    bl = set(backlog)
    buckets = {}
    for c in sorted(bl):
        wd = int(wd_of.get(c, 0)) - 1
        buckets.setdefault(wd, []).append(c)
    moved, unabsorbed = [], []
    for wd in sorted(buckets):
        slot_days = sorted(d for d in ok_days if pd.Timestamp(d).weekday() == wd)
        for c in buckets[wd]:
            placed = False
            for d in slot_days:
                if load[d] < k_max:
                    adapted[d].append(c)
                    load[d] += 1
                    moved.append((c, None, d))
                    placed = True
                    break
            if not placed:
                unabsorbed.append(c)
    rec = len(bl) - len(unabsorbed)
    return AdaptResult(line_id, str(as_of.date()), scope, tuple(moved),
                       len(backlog), rec, tuple(unabsorbed), adapted)
