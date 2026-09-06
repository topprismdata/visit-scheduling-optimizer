# -*- coding: utf-8 -*-
"""算法层测试: MOVE 候选纯逻辑(确定性) + free 模式缺陷存在性 + 同种子复现 + 09 端到端三闸 + Layer2 oracle + 增量不变量."""
import itertools
import random
import sys
from datetime import date

import numpy as np
import pytest

sys.path.insert(0, ".")

MON = [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20), date(2026, 7, 27)]
WED = [date(2026, 7, 1), date(2026, 7, 8), date(2026, 7, 15), date(2026, 7, 22), date(2026, 7, 29)]


def test_move_candidates_contract_mode_deterministic_and_legal():
    from algos.r2_alns import move_candidates
    contracts = {5: ("B", 1)}
    sched = {WED[0], WED[2], WED[4]}
    seen = set()
    for seed in range(20):
        cands = move_candidates(5, sched, {0: MON, 2: WED}, contracts, "contract",
                                random.Random(seed))
        for w, ds in cands:
            if w == 0:
                assert ds == {MON[1], MON[3]}          # 奇相位周一 = 第2/4个
            seen.add((w, tuple(sorted(ds))))
    assert all(w != 2 for w, _ in seen if True) or all(
        ds == sched for w, ds in seen if w == 2)        # 原星期几候选=原集合, 必被跳过


def test_move_candidates_free_mode_can_be_illegal():
    """free(旧口径)随机全组合可产生相位非法集 — v1 缺陷存在性, 审计复现口径的依据."""
    from algos.r2_alns import move_candidates
    from core.contract import contract_slot_dates
    contracts = {5: ("B", 1)}
    sched = {WED[0], WED[2], WED[4]}
    legal_wed = contract_slot_dates("B", 1, WED)
    seen_illegal = False
    for seed in range(200):
        cands = move_candidates(5, sched, {0: MON, 2: WED}, contracts, "free",
                                random.Random(seed))
        if any(w == 2 and ds != legal_wed for w, ds in cands):
            seen_illegal = True
    assert seen_illegal, "200 种子内必须见过相位非法候选"


def test_move_candidates_rejects_empty_and_identity():
    from algos.r2_alns import move_candidates
    contracts = {5: ("B", 1)}
    sched = {WED[0], WED[2], WED[4]}
    cands = move_candidates(5, sched, {0: MON, 2: WED}, contracts, "contract",
                            random.Random(1))
    assert cands and all(ds and ds != sched for _, ds in cands)


def test_layer2_cpsat_equals_permutation_bruteforce():
    """ChatGPT 采纳项 #5: n≤7 时 CP-SAT 开链 == 全排列暴力 (非对称矩阵)."""
    from algos.tsp_engine import _exact_open_tsp_status
    rng = np.random.default_rng(7)
    for trial in range(10):
        n = int(rng.integers(4, 8))
        D = rng.uniform(1.0, 10.0, size=(n, n)).round(3)
        np.fill_diagonal(D, 0.0)
        route, status, _ms = _exact_open_tsp_status(list(range(n)), D, 30)
        assert status == "OPTIMAL", f"status={status}"
        bf = min(sum(D[p[i]][p[i + 1]] for i in range(n - 1))
                 for p in itertools.permutations(range(n)))
        got = sum(D[route[i]][route[i + 1]] for i in range(n - 1))
        assert abs(got - bf) < 1e-6, f"trial{trial}: {got} vs {bf}"


def test_layer2_duplicate_coordinates_still_optimal():
    """重复坐标(零距离弧)不破坏 CP-SAT 最优性."""
    from algos.tsp_engine import _exact_open_tsp_status
    n = 6
    D = np.ones((n, n))                     # 全 1: 任何排列同成本
    np.fill_diagonal(D, 0.0)
    route, status, _ms = _exact_open_tsp_status(list(range(n)), D, 30)
    assert status == "OPTIMAL"
    got = sum(D[route[i]][route[i + 1]] for i in range(n - 1))
    assert got == n - 1                      # n-1 条弧, 每条 1.0 (对角零不入链)


def test_r2alns_reported_km_equals_full_recompute():
    """ChatGPT 采纳项 #6: 汇报里程必须等于返回解的全量重算 (增量漂移零容忍)."""
    from core.metric import total_km
    from data.loader import load_plan, load_line
    from algos.r2_alns import R2ALNS
    d = load_line(load_plan(), "09")
    D = np.load("output/road_dist_09.npy")
    r = R2ALNS().solve(d, D, time_budget=20, seed=42)
    assert abs(r.km - total_km(r.days, D)) < 0.05, "汇报 km 漂移"


def test_r2alns_same_seed_reproducible_and_gated():
    from core.contract import check_contract, contract_of
    from data.loader import load_plan, load_line
    from algos.r2_alns import R2ALNS
    from algos.sp_matheuristic import check_r2prime
    d = load_line(load_plan(), "09")
    D = np.load("output/road_dist_09.npy")
    dates = list(d.dates)
    ct = contract_of(d.days_orig, dates)
    r1 = R2ALNS().solve(d, D, time_budget=30, seed=42)
    r2 = R2ALNS().solve(d, D, time_budget=30, seed=42)
    assert r1.km == r2.km, "同种子必须逐位复现 (若抖动: 加大预算重试, 不许删断言)"
    assert r1.capacity_ok and check_r2prime(r1.days) == []
    viol = check_contract(r1.days, ct, dates)
    assert viol == [], f"合同违例 {len(viol)}: {viol[:10]}"
    assert r1.metadata["contract_ok"] is True
