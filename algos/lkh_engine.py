# -*- coding: utf-8 -*-
"""LKH engine (correct usage): ATSP + FULL_MATRIX + dummy depot (大常数C).
文档依据: LKH-3_PARAMETERS.pdf — FULL_MATRIX 对 TSP 只读下三角, 必须用 ATSP.
开放路径: 加 dummy 节点, 边权=大常数C (10*max), 解闭圈后剥离 dummy."""
import os, subprocess, tempfile

LKH_BIN = os.environ.get("LKH_BIN", "/tmp/LKH-3.0.14/LKH")


def lkh_open_path(stores, D, runs=10, max_trials=5000, cand=20, time_limit=240):
    """Solve open-path TSP over stores using LKH (ATSP).
    Returns ordered store indices.
    """
    m = len(stores)
    if m <= 3:
        return list(stores)
    n = m + 1
    M0 = max(max(row) for row in D)
    C = M0 * 10.0
    M = [[0.0] * n for _ in range(n)]
    for i in range(m):
        for j in range(m):
            if i != j:
                M[i][j] = float(D[stores[i]][stores[j]])
        M[i][m] = C
        M[m][i] = C
    with tempfile.TemporaryDirectory() as td:
        prob = os.path.join(td, "p.atsp")
        par = os.path.join(td, "p.par")
        out = os.path.join(td, "p.tour")
        with open(prob, "w") as f:
            f.write(f"NAME: gz\nTYPE: ATSP\nDIMENSION: {n}\nEDGE_WEIGHT_TYPE: EXPLICIT\nEDGE_WEIGHT_FORMAT: FULL_MATRIX\nEDGE_WEIGHT_SECTION\n")
            for row in M:
                f.write(" ".join("%.3f" % v for v in row) + "\n")
            f.write("EOF\n")
        with open(par, "w") as f:
            f.write(f"PROBLEM_FILE = {prob}\nTOUR_FILE = {out}\nRUNS = {runs}\nMAX_TRIALS = {max_trials}\nMAX_CANDIDATES = {cand}\nMOVE_TYPE = 5\nPATCHING_A = 2\nTOTAL_TIME_LIMIT = {time_limit}\n")
        try:
            subprocess.run([LKH_BIN, par], capture_output=True, text=True, timeout=time_limit + 15)
        except subprocess.TimeoutExpired:
            pass
        tour = []
        if os.path.exists(out):
            with open(out) as f:
                for line in f:
                    line = line.strip()
                    if line and line[0].isdigit():
                        tour.extend(int(x) for x in line.split())
        if not tour:
            return _nn2opt_fallback(stores, D)
        t0 = [v - 1 for v in tour]
        if m in t0:
            i = t0.index(m)
            path = t0[i + 1:] + t0[:i]
            return [stores[x] for x in path]
        return _nn2opt_fallback(stores, D)


def _nn2opt_fallback(stores, D):
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
