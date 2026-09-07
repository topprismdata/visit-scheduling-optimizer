# -*- coding: utf-8 -*-
"""Branch-and-Price 单元测试: 微型可证明实例 + 中型行为实例.

文献锚点 (Barnhart et al. 1998; Lübbecke & Desrosiers 2005; Ryan & Foster 1981):
- 分支落在原空间决策 (店-日指派对) 而非主问题变量; 定价可承载 forced/forbidden;
- 证明 (PROVEN_OPTIMAL) 只在小实例 + 精确定价全 OPTIMAL 下签发.

微型 (4 店, Mon/Tue × 2 周, 走廊 [2,2], 全 W f=2):
- 所有星期几槽位数相等 → 合同允许重配 → 原计划跨簇配对可优化为同簇配对;
- 规模极小 → 搜索耗尽且精确定价全证明 → PROVEN_OPTIMAL;
- 耗尽 + 证毕 ⇒ B&P incumbent 必等于该列池上 Contract-SP IP 最优 (关键不变量).

中型 (12 店 4 簇, Mon-Thu × 2 周): 断言合同/走廊/不劣化 (LP 松弛间隙大,
不 asserted PROVEN — 那需要上千节点, 属规模而非正确性问题).
"""
import datetime as dt
from collections import Counter
import random
import numpy as np

from algos.branch_and_price import BranchAndPrice, BranchAndPriceAlg
from algos.sp_matheuristic import dedupe_pool
from core.base import LineData
from core.contract import check_contract, contract_of
from core.metric import check_capacity, day_km
from opticore.heuristics import nn2opt_open
from visitmodel.sp.formulation import sp_solve_ip


def _make_line(line_id, x, dates, days_orig):
    freq = {}
    for seq in days_orig.values():
        for c in seq:
            freq[c] = freq.get(c, 0) + 1
    return LineData(
        line_id=line_id, line_name="synthetic", codes=[str(i) for i in range(len(x))],
        lon=list(x), lat=[0.0] * len(x), dates=list(dates), days_orig=days_orig,
        freq=freq, stores=len(x), visits=sum(len(v) for v in days_orig.values()),
    )


def _mini_line():
    """4 店: 0@0, 1@0.5 同簇; 2@10, 3@10.5 同簇. Mon/Tue 各 2 周, 全 W."""
    dates = [dt.date(2026, 7, 6), dt.date(2026, 7, 7),
             dt.date(2026, 7, 13), dt.date(2026, 7, 14)]
    days_orig = {dates[0]: [0, 2], dates[1]: [1, 3],
                 dates[2]: [0, 2], dates[3]: [1, 3]}
    return _make_line("M0", [0.0, 0.5, 10.0, 10.5], dates, days_orig)


def _mid_line():
    """12 店 4 簇; 原计划跨簇配对, 合同允许同簇重配."""
    dates = [dt.date(2026, 7, 6), dt.date(2026, 7, 7), dt.date(2026, 7, 8),
             dt.date(2026, 7, 9), dt.date(2026, 7, 13), dt.date(2026, 7, 14),
             dt.date(2026, 7, 15), dt.date(2026, 7, 16)]
    days_orig = {dates[0]: [0, 3, 8], dates[1]: [1, 4], dates[2]: [2, 5, 10],
                 dates[3]: [6, 7, 11], dates[4]: [0, 3], dates[5]: [1, 4],
                 dates[6]: [2, 5], dates[7]: [6, 7]}
    return _make_line("T0", [0.0, 0.5, 1.0, 10.0, 10.5, 11.0,
                             20.0, 20.5, 21.0, 30.0, 30.5, 31.0],
                      dates, days_orig)


def _dist(data):
    x = np.asarray(data.lon)
    return np.abs(x[:, None] - x[None, :])


def _orig_km(data, D):
    return sum(day_km(nn2opt_open(list(seq), D), D) for seq in data.days_orig.values())

def test_randomized_schedule_preserves_contract_and_changes_assignments():
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    eng = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                         data.min_daily_capacity, data.max_daily_capacity,
                         time_budget=1, exact_tl=0.1)

    schedule = eng._randomized_schedule(random.Random(7), swaps=12)
    assert any(set(schedule[dd]) != set(data.days_orig[dd]) for dd in dates)
    assert not check_contract(schedule, contracts, dates)
    assert check_capacity(schedule, data.max_daily_capacity, data.min_daily_capacity)


