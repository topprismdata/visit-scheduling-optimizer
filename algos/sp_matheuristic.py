# -*- coding: utf-8 -*-
"""SP/SC Matheuristic - 论文驱动的集合划分 + 对偶闭环列生成 (评审整改版 v3.1).

论文依据:
- Villegas et al. 2025 (OR Perspectives) [META]: SP 等式覆盖; 池内结构保证.
- Paradiso et al. 2020 (Operations Research) [ESF]: 列生成 + 受限主问题 + gap 收紧.

主问题: min Σ c_r x_r
        s.t. Σ_{r∈R_d} x_r = 1  ∀ 工作日 d
             Σ_{r∋c}   x_r = k_c ∀ 门店 c
             x_r ∈ {0,1}

业务约束:
- 双向作业走廊: min_daily ≤ |r| ≤ max_daily (列空间内生, 池与定价两处截断);
- R2' 星期几一致 (r2_prime=True): 每店全月只落一个星期几, 星期几本身可换
  (z[c,w]∈{0,1}, Σ_w z=1, 列绑定 x_i → z[c,wd(d)]);
- 认证口径 (评审 P1-1): 启发式定价 ⇒ 只输出受限主问题 rmp_lp 与池内差距
  pool_gap_pct, is_global_certified 恒 False.
"""
import time, random, datetime as _dt
from collections import Counter
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_capacity
from algos.registry import register


def log_cg(msg):
    print(msg, flush=True)


def _wd(date):
    return date.weekday() if hasattr(date, "weekday") else _dt.date.fromisoformat(str(date)).weekday()


def weekday_dates(dates):
    g = {}
    for dd in dates:
        g.setdefault(_wd(dd), []).append(dd)
    return g


def check_r2prime(days):
    """R2' 校验: 每店全月单一星期几. 返回违规店索引列表."""
    seen = {}
    for dd, seq in days.items():
        w = _wd(dd)
        for c in seq:
            seen.setdefault(c, set()).add(w)
    return [c for c, ws in seen.items() if len(ws) > 1]


def dedupe_pool(pool, top_k=6, max_daily=None, min_daily=None):
    """池去重/限宽/双向走廊门禁:
    1. 走廊过滤: 剔除 |r|>max_daily 或 |r|<min_daily 的非法列;
    2. 同 (date, 精确序列) 唯一; 3. 同 (date, 店集合) 保留 km 最小前 K 条."""
    if max_daily is not None and max_daily > 0:
        pool = [c for c in pool if len(c[1]) <= max_daily]
    if min_daily is not None and min_daily > 0:
        pool = [c for c in pool if len(c[1]) >= min_daily]
    seen_seq = set()
    by_set = {}
    for date, route, km in pool:
        key = (date, tuple(route))
        if key in seen_seq:
            continue
        seen_seq.add(key)
        by_set.setdefault((date, frozenset(route)), []).append((km, list(route)))
    out = []
    for (date, fset), lst in by_set.items():
        lst.sort()
        for km, route in lst[:top_k]:
            out.append((date, route, km))
    return out


def _z_open(k_c, wd_groups):
    """R2' 可行星期几集: 仅槽位数 ≥ f_c 的 w 对店 c 开放 (频次-槽位预剪枝)."""
    return {c: [w for w, ds in wd_groups.items() if f <= len(ds)] for c, f in k_c.items()}


