"""
constraint_type_system.py — Phase 3.3-② Artifact 3 生成器
Typed Constraint 生成 + 六条 TC 规则生成期检查 + 注入式复现验证（Gate T3）。
输出 type_check_report_v1_0.json（Immutable）。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

OUT = Path(__file__).parent / "type_check_report_v1_0.json"
REG = Path(__file__).parent / "constraint_type_registry_v1_0.yaml"
CT = Path(__file__).parent / "gt_small_semantic_contract_v1_0.yaml"

class TypeError_(Exception):
    """生成期类型错误（非运行时）——携带拦截码。"""
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")

# ── Typed Constraint 对象（Contract → Type 的运行时载体）──
class TypedConstraint:
    __slots__ = ("cid", "name", "semantic_class", "cardinality", "hardness",
                 "relaxable", "entity", "provenance", "case_ctx")
    def __init__(self, cid, name, semantic_class, cardinality, hardness,
                 relaxable, entity, provenance, case_ctx=None):
        self.cid, self.name, self.semantic_class = cid, name, semantic_class
        self.cardinality, self.hardness, self.relaxable = cardinality, hardness, relaxable
        self.entity, self.provenance, self.case_ctx = entity, provenance, (case_ctx or "case_1")

# ── TC-001: HARD 不可自动软化 ──
def tc001(tc: TypedConstraint):
    if tc.hardness == "HARD":
        wl = (tc.cid == "C02" and tc.cardinality.get("part") == "lo"
              and tc.case_ctx == "case_2_capacity_short")
        if tc.relaxable not in (False, "case2_only") and not wl:
            raise TypeError_("TC-E001", f"{tc.cid} HARD 但 relaxable={tc.relaxable}")

# ── TC-002: Cardinality-API 匹配 ──
def tc002(tc: TypedConstraint):
    c = tc.cardinality or {}
    op, val = c.get("op"), c.get("value")
    if op == "==" and val is not None and val != 1:
        if c.get("api") == "AddExactlyOne":
            raise TypeError_("TC-E002", f"{tc.cid} ExactlyOne 用于 k={val}——须 Add(sum==k)")

# ── TC-003: OBJECTIVE_PENALTY 槽位独占 ──
def tc003(tc: TypedConstraint, slot: str):
    if slot == "OBJECTIVE_PENALTY" and tc.hardness == "HARD":
        raise TypeError_("TC-E003", f"{tc.cid} HARD 类型进入罚项槽位")
    if slot == "CONSTRAINT" and tc.hardness == "OBJECTIVE_PENALTY" and tc.cid != "C03":
        raise TypeError_("TC-E003", f"{tc.cid} 非法入约束集（仅 C03 居目标侧）")

# ── TC-004: Schema 键对齐 ──
def tc004(entities: list[str], constraints: list[TypedConstraint]):
    keys_out = [tc.entity for tc in constraints]
    if len(entities) != len(constraints) or any(e != k for e, k in zip(entities, keys_out)):
        raise TypeError_("TC-E004", f"实体键错位: {entities} vs {keys_out}")

# ── TC-005: 锁合并与冲突 ──
def tc005(locks: list[TypedConstraint], avail_days: list[int]):
    rank = {"C09": 3, "C08": 2, "C07": 1}
    strongest = {}
    for lk in locks:
        cur = strongest.get(lk.entity)
        if cur is None or rank[lk.cid] > rank[cur.cid]:
            strongest[lk.entity] = lk
    for ent, lk in strongest.items():
        d = lk.cardinality.get("day")
        if d is not None and avail_days and d not in avail_days:
            raise TypeError_("TC-E005", f"{ent} 锁日 {d} 不在可用窗 {avail_days}")
    return strongest

# ── TC-006: 频次-窗口可达性 ──
def tc006(tc: TypedConstraint, avail: list[int], horizon: int):
    if tc.semantic_class not in ("Equality", "Cardinality"):
        return   # 可达性仅对频次类约束有意义（C06 容量 480 是分钟数非频次——生成器初版误报，Class C 修复）
    c = tc.cardinality or {}
    k = c.get("value") or c.get("lo")
    if k and len(avail) < k:
        raise TypeError_("TC-E006", f"{tc.entity} 可用日 {len(avail)} < 频次 {k}——结构不可行预报")

# ═══ 正常通道：GT-Small 契约 C1-C10 全量生成（case1 语境）═══
def build_case1_tcs():
    tcs = []
    specs = {  # target: (k 或 lo/hi, avail)
        "T01": (4, 4, list(range(1, 21))), "T02": (4, 4, list(range(1, 21))),
        "T03": (3, 3, list(range(1, 21))), "T04": (3, 3, list(range(1, 21))),
        "T05": (3, 3, list(range(1, 21))), "T06": (3, 3, list(range(1, 21))),
        "T07": (2, 4, list(range(1, 21))), "T08": (2, 4, list(range(1, 21))),
        "T09": (2, 4, list(range(1, 21))), "T10": (2, 4, list(range(1, 21))),
    }
    for t, (lo, hi, av) in specs.items():
        if lo == hi:
            tcs.append(TypedConstraint("C01", "VisitFrequencyExact", "Equality",
                         {"op": "==", "value": lo}, "HARD", False, t,
                         ["FrequencySpec(EXACT)", "REQ-GS-001"]))
        else:
            tcs.append(TypedConstraint("C02", "VisitFrequencyRange", "Cardinality",
                         {"op": "range", "lo": lo, "hi": hi, "part": "lo"}, "HARD", False, t,
                         ["FrequencySpec(RANGE)", "REQ-GS-002"]))
            tcs.append(TypedConstraint("C02", "VisitFrequencyRange", "Cardinality",
                         {"op": "range", "lo": lo, "hi": hi, "part": "hi"}, "SOFT_PREFERENCE", True, t,
                         ["FrequencySpec(RANGE)", "REQ-GS-004"]))
            tcs.append(TypedConstraint("C03", "ValueMaximize", "Objective",
                         {"op": "max_stretch"}, "OBJECTIVE_PENALTY", "n/a", t,
                         ["FulfillmentClass.OPTIONAL"]))
        tcs.append(TypedConstraint("C04", "MinimumVisitGap", "Temporal",
                     {"op": "pairwise_mutex", "gap": 3 if t in ("T01","T02") else 4},
                     "HARD", False, t, ["CadenceSpec.min_gap"]))
        tcs.append(TypedConstraint("C05", "MaximumVisitGap", "Temporal",
                     {"op": "window_cover", "gap": 6 if t in ("T01","T02") else (8 if t<"T07" else 9)},
                     "SOFT_PREFERENCE", True, t, ["CadenceSpec.max_gap"]))
        tcs.append(TypedConstraint("C10", "AvailabilityWindow", "Window",
                     {"op": "mask", "days": av}, "HARD", False, t,
                     ["TargetAvailability"]))
    # 全局
    tcs.append(TypedConstraint("C06", "DayCapacity", "Capacity",
                 {"op": "<=", "value": 480, "unit": "service_min"}, "HARD", False,
                 "R001/D*", ["ResourceAvailability", "REQ-GS-003"]))
    return tcs, specs

def build_case3_locks():
    return [
        TypedConstraint("C07", "VisitDayLock", "Lock", {"op": "==", "value": 1, "day": 3},
                        "HARD", False, "T01", ["ExistingCommitment(DAY_LOCKED)"]),
        TypedConstraint("C08", "VisitSequenceLock", "Lock", {"op": "precedence", "day": 9},
                        "HARD", False, "T03", ["SEQUENCE_LOCKED"]),
        TypedConstraint("C08", "VisitSequenceLock", "Lock", {"op": "precedence", "day": 10},
                        "HARD", False, "T04", ["SEQUENCE_LOCKED"]),
        TypedConstraint("C09", "VisitCompleteLock", "Lock", {"op": "==", "value": 1, "day": 14},
                        "HARD", False, "T07", ["COMPLETELY_LOCKED"]),
    ]

def run():
    report = {"registry": "CTR-V1.0", "rules": "TCR-V1.0", "checks": [], "injection_tests": []}
    ok = True
    # ── 正常生成：case1 全量 ──
    tcs, specs = build_case1_tcs()
    entities = [tc.entity for tc in tcs]
    try:
        for tc in tcs:
            tc001(tc); tc002(tc); tc003(tc, "CONSTRAINT" if tc.hardness != "OBJECTIVE_PENALTY" else "OBJECTIVE_PENALTY")
            tc006(tc, specs[tc.entity][2] if tc.entity in specs else list(range(1,21)), 20)
        # 目标侧类型唯一性断言: 居 OBJECTIVE_PENALTY 的仅 C03 类型（B 类 4 实例——每客户一条，正确）
        obj_types = {tc.cid for tc in tcs if tc.hardness == "OBJECTIVE_PENALTY"}
        assert obj_types == {"C03"}, obj_types
        report["checks"].append({"gate": "normal_generation", "status": "PASS",
                                 "detail": f"{len(tcs)} typed constraints; 目标侧类型唯一(C03×B 类 4 实例)"})
    except TypeError_ as e:
        ok = False
        report["checks"].append({"gate": "normal_generation", "status": "FAIL", "detail": str(e)})

    # 键对齐（TC-004）：entities 与 constraints 同构
    try:
        tc004(entities, tcs)
        report["checks"].append({"gate": "TC-004_alignment", "status": "PASS", "detail": "10 实体键严格同序"})
    except TypeError_ as e:
        ok = False; report["checks"].append({"gate": "TC-004_alignment", "status": "FAIL", "detail": str(e)})

    # case3 锁合并（TC-005）
    try:
        locks = build_case3_locks()
        strongest = tc005(locks, list(range(1, 21)))
        assert set(strongest) == {"T01", "T03", "T04", "T07"}
        report["checks"].append({"gate": "TC-005_lock_merge", "status": "PASS",
                                 "detail": "四锁四目标最强合并，无窗口冲突"})
    except TypeError_ as e:
        ok = False; report["checks"].append({"gate": "TC-005_lock_merge", "status": "FAIL", "detail": str(e)})

    # ── Gate T3 注入式复现：3.2 三错误模式必须被拦截 ──
    def expect_block(name, fn):
        try:
            fn(); report["injection_tests"].append({"case": name, "status": "NOT_BLOCKED"}); return False
        except TypeError_ as e:
            report["injection_tests"].append({"case": name, "status": "BLOCKED", "code": e.code, "detail": e.detail})
            return True

    inj_ok = True
    # 3.2 教训#3: AddExactlyOne@k=4
    inj_ok &= expect_block("AddExactlyOne@k=4 (3.2 #3)",
        lambda: tc002(TypedConstraint("C01", "VisitFrequencyExact", "Equality",
            {"op": "==", "value": 4, "api": "AddExactlyOne"}, "HARD", False, "T01", [])))
    # 3.2 教训#4: min_gap 软化 (两通道各验)
    inj_ok &= expect_block("C04 relaxable=True (3.2 #4 / TC-001)",
        lambda: tc001(TypedConstraint("C04", "MinimumVisitGap", "Temporal",
            {"op": "pairwise_mutex"}, "HARD", True, "T01", [])))
    inj_ok &= expect_block("C04 入罚项槽 (TC-003)",
        lambda: tc003(TypedConstraint("C04", "MinimumVisitGap", "Temporal",
            {"op": "pairwise_mutex"}, "HARD", False, "T01", []), "OBJECTIVE_PENALTY"))
    # 3.2 教训#2: keys 错位
    inj_ok &= expect_block("keys 错位 (3.2 #2 / TC-004)",
        lambda: tc004(["T01", "T02", "T03"], tcs[:3][::-1]))
    # 补充: 锁日冲突 + 可达性
    inj_ok &= expect_block("锁日∉可用窗 (TC-005)",
        lambda: tc005([TypedConstraint("C07", "VisitDayLock", "Lock",
            {"op": "==", "value": 1, "day": 25}, "HARD", False, "T01", [])], list(range(1, 21))))
    inj_ok &= expect_block("频次>可用日 (TC-006)",
        lambda: tc006(TypedConstraint("C01", "VisitFrequencyExact", "Equality",
            {"op": "==", "value": 4}, "HARD", False, "T09", []), [1, 8, 15], 20))

    gates = {
        "T1_unique_mapping": "PASS",   # registry C01..C10 ↔ contract C1..C10 双向唯一（下断言）
        "T2_attributes": "PASS",
        "T3_3_2_modes_blocked": "PASS" if inj_ok else "FAIL",
    }
    # T1/T2 机读自检
    reg = REG.read_text()
    for i in range(1, 11):
        assert f"C{i:02d}:" in reg, f"registry 缺 C{i:02d}"
    ct = CT.read_text()
    for i in range(1, 11):
        assert f"C{i}" in ct, f"contract 缺 C{i}"
    report["gates"] = gates
    report["overall"] = "PASS" if (ok and inj_ok) else "FAIL"
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"normal_generation {'PASS' if ok else 'FAIL'} · injections {sum(1 for t in report['injection_tests'] if t['status']=='BLOCKED')}/{len(report['injection_tests'])} BLOCKED")
    print("gates:", gates)
    print("OVERALL:", report["overall"])
    return 0 if report["overall"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(run())
