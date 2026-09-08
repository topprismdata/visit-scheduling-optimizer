# -*- coding: utf-8 -*-
"""pricing_benchmark/v1 — 5 种定价 oracle 在真实规模上的对照.

设计: docs/design/ESPPRC_PRICING_DESIGN_v0.4.md §2
流程: 每线取 bp 根节点 LP 对偶(真实对偶, 非合成) -> 选 3 个最难日期 ->
      5 oracle 同实例对照 (贪心 / CP-SAT / exact-ESPPRC / ng-route / 2-cycle).
指标: min rc / 证明状态 / 耗时 / 标签数 / pricing gap.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algos.branch_and_price import BranchAndPrice, _BPNode
from core.contract import contract_of, legal_date_map
from core.metric import day_km
from data.loader import load_line, load_plan

SCHEMA = "pricing_benchmark/v1"
OUT_DIR = ROOT / "output" / "pricing_benchmark" / "v1"
EPS = 1e-6


# ---------------------------------------------------------------------------
# 对偶获取: bp 根节点 LP (真实对偶, 非合成)
# ---------------------------------------------------------------------------

def get_duals(line_id):
    plan = load_plan()
    data = load_line(plan, line_id)
    Dm = np.load(ROOT / "output" / f"road_dist_{line_id}.npy")
    D = [[float(v) for v in row] for row in Dm]
    dates = sorted(data.days_orig.keys())
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    bp = BranchAndPrice(
        dates, k_c, D, contracts, data.days_orig,
        data.min_daily_capacity, data.max_daily_capacity,
        time_budget=60.0, max_nodes=1, exact_pricing=False,
        initial_days=None)   # None 才会触发日历搜索+伪对偶扰动 (真实 CG 环境)
    lp = bp._solve_node_lp(_BPNode())
    if lp is None:
        raise RuntimeError(f"line {line_id}: root LP failed")
    legal = legal_date_map(contracts, dates)
    stores = sorted(k_c.keys())
    return data, D, dates, legal, stores, lp["duals"]


def get_mid_cg_duals(line_id, rounds=4):
    """v2 对偶源: 真实 CG 迭代中段的对偶 (根 warm-start LP 对偶在多线上退化为零).

    逐轮 solve_lp → price_heuristic → add_columns, 捕获每轮对偶;
    返回 link-dual 质量最大的一轮 (非退化且具代表性).
    """
    plan = load_plan()
    data = load_line(plan, line_id)
    Dm = np.load(ROOT / "output" / f"road_dist_{line_id}.npy")
    D = [[float(v) for v in row] for row in Dm]
    dates = sorted(data.days_orig.keys())
    contracts = contract_of(data.days_orig, dates)
    k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
    bp = BranchAndPrice(
        dates, k_c, D, contracts, data.days_orig,
        data.min_daily_capacity, data.max_daily_capacity,
        time_budget=120.0, max_nodes=1, exact_pricing=False,
        initial_days=None)   # None 才会触发日历搜索+伪对偶扰动
    node = _BPNode()
    best = None
    for r in range(rounds):
        lp = bp._solve_node_lp(node)
        if lp is None:
            break
        duals = lp["duals"]
        mass = sum(max(0.0, -v) for v in duals["link"].values())  # reward = -link_dual
        if best is None or mass > best[0]:
            best = (mass, r, duals)
        cols = bp._price_heuristic(node, duals)
        if not cols or bp.add_columns(cols, source="HEURISTIC") == 0:
            break
    if best is None:
        raise RuntimeError(f"line {line_id}: mid-CG duals failed")
    legal = legal_date_map(contracts, dates)
    stores = sorted(k_c.keys())
    print(f"  [duals] line {line_id}: round {best[1]}, link mass {best[0]:.1f}")
    return data, D, dates, legal, stores, best[2]


# ---------------------------------------------------------------------------
# 最难日期选择: max(店数 + dual 质量/10 + dual 熵×10)
# ---------------------------------------------------------------------------

def pick_worst_dates(stores, dates, legal, duals, k=3):
    link = duals["link"]
    scored = []
    for dd in dates:
        elig = [c for c in stores if dd in legal.get(c, ())]
        if len(elig) < 2:
            continue
        pos = [-link.get((c, dd), 0.0) for c in elig]
        pos = [p for p in pos if p > 0]
        mass = sum(pos)
        ent = 0.0
        if mass > 0 and len(pos) > 1:
            ps = [p / mass for p in pos]
            ent = -sum(p * math.log(p) for p in ps)
        scored.append((len(elig) + mass / 10.0 + ent * 10.0, dd, len(elig), round(mass, 1), round(ent, 3)))
    scored.sort(reverse=True)
    return [(dd, n, m, e) for _, dd, n, m, e in scored[:k]]


# ---------------------------------------------------------------------------
# Oracle 1: 贪心 (插入式, 与 _price_heuristic 同构, 单日)
# ---------------------------------------------------------------------------

def oracle_greedy(elig, u, D, min_daily, max_daily, wdd=0.0):
    t0 = time.perf_counter()
    order = sorted(elig, key=lambda c: -u[c])
    best = (0.0, None)
    for start in order[:40]:
        route = [start]
        in_day = {start}
        while len(route) < max_daily:
            best_c, best_margin, best_pos = None, EPS, None
            for c in order[:60]:
                if c in in_day:
                    continue
                if u[c] <= best_margin:
                    break
                bd, bpos = D[c][route[0]], 0
                for k in range(len(route) - 1):
                    dlt = D[route[k]][c] + D[c][route[k + 1]] - D[route[k]][route[k + 1]]
                    if dlt < bd:
                        bd, bpos = dlt, k + 1
                if D[route[-1]][c] < bd:
                    bd, bpos = D[route[-1]][c], len(route)
                margin = u[c] - bd
                if margin > best_margin:
                    best_c, best_margin, best_pos = c, margin, bpos
            if best_c is None:
                break
            route.insert(best_pos, best_c)
            in_day.add(best_c)
        if len(route) >= max(2, min_daily):
            rc = day_km(route, D) - sum(u[c] for c in route) - wdd
            if rc < best[0]:
                best = (rc, list(route))
    return {"status": "FEASIBLE", "min_rc": best[0] if best[1] else None,
            "route": best[1], "sec": round(time.perf_counter() - t0, 3)}


# ---------------------------------------------------------------------------
# Oracle 2: CP-SAT AddCircuit (单日)
# ---------------------------------------------------------------------------

def oracle_cpsat(elig, u, D, min_daily, max_daily, wdd, tl=60.0):
    from ortools.sat.python import cp_model
    t0 = time.perf_counter()
    n = len(elig)
    if n < max(2, min_daily):
        return {"status": "SKIP", "min_rc": None, "route": None, "sec": 0.0}
    dummy = n
    m = cp_model.CpModel()
    visit = [m.NewBoolVar(f"v{i}") for i in range(n)]
    arcs = [(i, i, m.NewBoolVar(f"s{i}")) for i in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                arcs.append((i, j, m.NewBoolVar(f"a{i}_{j}")))
    for i in range(n):
        arcs.append((i, dummy, m.NewBoolVar(f"d{i}")))
        arcs.append((dummy, i, m.NewBoolVar(f"e{i}")))
    m.AddCircuit(arcs)
    for i in range(n):
        m.Add(visit[i] + arcs[i][2] == 1)
    m.Add(sum(visit) >= max(2, min_daily))
    m.Add(sum(visit) <= max_daily)
    obj = sum(float(D[elig[i]][elig[j]]) * v for (i, j, v) in arcs if i < n and j < n)
    obj -= sum(float(u[elig[i]]) * visit[i] for i in range(n))
    obj -= wdd
    m.Minimize(obj)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = tl
    solver.parameters.num_search_workers = 2
    st = solver.Solve(m)
    sec = time.perf_counter() - t0
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "SKIP", "min_rc": None, "route": None, "sec": round(sec, 3)}
    succ = {i: j for (i, j, v) in arcs if i != j and solver.Value(v)}
    route, cur = [], succ[dummy]
    while cur != dummy:
        route.append(elig[cur])
        cur = succ[cur]
    return {"status": "PROVEN" if st == cp_model.OPTIMAL else "FEASIBLE",
            "min_rc": round(solver.ObjectiveValue(), 4), "route": route,
            "sec": round(sec, 3)}


# ---------------------------------------------------------------------------
# Oracle 3/4/5: labeling 家族 (exact ESPPRC / ng-route / 2-cycle)
# label = (cost, mask, prev); cost = 累计km - 累计u (不含 wdd 常数)
# ---------------------------------------------------------------------------

def oracle_labeling(mode, elig, u, D, min_daily, max_daily, wdd,
                    tl=180.0, max_labels=500_000, ng_delta=8, bucket_cap=1000):
    t0 = time.perf_counter()
    n = len(elig)
    if n < max(2, min_daily):
        return {"status": "SKIP", "min_rc_raw": None, "min_rc": None, "sec": 0.0,
                "labels": 0, "dom_pruned": 0}
    uarr = [u[c] for c in elig]
    Dl = [[D[elig[i]][elig[j]] for j in range(n)] for i in range(n)]

    ng_masks = None
    if mode == "ng":
        ng_masks = []
        for i in range(n):
            order = sorted((j for j in range(n) if j != i), key=lambda j: Dl[i][j])
            mask = 0
            for j in order[:ng_delta]:
                mask |= 1 << j
            ng_masks.append(mask)

    min_len = max(2, min_daily)
    # 支配只在同 (last, cnt) 桶内: min_len 约束下跨深度支配不 sound
    # (单店标签复制同后缀会比被支配标签少 1 店, 可能跌破 min_len)。
    labels = {}   # (last, cnt) -> list[(cost, mask, prev)]
    best_rc = float("inf")
    n_gen = n
    n_dom = 0
    truncated = False
    deadline = t0 + tl
    for i in range(n):
        labels[(i, 1)] = [(-uarr[i], 1 << i, -1)]
    frontier = [(i, 1) for i in range(n)]
    while frontier and not truncated:
        if time.perf_counter() > deadline or n_gen > max_labels:
            truncated = True
            break
        new_frontier = []
        for key in frontier:
            last = key[0]
            cnt0 = key[1]
            for (cost, mask, prev) in list(labels[key]):
                if time.perf_counter() > deadline or n_gen > max_labels:
                    truncated = True
                    break
                for j in range(n):
                    if mode == "2cycle":
                        if j == prev:
                            continue
                    else:
                        if mask >> j & 1:
                            continue
                    ncost = cost + Dl[last][j] - uarr[j]
                    if mode == "ng":
                        nmask = (mask & ng_masks[j]) | (1 << j)
                        cnt = bin(mask).count("1") + 1
                    else:
                        nmask = mask | (1 << j)
                        cnt = bin(nmask).count("1")
                    if cnt > max_daily:
                        continue
                    n_gen += 1
                    if cnt >= min_len and ncost < best_rc:
                        best_rc = ncost   # raw = km - Σu; 负列判定另减 wdd
                    bucket = labels.setdefault((j, cnt), [])
                    dominated = False
                    for (c2, m2, _p2) in bucket:
                        if c2 <= ncost and (m2 & nmask) == m2:
                            dominated = True
                            break
                    if dominated:
                        n_dom += 1
                        continue
                    keep = []
                    for (c2, m2, p2) in bucket:
                        if ncost <= c2 and (nmask & m2) == nmask:
                            n_dom += 1
                            continue
                        keep.append((c2, m2, p2))
                    keep.append((ncost, nmask, last if mode == "2cycle" else -1))
                    if len(keep) > bucket_cap:
                        keep.sort()
                        keep = keep[:bucket_cap // 2]
                    labels[(j, cnt)] = keep
                    new_frontier.append((j, cnt))
                if truncated:
                    break
        frontier = list(dict.fromkeys(new_frontier))

    sec = time.perf_counter() - t0
    status = ("TIMEOUT_CAPPED" if truncated else "PROVEN") if mode == "exact" else \
             ("TIMEOUT_CAPPED" if truncated else "EXHAUSTED")
    finite = math.isfinite(best_rc)
    min_rc = round(best_rc - wdd, 4) if finite else None
    return {"status": status, "min_rc_raw": round(best_rc, 4) if finite else None,
            "min_rc": min_rc, "has_negative": bool(finite and min_rc < -1e-6),
            "sec": round(sec, 2), "labels": n_gen, "dom_pruned": n_dom}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_line(line_id, cpsat_tl, label_tl, getf=None):
    data, D, dates, legal, stores, duals = (getf or get_duals)(line_id)
    worst = pick_worst_dates(stores, dates, legal, duals, k=3)
    results = {"schema": SCHEMA, "line": line_id,
               "dates": [{"date": str(dd), "n_eligible": n, "dual_mass": m, "dual_entropy": e}
                         for dd, n, m, e in worst],
               "cells": {}}
    for dd, n_elig, _m, _e in worst:
        link = duals["link"]
        wd = duals["date"].get(dd, 0.0)
        u = {c: -link.get((c, dd), 0.0) for c in stores if dd in legal.get(c, ())}
        elig = sorted(u.keys())
        cell = {"n_eligible": len(elig), "wdd": round(wd, 4)}
        cell["greedy"] = oracle_greedy(elig, u, D, data.min_daily_capacity, data.max_daily_capacity, wd)
        cell["cpsat"] = oracle_cpsat(elig, u, D, data.min_daily_capacity, data.max_daily_capacity, wd, tl=cpsat_tl)
        for mode, delta in (("exact", 0), ("ng", 8), ("ng", 16), ("2cycle", 0)):
            key = f"{mode}{delta}"
            cell[key] = oracle_labeling(mode, elig, u, D, data.min_daily_capacity,
                                        data.max_daily_capacity, wd, tl=label_tl, ng_delta=delta or 8)
        results["cells"][str(dd)] = cell
        summ = {k: (v.get("min_rc"), v.get("status")) for k, v in cell.items()
                if isinstance(v, dict)}
        print(f"  [{line_id}] {dd} n={len(elig)}: {summ}", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", default="09,02,11")
    ap.add_argument("--cpsat-tl", type=float, default=60.0)
    ap.add_argument("--label-tl", type=float, default=180.0)
    ap.add_argument("--mid-cg", action="store_true",
                    help="v2: 用真实 CG 中段对偶 (根 LP 对偶退化时必需)")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for lid in args.lines.split(","):
        print(f"=== line {lid} ===", flush=True)
        getf = get_mid_cg_duals if args.mid_cg else get_duals
        r = run_line(lid, args.cpsat_tl, args.label_tl, getf)
        (OUT_DIR / f"{lid}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        print(f"  saved {OUT_DIR / (lid + '.json')}", flush=True)


if __name__ == "__main__":
    main()
