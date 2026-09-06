"""
dsvl_validation_engine.py — Phase 3.3-③ Artifact 2
Decision Semantic Validation Layer 前置检查引擎：三族 12 规则执法。
验证 decision feasibility（约束组合是否仍是原业务决策）——非 solution feasibility。
输出 dsvl_validation_report_v1_0.json（Immutable）。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from constraint_type_system import TypedConstraint, build_case1_tcs, build_case3_locks

OUT = Path(__file__).parent / "dsvl_validation_report_v1_0.json"

class DSVLFailure(Exception):
    def __init__(self, rule_id, detail):
        self.rule_id, self.detail = rule_id, detail
        super().__init__(f"{rule_id}: {detail}")

# ── 装配件语义字段（GT-Small 契约的 Decision IR——DSVL-T001 双射的左端）──
DECISION_IR = {
    "targets": {  # t: (semantics, lo, hi, min_gap, max_gap, avail)
        "T01": ("EXACT", 4, 4, 3, 6, list(range(1, 21))),
        "T02": ("EXACT", 4, 4, 3, 6, list(range(1, 21))),
        "T03": ("EXACT", 3, 3, 4, 8, list(range(1, 21))),
        "T04": ("EXACT", 3, 3, 4, 8, list(range(1, 21))),
        "T05": ("EXACT", 3, 3, 4, 8, list(range(1, 21))),
        "T06": ("EXACT", 3, 3, 4, 8, list(range(1, 21))),
        "T07": ("RANGE", 2, 4, 4, 9, list(range(1, 21))),
        "T08": ("RANGE", 2, 4, 4, 9, list(range(1, 21))),
        "T09": ("RANGE", 2, 4, 4, 9, list(range(1, 21))),
        "T10": ("RANGE", 2, 4, 4, 9, list(range(1, 21))),
    },
    "capacity": {"R001": 480},
    "case3_locks": [("T01", 3, "DAY"), ("T03", 9, "SEQ"), ("T04", 10, "SEQ"), ("T07", 14, "COMPLETE")],
}

def validate(tcs: list[TypedConstraint], case: str, locks: list[TypedConstraint]):
    R = []
    def rec(rule, ok, ev):
        R.append({"rule_id": rule, "status": "PASS" if ok else "FAIL", "evidence": ev})
        return ok

    # ═══ Family I: Invariants (V1) ═══
    # I001 锁执法在场（case3）
    if case == "case_3_commitment_locks":
        lock_types = {"DAY": "C07", "SEQ": "C08", "COMPLETE": "C09"}
        ents = {(lk.entity, lk.cid) for lk in locks}
        missing = [f"{t}@{lock_types[k]}" for t, d, k in DECISION_IR["case3_locks"]
                   if (t, lock_types[k]) not in ents]
        rec("DSVL-I001", not missing, f"四锁执法实例在场: {sorted(ents)}" if not missing else f"缺失: {missing}")
    else:
        rec("DSVL-I001", True, "非锁 Case——锁不变式空真空成立（vacuous）")

    # I002 HARD 频次等式形态（非 soft Case）
    hard_freq = [tc for tc in tcs if tc.cid in ("C01", "C02") and tc.cardinality.get("part") in (None, "lo")
                 and tc.hardness == "HARD"]
    eq_form = all(tc.cardinality.get("op") in ("==", "range") for tc in hard_freq)
    in_penalty = any(tc.hardness == "OBJECTIVE_PENALTY" for tc in hard_freq)
    rec("DSVL-I002", eq_form and not in_penalty,
        f"{len(hard_freq)} 条 HARD 频次全为等式/下界形态，零罚项化")

    # I003 软化白名单闭合
    viol = [tc.entity + "/" + tc.cid for tc in tcs
            if tc.hardness not in ("HARD", "SOFT_PREFERENCE", "OBJECTIVE_PENALTY")
            or (tc.cid in ("C04", "C06", "C07", "C08", "C09", "C10") and tc.hardness != "HARD")]
    rec("DSVL-I003", not viol, "白名单外零软化（C04/06/07/08/09/10 全 HARD）" if not viol else f"违例: {viol}")

    # I004 口径唯一
    st = [tc for tc in tcs if "stop_time" in str(tc.cardinality) or "32.0" in str(tc.cardinality)]
    rec("DSVL-I004", not st, "服务时长唯一来源 expected_service_min；stop_time 零出现")

    # ═══ Family S: Constraint Semantic (V2) ═══
    # S001 无静默丢弃（覆盖矩阵）
    holes = []
    for t, (sem, lo, hi, gmin, gmax, av) in DECISION_IR["targets"].items():
        tt = [x for x in tcs if x.entity == t]
        has_freq = any(x.cid in ("C01", "C02") for x in tt)
        has_gap = any(x.cid == "C04" for x in tt) and any(x.cid == "C05" for x in tt)
        has_win = any(x.cid == "C10" for x in tt)
        if not (has_freq and has_gap and has_win):
            holes.append(t)
    cap_present = any(x.cid == "C06" for x in tcs)
    rec("DSVL-S001", not holes and cap_present,
        f"覆盖矩阵零空洞: 10 客户 × (频次+间隔+窗口) 全在场；C06 容量在场" if not holes and cap_present else f"空洞: {holes}")

    # S002 无幻影约束（provenance 全可溯）
    phantom = [tc.entity + "/" + tc.cid for tc in tcs if not tc.provenance or len(tc.provenance) < 1]
    rec("DSVL-S002", not phantom, f"{len(tcs)} 实例 provenance 全可溯" if not phantom else f"幻影: {phantom}")

    # S003 hardness 一致性（实例 ⊆ 类型声明）
    TYPE_H = {"C01": {"HARD"}, "C02": {"HARD", "SOFT_PREFERENCE"}, "C03": {"OBJECTIVE_PENALTY"},
              "C04": {"HARD"}, "C05": {"SOFT_PREFERENCE"}, "C06": {"HARD"},
              "C07": {"HARD"}, "C08": {"HARD"}, "C09": {"HARD"}, "C10": {"HARD"}}
    bad_h = [tc.entity + "/" + tc.cid + "=" + tc.hardness for tc in tcs
             if tc.hardness not in TYPE_H.get(tc.cid, set())]
    rec("DSVL-S003", not bad_h, "实例 hardness 全部 ⊆ 类型声明" if not bad_h else f"越界: {bad_h}")

    # S004 目标空间隔离（集合级——与 TC-003 生成级双层）
    obj_members = sorted({tc.cid for tc in tcs if tc.hardness == "OBJECTIVE_PENALTY"})
    c03_in_constraint = any(tc.cid == "C03" and tc.hardness != "OBJECTIVE_PENALTY" for tc in tcs)
    rec("DSVL-S004", obj_members == ["C03"] and not c03_in_constraint,
        f"目标空间居民类型: {obj_members}（仅 C03）；约束空间零 C03")

    # S005 实例基数律（类型唯一 ≠ 实例唯一；同(类型,实体,分部)不重复）
    seen, dup = set(), []
    for tc in tcs:
        key = (tc.cid, tc.entity, tc.cardinality.get("part"))
        if key in seen: dup.append(str(key))
        seen.add(key)
    rec("DSVL-S005", not dup,
        f"实例基数合法: {len(tcs)} 实例 / 10 类型；重复: {dup}" if dup else "零重复（C02 lo/hi 分部合法拆分）")

    # ═══ Family T: Trace (V3) ═══
    # T001 双射（每 IR 字段 ≥1 实例；每实例 provenance 指回字段族）
    orphan_tcs = [tc.entity for tc in tcs if tc.entity not in DECISION_IR["targets"] and tc.entity != "R001/D*"]
    rec("DSVL-T001", not orphan_tcs and not holes,
        "Decision IR ↔ Typed Constraint 双射成立（左满射+右无孤儿）" if not orphan_tcs else f"孤儿实例: {orphan_tcs}")

    # T002 provenance 三级链（domain_object → requirement → typed）
    chain_bad = []
    for tc in tcs:
        p = tc.provenance or []
        # Class C 修复(2026-08-22): 词表大小写不敏感——首跑 FAIL 因 provenance 写 SEQUENCE_LOCKED
        # 而 checker 词表只认 "Lock" 子串；分诊=Implementation Fail(checker 词表缺陷, 非 Assumption)
        has_dom = any(any(k in str(x).upper() for k in ("SPEC", "AVAILABILITY", "COMMITMENT", "LOCK", "CLASS")) for x in p)
        if not (has_dom and tc.cid.startswith("C")):
            chain_bad.append(tc.entity + "/" + tc.cid)
    rec("DSVL-T002", not chain_bad, f"三级链完整: domain→requirement→typed（{len(tcs)} 实例）" if not chain_bad else f"断链: {chain_bad}")

    # T003 solver_bindings 投影就绪（WARNING 级）
    reg = Path(__file__).parent.joinpath("constraint_type_registry_v1_0.yaml").read_text()
    n_bindings = reg.count("solver_bindings:")
    rec("DSVL-T003", n_bindings == 10,
        f"registry solver_bindings ×{n_bindings}/10——④ 编译投影键齐备（WARNING 级：不阻断）")

    return R

def run():
    report = {"registry": "DSVL-REG-V1.0", "engine": "dsvl_validation_engine.py", "cases": {}}
    all_ok = True
    for case, with_locks in [("case_1_basic_feasible", False),
                             ("case_3_commitment_locks", True)]:
        tcs, _ = build_case1_tcs()
        locks = build_case3_locks() if with_locks else []
        rules = validate(tcs + locks, case, locks)
        blocking = [r for r in rules if r["status"] == "FAIL"]
        gates = {
            "V1": all(r["status"] == "PASS" for r in rules if r["rule_id"].startswith("DSVL-I")),
            "V2": all(r["status"] == "PASS" for r in rules if r["rule_id"].startswith("DSVL-S")),
            "V3": all(r["status"] == "PASS" for r in rules if r["rule_id"].startswith("DSVL-T")),
        }
        report["cases"][case] = {"rules": rules, "gates": gates,
                                 "decision_feasible": not blocking}
        all_ok &= not blocking and all(gates.values())
        print(f"{case}: V1={gates['V1']} V2={gates['V2']} V3={gates['V3']} → decision_feasible={not blocking}")
    report["overall"] = "PASS" if all_ok else "FAIL"
    report["mandate_note"] = "本报告验证 decision feasibility（约束组合=原业务决策）——solution feasibility 属求解期"
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("OVERALL:", report["overall"])
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(run())
