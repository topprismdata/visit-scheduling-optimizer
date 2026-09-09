import copy
import pytest
from svc.schemas.validate import validate_obj, SchemaError

MIN_PROBLEM = {
    "schema": "visitflow/problem", "version": "2.0",
    "inputs_hash": "sha256:ab", "line_id": "09",
    "cycle": {"n_days": 1},
    "stores": [{"id": 0, "code": "C001", "lon": 113.25, "lat": 23.05,
                 "rhythm": {"period": 1, "phase": 1, "visits_per_period": 1,
                             "ambiguous": False, "source": "derived"}}],
    "corridor": {"min_daily": 2, "max_daily": 3},
    "original_assignment_idx": {"1": [0]},
    "distance": {"kind": "osm_cycling", "scope": "per-line",
                  "matrix_ref": "sha256:cd", "format": "npz", "n": 1,
                  "unreachable_sentinel": 1e9},
    "meta": {"n_stores": 1, "n_visits": 3},
}
MIN_MODEL = {
    "schema": "visitflow/model", "version": "1.0",
    "problem_hash": "sha256:ab",
    "formulation": {"kind": "fixed-row-v2", "vars": {}},
    "legal_domain": {"pairs_total": 1, "pairs_legal": 1, "fixed": 0},
    "feasibility_precheck": {"capacity_ok": True, "contract_ok": True,
                              "corridor_ok": True},
    "meta": {"compile_ms": 1},
}
MIN_SOLUTION = {
    "schema": "visitflow/solution", "version": "1.0",
    "problem_hash": "sha256:ab", "model_hash": "sha256:cd",
    "status": "FEASIBLE",
    "assignment": {"2026-07-01": {"route_idx": [0], "route_codes": ["C001"],
                                   "km": 0.0}},
    "totals": {"km": 0.0, "vs_original_pct": 0.0, "moved_stores": 0},
    "gates": {"count_ok": True, "capacity_ok": True, "r2_ok": True,
               "contract_ok": True, "structure_ok": True},
    "runtime": {"engine": "r2_alns", "engine_version": "git:x",
                 "stage_versions": {}, "seeds": [42], "budget_s": 1,
                 "iters": 1, "wall_sec": 0.1},
    "certificates": {"pool_lp": None, "certified_global_lb": None,
                      "global_gap_pct": None},
    "output_hash": "sha256:ef",
    "meta": {},
}


def test_problem_spec_valid():
    validate_obj(copy.deepcopy(MIN_PROBLEM), "problem")


def test_problem_spec_rejects_bad_rhythm_period():
    bad = copy.deepcopy(MIN_PROBLEM)
    bad["stores"][0]["rhythm"]["period"] = 0
    with pytest.raises(SchemaError):
        validate_obj(bad, "problem")


def test_model_and_solution_valid():
    validate_obj(copy.deepcopy(MIN_MODEL), "model")
    validate_obj(copy.deepcopy(MIN_SOLUTION), "solution")


def test_solution_rejects_failed_gates_with_feasible_status():
    bad = copy.deepcopy(MIN_SOLUTION)
    bad["gates"]["contract_ok"] = False
    with pytest.raises(SchemaError):
        validate_obj(bad, "solution")


def test_unknown_schema_name():
    with pytest.raises(SchemaError):
        validate_obj({}, "nope")
