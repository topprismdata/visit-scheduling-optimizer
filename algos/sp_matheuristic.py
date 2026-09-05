# -*- coding: utf-8 -*-
"""SP/SC Matheuristic - 论文驱动的集合划分 + 列生成 (带业务单日容量硬约束).

论文依据:
- Villegas et al. 2025 (OR Perspectives) [META]: SP 等式覆盖; 结构保证不劣于池内最优.
- Paradiso et al. 2020 (Operations Research) [ESF]: 列生成 + 受限主问题 + gap 收紧.

业务约束:
- 单日容量硬约束: 列空间 R_d 只包含 len(route) <= max_daily 的合法物理日计划,
  定价子问题在 len(route) == max_daily 时强制截断.
"""
import time, json, random
from collections import Counter
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_capacity
from algos.registry import register


def log_cg(msg):
    print(msg, flush=True)


def dedupe_pool(pool, top_k=6, max_daily=None, min_daily=None):
    """池去重/限宽/双向容量门禁: 
    1. 物理走廊过滤: 严格剔除 len(route) > max_daily 或 < min_daily 的非法列;
    2. 同 (date, 精确序列) 唯一;
    3. 同 (date, 店集合) 保留 km 最小前 K 条.
    """
    if max_daily is not None and max_daily > 0:
        pool = [c for c in pool if len(c[1]) <= max_daily]
    if min_daily is not None and min_daily > 0:
        pool = [c for c in pool if len(c[1]) >= min_daily]
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


def price_columns(dates, k_c, duals, D, candidates_per_date=24, top_m=40, col_iter=60, max_daily=None, min_daily=None):
    """定价子问题 (启发式, [ESF] §7.1 批量定价 + 支配剪枝 + 容量硬截断).
    rc = km(r) - Σ_{c∈r} u_c - w_d  ([ESF] 式(8) 集合划分版). 
    约束: len(route) <= max_daily, 到达上限时自动停止添加门店.
    """
    u = duals["store"]; w = duals["date"]
    all_stores = sorted(k_c.keys(), key=lambda c: -u.get(c, 0.0))[:top_m]
    cands = []
    for dd in dates:
        w_d = w.get(dd, 0.0)
        for start_c in all_stores:
            if u.get(start_c, 0.0) <= 0:
                break
            route = [start_c]
            in_day = {start_c}
            while True:
                if max_daily is not None and len(route) >= max_daily:
                    break  # 到达业务单日容量红线, 严禁继续塞店
                best_c, best_margin, best_pos = None, 1e-9, None
                for c in all_stores:
                    if c in in_day:
                        continue
                    uc = u.get(c, 0.0)
                    if uc <= best_margin:
                        break  # 对偶降序, 剪枝
                    bd, bp = D[c][route[0]], 0
                    for k in range(len(route) - 1):
                        d = D[route[k]][c] + D[c][route[k+1]] - D[route[k]][route[k+1]]
                        if d < bd:
                            bd, bp = d, k + 1
                    d_last = D[route[-1]][c]
                    if d_last < bd:
                        bd, bp = d_last, len(route)
                    margin = uc - bd
                    if margin > best_margin:
                        best_c, best_margin, best_pos = c, margin, bp
                if best_c is None:
                    break
                route.insert(best_pos, best_c)
                in_day.add(best_c)
            rc = day_km(route, D) - sum(u.get(c, 0.0) for c in route) - w_d
            min_len = max(2, min_daily if min_daily is not None else 2)
            if rc < -1e-6 and len(route) >= min_len:
                cands.append((rc, dd, list(route), round(day_km(route, D), 3)))
    cands.sort(key=lambda z: z[0])
    return [(dd, route, km) for rc, dd, route, km in cands[:col_iter]]


