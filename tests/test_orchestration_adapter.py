# -*- coding: utf-8 -*-
"""orchestration.adapter 测试: LineData→事实→语义规格→数学实例→验解 全链 (合成数据, CI 可跑)."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, ".")

from core.base import LineData
from orchestration import compile_line_spec, line_data_facts
from visitmodel import MathCompiler, MathValidator

D = date
MON = (D(2026, 3, 2), D(2026, 3, 9))
TUE = (D(2026, 3, 3), D(2026, 3, 10))
WED = (D(2026, 3, 4), D(2026, 3, 11))
THU = (D(2026, 3, 5), D(2026, 3, 12))
FRI = (D(2026, 3, 6), D(2026, 3, 13))
DATES = list(sorted(MON + TUE + WED + THU + FRI))

# idx→code: 0=W1(周一) 1=W1b(周一) 2=W2(周二) 3=W3(周三) 4=W4(周四) 5=B1(周五相位0) 6=B2(周五相位1)
CODES = ["W1", "W1b", "W2", "W3", "W4", "B1", "B2"]
DAYS = {
    MON[0]: [0, 1], MON[1]: [0, 1],
    TUE[0]: [2], TUE[1]: [2],
    WED[0]: [3], WED[1]: [3],
    THU[0]: [4], THU[1]: [4],
    FRI[0]: [5],
    FRI[1]: [6],
}


def _line() -> LineData:
    freq = {"W1": 2, "W1b": 2, "W2": 2, "W3": 2, "W4": 2, "B1": 1, "B2": 1}
    visits = sum(len(v) for v in DAYS.values())
    return LineData(
        line_id="T1", line_name="合成测试线", codes=CODES,
        lon=[110.0] * 7, lat=[30.0] * 7, dates=DATES, days_orig=dict(DAYS),
        freq=freq, stores=len(CODES), visits=visits,
    )


def test_line_data_facts_maps_index_to_code():
    facts = line_data_facts(_line())
    assert facts["days_orig"][MON[0]] == ["W1", "W1b"]
    assert facts["workdays"] == DATES


def test_compile_line_spec_end_to_end_validates_original_plan():
    """全链: LineData → L1 语义规格(零例外闸) → L2 数学实例 → 独立验解原计划 = OK."""
    line = _line()
    spec = compile_line_spec(line, protected_codes=("W1",))
    assert spec.corridor.source == "historical_baseline"
    assert spec.protected_codes == frozenset({"W1"})
    by = {c.customer_code: c for c in spec.contracts}
    assert by["B1"].phase == 0 and by["B2"].phase == 1
    inst = MathCompiler().compile(spec)
    original = {d: tuple(line.codes[i] for i in seq) for d, seq in line.days_orig.items()}
    rep = MathValidator().validate(inst, original)
    assert rep.ok, rep.violations


def test_compile_line_spec_zero_exception_gate():
    """违例线路(跨星期几门店)在 L1 闸即拒绝, 不进 L2."""
    line = _line()
    broken = dict(line.days_orig)
    broken[WED[0]] = [3, 6]   # B2(周五相位1) 出现在周三 → 跨星期几
    bad = LineData(
        line_id="BAD", line_name="违例线", codes=CODES,
        lon=[110.0] * 7, lat=[30.0] * 7, dates=DATES, days_orig=broken,
        freq=line.freq, stores=7, visits=sum(len(v) for v in broken.values()),
    )
    with pytest.raises(ValueError, match="零例外闸未过"):
        compile_line_spec(bad)


class _GreedyBackend:
    """最小协议后端 (与 VisitModel tests 内实现同思路): 按日装满欠义务的合法客户."""

    def solve(self, instance, config):
        from visit_math_api import SolveResult as _Res
        remaining = dict(instance.required_visits)
        assignments = {}
        for d in instance.workdays:
            day = []
            for c in instance.customers:
                if remaining.get(c, 0) > 0 and d in instance.eligible_days.get(c, frozenset()):
                    day.append(c)
                    remaining[c] -= 1
            assignments[d] = tuple(day)
        ok = all(v == 0 for v in remaining.values())
        return _Res(
            status="OPTIMAL" if ok else "INFEASIBLE",
            assignments=assignments,
            objective_vector=(0.0,) * len(instance.objective_terms),
            termination_reason="exhaustive-deterministic",
            instance_hash=dict(instance.metadata).get("content_hash", ""),
        )


def test_decision_episode_emitted_and_deterministic():
    """G4: 留痕组装 + 同决策重放同 episode_hash."""
    from orchestration import emit_episode
    from visit_math_api import DecisionEpisode, episode_hash
    from visit_math_api import SolverConfig as _Cfg

    line = _line()
    spec = compile_line_spec(line)
    inst = MathCompiler().compile(spec)
    result = _GreedyBackend().solve(inst, _Cfg(backend="greedy", seed=7))

    ep = emit_episode(spec, inst, result, _Cfg(backend="greedy", seed=7), solver_version="t1")
    assert isinstance(ep, DecisionEpisode)
    assert ep.semantic_spec_hash == spec.metadata.content_hash
    assert ep.status == "OPTIMAL" and ep.seed == 7

    ep2 = emit_episode(spec, inst, result, _Cfg(backend="greedy", seed=7), solver_version="t1")
    assert episode_hash(ep) == episode_hash(ep2), "同决策重放必须同指纹"


def test_episode_rejects_unversioned_spec():
    """metadata 缺失的 spec 拒绝留痕 (不可复现的求解不允许入账)."""
    from orchestration import emit_episode
    from visit_math_api import SolverConfig as _Cfg
    from visit_semantic_api import VisitSemanticSpec as _S

    spec = compile_line_spec(_line())
    bare = _S(horizon=spec.horizon, contracts=spec.contracts, corridor=spec.corridor)
    inst = MathCompiler().compile(spec)
    result = _GreedyBackend().solve(inst, _Cfg(backend="greedy"))
    with pytest.raises(ValueError, match="不可复现"):
        emit_episode(bare, inst, result, _Cfg(backend="greedy"))


def test_escalation_levels():
    """状态机: 绿→NONE; 义务/走廊违例→L2 重编译; 合同语义违例→L1 授权."""
    from datetime import date as _date

    from orchestration import Level, escalate
    from visit_math_api import SolveResult as _Res, SolverConfig as _Cfg

    line = _line()
    spec = compile_line_spec(line)
    inst = MathCompiler().compile(spec)

    # 绿: 无升级
    good = _Res(status="OPTIMAL", assignments=_ideal_assignments(),
                objective_vector=(0.0,))
    assert escalate(inst, good, MathValidator().validate(
        inst, _ideal_assignments())).level is Level.NONE

    # 义务违例 (B2 缺访) → L2 重编译 (可滚动吸收)
    broken = dict(_ideal_assignments())
    del broken[D(2026, 3, 13)]
    rep = MathValidator().validate(inst, broken)
    bad = _Res(status="FEASIBLE", assignments=broken, objective_vector=(0.0,))
    esc = escalate(inst, bad, rep)
    assert esc.level is Level.L2_RECONCILE
    assert "contract_obligation" in esc.violated_rule_ids

    # 合同语义违例 (店坐在非法日期) → L1 授权 (solver 无权改合同)
    broken2 = dict(_ideal_assignments())
    broken2[D(2026, 3, 3)] = ("W2", "W1")  # W1 出现在周二 = 非法日期
    rep2 = MathValidator().validate(inst, broken2)
    esc2 = escalate(inst, _Res(status="FEASIBLE", assignments=broken2,
                               objective_vector=(0.0,)), rep2)
    assert esc2.level is Level.L1_AUTHORIZE
    assert any("contract_legal_slots" in r for r in esc2.violated_rule_ids)
    assert "ExceptionGrant" in esc2.action

    # 求解器自报 INFEASIBLE (无明细) → L2 重编译
    inf = _Res(status="INFEASIBLE", assignments={}, objective_vector=(),
               termination_reason="no feasible column set")
    assert escalate(inst, inf).level is Level.L2_RECONCILE


def _ideal_assignments():
    return {
        D(2026, 3, 2): ["W1", "W1b"], D(2026, 3, 3): ["W2"], D(2026, 3, 4): ["W3"],
        D(2026, 3, 5): ["W4"], D(2026, 3, 6): ["B1"], D(2026, 3, 9): ["W1", "W1b"],
        D(2026, 3, 10): ["W2"], D(2026, 3, 11): ["W3"], D(2026, 3, 12): ["W4"],
        D(2026, 3, 13): ["B2"],
    }


class _MappingProxyOf(dict):
    pass
