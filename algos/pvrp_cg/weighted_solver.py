"""Weighted CG solver — 价值加权的列生成 (Phase 2, 深化版)。

真正调用 solver._solve_core 并注入加权 col_cost_fn，使高价值客户获得更低的
列成本（虚拟折扣），从而在 column generation 的 pricing 和 final IP 中被优先纳入。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .policy import PlanningPolicy


def _col_cost_time_with_value(
    T: list[list[float]],
    t0: list[float],
    svc: Sequence[float],
    value_scores: Sequence[float],
    ids: Sequence[int],
    value_weight: float = 0.0,
) -> float:
    """带价值折扣的列成本 = 原始工时 - value_weight × Σ(value_score × svc)。"""
    if not ids:
        return 0.0
    travel = t0[ids[0]]
    for k in range(len(ids) - 1):
        travel += T[ids[k]][ids[k + 1]]
    service_total = sum(svc[i] for i in ids)
    value_bonus = sum(value_scores[i] * svc[i] for i in ids) * value_weight
    return max(0.0, travel + service_total - value_bonus)


def solve_weighted_cg(
    n: int,
    T: list[list[float]],
    t0: list[float],
    svc: Sequence[float],
    freq: Sequence[int],
    value_scores: Sequence[float] | None = None,
    days: int = 20,
    daily_cap: float = 540.0,
    value_weight: float = 0.0,
    time_limit: int = 30,
    verbose: bool = False,
) -> tuple[list | None, float, str, dict]:
    """价值加权的 time-calibrated 列生成 (完整 pricing loop)。

    与 solve_time_cg 相同约束但注入自定义 col_cost_fn 到 _solve_core，
    使 pricing 的 dual-guided selection 融合客户价值评分。

    Args:
        n / T / t0 / svc / freq / days / daily_cap / time_limit: 同 solve_time_cg。
        value_scores: [0,1] 归一化客户价值评分 (None = 全 0, 退化为纯效率模式)。
        value_weight: 价值权重系数 [0, ~5]。0 = 纯效率; >0 高价值客户列成本更低。
        verbose: 是否打印日志。

    Returns:
        (assigns, total, status, stats) — 同 solve_time_cg。
    """
    from .solver import _solve_core

    scores = value_scores or [0.0] * n

    def col_cost_fn(ids: list[int]) -> float:
        return _col_cost_time_with_value(T, t0, svc, scores, ids, value_weight)

    return _solve_core(
        n=n,
        D=T,
        t0=t0,
        freq=list(freq),
        days=days,
        col_cost_fn=col_cost_fn,
        closed=True,
        t0_vec=t0,
        daily_cap=daily_cap,
        time_limit=time_limit,
        verbose=verbose,
    )
