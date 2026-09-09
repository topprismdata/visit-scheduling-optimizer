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
    assert pre["capacity_ok"] and pre["contract_ok"] and pre["corridor_ok"]
    # 合法域统计: 1 店 × 1 日 = 1 对, 全合法
    assert m["legal_domain"]["pairs_total"] == 1
    assert m["legal_domain"]["pairs_legal"] == 1
    assert m["legal_domain"]["fixed"] == 0


def test_manifest_flags_infeasible_corridor():
    spec = min_problem()
    spec["corridor"]["min_daily"] = 5   # 1 店 < 走廊下限
    m = build_manifest(spec)
    assert m["feasibility_precheck"]["corridor_ok"] is False
