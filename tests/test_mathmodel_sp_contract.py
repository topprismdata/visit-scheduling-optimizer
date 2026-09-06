# -*- coding: utf-8 -*-
"""数学层测试: SP 合同模式的可行集 == 语义合法集.
部件单元 + RHS 可行模式穷举 + 3^9 暴力枚举等价 + LP≤IP + 真实 09 线结构保证."""
import sys
import itertools
import json
from datetime import date

import pytest

sys.path.insert(0, ".")

MON = [date(2026, 7, 6), date(2026, 7, 13), date(2026, 7, 20), date(2026, 7, 27)]
WED = [date(2026, 7, 1), date(2026, 7, 8), date(2026, 7, 15), date(2026, 7, 22), date(2026, 7, 29)]
DATES = sorted(MON + WED)


def _contracts():
    from core.contract import contract_of
    days = {m: [0] for m in MON}
    days[WED[1]] = [1]; days[WED[3]] = [1]
    days[WED[0]] = [2]; days[WED[2]] = [2]; days[WED[4]] = [2]
    return contract_of(days, DATES)


def _pool():
    p = []
    for m in MON:
        p.append((m, [0], 1.0))
        if m in (MON[0], MON[2]):
            p += [(m, [1], 2.0), (m, [0, 1], 2.8)]
        if m in (MON[1], MON[3]):
            p += [(m, [2], 2.5), (m, [0, 2], 3.3)]
    for w in WED:
        p.append((w, [0], 1.0))
        if w in (WED[1], WED[3]):
            p += [(w, [1], 2.0), (w, [0, 1], 2.8)]
        if w in (WED[0], WED[2], WED[4]):
            p += [(w, [2], 2.5), (w, [0, 2], 3.3)]
    p.append((WED[0], [1], 1.5))   # 相位非法列: 店1 出现在奇相位周三
    return p


def test_fw_table_matches_contract_counts():
    from algos.sp_matheuristic import _fw_table, weekday_dates
    from core.contract import contract_slot_dates
    ct = _contracts()
    fw = _fw_table(ct, weekday_dates(DATES))
    assert fw[0] == {0: 4, 2: 5}
    assert fw[1] == {0: 2, 2: 2}
    assert fw[2] == {0: 2, 2: 3}
    for c, tbl in fw.items():
        for w, f in tbl.items():
            assert f == len(contract_slot_dates(*ct[c], weekday_dates(DATES)[w]))


def test_pool_filter_drops_exactly_illegal():
    from algos.sp_matheuristic import _contract_pool_filter
    from core.contract import legal_date_map
    ct = _contracts()
    out, drop = _contract_pool_filter(_pool(), legal_date_map(ct, DATES))
    assert drop == 1 and (WED[0], [1], 1.5) not in out
    legal = legal_date_map(ct, DATES)
    assert all(d in legal[c] for d, r, _ in out for c in r)


def test_linearized_rhs_admits_exactly_legal_patterns():
    from ortools.sat.python import cp_model
    from algos.sp_matheuristic import _fw_table, weekday_dates
    from core.contract import legal_date_map
    fw = _fw_table(_contracts(), weekday_dates(DATES))[2]   # 店2 (B,1)
    legal = legal_date_map(_contracts(), DATES)[2]
    feasible = []
    for mon_dates in [()] + [c for k in (2,) for c in itertools.combinations(MON, k)]:
        for wed_dates in [()] + [c for k in (3,) for c in itertools.combinations(WED, k)]:
            if not mon_dates and not wed_dates:
                continue
            m2 = cp_model.CpModel()
            # cols: 列索引→日期 (修正原稿方向); 合法性剪枝 = SP 里的池过滤在微型模型中的对应物
            cols = {**{i: m for i, m in enumerate(MON)}, **{4 + i: w for i, w in enumerate(WED)}}
            x = {i: m2.NewBoolVar(f"x{i}") for i in cols}
            z = {w: m2.NewBoolVar(f"z{w}") for w in (0, 2)}
            m2.AddExactlyOne(list(z.values()))
            m2.Add(sum(x.values()) == sum(fw[w] * z[w] for w in (0, 2)))
            on = {i for i, d in cols.items() if d in mon_dates + wed_dates}
            for i, d in cols.items():
                if d not in legal:
                    m2.Add(x[i] == 0)
                m2.Add(x[i] <= z[d.weekday()])
                m2.Add(x[i] == (1 if i in on else 0))
            if cp_model.CpSolver().Solve(m2) in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                feasible.append((mon_dates, wed_dates))
    assert set(feasible) == {((), (WED[0], WED[2], WED[4])), ((MON[1], MON[3]), ())}


def _brute_force(contract_mode=True):
    from core.contract import legal_date_map, check_contract
    ct = _contracts()
    legal = legal_date_map(ct, DATES)
    k_c = {0: 4, 1: 2, 2: 3}
    by_date = {}
    for d, r, km in _pool():
        by_date.setdefault(d, []).append((r, km))
    best = None
    for combo in itertools.product(*(by_date[d] for d in DATES)):
        sched = {c: set() for c in ct}
        ok = True
        for d, (r, _) in zip(DATES, combo):
            for c in r:
                if contract_mode and d not in legal[c]:
                    ok = False
                sched[c].add(d)
        if not ok:
            continue
        days = {d: list(r) for d, (r, _) in zip(DATES, combo)}
        if contract_mode and check_contract(days, ct, DATES):
            continue
        if any(not v for v in sched.values()):
            continue
        if not contract_mode and any(len(s) != k_c[c] for c, s in sched.items()):
            continue   # legacy 模型含 ==k_c 覆盖; 合同模式计数由 check_contract 精确相等蕴含
        km = sum(k for _, k in combo)
        best = km if best is None else min(best, km)
    return best