def sp_solve_lp(dates, k_c, pool, timeout_s=60, r2_prime=False):
    """受限主问题 LP 值 (GLOP). 返回 (rmp_lp, duals) 或 (None, None)."""
    from ortools.linear_solver import pywraplp
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return None, None
    x = {i: solver.NumVar(0, 1, f"x{i}") for i in range(len(pool))}
    cons_date, cons_store = {}, {}
    for dd in dates:
        cols = [i for i, (date, _, _) in enumerate(pool) if date == dd]
        if not cols:
            return None, None
        cons_date[dd] = solver.Add(sum(x[i] for i in cols) == 1)
    for c, k in k_c.items():
        cols = [i for i, (_, route, _) in enumerate(pool) if c in route]
        if cols:
            cons_store[c] = solver.Add(sum(x[i] for i in cols) == k)
    z = {}
    if r2_prime:
        for c, ws in _z_open(k_c, weekday_dates(dates)).items():
            if not ws:
                return None, None
            zc = {w: solver.NumVar(0, 1, f"z_{c}_{w}") for w in ws}
            solver.Add(sum(zc.values()) == 1)
            z[c] = zc
        for i, (date, route, _) in enumerate(pool):
            w = _wd(date)
            for c in set(route):
                if c in z and w in z[c]:
                    solver.Add(x[i] - z[c][w] <= 0)
    solver.Minimize(sum(pool[i][2] * x[i] for i in x))
    solver.SetTimeLimit(int(timeout_s * 1000))
    st = solver.Solve()
    if st not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        return None, None
    duals = {"store": {c: cons_store[c].DualValue() for c in cons_store},
             "date": {dd: cons_date[dd].DualValue() for dd in cons_date}}
    return solver.Objective().Value(), duals


def price_columns(dates, k_c, duals, D, candidates_per_date=24, top_m=40, col_iter=60,
                  max_daily=None, min_daily=None):
    """定价子问题 (启发式, [ESF] §7.1 批量定价 + 支配剪枝 + 走廊硬截断).
    rc = km(r) - Σ u_c - w_d. 能力边界: 只报告"发现"的负列, 不证明不存在其他负列."""
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
                    break
                best_c, best_margin, best_pos = None, 1e-9, None
                for c in all_stores:
                    if c in in_day:
                        continue
                    uc = u.get(c, 0.0)
                    if uc <= best_margin:
                        break
                    bd, bp = D[c][route[0]], 0
                    for k in range(len(route) - 1):
                        dlt = D[route[k]][c] + D[c][route[k+1]] - D[route[k]][route[k+1]]
                        if dlt < bd:
                            bd, bp = dlt, k + 1
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
            lo = max(2, min_daily or 2)
            if rc < -1e-6 and len(route) >= lo:
                cands.append((rc, dd, list(route), round(day_km(route, D), 3)))
    cands.sort(key=lambda z0: z0[0])
    return [(dd, route, km) for rc, dd, route, km in cands[:col_iter]]


def column_generate(dates, k_c, pool, D, max_iter=12, verbose=False,
                    top_m=40, col_iter=60, max_daily=None, min_daily=None, r2_prime=False):
    """列生成循环: LP -> 定价 -> 负约简成本列回灌 -> 收敛.
    收敛判据 (评审 P1-1 修正): 最小化问题加列后 rmp_lp 单调【下降】; 连续 3 轮无下降或无新列即停."""
    pool = list(pool)
    converged = False
    iters = 0
    rmp_lp = None
    stall = 0
    for it in range(max_iter):
        iters = it + 1
        rmp_lp_new, duals = sp_solve_lp(dates, k_c, pool, r2_prime=r2_prime)
        if rmp_lp_new is None:
            break
        improved = (rmp_lp is None) or (rmp_lp - rmp_lp_new > 1e-3)
        rmp_lp = min(rmp_lp, rmp_lp_new) if rmp_lp is not None else rmp_lp_new
        new_cols = price_columns(dates, k_c, duals, D, top_m=top_m, col_iter=col_iter,
                                 max_daily=max_daily, min_daily=min_daily)
        before = len(pool)
        pool = dedupe_pool(pool + new_cols, max_daily=max_daily, min_daily=min_daily)
        added = len(pool) - before
        if verbose:
            log_cg(f"  CG iter {it+1}: rmp_lp={rmp_lp:.2f} 新列 {added} (定价候选 {len(new_cols)})")
        stall = 0 if improved else stall + 1
        if added == 0 or stall >= 3:
            converged = True
            break
    return rmp_lp, pool, iters, converged