def column_generate(dates, k_c, pool, D, max_iter=12, verbose=False,
                    top_m=40, col_iter=60, max_daily=None, min_daily=None):
    """真列生成循环: LP -> 定价 -> 负约简成本列回灌 -> 迭代至收敛.
    保证生成的所有新列满足 len(route) <= max_daily.
    """
    pool = list(pool)
    converged = False
    iters = 0
    rmp_lp = None
    stall = 0
    for it in range(max_iter):
        iters = it + 1
        rmp_lp_new, duals = sp_solve_lp(dates, k_c, pool)
        if rmp_lp_new is None:
            break
        # 最小化问题: 回灌负约简成本列后, 主问题松弛解 rmp_lp 应当下降 (成本降低)
        improved = (rmp_lp is None) or (rmp_lp - rmp_lp_new > 1e-3)
        rmp_lp = min(rmp_lp, rmp_lp_new) if rmp_lp is not None else rmp_lp_new
        new_cols = price_columns(dates, k_c, duals, D, top_m=top_m, col_iter=col_iter, max_daily=max_daily, min_daily=min_daily)
        before = len(pool)
        pool = dedupe_pool(pool + new_cols, max_daily=max_daily, min_daily=min_daily)
        added = len(pool) - before
        if verbose:
            log_cg(f"  CG iter {it+1}: rmp_lp={rmp_lp:.2f} 新列 {added} (定价候选 {len(new_cols)})")
        if not improved:
            stall += 1
        else:
            stall = 0
        if added == 0 or stall >= 3:
            converged = True
            break
    return rmp_lp, pool, iters, converged

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
    """SP + 列生成 matheuristic (带业务单日容量硬门禁)."""
    name = "sp_matheuristic"

    def solve(self, data, D, time_budget=120, pool=None, rounds=2, sa_burst=6.0,
              top_m=40, col_iter=60, max_daily=None, min_daily=None):
        assert pool, "SPMatheuristic 需要外部路线池"
        import numpy as np
        D = np.asarray(D)
        rng = random.Random(42)
        dates = list(data.dates)
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        min_daily = min_daily or getattr(data, 'min_daily_capacity', 0) or min(len(v) for v in data.days_orig.values())
        max_daily = max_daily or getattr(data, 'max_daily_capacity', 0) or max(len(v) for v in data.days_orig.values())
        
        # 1. 物理容量前置过滤: 严格剔除不在 [min_daily, max_daily] 走廊内的非法列
        pool = dedupe_pool(pool, max_daily=max_daily, min_daily=min_daily)
        t0 = time.time()

        # 2. 真列生成: LP -> 对偶定价 (带容量截断) -> 负约简成本列回灌 -> 收敛
        rmp_lp, pool, cg_iters, converged = column_generate(
            dates, k_c, pool, D, max_iter=15, verbose=True, top_m=top_m, col_iter=col_iter, max_daily=max_daily, min_daily=min_daily)
        best_km, best_days = sp_solve_ip(dates, k_c, pool,
                                         timeout_s=max(10, (t0 + time_budget - time.time()) * 0.5))
        if best_km is None:
            return AlgoResult(name=self.name, days={}, km=float("inf"), metadata={"error": "SP infeasible"})

        # 3. 迭代精化: 冷 SA 打磨 (带容量硬门禁) -> 新列回灌 -> 重解
        from algos.hgs_pvrp import _sa_improve
        history = [(best_km, "sp-round0")]
        for r in range(rounds):
            if time.time() - t0 > time_budget:
                break
            child = {dd: list(best_days[dd]) for dd in dates}
            _sa_improve(child, D, dates, rng,
                        min(t0 + time_budget, time.time() + sa_burst), hot=0.12, max_daily=max_daily, min_daily=min_daily)
            for dd in dates:
                if min_daily <= len(child[dd]) <= max_daily:
                    pool.append((dd, list(child[dd]), day_km(child[dd], D)))
            pool = dedupe_pool(pool, max_daily=max_daily, min_daily=min_daily)
            km2, days2 = sp_solve_ip(dates, k_c, pool,
                                     timeout_s=max(10, (t0 + time_budget - time.time())))
            if km2 is not None and km2 < best_km - 1e-9:
                best_km, best_days = km2, days2
            history.append((best_km, f"sp-round{r+1}"))

        rmp_lp2, _ = sp_solve_lp(dates, k_c, pool)
        if rmp_lp2 is not None and rmp_lp is not None:
            rmp_lp = min(rmp_lp, rmp_lp2)
            
        cap_ok = check_capacity(best_days, max_daily, min_daily)
        pool_gap = round((best_km - rmp_lp) / best_km * 100, 2) if rmp_lp else None
        return AlgoResult(name=self.name, days=best_days, km=best_km,
                          capacity_ok=cap_ok,
                          metadata={"rmp_lp": rmp_lp, "lb": rmp_lp,  # 受限路线池 LP 松弛值 (非无条件全局下界)
                                    "pool": len(pool),
                                    "min_daily": min_daily, "max_daily": max_daily, "capacity_ok": cap_ok,
                                    "pool_gap_pct": pool_gap, "gap_pct": pool_gap,  # 受限池内整型差距
                                    "is_global_certified": False,  # 启发式定价无法保证全局无遗漏负列
                                    "cg_iters": cg_iters, "cg_converged": converged,
                                    "history": history})
