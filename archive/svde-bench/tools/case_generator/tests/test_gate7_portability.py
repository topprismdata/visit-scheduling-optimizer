"""Day 3 Acceptance Test: Gate 7 Portability Test.

Proves that an independent second fixture in a different domain (visit scheduling)
executes through the complete benchmark pipeline (validation -> oracle -> agent -> evaluation -> profile)
without requiring any code modifications to the pipeline.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.schema_validator import validate_case
from tools.case_generator.oracle_runner import OracleRunner

VISIT_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "visit_case"


def test_gate7_second_fixture_validates_cleanly():
    """Gate 7.1: Second fixture passes Schema and Decision-Completeness validation."""
    res = validate_case(VISIT_FIXTURE)
    assert res.ok(), f"Visit fixture validation failed: {res.errors}"


def test_gate7_second_fixture_oracle_solves():
    """Gate 7.2: Second fixture solves cleanly with Oracle without code changes."""
    runner = OracleRunner(timeout_sec=30)
    res = runner.run_directory(VISIT_FIXTURE)
    assert res.status in ["OPTIMAL", "FEASIBLE"], f"Oracle failed on second fixture: {res.status}"
    assert res.case_id == "FIXTURE-VISIT-001"


def test_gate7_second_fixture_full_pipeline_portability():
    """Gate 7.3: Full pipeline produces valid DecisionProfile on second fixture."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    out = pipeline.run_case_dir(VISIT_FIXTURE)
    
    assert out["ok"] is True, f"Pipeline failed on visit fixture: {out}"
    assert out["case_id"] == "FIXTURE-VISIT-001"
    assert out["oracle_status"] in ["OPTIMAL", "FEASIBLE"]
    
    prof = out["profile"]
    assert prof["decision_profile"]["domain"] == "visit"
    assert prof["decision_profile"]["case_id"] == "FIXTURE-VISIT-001"
    assert "evaluation" in prof
    assert "semantic" in prof["evaluation"]
    assert "feasibility" in prof["evaluation"]
    assert "runtime" in prof["evaluation"]
    assert "memory" in prof["evaluation"]
    assert prof["reproducibility"]["deterministic"] is True
