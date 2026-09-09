"""Stage 1 v2: 节奏式问题定义 (日历无关)."""
import numpy as np
import pandas as pd
import pytest
from svc.schemas.validate import validate_obj
from svc.stages.semantic import (build_calendar_map, build_spec_from_df,
                                  _derive_rhythm)

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


def test_rhythm_derivation_weekly_biweekly_monthly():
    # 每周(每7拜访日): 1,8,15,22 / 23天
    r = _derive_rhythm([1, 8, 15, 22], 23)
    assert (r["period"], r["phase"], r["visits_per_period"], r["ambiguous"]) == (7, 1, 1, False)
    # 双周: 6,20 / 23天
    r = _derive_rhythm([6, 20], 23)
    assert (r["period"], r["phase"], r["ambiguous"]) == (14, 6, False)
    # 月访(次/周期): 13 / 23天
    r = _derive_rhythm([13], 23)
    assert (r["period"], r["ambiguous"]) == (23, False)
    # 节奏断裂: 1,8,22 (缺15) -> ambiguous
    r = _derive_rhythm([1, 8, 22], 23)
    assert r["ambiguous"] is True


def test_build_spec_v2_no_calendar_fields():
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(make_line_df(), "09", D)
    validate_obj(spec, "problem")
    # 日历无关: 全文不允许出现 ISO 日期
    assert "2026-07" not in str(spec)
    assert spec["cycle"]["n_days"] == 2
    assert spec["stores"][0]["rhythm"] == {"period": 1, "phase": 1,
                                            "visits_per_period": 1,
                                            "ambiguous": False,
                                            "source": "derived"}
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