def test_ip_optimum_equals_bruteforce_semantic_opt():
    from algos.sp_matheuristic import sp_solve_ip
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    km, days = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    assert km == pytest.approx(_brute_force(True), abs=1e-6) == pytest.approx(14.0, abs=1e-6)
    km_legacy, _ = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30)
    assert km_legacy == pytest.approx(_brute_force(False), abs=1e-6)
    assert km < km_legacy, "两模型恰在槽位计数处分叉: 合同模式允许 W 店换绑星期几 (5 槽全访)"
def test_ip_diagnostics_expose_solver_certificate():
    from visitmodel.sp.formulation import sp_solve_ip

    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    km, days, diagnostics = sp_solve_ip(
        DATES, k_c, _pool(), timeout_s=30, contract=ct,
        return_diagnostics=True,
    )

    assert days
    assert diagnostics["solver_status"] == "OPTIMAL"
    assert diagnostics["optimality_proven"] is True
    assert diagnostics["objective_value_milli"] == pytest.approx(km * 1000)
    assert diagnostics["best_bound_milli"] == pytest.approx(
        diagnostics["objective_value_milli"]
    )
    assert diagnostics["pool_size"] > 0

def test_lp_le_ip_on_synthetic():
    from algos.sp_matheuristic import sp_solve_lp, sp_solve_ip
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    lp, _ = sp_solve_lp(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    ip, _ = sp_solve_ip(DATES, k_c, _pool(), timeout_s=30, contract=ct)
    assert lp is not None and lp <= ip + 1e-6


def test_starved_store_zero_legal_columns_is_infeasible():
    """合同模式: 池过滤后零合法列的义务店 = 不可行 (返回 None), 而非静默未服务解.
    复现审查用例: 剥除店1全部列后, 修复前返回缺店1的解且 check_contract=[1]."""
    from algos.sp_matheuristic import sp_solve_ip, sp_solve_lp
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    pool = [col for col in _pool() if 1 not in col[1]]   # 池过滤可饿死原池中的店
    assert sp_solve_ip(DATES, k_c, pool, timeout_s=30, contract=ct) == (None, None)
    assert sp_solve_lp(DATES, k_c, pool, timeout_s=30, contract=ct) == (None, None)


def test_pricing_legal_and_rc_exact_under_random_duals():
    """ChatGPT 共研采纳项: 定价合法性 + rc 精确性 oracle (随机 dual 20 轮).
    ≤2 店路线时贪心插入即精确, rc 必须等于两序全枚举最优."""
    import random
    import numpy as np
    from algos.sp_matheuristic import price_columns
    from core.contract import legal_date_map
    from core.metric import day_km
    ct = _contracts()
    k_c = {0: 4, 1: 2, 2: 3}
    legal = legal_date_map(ct, DATES)
    D = np.array([[0.0, 1.0, 2.0], [1.0, 0.0, 1.0], [2.0, 1.0, 0.0]])
    n_legal = 0
    for seed in range(20):
        rng = random.Random(seed)
        duals = {"store": {c: rng.uniform(0.0, 5.0) for c in k_c},
                 "date": {d: rng.uniform(-1.0, 1.0) for d in DATES}}
        cols = price_columns(DATES, k_c, duals, D, top_m=3, col_iter=50,
                             max_daily=2, min_daily=2, legal=legal)
        for dd, route, km in cols:
            assert all(dd in legal[c] for c in route), "定价返回了合同非法列"
            assert abs(day_km(route, D) - km) <= 5e-4, "rc 里的 km 与重算不符"
            if len(route) == 2:
                u = duals["store"]; w_d = duals["date"][dd]
                rc_got = day_km(route, D) - sum(u[c] for c in route) - w_d
                rc_best = min(day_km(list(p), D) for p in itertools.permutations(route)) - sum(u[c] for c in route) - w_d
                assert abs(rc_got - rc_best) < 1e-9, "≤2 店时贪心必须精确"
                n_legal += 1
    assert n_legal > 0, "oracle 未产生任何列, 测试无效"


def test_09_baseline_only_pool_structure_guarantee():
    import numpy as np
    from data.loader import load_plan, load_line
    from core.contract import contract_of, check_contract, legal_date_map
    from core.metric import day_km
    from algos.tsp_engine import _exact_open_tsp
    from algos.sp_matheuristic import sp_solve_ip, sp_solve_lp, _contract_pool_filter
    pv = load_plan()
    d = load_line(pv, "09")
    D = np.load("output/road_dist_09.npy")
    dates = list(d.dates)
    ct = contract_of(d.days_orig, dates)
    k_c = {c: sum(1 for dd, seq in d.days_orig.items() if c in seq) for c in ct}
    pool = []
    for dd, seq in d.days_orig.items():
        seq_opt = _exact_open_tsp(list(seq), D, time_limit=30)
        pool.append((dd, list(seq_opt), round(day_km(seq_opt, D), 3)))
    pool2, drop = _contract_pool_filter(pool, legal_date_map(ct, dates))
    assert drop == 0, "原始计划零例外, 基线A 列不应被合同过滤误伤"
    km, days = sp_solve_ip(dates, k_c, pool2, timeout_s=60, contract=ct)
    baseA = json.load(open("output/cpsat_plan_baselines.json"))["09"]
    assert abs(km - baseA) < 0.1, f"结构保证破坏: {km} vs {baseA}"
    assert check_contract(days, ct, dates) == []
    lp, _ = sp_solve_lp(dates, k_c, pool2, timeout_s=60, contract=ct)
    assert lp is not None and lp <= km + 1e-6
