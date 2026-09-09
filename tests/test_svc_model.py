import json
from pathlib import Path

import pytest
from svc.hashing import sha256_of
from svc.schemas.validate import validate_obj
from svc.stages.model import build_manifest

SCHEMA_DIR = Path("svc/schemas")


def min_problem():
    return {
        "schema": "visitflow/problem", "version": "2.1",
        "inputs_hash": "sha256:ab", "line_id": "09",
        "cycle": {"n_days": 1},
        "stores": [{"id": 0, "code": "C001", "lon": 113.25, "lat": 23.05,
     "frequency": {"horizon": 1, "visits": 1, "pattern": "1",
                    "ambiguous": False, "source": "derived"}}],
        "corridor": {"min_daily": 2, "max_daily": 3},
    "objective": {"sense": "min", "metric": "total_route_km"},
        "original_assignment_idx": {"1": [0]},
        "distance": {"kind": "osm_cycling", "scope": "per-line",
                      "matrix_ref": "sha256:cd", "format": "npz", "n": 1,
                      "unreachable_sentinel": 1e9},
        "meta": {"n_stores": 1, "n_visits": 3},
    }


def test_manifest_schema_valid_and_pure():
    spec = min_problem()
    m = build_manifest(spec)
    validate_obj(m, "model")
    assert m["problem_hash"] == sha256_of(spec)
    # 建模层纯净: 不含引擎提示 (spec v0.2 修正 4)
    assert "solver_hints" not in m
    pre = m["feasibility_precheck"]
    assert pre["capacity_max_ok"] and pre["corridor_ok"]
    # 完整数学模型定义: 集合/变量/目标/约束一个不少
    assert m["sets"]["D"]["size"] == 1 and m["sets"]["C"]["size"] == 1
    assert m["decision_variables"]["y_cd"]["count"] == 1
    assert m["objective"]["sense"] == "min"
    assert set(m["constraints"]) == {"frequency_total", "spacing",
                                      "corridor_min", "corridor_max",
                                      "r2_single_phase", "legality"}
    assert m["constraints"]["corridor_min"]["rows"] == 1
    # 每店参数表
    assert m["store_parameters"][0]["visits_total_target"] == 1


def test_manifest_flags_infeasible_capacity():
    spec = min_problem()
    spec["stores"].append(dict(spec["stores"][0], id=1, code="C002"))
    spec["meta"]["n_stores"] = 2
    spec["corridor"]["max_daily"] = 1   # 2 家店每天最多 1 次, 需求 2 次 -> 不可行
    m = build_manifest(spec)
    assert m["feasibility_precheck"]["capacity_max_ok"] is False
