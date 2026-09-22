# -*- coding: utf-8 -*-
"""偏差级联回溯 (v0.4 §6 月循环): 每个销售从 W1D1 起的执行漂移轨迹.

老板命题: "第一周一旦偏差, 后面都会乱" — 本模块把它变成可算的:
  backlog(d)   = 截至 d 累计"计划了但没执行"的店数 (欠访存量)
  catchup(d)   = d 日执行中属于"补前几天欠账"的店数 (级联是否被消化)
  never(d)     = 截至 d 的欠访中, 到月末仍未执行的比例 (级联是否固化)
  first_dev    = 首个同日执行率 <0.5 或 backlog 跳升 ≥3 的日期

能回答: 偏差何时开始 / 是否被补 / 是否级联固化 / 级联与月末覆盖的关系。
不能回答: 确认的"为什么"(需 OverrideEvent 归因 / 回访); 本模块只产出
候选归因 (模板冲突 / 超载 / 停工 / 片区错配)。

数据口径: 只用 日期×店集合; 打卡时间/GPS 不作证据。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import pandas as pd

DEV_SAMEDAY = 0.5      # 同日执行率低于此 = 偏差日
BACKLOG_JUMP = 3       # backlog 单日跳升 ≥ 此值 = 偏差日


@dataclass(frozen=True)
class CascadePoint:
    d: str
    wd: int
    planned_n: int
    actual_n: int
    same: int
    new_miss: int
    catchup: int
    extra: int
    backlog_end: int          # 当日收盘欠访存量
    dev: bool                 # 是否偏差日


@dataclass(frozen=True)
class CascadeCurve:
    line_id: str
    points: tuple
    w1_backlog: int           # W1 收盘欠访
    w1_planned: int
    never_share: float        # W1 欠访中月末仍未执行比例 (级联固化度)
    first_dev: Optional[str]
    final_coverage: float
    final_same: float

    @property
    def cascade_risk(self) -> str:
        if self.w1_planned == 0:
            return "no_w1"
        share = self.w1_backlog / self.w1_planned
        if share >= 0.3 and self.never_share >= 0.5:
            return "cascade_solidified"     # W1 欠且没补 → 级联固化
        if share >= 0.3:
            return "cascade_recovered"      # W1 欠但补回来了
        return "stable"


def cascade_curve(line_id: str, plan: pd.DataFrame, act: pd.DataFrame) -> CascadeCurve:
    """plan: [customer_code, plan_day]; act: [customer_code, call_date] (单线)."""
    plan = plan.copy()
    plan["d"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    act = act.copy()
    act["d"] = pd.to_datetime(act["call_date"]).dt.normalize()
    psets = {d: set(g["customer_code"]) for d, g in plan.groupby("d")}
    asets = {d: set(g["customer_code"]) for d, g in act.groupby("d")}
    all_days = sorted(set(psets) | set(asets))
    exec_sf, plan_sf = set(), set()
    pts, prev_backlog = [], 0
    first_dev = None
    for d in all_days:
        P, A = psets.get(d, set()), asets.get(d, set())
        plan_sf |= P
        catchup = len(A & (plan_sf - P - exec_sf))       # 补前几天欠账
        extra = len(A - plan_sf)
        same = len(A & P)
        new_miss = len(P - A - exec_sf)
        exec_sf |= A
        backlog = len(plan_sf - exec_sf)
        dev = (len(P) > 0 and same / len(P) < DEV_SAMEDAY) or (backlog - prev_backlog >= BACKLOG_JUMP)
        if dev and first_dev is None:
            first_dev = str(d.date())
        pts.append(CascadePoint(str(d.date()), int(d.dayofweek), len(P), len(A), same,
                                new_miss, catchup, extra, backlog, dev))
        prev_backlog = backlog
    # W1 = 月内第 1 周 (day 1-7)
    w1_pts = [p for p in pts if int(p.d[8:10]) <= 7]
    w1_backlog = w1_pts[-1].backlog_end if w1_pts else 0
    w1_planned = sum(p.planned_n for p in w1_pts)
    w1_missed = set()
    es = set()
    for d in all_days:
        if int(str(d.date())[8:10]) <= 7:
            w1_missed |= (psets.get(d, set()) - asets.get(d, set()))
        es |= asets.get(d, set())
    never = len(w1_missed - es) / len(w1_missed) if w1_missed else 0.0
    cov = len(es & set().union(*psets.values())) / max(len(set().union(*psets.values())), 1)
    same_tot = sum(p.same for p in pts)
    same_all = sum(p.planned_n for p in pts)
    return CascadeCurve(line_id, tuple(pts), w1_backlog, w1_planned, round(never, 3),
                        first_dev, round(cov, 3), round(same_tot / max(same_all, 1), 3))


def cascade_table(curves: list) -> pd.DataFrame:
    rows = [{"line": c.line_id, "w1_planned": c.w1_planned, "w1_backlog": c.w1_backlog,
             "never_share": c.never_share, "first_dev": c.first_dev,
             "final_coverage": c.final_coverage, "final_same": c.final_same,
             "risk": c.cascade_risk} for c in curves]
    return pd.DataFrame(rows)
