"""Tests for SVDE Real-Data Precheck & Automated decide() Integration."""
import sys
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import svde
from svde.contracts import DecisionRequest, DecisionArtifact, CompilationError
from svde.verification.data_precheck import DataPrecheckValidator


def test_decide_automatically_runs_precheck_and_rejects_bad_data():
    """Gap 1 Fix: Calling svde.decide() with bad data automatically raises CompilationError from precheck."""
    bad_req = DecisionRequest(
        request_id="AUTO-PRECHECK-FAIL",
        domain="delivery",
        intent={"primary_objective": "test"},
        world_state={
            "fleet": [{"id": "V1", "capacity_kg": -50.0}],  # Negative capacity
            "orders": [{"id": "O1", "weight_kg": 100}]
        }
    )

    with pytest.raises(CompilationError) as excinfo:
        svde.decide(bad_req)
    assert "Pre-flight data validation failed" in str(excinfo.value)
    assert "must be non-negative numeric" in str(excinfo.value)


def test_routing_precheck_requires_depot_and_full_matrix():
    """Gap 2 Fix: Routing precheck asserts depot presence and full edge matrix connectivity."""
    validator = DataPrecheckValidator()

    # Case A: Missing depot in routing domain
    no_depot_req = DecisionRequest(
        request_id="NO-DEPOT-REQ",
        domain="city_routing",
        intent={},
        world_state={
            "stops": [{"id": "STOP_A", "is_depot": False}],
            "distance_matrix": {"STOP_A": {"STOP_A": 0.0}}
        }
    )
    rep_a = validator.validate(no_depot_req)
    assert rep_a.is_valid is False
    assert any("explicit depot" in e.message for e in rep_a.errors)

    # Case B: Incomplete edge matrix (missing STOP_B -> STOP_A)
    incomplete_matrix_req = DecisionRequest(
        request_id="INCOMPLETE-MAT-REQ",
        domain="city_routing",
        intent={},
        world_state={
            "stops": [{"id": "DEPOT", "is_depot": True}, {"id": "STOP_A"}, {"id": "STOP_B"}],
            "distance_matrix": {
                "DEPOT": {"STOP_A": 10.0, "STOP_B": 20.0},
                "STOP_A": {"DEPOT": 10.0, "STOP_B": 5.0}
                # Missing STOP_B row!
            }
        }
    )
    rep_b = validator.validate(incomplete_matrix_req)
    assert rep_b.is_valid is False
    assert any("Missing distance matrix row for stop 'STOP_B'" in e.message for e in rep_b.errors)
