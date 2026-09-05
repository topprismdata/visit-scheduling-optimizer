# -*- coding: utf-8 -*-
"""SP/SC Matheuristic - 论文驱动的集合划分后优化器 (2026-09-05).

论文依据:
- Villegas et al. 2025 (OR Perspectives) [META]: SP 等式覆盖平均 +1.08%, 局部搜索
  基线 +0.37%, 后优化式 +0.62%; 结构保证: 结果永不劣于池内最佳单解.
- Paradiso et al. 2020 (Operations Research) [ESF]: 列生成 + 受限主问题精确求解 +
  迭代 gap 收紧; 本实现为 163 店规模的启发式投影 (列=多算法/多种子日路线).

主问题 (业务约束注入 [META] 式(1)-(3)):
    min  Σ c_r x_r
    s.t. Σ_{r∈R_d} x_r = 1    ∀ 工作日 d   (每日恰一条路线)
         Σ_{r∋c}   x_r = k_c  ∀ 门店 c     (每店出现次数精确覆盖)
         x_r ∈ {0,1}
"""
import time, json, random
from collections import Counter
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km
from algos.registry import register


def dedupe_pool(pool, top_k=6):
    """池去重/限宽: 同 (date, 精确序列) 唯一; 同 (date, 店集合) 保留 km 最小前 K 条."""
    seen_seq = {}
    by_set = {}
    for date, route, km in pool:
        key = (date, tuple(route))
        if key in seen_seq:
            continue
        seen_seq[key] = km
        by_set.setdefault((date, frozenset(route)), []).append((km, list(route)))
    out = []
    for (date, fset), lst in by_set.items():
        lst.sort()
        for km, route in lst[:top_k]:
            out.append((date, route, km))
    return out


def sp_solve_lp(dates, k_c, pool, timeout_s=60):
    """LP 松弛下界 (GLOP). 返回 (lb, duals) — duals={'store': u_c, 'date': w_d}."""
    from ortools.linear_solver import pywraplp
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return None, None
    x = {}
    for idx, (date, route, km) in enumerate(pool):
        x[idx] = solver.NumVar(0, 1, f"x{idx}")
    cons_date = {}
    for dd in dates:
        cols = [i for i, (date, _, _) in enumerate(pool) if date == dd]
        if not cols:
            return None, None
        cons_date[dd] = solver.Add(sum(x[i] for i in cols) == 1)
    cons_store = {}
    for c, k in k_c.items():
        cols = [i for i, (_, route, _) in enumerate(pool) if c in route]
        if cols:
            cons_store[c] = solver.Add(sum(x[i] for i in cols) == k)
    solver.Minimize(sum(pool[i][2] * x[i] for i in x))
    solver.SetTimeLimit(int(timeout_s * 1000))
    st = solver.Solve()
    if st not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return None, None
    duals = {"store": {c: cons_store[c].DualValue() for c in cons_store},
             "date": {dd: cons_date[dd].DualValue() for dd in cons_date}}
    return solver.Objective().Value(), duals


def price_columns(dates, k_c, duals, D, candidates_per_date=24, top_m=40, col_iter=60):
    """定价子问题 (启发式, 性能优化版).
    论文锚点: [ESF] §7.1 批量定价(col_iter) + 支配剪枝; 增量边算术 O(1) 插入增量.
    rc = km(r) - Σ_{c∈r} u_c - w_d  ([ESF] 式(8) 的集合划分版)."""
    u = duals["store"]; w = duals["date"]
    all_stores = sorted(k_c.keys(), key=lambda c: -u.get(c, 0.0))[:top_m]
    cands = []
    for dd in dates:
        w_d = w.get(dd, 0.0)
        for start_c in all_stores:
            if u.get(start_c, 0.0) <= 0:
                break  # 对偶降序: 起点奖品非正, 后续更差
            route = [start_c]
            in_day = {start_c}
            prize = u.get(start_c, 0.0)
            while True:
                best_c, best_margin, best_pos, best_delta = None, 1e-9, None, None
                for c in all_stores:
                    if c in in_day:
                        continue
                    uc = u.get(c, 0.0)
                    if uc <= best_margin:
                        break  # 对偶降序, 剪枝 ([ESF] dominance)
                    # O(1) 最优插入位: 开放链边算术
                    bd, bp = float("inf"), 0
                    prev = route[0]
                    bd, bp = D[c][prev], 0
                    for k in range(len(route) - 1):
                        d = D[route[k]][c] + D[c][route[k+1]] - D[route[k]][route[k+1]]
                        if d < bd:
                            bd, bp = d, k + 1
                    d_last = D[route[-1]][c]
                    if d_last < bd:
                        bd, bp = d_last, len(route)
                    margin = uc - bd
                    if margin > best_margin:
                        best_c, best_margin, best_pos, best_delta = c, margin, bp, bd
                if best_c is None:
                    break
                route.insert(best_pos, best_c)
                in_day.add(best_c)
            rc = day_km(route, D) - sum(u.get(c, 0.0) for c in route) - w_d
            if rc < -1e-6 and len(route) >= 2:
                cands.append((rc, dd, list(route), round(day_km(route, D), 3)))
    # 批量上限: 每轮只回灌最负的 col_iter 条 ([ESF] col_iter)
    cands.sort(key=lambda z: z[0])
    return [(dd, route, km) for rc, dd, route, km in cands[:col_iter]]