def sp_solve_ip(dates, k_c, pool, timeout_s=120, r2_prime=False):
    """SP 整数精确解 (CP-SAT). r2_prime=True 时施加每店单一星期几硬约束."""
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
    if r2_prime:
        z = {}
        for c, ws in _z_open(k_c, weekday_dates(dates)).items():
            if not ws:
                return None, None
            zc = {w: m.NewBoolVar(f"z_{c}_{w}") for w in ws}
            m.AddExactlyOne(list(zc.values()))
            z[c] = zc
        for i, (date, route, _) in enumerate(pool):
            w = _wd(date)
            for c in set(route):
                if c in z and w in z[c]:
                    m.Add(xv[i] <= z[c][w])
    m.Minimize(sum(int(round(pool[i][2] * 1000)) * xv[i] for i in xv))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = timeout_s
    solver.parameters.num_search_workers = 8
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
    """SP + 对偶闭环列生成 (双向走廊 + 可选 R2' 星期几一致 + 池内差距口径)."""
    name = "sp_matheuristic"

    def solve(self, data, D, time_budget=120, pool=None, rounds=2, sa_burst=6.0,
              top_m=40, col_iter=60, max_daily=None, min_daily=None, r2_prime=False):
        assert pool, "SPMatheuristic 需要外部路线池"
        import numpy as np
        D = np.asarray(D)
        rng = random.Random(42)
        dates = list(data.dates)
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        max_daily = max_daily or getattr(data, 'max_daily_capacity', 0) or max(len(v) for v in data.days_orig.values())
        min_daily = min_daily or getattr(data, 'min_daily_capacity', 0) or min(len(v) for v in data.days_orig.values())

        pool = dedupe_pool(pool, max_daily=max_daily, min_daily=min_daily)
        t0 = time.time()

        rmp_lp, pool, cg_iters, converged = column_generate(
            dates, k_c, pool, D, max_iter=15, verbose=True, top_m=top_m, col_iter=col_iter,
            max_daily=max_daily, min_daily=min_daily, r2_prime=r2_prime)

        best_km, best_days = sp_solve_ip(dates, k_c, pool,
                                         timeout_s=max(10, (t0 + time_budget - time.time()) * 0.5),
                                         r2_prime=r2_prime)
        if best_km is None:
            return AlgoResult(name=self.name, days={}, km=float("inf"), capacity_ok=False,
                              metadata={"error": "SP infeasible (走廊/R2' 下无可行组合)",
                                        "r2_prime": r2_prime})

        from algos.hgs_pvrp import _sa_improve
        history = [(best_km, "sp-round0")]
        for r in range(rounds):
            if time.time() - t0 > time_budget:
                break
            child = {dd: list(best_days[dd]) for dd in dates}
            _sa_improve(child, D, dates, rng,
                        min(t0 + time_budget, time.time() + sa_burst), hot=0.12,
                        max_daily=max_daily, min_daily=min_daily)
            if not r2_prime or not check_r2prime(child):
                for dd in dates:
                    if min_daily <= len(child[dd]) <= max_daily:
                        pool.append((dd, list(child[dd]), round(day_km(child[dd], D), 3)))
                pool = dedupe_pool(pool, max_daily=max_daily, min_daily=min_daily)
                km2, days2 = sp_solve_ip(dates, k_c, pool,
                                         timeout_s=max(10, (t0 + time_budget - time.time())),
                                         r2_prime=r2_prime)
                if km2 is not None and km2 < best_km - 1e-9:
                    best_km, best_days = km2, days2
            history.append((best_km, f"sp-round{r+1}"))

        rmp_lp2, _ = sp_solve_lp(dates, k_c, pool, r2_prime=r2_prime)
        if rmp_lp2 is not None and rmp_lp is not None:
            rmp_lp = min(rmp_lp, rmp_lp2)

        cap_ok = check_capacity(best_days, max_daily, min_daily)
        r2_ok = (not r2_prime) or (len(check_r2prime(best_days)) == 0)
        pool_gap = round((best_km - rmp_lp) / best_km * 100, 2) if rmp_lp else None
        return AlgoResult(name=self.name, days=best_days, km=best_km,
                          capacity_ok=cap_ok,
                          metadata={"rmp_lp": rmp_lp, "lb": rmp_lp,   # 受限主问题 LP 值(非全局下界)
                                    "pool": len(pool),
                                    "min_daily": min_daily, "max_daily": max_daily,
                                    "r2_prime": r2_prime, "capacity_ok": cap_ok, "r2prime_ok": r2_ok,
                                    "pool_gap_pct": pool_gap, "gap_pct": pool_gap,
                                    "is_global_certified": False,
                                    "cg_iters": cg_iters, "cg_converged": converged,
                                    "history": history})
