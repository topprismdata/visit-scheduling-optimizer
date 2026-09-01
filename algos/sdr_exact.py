# -*- coding: utf-8 -*-
"""sdr_exact: 集合划分 + 列生成精确框架.
阶段1: 多算法/多起点/随机扰动 → 大规模路线池 (每日期 ≥K 条候选)
阶段2: CP-SAT Set Partitioning 组合 (对池内路线精确)
阶段3: LP 松弛 (ortools GLOP) → 下界 LB → gap 报告
参考: Paradiso 2020 ESF (列枚举+分支切割) + Villegas 2025 SP/SC matheuristic.
"""
import time, random
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km
from algos.registry import register
from algos.tsp_engine import _nn2opt_open, _exact_open_tsp
from core.route_pool import RoutePool, Route


def _gen_pool(data, D, per_date=60, seed=42, time_budget=600):
    """生成路线池: 计划 + NN2opt + 多起点随机 NN2opt + 2opt 扰动."""
    rng = random.Random(seed)
    pool = RoutePool()
    dates = data.dates
    start = time.time()
    per_line_budget = time_budget / max(len(dates), 1)
    for dd in dates:
        seeds = list(data.days_orig[dd])
        # 1. 原始
        pool.add(Route(date=dd, stores=tuple(seeds), cost=day_km(seeds, D), algo="plan"))
        # 2. NN2opt 确定性
        r = _nn2opt_open(seeds, D)
        pool.add(Route(date=dd, stores=tuple(r), cost=day_km(r, D), algo="nn2opt"))
        # 3. 多起点随机 NN2opt
        n_seeds = len(seeds)
        n_rand = max(1, per_date - 2)
        for _ in range(n_rand):
            if time.time() - start > time_budget:
                break
            shuf = list(seeds)
            rng.shuffle(shuf)
            r = _nn2opt_open(shuf, D)
            pool.add(Route(date=dd, stores=tuple(r), cost=day_km(r, D), algo="ms"))
    return pool


def _sp_solve(data, D, pool, time_budget=300, warm_start=None):
    """CP-SAT Set Partitioning: 每天选1条, 每店覆盖 freq 次."""
    from ortools.sat.python import cp_model
    dates = data.dates; codes = data.codes
    model = cp_model.CpModel()
    routes_by_date = {}
    for dd in dates:
        routes_by_date[dd] = pool.get_routes(dd)
    x = {}
    for dd in dates:
        for ri, r in enumerate(routes_by_date[dd]):
            x[(dd, ri)] = model.NewBoolVar(f'x_{dd}_{ri}')
    for dd in dates:
        model.Add(sum(x[(dd, ri)] for ri in range(len(routes_by_date[dd]))) == 1)
    store_incs = {si: [] for si in range(len(codes))}
    for dd in dates:
        for ri, r in enumerate(routes_by_date[dd]):
            for si in r.stores:
                store_incs[si].append((dd, ri))
    for si in range(len(codes)):
        freq = data.freq.get(codes[si], 0)
        if freq:
            model.Add(sum(x[(dd, ri)] for (dd, ri) in store_incs[si]) == freq)
    model.Minimize(sum(r.cost * x[(dd, ri)] for dd in dates for ri, r in enumerate(routes_by_date[dd])))
    # warm start
    if warm_start:
        for dd, seq in warm_start.items():
            key = tuple(seq)
            for ri, r in enumerate(routes_by_date[dd]):
                if r.stores == key:
                    model.AddHint(x[(dd, ri)], 1)
                    break
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(60, time_budget)
    solver.parameters.num_search_workers = 8
    st = solver.Solve(model)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        days = {}
        for dd in dates:
            for ri, r in enumerate(routes_by_date[dd]):
                if solver.Value(x[(dd, ri)]):
                    days[dd] = list(r.stores); break
        ub = total_km(days, D)
        lb = solver.BestObjectiveBound() if hasattr(solver, 'BestObjectiveBound') else ub
        gap = (ub - lb) / ub if ub > 0 else 0.0
        return days, ub, lb, gap, st
    return None, None, None, None, st


def _lp_lb(data, D, pool, time_budget=120):
    """LP 松弛下界 via GLOP (集合划分连续松弛)."""
    try:
        from ortools.linear_solver import pywraplp
    except Exception:
        return None
    dates = data.dates; codes = data.codes
    solver = pywraplp.Solver.CreateSolver('GLOP')
    if not solver:
        return None
    routes_by_date = {dd: pool.get_routes(dd) for dd in dates}
    x = {}
    for dd in dates:
        for ri, r in enumerate(routes_by_date[dd]):
            x[(dd, ri)] = solver.NumVar(0.0, 1.0, f'x_{dd}_{ri}')
    for dd in dates:
        solver.Add(solver.Sum(x[(dd, ri)] for ri in range(len(routes_by_date[dd]))) == 1)
    store_incs = {si: [] for si in range(len(codes))}
    for dd in dates:
        for ri, r in enumerate(routes_by_date[dd]):
            for si in r.stores:
                store_incs[si].append((dd, ri))
    for si in range(len(codes)):
        freq = data.freq.get(codes[si], 0)
        if freq:
            solver.Add(solver.Sum(x[(dd, ri)] for (dd, ri) in store_incs[si]) == freq)
    obj = solver.Objective()
    for dd in dates:
        for ri, r in enumerate(routes_by_date[dd]):
            obj.SetCoefficient(x[(dd, ri)], r.cost)
    obj.SetMinimization()
    st = solver.Solve()
    if st == pywraplp.Solver.OPTIMAL:
        return solver.Objective().Value()
    return None


@register
class SDRExact(Algorithm):
    """集合划分 + 列生成: 大池枚举 → CP-SAT 组合 → LP下界 gap."""
    name = "sdr_exact"

    def solve(self, data, D, time_budget=600, per_date=60, warm_start=None, pool=None):
        t0 = time.time()
        if pool is None:
            pool = _gen_pool(data, D, per_date=per_date, time_budget=time_budget * 0.5)
        gen_t = time.time() - t0
        t1 = time.time()
        days, ub, lb, gap, st = _sp_solve(data, D, pool,
                                          time_budget=max(30, time_budget * 0.4),
                                          warm_start=warm_start)
        sp_t = time.time() - t1
        t2 = time.time()
        lp = _lp_lb(data, D, pool, time_budget=min(60, time_budget * 0.1))
        lp_t = time.time() - t2
        if days is None:
            return AlgoResult(name=self.name,
                              days={dd: list(seq) for dd, seq in data.days_orig.items()},
                              km=total_km(data.days_orig, D),
                              metadata={"pool": pool.stats(), "gen_s": gen_t, "sp_s": sp_t, "lp_s": lp_t})
        return AlgoResult(name=self.name, days=days, km=ub,
                          metadata={
                              "pool": pool.stats(),
                              "lb": round(lb, 1) if lb else None,
                              "lp_lb": round(lp, 1) if lp else None,
                              "gap": round(gap, 4) if gap is not None else None,
                              "gen_s": round(gen_t, 1), "sp_s": round(sp_t, 1), "lp_s": round(lp_t, 1),
                          })
