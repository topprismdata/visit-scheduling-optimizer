"""Stage 1 v2: 节奏式问题定义 (日历无关)."""
import numpy as np
import pandas as pd
import pytest
from svc.schemas.validate import validate_obj
from svc.stages.semantic import (build_calendar_map, build_spec_from_df,
                                  _derive_frequency)

DATES = [pd.Timestamp("2026-07-01").date(), pd.Timestamp("2026-07-02").date()]


def make_line_df():
    """4 店 2 日: 店0/1 每天, 店2 仅第1天, 店3 仅第2天."""
    rows = []
    plan_map = {0: DATES, 1: DATES, 2: DATES[:1], 3: DATES[1:]}
    for sid, ds in plan_map.items():
        for di, dd in enumerate(ds):
            rows.append({"客户编码": f"C00{sid}", "销售名称": "海珠荔湾09",
                          "经度": 113.25 + sid * 0.01, "纬度": 23.05 + sid * 0.01,
                          "拜访顺序": di + 1, "date": dd,
                          "拜访日期": dd.strftime("%Y-%m-%d")})
    return pd.DataFrame(rows)


def test_frequency_derivation_classes():
    # ~5 次/23天 -> 周1次 (次/周, horizon 5)
    f = _derive_frequency([1, 6, 11, 16, 21], 23)
    assert (f["horizon"], f["visits"], f["ambiguous"]) == (5, 1, False)
    # ~2 次/23天 -> 次/2周 (horizon 10)
    f = _derive_frequency([4, 14], 23)
    assert (f["horizon"], f["visits"], f["ambiguous"]) == (10, 1, False)
    # 1 次/23天 -> 次/4周 (horizon 20)
    f = _derive_frequency([13], 23)
    assert (f["horizon"], f["visits"], f["ambiguous"]) == (20, 1, False)
    # 7 次/23天 -> 周1.5次 -> 周访档, 每周 2 次
    f = _derive_frequency(list(range(1, 8)), 23)
    assert f["visits"] == 2 and f["ambiguous"] is True   # 周1.5次不成整档 -> 诚实标歧义
    # 无 pattern 字段: pattern 属于求解器决策变量
    assert "pattern" not in f


def _derive_frequency(*a, **k):
    from svc.stages.semantic import _derive_frequency as _f
    return _f(*a, **k)


def test_build_spec_v2_no_calendar_fields():
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(make_line_df(), "09", D)
    validate_obj(spec, "problem")
    # 日历无关: 全文不允许出现 ISO 日期
    assert "2026-07" not in str(spec)
    assert spec["cycle"]["n_days"] == 2
    assert spec["stores"][0]["frequency"]["visits"] == 5   # 每工作周 2 次 × ... mini 全勤
    assert spec["stores"][0]["frequency"]["horizon"] == 2   # 兜底 = 周期长
    # 分配键 = 拜访日序号
    assert spec["original_assignment_idx"]["1"] == [0, 1, 2]   # 店0/1/2
    assert spec["original_assignment_idx"]["2"] == [3, 0, 1]   # 按拜访顺序: 店3先(顺序1)
    spec2 = build_spec_from_df(make_line_df(), "09", D)
    assert spec["inputs_hash"] == spec2["inputs_hash"]


def test_calendar_map_separate():
    from svc.stages.semantic import build_calendar_map
    cm = build_calendar_map(make_line_df(), "09")
    validate_obj(cm, "calendar_map")
    assert cm["mapping"][0] == {"day": 1, "date": "2026-07-01", "weekday": "Wed"}
