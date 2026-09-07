# -*- coding: utf-8 -*-
"""P0-3 回归守卫: ALNS v4 跨日移动必须落在合同合法域内 (双周相位不可破坏).

背景: same_weekday_only 只保星期几; 双周店跨周同星期移动曾绕过相位合同.
修复: shift/swap 候选过滤 legal.get(c) + 输出 contract_ok 闸."""
import numpy as np

from core.contract import check_contract, contract_of
from data.loader import load_line, load_plan


def test_alns_v4_never_breaks_contract_phase_on_09():
    """09 线含双周店: 微调后合同/相位必须零违例 (P0-3 回归)."""
    from algos.alns_v4 import ALNSv4

    d = load_line(load_plan(), "09")
    D = np.load("output/road_dist_09.npy")
    dates = list(d.dates)
    contracts = contract_of(d.days_orig, dates)

    r = ALNSv4().solve(d, D, time_budget=20, seed=42, lam=2.0, mu=0.5)

    assert r.days, "v4 应返回日历"
    assert len(check_contract(r.days, contracts, dates)) == 0
    assert r.metadata["contract_violations"] == 0
    assert r.contract_ok is True


def test_alns_v4_move_candidates_respect_biweekly_phase_determinism():
    """同 seed 两次运行逐位一致 (确定性红线; 合法域过滤不引入随机性)."""
    from algos.alns_v4 import ALNSv4

    d = load_line(load_plan(), "09")
    D = np.load("output/road_dist_09.npy")
    r1 = ALNSv4().solve(d, D, time_budget=10, seed=7, lam=2.0, mu=0.5)
    r2 = ALNSv4().solve(d, D, time_budget=10, seed=7, lam=2.0, mu=0.5)
    assert r1.km == r2.km
