# -*- coding: utf-8 -*-
"""义务合规率 — 适配的正确 KPI (v0.4 §10.1).

证据: 业代不追欠账 (W1 未执行店 71% 丢弃); 欠账插入式适配是管理干预,
不是行为模拟 → 其价值不能用"与实际对齐"(Jaccard)衡量, 只能用义务合规衡量。

定义:
  门店义务合规 = min(实际到访, 计划到访) / 计划到访  (超访不加分, 缺访受罚)
  相位合规     = 实际到访周相位 ∩ 计划相位 ≠ ∅ 的门店占比 (双周合同的相位是义务)
"""
from __future__ import annotations

from typing import Mapping, Sequence


def store_compliance(planned: Mapping[str, int],
                     actual: Mapping[str, int]) -> float:
    """义务合规率: 有计划门店的 min(实际,计划)/计划 均值.

    planned 为 0 或缺失的门店不计入 (无义务则无合规问题)。
    """
    items = [(int(v), int(actual.get(k, 0))) for k, v in planned.items() if v]
    if not items:
        return 1.0
    return sum(min(a, p) / p for p, a in items) / len(items)


def phase_hit(planned_phase: Mapping[str, int],
              actual_phases: Mapping[str, Sequence[int]]) -> float:
    """相位合规: 实际到访周相位包含计划相位的门店占比.

    双周合同下相位(0=偶周/1=奇周)是义务。
    planned_phase: 门店 → 计划相位 ∈ {0,1}
    actual_phases: 门店 → 实际到访的周相位集合 (值域 {0,1}, 非周号)
    """
    items = list(planned_phase.items())
    if not items:
        return 1.0
    ok = sum(1 for k, ph in items if ph in set(actual_phases.get(k, ())))
    return ok / len(items)


def line_kpi(planned_counts: Mapping[str, int],
             actual_counts: Mapping[str, int],
             planned_phase: Mapping[str, int],
             actual_phases: Mapping[str, Sequence[int]]) -> dict:
    """单线 KPI 汇总 (合规率是主指标; 到访率仅作参考)."""
    return {
        "compliance": store_compliance(planned_counts, actual_counts),
        "phase": phase_hit(planned_phase, actual_phases),
        "visit_rate": (sum(min(int(actual_counts.get(k, 0)), int(v))
                           for k, v in planned_counts.items())
                       / max(sum(int(v) for v in planned_counts.values()), 1)),
    }