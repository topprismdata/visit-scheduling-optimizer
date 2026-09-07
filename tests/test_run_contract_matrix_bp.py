# -*- coding: utf-8 -*-
"""bp 模式 reroute 剪枝: 先 (date,店集) 去重+走廊过滤, 再交 CP-SAT 精排."""
import datetime as dt
import numpy as np
import pytest


def _pool():
    dates = [dt.date(2026, 7, 6), dt.date(2026, 7, 7)]
    big = list(range(35))          # 35 店 = max_daily
    cols = []
    for d in dates:
        cols.append((d, big, 100.0))                    # 同店集不同序 ×3
        cols.append((d, list(reversed(big)), 101.0))
        cols.append((d, big[1:] + big[:1], 102.0))
        cols.append((d, big + [99], 150.0))             # 36 店 = 超走廊, 应滤除
    return cols


def test_prune_engine_pool_dedupes_and_caps():
    from experiments.run_contract_matrix import prune_engine_pool
    out = prune_engine_pool(_pool(), max_daily=35, min_daily=2)
    sizes = {}
    for d, route, _km in out:
        assert len(route) <= 35
        sizes.setdefault(d, set()).add(frozenset(route))
    assert all(len(v) == 1 for v in sizes.values())      # 每日期只剩一个店集
    assert len(out) == 2


def test_prune_engine_pool_top_k_bounds_pool_growth():
    from experiments.run_contract_matrix import prune_engine_pool
    dates = [dt.date(2026, 7, 6)]
    cols = [(dates[0], [i, 100 + i], float(i)) for i in range(50)]  # 50 个不同店集
    out = prune_engine_pool(cols, max_daily=35, min_daily=2, top_k=8)
    assert len(out) == 8
    assert sorted(km for _, _, km in out) == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
