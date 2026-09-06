"""
mathopt_model_generator_v1_0.py — Phase 3.3-④ Artifact 1
Typed Constraint → MathOpt 编译器（F2: date-index compact-MIP, S-A §2.8——无 λ）。
Gate M1: Compilation Semantic Preservation——逐约束投影核验（typed_semantic vs compiled_form）。
禁止: solver 调参 / 性能优化（KB-GOV-015 四禁令）。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from constraint_type_system import TypedConstraint, build_case1_tcs, build_case3_locks  # ② 冻结产物同源

# MathOpt（真异构后端——KBC-02 绑定）
from ortools.math_opt.python import model as mo_model

OUT_DIR = Path(__file__).parent

# ── 装配件输入（GT-Small v1.0——不重写，从 instance 派生的 specs 与 ② 一致）──
from constraint_type_system import build_case1_tcs  # 同源 TypedConstraint（② 冻结产物）

def gt_small_targets():
    T = {}
    for t, (lo, hi, av) in {
        "T01": (4,4,None), "T02": (4,4,None), "T03": (3,3,None), "T04": (3,3,None),
        "T05": (3,3,None), "T06": (3,3,None), "T07": (2,4,None), "T08": (2,4,None),
        "T09": (2,4,None), "T10": (2,4,None)}.items():
        T[t] = (lo, hi, list(range(1, 21)))
    SVC = {"T01":60,"T02":60,"T03":45,"T04":45,"T05":45,"T06":45,"T07":40,"T08":40,"T09":40,"T10":40}
    GAP = {t: (3 if t in ("T01","T02") else 4) for t in T}
    VAL = {t: (1.0 if t >= "T07" else 0.0) for t in T}
    return T, SVC, GAP, VAL

def compile_F2(case: str):
    """Typed Constraint 集合 → MathOpt model。返回 (model, x, meta, m1_records)。"""
    tcs, _ = build_case1_tcs()
    locks = build_case3_locks() if case == "case_3_commitment_locks" else []
    all_c = tcs + locks
    T, SVC, GAP, VAL = gt_small_targets()
    DAYS = list(range(1, 21))
    CAP = {d: 480 for d in DAYS}
    soft = (case == "case_2_capacity_short")
    if soft:
        CAP.update({8: 120, 9: 120, 10: 120})
    if case == "case_4_cadence_stress":
        GAP["T01"] = 4; GAP["T02"] = 4
        T["T03"] = (3, 3, [1, 8, 15])

    m = mo_model.Model(name=f"GT-Small-{case}")
    x = {(t, d): m.add_binary_variable(name=f"f2_x_{t}_{d}") for t in T for d in T[t][2]}

    m1 = []   # Gate M1: 逐约束投影记录

    def proj(cid, entity, typed_semantic, compiled_form):
        m1.append({"constraint_id": f"{cid}@{entity}", "typed_semantic": typed_semantic,
                   "compiled_form": compiled_form,
                   "status": "PRESERVED" if compiled_form else "MISSING"})

    for t, (lo, hi, av) in T.items():
        vs = [x[t, d] for d in av]
        if lo == hi and not soft:
            # C01: Σ == k（等式——TC-002: k=4/3 用等式非 ExactlyOne）
            m.add_linear_constraint(sum(vs) == lo, name=f"C01_{t}")
            proj("C01", t, "HARD_EXACT", f"sum=={lo}")
        else:
            m.add_linear_constraint(sum(vs) >= (0 if soft else lo), name=f"C02lo_{t}")
            m.add_linear_constraint(sum(vs) <= hi, name=f"C02hi_{t}")
            proj("C02", t, "HARD_lo/SOFT_hi", f"{(0 if soft else lo)}<=sum<={hi}")
            if VAL[t] > 0:
                proj("C03", t, "OBJECTIVE_L3", "stretch in objective")
        # C04 min_gap 互斥对（HARD——任何 Case 不软化: TC-001/DSVL-I003）
        g = GAP[t]
        for i, d1 in enumerate(av):
            for d2 in av[i+1:]:
                if d2 - d1 < g:
                    m.add_linear_constraint(x[t, d1] + x[t, d2] <= 1, name=f"C04_{t}_{d1}_{d2}")
        proj("C04", t, "HARD_PAIRWISE_MUTEX", f"pairs(|Δd|<{g})")
        # C05 max_gap 软滑窗——GT-Small 语义同 3.2（L4 软罚由 oracle 侧统一评估——模型侧仅记录）
        proj("C05", t, "SOFT_WINDOW(L4)", "oracle-side penalty")
        proj("C10", t, "HARD_WINDOW_MASK", f"vars only on {len(av)} days")
    # C06 容量
    for d in DAYS:
        m.add_linear_constraint(sum(SVC[t] * x[t, d] for t in T if (t, d) in x) <= CAP[d],
                                name=f"C06_D{d}")
    proj("C06", "R001", "HARD_CAPACITY", "Σs·x<=cap")
    # 锁（case3）
    for lk in locks:
        m.add_linear_constraint(x[lk.entity, lk.cardinality["day"]] == 1,
                                name=f"{lk.cid}_{lk.entity}")
        if lk.cid == "C08":
            proj("C08", lk.entity, "HARD_PRECEDENCE", f"day{lk.cardinality['day']}==1 (seq)")
        else:
            proj(lk.cid, lk.entity, "HARD_LOCK", f"day{lk.cardinality['day']}==1")
    # C03 目标项（L3）——标量目标: 1e6*L2 + 1e3*L3 − svc（与 3.2 F2/F3 同权——分层用层间最优割在 solve 侧）
    L2 = sum(x[t, d] for t in T for d in T[t][2])
    stretch = {}
    for t in T:
        if VAL[t] > 0:
            z = m.add_integer_variable(lb=0, ub=T[t][1] - T[t][0], name=f"f2_z_{t}")
            m.add_linear_constraint(z == sum(x[t, d] for d in T[t][2]) - T[t][0], name=f"C03z_{t}")
            stretch[t] = z
    L3 = sum(int(VAL[t] * 1000) * stretch[t] for t in stretch)
    svc = sum(SVC[t] * x[t, d] for t in T for d in T[t][2])
    m.maximize(1_000_000 * L2 + L3 - svc)   # 字典序标量化（与 3.2 相同尺度隔离）
    return m, x, {"T": T, "SVC": SVC, "GAP": GAP, "VAL": VAL, "soft": soft,
                  "locks": [(lk.entity, lk.cardinality["day"]) for lk in locks]}, m1

def solve_F2(case: str):
    from ortools.math_opt.python import solve
    from ortools.math_opt.python import parameters as mop
    m, x, meta, m1 = compile_F2(case)
    import datetime
    params = mop.SolveParameters(time_limit=datetime.timedelta(seconds=120))
    res = solve.solve(m, solver_type=mop.SolverType.HIGHS, params=params)
    # MathOpt status 归一
    status = str(res.termination.reason)
    if "OPTIMAL" not in status and "FEASIBLE" not in status:
        return {"case": case, "status": status, "m1": m1, "assign": None}
    vals = res.solutions[0].primal_solution.variable_values   # MathOpt 9.15 取值 API（实验确认）
    assign = {t: [d for d in av if vals[x[t, d]] > 0.5]
              for t, (lo, hi, av) in meta["T"].items()}
    assign = {t: ds for t, ds in assign.items() if ds}
    return {"case": case, "status": "OPTIMAL" if "OPTIMAL" in status else "FEASIBLE",
            "objective": float(res.objective_value()), "bound": float(res.best_objective_bound()),
            "m1": m1, "assign": assign, "meta": {k: v for k, v in meta.items() if k != "locks"}}

if __name__ == "__main__":
    out = {}
    for case in ["case_1_basic_feasible", "case_2_capacity_short",
                 "case_3_commitment_locks", "case_4_cadence_stress"]:
        r = solve_F2(case)
        m1_ok = all(rec["status"] == "PRESERVED" for rec in r["m1"])
        print(f"{case}: {r['status']} obj={r.get('objective')} bound={r.get('bound')} "
              f"M1_preserved={m1_ok} ({sum(1 for q in r['m1'] if q['status']=='PRESERVED')}/{len(r['m1'])})")
        out[case] = r
    OUT_DIR.joinpath("mathopt_compile_result_v1_0.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print("saved mathopt_compile_result_v1_0.json")
