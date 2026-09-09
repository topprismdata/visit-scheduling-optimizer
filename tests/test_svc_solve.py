"""端到端 mini: 合成 spec → R2-ALNS → SolutionBundle (五道闸 + 重排口径)."""
import numpy as np
import pandas as pd
import pytest
from svc.hashing import sha256_of
from svc.schemas.validate import validate_obj
from svc.stages.semantic import build_spec_from_df
from svc.stages.model import build_manifest
from svc.stages.solve import solve_spec

DATES = [pd.Timestamp("2026-07-01").date(), pd.Timestamp("2026-07-02").date()]


def make_spec():
    rows = []
    # 每店恰一天 (派生合同全为 W, 微型日历下 check_contract 可过)
    plan_map = {0: DATES[:1], 1: DATES[:1], 2: DATES[1:], 3: DATES[1:]}
    for sid, ds in plan_map.items():
        for di, dd in enumerate(ds):
            rows.append({"客户编码": f"C00{sid}", "销售名称": "海珠荔湾09",
                          "经度": 113.25 + sid * 0.01, "纬度": 23.05 + sid * 0.01,
                          "拜访顺序": di + 1, "date": dd,
                          "拜访日期": dd.strftime("%Y-%m-%d")})
    df = pd.DataFrame(rows)
    D = np.array([[0, 2, 3, 4], [2, 0, 1, 2], [3, 1, 0, 1], [4, 2, 1, 0]],
                  dtype=float)
    spec = build_spec_from_df(df, "09", D)
    return spec, D


def test_solve_end_to_end_mini():
    spec, D = make_spec()
    model = build_manifest(spec)
    bundle = solve_spec(spec, D, model_hash=sha256_of(model), seeds=[42],
                         budget_s=2, cp_timeout=5, engine_version="git:test")
    validate_obj(bundle, "solution")
    assert bundle["status"] == "FEASIBLE"
    # 哈希链
    assert bundle["problem_hash"] == sha256_of(spec)
    assert bundle["model_hash"] == sha256_of(model)
    # 双出: 索引 + 编码
    day0 = bundle["assignment"]["1"]
    assert len(day0["route_idx"]) == len(day0["route_codes"])
    assert day0["route_codes"] == [f"C00{i}" for i in day0["route_idx"]]
    # 五道闸全过才允许 FEASIBLE
    assert all(bundle["gates"].values())
    # km 与重排后路线一致
    assert abs(bundle["totals"]["km"] -
               sum(d["km"] for d in bundle["assignment"].values())) < 1e-6


def test_solve_deterministic_same_seed():
    spec, D = make_spec()
    a = solve_spec(spec, D, model_hash="sha256:x", seeds=[42], budget_s=1,
                    cp_timeout=5, engine_version="git:test")
    b = solve_spec(spec, D, model_hash="sha256:x", seeds=[42], budget_s=1,
                    cp_timeout=5, engine_version="git:test")
    assert a["output_hash"] == b["output_hash"]


def test_structure_gate_sentinel_arc_fails():
    """哨兵弧 (不可达对) 出现在路线中 -> structure_ok=False -> FAILED."""
    from svc.stages.solve import _compute_gates
    import datetime as _dt
    from core.contract import contract_of
    spec, D = make_spec()
    D2 = D.copy()
    D2[0][1] = D2[1][0] = 1e9   # 店 0-1 之间不可达
    dates = [_dt.date(2000, 1, 1), _dt.date(2000, 1, 2)]
    days_orig = {dates[0]: [0, 1], dates[1]: [2, 3]}
    gates = _compute_gates({1: [0, 1], 2: [2, 3]}, dates, spec,
                            contract_of(days_orig, dates), D2, True)
    assert gates["structure_ok"] is False
    assert gates["capacity_ok"] is True