def column_generate(dates, k_c, pool, D, max_iter=12, tol=1e-4, verbose=False):
    """真列生成循环: LP -> 定价 -> 负约简成本列回灌 -> 迭代至收敛.
    终止: 对偶无新负列, 或 LP 下界连续 3 轮不动 ([ESF] 步骤7 gap 迭代同型).
    返回 (lp_lb, pool, iters, converged)."""
    pool = list(pool)
    converged = False
    iters = 0
    lb = None
    stall = 0
    for it in range(max_iter):
        iters = it + 1
        lb_new, duals = sp_solve_lp(dates, k_c, pool)
        if lb_new is None:
            break
        improved = (lb is None) or (lb_new > lb + 1e-3)
        lb = max(lb, lb_new) if lb is not None else lb_new
        new_cols = price_columns(dates, k_c, duals, D)
        before = len(pool)
        pool = dedupe_pool(pool + new_cols)
        added = len(pool) - before
        if verbose:
            log_cg(f"  CG iter {it+1}: lb={lb:.2f} 新列 {added} (定价候选 {len(new_cols)})")
        if not improved:
            stall += 1
        else:
            stall = 0
        if added == 0 or stall >= 3:
            converged = True
            break
    return lb, pool, iters, converged


def log_cg(msg):
    print(msg, flush=True)


def sp_solve_ip(dates, k_c, pool, timeout_s=120):
    """SP 整数精确解 (CP-SAT). 返回 (km, {date: route}) 或 (None, None)."""
    from ortools.sat.python import cp_model
    m = cp_model.CpModel()
    xv = {}
    for idx, (date, route, km) in enumerate(pool):
        xv[idx] = m.NewBoolVar(f"x{idx}")
    for dd in dates:
        cols = [i for i, (date, _, _) in enumerate(pool) if date == dd]
        if not cols:
            return None, None
        m.AddExactlyOne([xv[i] for i in cols])
    for c, k in k_c.items():
        cols = [i for i, (_, route, _) in enumerate(pool) if c in route]
        if cols:
            m.Add(sum(xv[i] for i in cols) == k)
    m.Minimize(sum(int(round(pool[i][2] * 1000)) * xv[i] for i in xv))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_s
    solver.parameters.num_search_workers = 4
    st = solver.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, None
    sel = {dd: None for dd in dates}
    for i, (date, route, km) in enumerate(pool):
        if solver.Value(xv[i]):
            cur = sel[date]
            if cur is None or km < cur[1]:
                sel[date] = (list(route), km)
    if any(v is None for v in sel.values()):
        return None, None
    return sum(v[1] for v in sel.values()), {dd: v[0] for dd, v in sel.items()}


@register
class SPMatheuristic(Algorithm):
    """对给定路线池做集合划分精确重组 (论文 [META] Alg.1/Alg.2 的 SP 组件).

    期望输入: pool = [(date, route_list, km), ...] (由运行器收集多算法/多种子路线).
    """
    name = "sp_matheuristic"

    def solve(self, data, D, time_budget=120, pool=None, rounds=2, sa_burst=6.0):
        assert pool, "SPMatheuristic 需要外部路线池"
        import numpy as np
        D = np.asarray(D)
        rng = random.Random(42)
        dates = list(data.dates)
        k_c = Counter(c for dd in dates for c in data.days_orig[dd])
        k_c = dict(k_c)
        pool = dedupe_pool(pool)
        t0 = time.time()

        # 真列生成: LP -> 对偶定价 -> 负约简成本列回灌 -> 迭代至收敛 ([ESF] 步骤2-3 启发式版)
        cg_time = min(time_budget * 0.6, 900)
        lb, pool, cg_iters, converged = column_generate(
            dates, k_c, pool, D, max_iter=15, verbose=True)

        best_km, best_days = sp_solve_ip(dates, k_c, pool,
                                         timeout_s=max(10, (t0 + time_budget - time.time()) * 0.5))
        if best_km is None:
            return AlgoResult(name=self.name, days={}, km=float("inf"), metadata={"error": "SP infeasible"})

        # 迭代精化 ([META] Alg.2): 冷 SA 打磨 SP 解 -> 新列回灌 -> 重解
        from algos.hgs_pvrp import _sa_improve
        history = [(best_km, "sp-round0")]
        for r in range(rounds):
            if time.time() - t0 > time_budget:
                break
            child = {dd: list(best_days[dd]) for dd in dates}
            _sa_improve(child, D, dates, rng,
                        min(t0 + time_budget, time.time() + sa_burst), hot=0.12)
            for dd in dates:
                pool.append((dd, list(child[dd]), day_km(child[dd], D)))
            pool = dedupe_pool(pool)
            km2, days2 = sp_solve_ip(dates, k_c, pool,
                                     timeout_s=max(10, (t0 + time_budget - time.time())))
            if km2 is not None and km2 < best_km - 1e-9:
                best_km, best_days = km2, days2
            history.append((best_km, f"sp-round{r+1}"))

        lb2, _ = sp_solve_lp(dates, k_c, pool)
        if lb2 is not None and lb is not None:
            lb = min(lb, lb2)
        return AlgoResult(name=self.name, days=best_days, km=best_km,
                          metadata={"lb": lb, "pool": len(pool),
                                    "gap_pct": round((best_km - lb) / best_km * 100, 2) if lb else None,
                                    "cg_iters": cg_iters, "cg_converged": converged,
                                    "history": history})
