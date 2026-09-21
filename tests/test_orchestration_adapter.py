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