def test_warm_start_contains_alternative_legal_columns():
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    eng = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                         data.min_daily_capacity, data.max_daily_capacity,
                         time_budget=1, exact_tl=0.1)

    assert len(eng.pool) > len(dates), "B&P 冷启动不能只有原计划单列"


def test_initial_schedule_and_columns_are_used_as_warm_start():
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    seed = {dd: ([0, 1] if dd.weekday() == 0 else [2, 3]) for dd in dates}
    seed_cols = [(dd, route, round(day_km(route, D), 3))
                 for dd, route in seed.items()]

    eng = BranchAndPrice(
        dates, k_c, D, contracts, data.days_orig,
        data.min_daily_capacity, data.max_daily_capacity,
        time_budget=1, exact_pricing=False,
        initial_days=seed, initial_pool=seed_cols,
    )

    assert eng.incumbent[1] == seed
    assert all((dd, frozenset(route)) in eng.pool_keys
               for dd, route, _km in seed_cols)


def test_mini_proves_optimal_and_improves():
    data = _mini_line()
    D = _dist(data)
    res = BranchAndPriceAlg().solve(data, D, time_budget=60, max_nodes=300, exact_tl=2.0)

    assert res.days, "B&P 应返回 incumbent"
    assert res.capacity_ok
    assert res.contract_ok, f"合同闸违例: {res.metadata}"
    assert res.metadata["status"] == "PROVEN_OPTIMAL"

    orig = _orig_km(data, D)
    assert res.km < orig - 1.0, f"未发现重配改进: bp={res.km} vs orig={orig}"

def test_mini_incumbent_equals_pool_ip_when_proven():
    """耗尽 + 证毕时, B&P incumbent == 该列池上 Contract-SP IP 最优 (关键不变量)."""
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    from collections import Counter
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    eng = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                         data.min_daily_capacity, data.max_daily_capacity,
                         time_budget=60, max_nodes=300, exact_tl=2.0)
    out = eng.solve()
    assert out["status"] == "PROVEN_OPTIMAL"
    assert out["incumbent_days"] is not None

    pool = dedupe_pool(out["pool"], max_daily=2, min_daily=2)
    ip_km, ip_days = sp_solve_ip(dates, k_c, pool, timeout_s=30,
                                 r2_prime=True, contract=contracts)
    assert ip_days is not None
    assert abs(ip_km - out["incumbent_km"]) < 1e-3, (
        f"池上 IP ({ip_km}) != B&P incumbent ({out['incumbent_km']})")

    viol = check_contract(out["incumbent_days"], contracts, dates)
    assert not viol
    assert check_capacity(out["incumbent_days"],
                          data.max_daily_capacity, data.min_daily_capacity)


def test_mid_returns_contract_valid_solution():
    data = _mid_line()
    D = _dist(data)
    res = BranchAndPriceAlg().solve(data, D, time_budget=90, max_nodes=400, exact_tl=1.0)

    assert res.days, "B&P 应返回 incumbent"
    assert res.capacity_ok
    assert res.contract_ok, f"合同闸违例: {res.metadata}"

    orig = _orig_km(data, D)
    assert res.km <= orig + 1e-6, "B&P 不应劣于原计划"
def test_proof_status_downgrades_when_node_lp_was_not_optimal():
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    from collections import Counter
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    eng = BranchAndPrice(
        dates, k_c, D, contracts, data.days_orig,
        data.min_daily_capacity, data.max_daily_capacity,
        time_budget=1,
    )
    eng.converge_attempts = 1
    eng.converge_proven = 1
    eng.lp_nonoptimal_nodes = 1

    assert eng._tree_status() == "BOUND_HEURISTIC"


def test_unproven_pricing_does_not_issue_lower_bound():
    """启发式定价未证明无负 rc 列时: root_lb 不签发（None），RMP 值不得冒充下界；incumbent 仍保底返回."""
    data = _mini_line()
    D = _dist(data)
    dates = list(data.dates)
    contracts = contract_of(data.days_orig, dates)
    k_c = Counter(c for dd in dates for c in data.days_orig[dd])
    eng = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                         data.min_daily_capacity, data.max_daily_capacity,
                         time_budget=30, exact_pricing=False)
    out = eng.solve()
    assert out["status"] in ("BOUND_HEURISTIC", "TIME_LIMIT")
    assert out["root_lb"] is None          # 未证明 → 不签发下界（rmp_lp_value 只作观测）
    assert out["incumbent_days"] is not None
