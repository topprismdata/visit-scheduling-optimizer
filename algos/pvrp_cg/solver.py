"""
Set-partitioning master with dual-guided column generation.

A column is a feasible day-group G ⊆ customers, with cost c(G) computed by
algos.pvrp_cg.travel. The master problem is:

    min Σ_{G, t} c(G) · λ_{G,t}
    s.t. coverage / interval / daily time cap
         Σ_G λ_{G,t} ≤ 1                (one column per day)
         Σ_{G∋i, t} λ_{G,t} = f_i      (every customer visited f_i times)
         x_{i,t} := Σ_{G∋i} λ_{G,t}
         interval: x_{i,t1} + x_{i,t2} ≤ 1  for t2 ∈ [t1+1, t1+Δ_i]

Algorithm
---------
1. Initial column pool P: singletons, NN pairs/triples/.../6-groups
   (top-K cheapest per seed), plus a Pass1 seed (CP-SAT ≤ 6/day + freq + interval).
2. REPEAT (≤ CG_ROUNDS):
   2a. LP-solve master with column pool P using pywraplp GLOP
       (variables continuous, integrality enforced only at the end).
   2b. For each (day t, seed customer s): greedily build S
       starting from {s}, adding j★ that maximizes
       π_{j,t} − [c(S ∪ {j}) − c(S)],
       while the marginal gain is > 1e-6 and |S| ≤ MAX_PER_DAY.
   2c. Add up to MAX_NEW_COLS most-negative-reduced-cost columns to P.
3. Final CP-SAT IP solve (300 s default) with the LP-rounded schedule
   as a solution hint.
4. (Optional) Workload-balancing re-assignment: keep day-groups, permute
   day indices, minimise max load. ≤ 60 s.

Return
------
  assigns[d] : list of customer indices visited on day d
  total_time : sum of column costs
  status     : CP-SAT status string
  stats      : {"n_columns", "lp_obj", "loads", "balanced"}
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import combinations

from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model

from .travel import hk_closed, hk_open, nn2opt_closed

INF = float("inf")
DAYS_DEFAULT = 20
MAX_PER_DAY = 6
NN_K = 10
TOP_GROUPS = 8
CG_ROUNDS = 8
MAX_NEW_COLS = 300
PASS1_TIME = 60
MIP_TIME = 300


# ---------------------------------------------------------------------------
# Column-cost oracle
# ---------------------------------------------------------------------------
def _col_cost_open(D: list[list[float]], idxs: Sequence[int]) -> float:
    if len(idxs) < 2:
        return 0.0
    sub = [[D[a][b] for b in idxs] for a in idxs]
    return hk_open(sub) if len(idxs) <= 9 else hk_open(sub)


def _col_cost_closed(D: list[list[float]], t0: Sequence[float], idxs: Sequence[int]) -> float:
    if not idxs:
        return 0.0
    if len(idxs) == 1:
        return 2 * t0[idxs[0]]
    sub = [[D[a][b] for b in idxs] for a in idxs]
    sd0 = [t0[a] for a in idxs]
    if len(idxs) <= 9:
        return hk_closed(sub, sd0)
    return nn2opt_closed(sub, sd0)


def _col_cost_time(T: list[list[float]], t0: Sequence[float],
                   svc: Sequence[float], idxs: Sequence[int]) -> float:
    if not idxs:
        return 0.0
    if len(idxs) == 1:
        return 2 * t0[idxs[0]] + svc[idxs[0]]
    sub = [[T[a][b] for b in idxs] for a in idxs]
    sd0 = [t0[a] for a in idxs]
    travel = hk_closed(sub, sd0) if len(idxs) <= 9 else nn2opt_closed(sub, sd0)
    return travel + sum(svc[a] for a in idxs)


# ---------------------------------------------------------------------------
# LP relaxation (GLOP) for dual extraction
# ---------------------------------------------------------------------------
def _lp_duals(pool: Sequence[frozenset], costs: Sequence[float], days: int,
              freq: Sequence[int], pool_idx: dict
              ) -> tuple[list | None, list | None, float | None, str]:
    """LP-solve master with column pool pool; return (pi, mu, lp_obj, status)."""
    n = len(freq)
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return None, None, None, "NO_SOLVER"

    w = {}
    for gi, _ in enumerate(pool):
        for d in range(days):
            w[gi, d] = solver.NumVar(0.0, 1.0, f"w{gi}_{d}")
    x = {}
    for i in range(n):
        for d in range(days):
            x[i, d] = solver.NumVar(0.0, 1.0, f"x{i}_{d}")

    day_cons = [solver.Add(sum(w[gi, d] for gi in range(len(pool))) <= 1.0) for d in range(days)]
    lcons = {}
    for i in range(n):
        for d in range(days):
            gs = [w[gi, d] for gi, g in enumerate(pool) if i in g]
            lcons[i, d] = solver.Add(sum(gs) - x[i, d] == 0.0)
    for i in range(n):
        solver.Add(sum(x[i, d] for d in range(days)) == freq[i])

    solver.Minimize(sum(costs[gi] * w[gi, d] for gi in range(len(pool)) for d in range(days)))
    st = solver.Solve()
    if st != pywraplp.Solver.OPTIMAL:
        return None, None, None, f"LP_{st}"

    mu = [day_cons[d].dual_value() for d in range(days)]
    pi = [[lcons[i, d].dual_value() for d in range(days)] for i in range(n)]
    return pi, mu, solver.Objective().Value(), "Optimal"


# ---------------------------------------------------------------------------
# Pricing: dual-guided greedy column construction
# ---------------------------------------------------------------------------
def _price_columns(pi: list, mu: list, D: list[list[float]], t0: Sequence[float],
                   days: int, n: int, col_cost_fn: Callable,
                   pool_set: set[frozenset], nbrs20: list[list[int]]
                   ) -> list[tuple[frozenset, float, float, int]]:
    """For each (day, seed), greedily build a set S with most-negative rc."""
    found: dict = {}
    for d in range(days):
        mud = mu[d] if mu else 0.0
        for seed in range(n):
            S = [seed]
            c_cur = col_cost_fn(S)
            total_pi = pi[seed][d]
            improved = True
            while improved and len(S) < MAX_PER_DAY:
                improved = False
                best_j, best_gain, best_c = None, -1e-9, c_cur
                for j in nbrs20[S[0]]:
                    if j in S:
                        continue
                    cand = sorted(S + [j])
                    c_new = col_cost_fn(cand)
                    gain = pi[j][d] - (c_new - c_cur)
                    if gain > best_gain:
                        best_gain, best_j, best_c = gain, j, c_new
                if best_j is not None and best_gain > 1e-6:
                    S = sorted(S + [best_j])
                    c_cur = best_c
                    total_pi += pi[best_j][d]
                    improved = True
            if len(S) >= 2:
                fs = frozenset(S)
                if fs in pool_set:
                    continue
                rc = c_cur - total_pi - mud
                if rc < -1e-4:
                    prev = found.get(fs)
                    if prev is None or rc < prev[1]:
                        found[fs] = (c_cur, rc, d)
    out = [(fs, v[0], v[1], v[2]) for fs, v in found.items()]
    out.sort(key=lambda t: t[2])
    return out


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------
def _init_pool(n: int, D, t0, col_cost_fn, freq, days,
               pool_set: set[frozenset], groups: dict):
    """Singletons + NN pairs/triples/.../6 groups (top-K cheapest per seed)."""
    for i in range(n):
        fs = frozenset([i])
        groups[fs] = col_cost_fn([i])
        pool_set.add(fs)
    nbrs = [sorted(range(n), key=lambda j: D[i][j])[1:NN_K + 1] for i in range(n)]
    for i in range(n):
        for j in nbrs[i]:
            fs = frozenset([i, j])
            if fs not in groups:
                groups[fs] = col_cost_fn(sorted(fs))
                pool_set.add(fs)
    for size in range(3, MAX_PER_DAY + 1):
        for i in range(n):
            cand = []
            pool_local = [i] + nbrs[i]
            if len(pool_local) < size:
                continue
            for combo in combinations(pool_local[1:], size - 1):
                fs = frozenset([i] + list(combo))
                if fs in groups:
                    continue
                cand.append((col_cost_fn(sorted(fs)), fs))
            cand.sort(key=lambda z: z[0])
            for cost, fs in cand[:TOP_GROUPS]:
                groups[fs] = cost
                pool_set.add(fs)


def _mip_solve(pool: Sequence[frozenset], costs: Sequence[float],
               freq: Sequence[int], days: int, col_cost_fn: Callable,
               hint: dict | None, time_limit: int = MIP_TIME,
               closed: bool = True, t0: Sequence[float] | None = None,
               daily_cap: float | None = None):
    """Final IP solve with the enriched column pool and a solution hint."""
    n = len(freq)
    m = cp_model.CpModel()
    w = {(gi, d): m.NewBoolVar(f"w{gi}_{d}") for gi in range(len(pool)) for d in range(days)}
    x = {(i, d): m.NewBoolVar(f"b{i}_{d}") for i in range(n) for d in range(days)}
    for d in range(days):
        m.Add(sum(w[gi, d] for gi in range(len(pool))) <= 1)
    for i in range(n):
        for d in range(days):
            gs = [gi for gi, g in enumerate(pool) if i in g]
            m.Add(sum(w[gi, d] for gi in gs) == x[i, d])
    for i in range(n):
        m.Add(sum(x[i, d] for d in range(days)) == freq[i])
    for i in range(n):
        if freq[i] >= 2:
            gap = max(1, days // (freq[i] + 1))
            for d1 in range(days):
                for d2 in range(d1 + 1, d1 + gap):
                    if d2 < days:
                        m.AddBoolOr([x[i, d1].Not(), x[i, d2].Not()])
    if daily_cap is not None and t0 is not None and closed:
        for d in range(days):
            m.Add(sum(int(costs[gi] * 100) * w[gi, d] for gi in range(len(pool))) <= int(daily_cap * 100))
    m.Minimize(sum(int(costs[gi] * 100) * w[gi, d] for gi in range(len(pool)) for d in range(days)))

    if hint:
        gidx = {g: gi for gi, g in enumerate(pool)}
        hints = {}
        for d in range(days):
            sd = hint.get(d)
            for gi in range(len(pool)):
                hints[w[gi, d]] = 0
            if sd is not None and sd in gidx:
                hints[w[gidx[sd], d]] = 1
            for i in range(n):
                hints[x[i, d]] = 1 if (sd and i in sd) else 0
        for var, val in hints.items():
            m.AddHint(var, val)

    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_workers = 8
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        assigns = [[] for _ in range(days)]
        for d in range(days):
            for gi, g in enumerate(pool):
                if s.Value(w[gi, d]):
                    assigns[d] = sorted(g)
        total = sum(col_cost_fn(a) for a in assigns if a)
        return assigns, total, str(s.StatusName(st))
    return None, float("inf"), str(s.StatusName(st))


def _balance(assigns: list[list], freq: Sequence[int], days: int,
             col_cost_fn: Callable, time_limit: int = 60) -> tuple[list, float, bool, list]:
    """Min-max day-load re-assignment (Nekooghadirli 2022)."""
    day_groups = [frozenset(a) for a in assigns if a]
    if not day_groups:
        return assigns, 0.0, False, []
    gcosts = {fs: col_cost_fn(list(fs)) for fs in day_groups}
    m = cp_model.CpModel()
    y = {}
    for k, _ in enumerate(day_groups):
        for d in range(days):
            y[k, d] = m.NewBoolVar(f"y{k}_{d}")
    for k in range(len(day_groups)):
        m.Add(sum(y[k, d] for d in range(days)) == 1)
    load = {}
    for d in range(days):
        load[d] = m.NewIntVar(0, 10_000_000, f"L{d}")
        m.Add(load[d] == sum(int(gcosts[fs] * 100) * y[k, d] for k, fs in enumerate(day_groups)))
    for i in range(len(freq)) if hasattr(freq, "__len__") else []:
        pass
    # interval constraints per customer
    # (re-derive from freq via the customer index; freq is passed in)
    for cust in range(len(freq)):
        if freq[cust] >= 2:
            gap = max(1, days // (freq[cust] + 1))
            ks_c = [k for k, fs in enumerate(day_groups) if cust in fs]
            if len(ks_c) >= 2:
                for d1 in range(days):
                    for d2 in range(d1 + 1, d1 + gap):
                        if d2 < days:
                            m.AddBoolOr([y[k, d1].Not() for k in ks_c] + [y[k, d2].Not() for k in ks_c])
    zmax = m.NewIntVar(0, 10_000_000, "zmax")
    for d in range(days):
        m.Add(zmax >= load[d])
    m.Minimize(zmax)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = time_limit
    s.parameters.num_workers = 8
    st = s.Solve(m)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        balanced = [[] for _ in range(days)]
        for d in range(days):
            for k, fs in enumerate(day_groups):
                if s.Value(y[k, d]):
                    balanced[d] = sorted(fs)
        return balanced, sum(gcosts[frozenset(a)] for a in balanced if a), True, [gcosts[frozenset(a)] for a in balanced if a]
    return assigns, sum(gcosts.values()), False, [gcosts[fs] for fs in day_groups]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def solve_distance_cg(n: int, D: list[list[float]], depot_idx: int,
                      freq: Sequence[int],
                      days: int = DAYS_DEFAULT,
                      time_limit: int = MIP_TIME,
                      verbose: bool = True
                      ) -> tuple[list | None, float, str, dict]:
    """Distance caliber: closed-loop route with depot commute."""
    global _GLOBAL
    _GLOBAL = {"D": D}
    t0 = [D[depot_idx][i] for i in range(n)]
    closed = True
    col_cost_fn = lambda ids: _col_cost_closed(D, t0, ids)
    return _solve_core(n, D, t0, freq, days, col_cost_fn, closed, t0,
                       daily_cap=None, time_limit=time_limit, verbose=verbose)


def solve_open_cg(n: int, D: list[list[float]],
                  freq: Sequence[int],
                  days: int = DAYS_DEFAULT,
                  time_limit: int = MIP_TIME,
                  verbose: bool = True
                  ) -> tuple[list | None, float, str, dict]:
    """Open-route caliber: customer chain only (no depot)."""
    _GLOBAL = {"D": D}
    t0 = [0.0] * n
    closed = False
    col_cost_fn = lambda ids: _col_cost_open(D, ids)
    return _solve_core(n, D, t0, freq, days, col_cost_fn, closed, t0,
                       daily_cap=None, time_limit=time_limit, verbose=verbose)


def solve_time_cg(n: int, T: list[list[float]], t0: Sequence[float],
                  svc: Sequence[float],
                  freq: Sequence[int],
                  days: int = DAYS_DEFAULT,
                  daily_cap: float = 540.0,
                  time_limit: int = MIP_TIME,
                  verbose: bool = True
                  ) -> tuple[list | None, float, str, dict]:
    """Time-calibrated caliber: calibrated travel + service + per-visit dwell."""
    D = T  # use T for pairwise short-circuit (T[i][j] already includes parking)
    col_cost_fn = lambda ids: _col_cost_time(T, t0, svc, ids)
    return _solve_core(n, D, t0, freq, days, col_cost_fn, True, t0,
                       daily_cap=daily_cap, time_limit=time_limit, verbose=verbose)


def _solve_core(n, D, t0, freq, days, col_cost_fn, closed, t0_vec,
                daily_cap, time_limit, verbose):
    # 1. Initial pool
    groups: dict = {}
    pool_set: set = set()
    _init_pool(n, D, t0, col_cost_fn, freq, days, pool_set, groups)
    # 2. Pass1 seed (lightweight CP-SAT ≤ 6/day + freq + interval, with col-cost-aware tie-breaking)
    seed = _build_seed_cp_sat(n, days, freq, col_cost_fn, t0_vec if closed else None, closed)
    for d, sd in seed.items():
        groups[sd] = col_cost_fn(sorted(sd))
        pool_set.add(sd)

    # 3. CG loop
    pool_list = list(groups.keys())
    pool_cost = [groups[g] for g in pool_list]
    lp_final = None
    for rnd in range(CG_ROUNDS):
        pi, mu, lp_obj, st = _lp_duals(pool_list, pool_cost, days, freq, {})
        if pi is None or mu is None:
            break
        lp_final = lp_obj
        nbrs20 = [sorted(range(n), key=lambda j: D[i][j])[1:19] for i in range(n)]
        new_cols = _price_columns(pi, mu, D, t0_vec, days, n, col_cost_fn, pool_set, nbrs20)
        if not new_cols:
            if verbose:
                print(f"  CG{rnd}: LP收敛 {lp_obj:.0f}", flush=True)
            break
        added = 0
        for fs, c, rc, d in sorted(new_cols, key=lambda t: t[2])[:MAX_NEW_COLS]:
            groups[fs] = c
            pool_set.add(fs)
            added += 1
        pool_list = list(groups.keys())
        pool_cost = [groups[g] for g in pool_list]
        if verbose:
            print(f"  CG{rnd}: +{added}列, 池={len(pool_list)}, LP={lp_obj:.0f}", flush=True)

    # 4. Final MIP
    assigns, total, status = _mip_solve(pool_list, pool_cost, freq, days,
                                       col_cost_fn, hint=seed,
                                       time_limit=time_limit, closed=closed,
                                       t0=t0_vec, daily_cap=daily_cap)
    stats = {"n_columns": len(pool_list), "lp_obj": lp_final, "balanced": False}
    if assigns is None:
        return None, float("inf"), status, stats

    # 5. Balance re-assignment
    if daily_cap is not None:
        b_assigns, b_total, balanced, loads = _balance(assigns, freq, days, col_cost_fn)
        stats["balanced"] = balanced
        stats["loads"] = loads
        if balanced:
            return b_assigns, b_total, status, stats
    stats["loads"] = [col_cost_fn(a) for a in assigns if a]
    return assigns, total, status, stats


def _build_seed_cp_sat(n, days, freq, col_cost_fn, t0, closed):
    """Build a feasible seed schedule via CP-SAT (≤ 6/day, freq, interval)."""
    m = cp_model.CpModel()
    x = {(i, d): m.NewBoolVar(f"a{i}_{d}") for i in range(n) for d in range(days)}
    for i in range(n):
        m.Add(sum(x[i, d] for d in range(days)) == freq[i])
    for d in range(days):
        m.Add(sum(x[i, d] for i in range(n)) <= MAX_PER_DAY)
    for i in range(n):
        if freq[i] >= 2:
            gap = max(1, days // (freq[i] + 1))
            for d1 in range(days):
                for d2 in range(d1 + 1, d1 + gap):
                    if d2 < days:
                        m.AddBoolOr([x[i, d1].Not(), x[i, d2].Not()])
    # Light proxy: minimize sum of singleton col-cost × x
    terms = []
    for i in range(n):
        c = int(col_cost_fn([i]) * 100)
        for d in range(days):
            terms.append(c * x[i, d])
    m.Minimize(sum(terms) if terms else 0)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = PASS1_TIME
    s.parameters.num_workers = 8
    if s.Solve(m) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {}
    seed = {}
    for d in range(days):
        sd = frozenset(i for i in range(n) if s.Value(x[i, d]))
        if sd:
            seed[d] = sd
    return seed
