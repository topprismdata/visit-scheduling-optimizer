"""合成 line_df: 4 店, 2 日 (2026-07-01 周三, 2026-07-02 周四)."""
import numpy as np
import pandas as pd
import pytest
from svc.schemas.validate import validate_obj
from svc.stages.semantic import build_spec_from_df

DATES = [pd.Timestamp("2026-07-01").date(), pd.Timestamp("2026-07-02").date()]


def make_line_df():
    rows = []
    plan_map = {0: DATES, 1: DATES, 2: DATES[:1], 3: DATES[1:]}
    for sid, ds in plan_map.items():
        for di, dd in enumerate(ds):
            rows.append({
                "客户编码": f"C00{sid}", "销售名称": "海珠荔湾09",
                "经度": 113.25 + sid * 0.01, "纬度": 23.05 + sid * 0.01,
                "拜访顺序": di + 1, "date": dd,
                "拜访日期": dd.strftime("%Y-%m-%d"),
            })
    return pd.DataFrame(rows)


def test_build_spec_schema_valid_and_hashes():
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(make_line_df(), "09", D)
    validate_obj(spec, "problem")
    assert spec["line_id"] == "09"
    assert spec["calendar"]["n_days"] == 2
    assert len(spec["stores"]) == 4
    assert spec["stores"][0]["contract"]["required_visits"] == 2
    assert spec["stores"][2]["contract"]["required_visits"] == 1
    assert spec["stores"][2]["contract"]["kind"] in ("W", "B")
    # legal_date_map 实测语义: 微型日历下 W 店合法域 = 全日期 (union over weekdays)
    assert spec["stores"][2]["legal_dates_idx"] == [0, 1]
    # 店 0/1 两天都拜访, 店 2 仅 07-01
    assert spec["original_assignment"]["2026-07-01"] == [0, 1, 2]
    assert spec["original_assignment"]["2026-07-02"] == [0, 1, 3]
    assert spec["distance"]["n"] == 4
    spec2 = build_spec_from_df(make_line_df(), "09", D)
    assert spec["inputs_hash"] == spec2["inputs_hash"]


def test_build_spec_deterministic_store_order():
    df = make_line_df().sample(frac=1.0, random_state=7)
    D = np.zeros((4, 4))
    spec = build_spec_from_df(df, "09", D)
    assert [s["code"] for s in spec["stores"]] == ["C000", "C001", "C002", "C003"]
