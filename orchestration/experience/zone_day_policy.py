# -*- coding: utf-8 -*-
"""ZoneDayPolicy — 第一个生产级 Learned Preference (v0.3 §8).

定义: 每销售线在 H3 res7 网格上的 星期几→片区 分布, 从实际打卡学习。
证据 (2026-09-21 全国 547 线): 模板一致度 → 同日执行 r=0.82
(一致≥75% → 94%, <40% → 29%); 粒度校准: res7 HHI 0.65 (res8 0.15 太碎,
区县 0.86 是行政边界错觉)。

用途 (v0.3 §8):
  ① 计划出厂质检: alignment_score(plan) → predict_compliance()
  ② L3 软偏好: change_count 按模板距离加权 (接入点 = ObjectiveSpec 权重)
  ③ 诊断基线: 超载/停工分型
禁令: 不得作为硬约束下发 (升格需业务确认, 走 L1 通道)。

数据治理: 只消费 日期×店集合 + 客户主数据坐标 (打卡时间/GPS 不可信,
v0.3 §9)。
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone as _tz
from types import MappingProxyType
from typing import Mapping

import pandas as pd

LEARNED_SCHEMA = "zone_day_policy/v1"
H3_RES = 7
MIN_WD_SUPPORT = 3  # 星期几至少 3 次打卡才出 top_cell 判定


@dataclass(frozen=True)
class ZoneDayTemplate:
    """一条销售线的 星期几→片区 经验模板 (LEARNED 级, 非 BUSINESS_INVARIANT)."""

    line_id: str
    res: int
    support: int                       # 全周可用打卡总数
    prob: Mapping                      # {wd: {cell: P(cell|wd)}} Laplace 平滑
    top_cell: Mapping                  # {wd: cell} (support≥MIN_WD_SUPPORT)
    confidence: Mapping                # {wd: Wilson 下界 of top 份额}
    learned_at: str

    def p(self, wd: int, cell: str) -> float:
        return self.prob.get(wd, {}).get(cell, 0.0)


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    """Wilson score 下界 (95%): 小样本自动降权."""
    if n <= 0:
        return 0.0
    ph = k / n
    denom = 1 + z * z / n
    centre = ph + z * z / (2 * n)
    adj = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return max(0.0, (centre - adj) / denom)


def learn_zone_day_policy(
    actuals: pd.DataFrame,
    cell_map: Mapping[str, str],
    res: int = H3_RES,
) -> dict:
    """actuals: [salesperson_code, call_date(datetime), customer_code].

    cell_map: {customer_code: h3_cell} — 必须用客户主数据坐标 (非打卡 GPS)。
    返回 {line_id: ZoneDayTemplate}。
    """
    a = actuals.copy()
    a["cell"] = a["customer_code"].map(cell_map)
    a = a.dropna(subset=["cell"])
    a["wd"] = pd.to_datetime(a["call_date"]).dt.dayofweek
    out: dict[str, ZoneDayTemplate] = {}
    for lid, g in a.groupby("salesperson_code"):
        universe = sorted(set(g["cell"]))
        k = max(len(universe), 1)
        counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for wd, gg in g.groupby("wd"):
            for c, n in gg["cell"].value_counts().items():
                counts[wd][c] = int(n)
        prob: dict[int, dict[str, float]] = {}
        top_cell: dict[int, str] = {}
        conf: dict[int, float] = {}
        for wd in range(5):
            cw = dict(counts.get(wd, {}))
            n = sum(cw.values())
            if n == 0:
                continue
            prob[wd] = {c: (cw.get(c, 0) + 1) / (n + k) for c in universe}
            if n >= MIN_WD_SUPPORT:
                top = max(cw, key=cw.get)
                top_cell[wd] = top
                conf[wd] = round(wilson_lower(cw[top], n), 3)
        total = int(len(g))
        out[str(lid)] = ZoneDayTemplate(
            line_id=str(lid), res=res, support=total,
            prob=MappingProxyType({w: MappingProxyType(p) for w, p in prob.items()}),
            top_cell=MappingProxyType(top_cell),
            confidence=MappingProxyType(conf),
            learned_at=datetime.now(_tz.utc).isoformat(timespec="seconds"),
        )
    return out


def alignment_score(plan: pd.DataFrame, tpl: ZoneDayTemplate) -> dict:
    """计划 vs 模板的一致度. plan: [plan_day(datetime), customer_code, cell].

    likelihood = mean P(cell|wd)  (Laplace 平滑模板概率, 主指标)
    argmax     = 计划各星期几主导格 == 模板主导格 的占比
                 (与 2026-08 全国 r=0.82 研究同口径, 出厂质检器用这个)
    """
    p = plan.copy()
    if "cell" not in p.columns:
        raise ValueError("plan 需带 cell 列 (customer_code→h3 预映射)")
    p["wd"] = pd.to_datetime(p["plan_day"]).dt.dayofweek
    probs = [tpl.p(int(r.wd), r.cell)
             for r in p.itertuples() if int(r.wd) in tpl.prob]
    likelihood = sum(probs) / len(probs) if probs else 0.0
    return {"likelihood": round(likelihood, 4), "argmax": _argmax_align(p, tpl)}


def _argmax_align(plan_wd: pd.DataFrame, tpl: ZoneDayTemplate) -> float:
    hits = tot = 0
    for wd, gg in plan_wd.groupby("wd"):
        if wd not in tpl.top_cell or len(gg) < 3:
            continue
        # 计划该星期几的主导格 (需要 plan 带 cell 列)
        if "cell" not in gg.columns:
            return float("nan")
        top_plan = gg["cell"].value_counts().index[0]
        hits += int(top_plan == tpl.top_cell[wd])
        tot += 1
    return round(hits / tot, 4) if tot else float("nan")


# 2026-08 全国校准锚点 (547 线): argmax 一致 <40% → 同日执行 29%; ≥75% → 94%
_COMPLIANCE_ANCHORS = [(0.0, 0.29), (0.40, 0.29), (0.75, 0.94), (1.0, 0.94)]


def predict_compliance(alignment: float) -> float:
    """出厂质检: 模板一致度 → 预测同日执行率 (分段线性, 2026-08 全国校准).

    注意: 这是经验预测 (PREDICTION 级), 不是保证; Drift 模型 (v0.3 §4-D)
    负责持续验证锚点是否失效。
    """
    if alignment != alignment:  # NaN
        return float("nan")
    pts = _COMPLIANCE_ANCHORS
    if alignment <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if alignment <= x1:
            return round(y0 + (y1 - y0) * (alignment - x0) / (x1 - x0), 3)
    return pts[-1][1]
