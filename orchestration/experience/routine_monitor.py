# -*- coding: utf-8 -*-
"""隐约束监控与 elicitation (v0.4 §9 增补).

老板命题: "业务可能周二开周会, 周五坐火车去郊区, 这些我们其实不知道。"
形式化: 观测 = 脚印 (zone×weekday×week 计数); 原因 = 隐变量
(周会日/郊区日/集市日/个人安排)。θ(rep,weekday) 是隐过程的边际投影。

三个推论进架构:
  1. 边际模型有效 ⟺ 隐约束稳定 → 用 prequential log-loss 突刺做变点检测
  2. 最便宜的高价值数据 = 结构化提问 (elicitation), 把隐变量变观测条件
  3. 提问答案 ⇒ routine 有结构性原因 ⇒ 更稳定 ⇒ 慢衰减 + 高适配置信
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

# elicitation 问题枚举 (每月每销售最多问一次, 可不答)
ELICIT_KINDS = ("meeting_day", "suburb_day", "market_day", "personal_fixed", "other")


@dataclass(frozen=True)
class ElicitationEvent:
    """一次结构化提问 (原因通道). 答案可缺省."""

    line_id: str
    kind: str                    # ELICIT_KINDS
    asked_week: int
    answer: Optional[str] = None  # e.g. "Tuesday" / "Friday" / None=未答
    trigger: str = "change_point"  # change_point | monthly_routine | manual


def detect_change_points(loss_by_week: Sequence[float],
                         baseline_mult: float = 2.0,
                         min_weeks: int = 2) -> list:
    """prequential log-loss 突刺 = 隐约束变化信号.

    spike_t: loss_t > baseline_mult × mean(loss_<t) 且 t ≥ min_weeks.
    返回突刺周索引 (0-based 周序).
    """
    loss = list(loss_by_week)
    out = []
    for t in range(min_weeks, len(loss)):
        base = float(np.mean(loss[:t]))
        if base > 0 and loss[t] > baseline_mult * base:
            out.append(t)
    return out


def apply_elicitation(alpha: Mapping[str, float], lam: float,
                      elicited: Optional[ElicitationEvent] = None) -> tuple:
    """条件化先验: 有 elicitation 答案 ⇒ routine 有结构性原因 ⇒ 更稳定.

    返回 (alpha_sharpened, lam_new):
      - 有答案: 在历史主导块上 sharpen (×2), λ 提高 (0.9→0.95 慢衰减)
      - 无答案/无事件: 原样
    不改变均值方向, 只提高置信/稳定性 — 边际模型的方向仍由脚印决定。
    """
    if elicited is None or elicited.answer is None:
        return dict(alpha), lam
    if not alpha:
        return dict(alpha), lam
    top = max(alpha, key=alpha.get)
    sharpened = {k: (v * 2.0 if k == top else v) for k, v in alpha.items()}
    return sharpened, min(0.95, lam + 0.05)


def reset_prior_on_change_point(city_prior: Mapping[str, float],
                                alpha: Mapping[str, float],
                                t: int, change_points: Sequence[int]) -> dict:
    """变点周 ⇒ 重置 α 到城市先验 (边际模型不再可信, 从头学)."""
    if t in set(change_points):
        return dict(city_prior)
    return dict(alpha)
