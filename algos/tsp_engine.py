# -*- coding: utf-8 -*-
"""TSP engine: CP-SAT exact + NN2opt heuristic. 换内核不改模型.

求解凭证契约 (Review P2-5): 暴露 solve_status 区分
OPTIMAL (数学证明全局最优) / FEASIBLE (限时内找到可行解, 未证明) / HEURISTIC (求解失败回退启发式).
"""
import numpy as np
from ortools.sat.python import cp_model
def _exact_open_tsp_status(stores, D, time_limit=120):
    """CP-SAT exact open TSP (dummy depot, AddCircuit).
    返回 (route, status, elapsed_ms):
      status ∈ {'OPTIMAL', 'FEASIBLE', 'HEURISTIC_FALLBACK', 'TRIVIAL'}
    """
    import time
    m = len(stores)
    if m <= 3:
        return list(stores), 'TRIVIAL', 0.0
    t0 = time.perf_counter()
    n = m + 1
    model = cp_model.CpModel()
    arcs = []
    for i in range(m):
        for j in range(m):
            if i != j: arcs.append((i, j, model.NewBoolVar(f'x{i}_{j}')))
    for i in range(m):
        arcs.append((i, m, model.NewBoolVar(f'd{i}')))
        arcs.append((m, i, model.NewBoolVar(f'e{i}')))
    out = {v: [] for v in range(n)}; inn = {v: [] for v in range(n)}
    for (i, j, v) in arcs: out[i].append(v); inn[j].append(v)
    for v in range(n):
        model.Add(sum(out[v]) == 1); model.Add(sum(inn[v]) == 1)
    x = {(i, j): v for (i, j, v) in arcs if i < n and j < n}
    obj = sum(float(D[stores[i]][stores[j]]) * x[(i, j)] for i in range(m) for j in range(m) if i != j)
    model.AddCircuit(arcs)
    model.Minimize(obj)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    st = solver.Solve(model)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    if st == cp_model.OPTIMAL:
        status = 'OPTIMAL'
    elif st == cp_model.FEASIBLE:
        status = 'FEASIBLE'
    else:
        return _nn2opt_open(stores, D), 'HEURISTIC_FALLBACK', elapsed_ms
    tour = [m]  # start at dummy
    for _ in range(n):
        for (i, j, v) in arcs:
            if i == tour[-1] and solver.Value(v):
                tour.append(j); break
    tour = tour[:-1]  # remove last back to dummy
    i = tour.index(m)
    path = tour[i+1:] + tour[:i]
    return [stores[v] for v in path], status, round(elapsed_ms, 2)

def _exact_open_tsp(stores, D, time_limit=120):
    """向后兼容: 仅返回路线 (内部委托 _exact_open_tsp_status)."""
    route, _status, _ms = _exact_open_tsp_status(stores, D, time_limit)
    return route

def _nn2opt_open(stores, D):
    seq = list(stores); n = len(seq)
    if n <= 3: return seq
    unv = set(range(1, n)); out = [0]
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: D[seq[l]][seq[j]])); unv.discard(out[-1])
    route = [seq[t] for t in out]
    for _ in range(30):
        imp = False
        for a in range(1, n - 2):
            for b in range(a + 1, n - 1):
                if D[route[a-1]][route[b]] + D[route[a]][route[b+1]] < D[route[a-1]][route[a]] + D[route[b]][route[b+1]] - 1e-9:
                    route[a:b+1] = route[a:b+1][::-1]; imp = True
        if not imp: break
    return route

class TSPEngine:
    name = "base"
    def solve(self, stores, D): raise NotImplementedError

class ExactTSPEngine(TSPEngine):
    name = "cpsat"
    def __init__(self, tl=180): self.tl = tl
    def solve(self, stores, D): return _exact_open_tsp(stores, D, self.tl)

class NN2OptEngine(TSPEngine):
    name = "nn2opt"
    def solve(self, stores, D): return _nn2opt_open(stores, D)

ENGINES = {"nn2opt": NN2OptEngine, "cpsat": ExactTSPEngine}
def get_engine(name="cpsat", **kw): return ENGINES[name](**kw)
