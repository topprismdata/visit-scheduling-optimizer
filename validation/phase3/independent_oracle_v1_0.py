"""
independent_oracle_v1_0.py — Phase 3.3-④ Artifact 2
GT-Small Exact Solver Oracle（独立实现——oracle 定义 v1_0 强制隔离）。
独立性: 独立变量命名空间 o_x_* / 独立求解参数(seed/workers) / 目标标量化独立推导 /
不 import mathopt_model_generator 任何模型/约束/目标代码。
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from ortools.sat.python import cp_model

OUT = Path(__file__).parent / "oracle_result_v1_0.json"

def oracle_targets(case):
    T = {t: [3 if False else (3 if t in ("T01","T02") else 4) for _ in (0,)][0] for t in ()}
    base = {
        "T01": dict(lo=4, hi=4, s=60, gmin=3, gmax=6, v=0.0),
        "T02": dict(lo=4, hi=4, s=60, gmin=3, gmax=6, v=0.0),
        "T03": dict(lo=3, hi=3, s=45, gmin=4, gmax=8, v=0.0),
        "T04": dict(lo=3, hi=3, s=45, gmin=4, gmax=8, v=0.0),
        "T05": dict(lo=3, hi=3, s=45, gmin=4, gmax=8, v=0.0),
        "T06": dict(lo=3, hi=3, s=45, gmin=4, gmax=8, v=0.0),
        "T07": dict(lo=2, hi=4, s=40, gmin=4, gmax=9, v=1.0),
        "T08": dict(lo=2, hi=4, s=40, gmin=4, gmax=9, v=1.0),
        "T09": dict(lo=2, hi=4, s=40, gmin=4, gmax=9, v=1.0),
        "T10": dict(lo=2, hi=4, s=40, gmin=4, gmax=9, v=1.0),
    }
    days = {t: list(range(1, 21)) for t in base}
    cap = {d: 480 for d in range(1, 21)}
    locks = []
    if case == "case_2_capacity_short":
        cap.update({8: 120, 9: 120, 10: 120})
    elif case == "case_3_commitment_locks":
        locks = [("T01", 3, "DAY"), ("T03", 9, "SEQ"), ("T04", 10, "SEQ"), ("T07", 14, "COMPLETE")]
    elif case == "case_4_cadence_stress":
        base["T01"]["gmin"] = 4; base["T02"]["gmin"] = 4
        days["T03"] = [1, 8, 15]
    return base, days, cap, locks

def solve_oracle(case, soft=False):
    """soft=case2 语义: 频次可短缺(lo→0), min_gap/容量/锁仍 HARD。目标标量化独立推导:
    L2 权 1e6 · L3 权 1e3(v×1000) · service 权 1——与 F2 相同量纲但推导过程独立成文。"""
    base, days, cap, locks = oracle_targets(case)
    soft = (case == "case_2_capacity_short")
    m = cp_model.CpModel()
    x = {(t, d): m.NewBoolVar(f"o_x_{t}_{d}") for t in base for d in days[t]}
    for t, sp in base.items():
        vs = [x[t, d] for d in days[t]]
        if sp["lo"] == sp["hi"] and not soft:
            m.Add(sum(vs) == sp["lo"])
        else:
            m.Add(sum(vs) >= (0 if soft else sp["lo"]))
            m.Add(sum(vs) <= sp["hi"])
        av = days[t]
        for i, d1 in enumerate(av):
            for d2 in av[i+1:]:
                if d2 - d1 < sp["gmin"]:
                    m.AddAtMostOne([x[t, d1], x[t, d2]])
    for d in cap:
        m.Add(sum(base[t]["s"] * x[t, d] for t in base if (t, d) in x) <= cap[d])
    for t, d, kind in locks:
        m.Add(x[t, d] == 1)
    L2 = sum(x[t, d] for t in base for d in days[t])
    zvars = []
    for t, sp in base.items():
        if sp["v"] > 0:
            zv = m.NewIntVar(0, sp["hi"] - sp["lo"], f"o_z_{t}")
            m.Add(zv == sum(x[t, d] for d in days[t]) - sp["lo"])
            zvars.append((zv, int(sp["v"] * 1000)))
    L3 = sum(w * zv for zv, w in zvars)
    svc = sum(base[t]["s"] * x[t, d] for t in base for d in days[t])
    m.Maximize(1_000_000 * L2 + L3 - svc)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = 300.0
    s.parameters.num_search_workers = 8
    s.parameters.random_seed = 42
    st = s.Solve(m)
    if st == cp_model.OPTIMAL:
        assign = {t: [d for d in days[t] if s.Value(x[t, d])] for t in base}
        return {"status": "OPTIMAL", "objective": s.ObjectiveValue(),
                "bound": s.BestObjectiveBound(),
                "assign": {t: ds for t, ds in assign.items() if ds}}
    if st == cp_model.FEASIBLE:
        return {"status": "FEASIBLE_ONLY", "objective": s.ObjectiveValue(), "assign": None}   # oracle 降级——定义 v1_0 不允许
    return {"status": str(s.StatusName(st)), "assign": None}

if __name__ == "__main__":
    out = {}
    ok = True
    for case in ["case_1_basic_feasible", "case_2_capacity_short",
                 "case_3_commitment_locks", "case_4_cadence_stress"]:
        r = solve_oracle(case)
        ok &= (r["status"] == "OPTIMAL")
        print(f"{case}: {r['status']} obj={r.get('objective')} bound={r.get('bound')}")
        out[case] = r
    out["overall"] = "PASS" if ok else "FAIL"
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print("OVERALL:", out["overall"])
    sys.exit(0 if ok else 1)
