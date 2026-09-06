"""Day 2 Acceptance Test: Minimal fixture completes full pipeline and produces deterministic DecisionProfile."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.oracle_runner import OracleRunner
from svdebench.agents.baseline import SemanticAwareAgent, PureSolverMockAgent

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "minimal_case"


def test_oracle_runner_solves_fixture():
    runner = OracleRunner(timeout_sec=30)
    res = runner.run_directory(FIXTURE)
    assert res.status in ["OPTIMAL", "FEASIBLE"], f"Oracle status unexpected: {res.status}"
    assert res.runtime_sec > 0.0
    assert res.case_id == "FIXTURE-MINIMAL-001"


def test_full_pipeline_produces_valid_profile():
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    out = pipeline.run_case_dir(FIXTURE, agent_cls=SemanticAwareAgent)
    
    assert out["ok"] is True
    assert "profile" in out
    
    prof = out["profile"]
    assert "decision_profile" in prof
    assert "evaluation" in prof
    assert "overall" in prof
    assert "failure_analysis" in prof
    assert "reproducibility" in prof

    # Core required evaluation dimensions
    ev = prof["evaluation"]
    assert "semantic" in ev and "evidence" in ev["semantic"]
    assert "feasibility" in ev
    assert "runtime" in ev
    assert "memory" in ev
    
    # Evidence must NOT be omitted
    assert ev["semantic"]["evidence"] is not None and len(ev["semantic"]["evidence"]) > 0


def test_pipeline_decision_differentiation():
    """Confirms agent differentiation: SemanticAwareAgent vs PureSolverMockAgent."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    out_aware = pipeline.run_case_dir(FIXTURE, agent_cls=SemanticAwareAgent)
    out_pure = pipeline.run_case_dir(FIXTURE, agent_cls=PureSolverMockAgent)

    prof_aware = out_aware["profile"]
    prof_pure = out_pure["profile"]

    # SemanticAwareAgent honors semantic constraints -> Grade A
    # PureSolverMockAgent ignores semantic locks -> Grade F or lower
    assert prof_aware["overall"]["grade"] == "A"
    assert prof_pure["overall"]["grade"] in ["F", "D"]


def test_pipeline_is_deterministic():
    """Gate 6: Running the full pipeline twice on the same case yields identical Profiles."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    r1 = pipeline.run_case_dir(FIXTURE, agent_cls=SemanticAwareAgent)
    r2 = pipeline.run_case_dir(FIXTURE, agent_cls=SemanticAwareAgent)

    p1 = r1["profile"]
    p2 = r2["profile"]

    assert p1["overall"] == p2["overall"]
    assert p1["evaluation"]["semantic"]["score"] == p2["evaluation"]["semantic"]["score"]
    assert p1["evaluation"]["feasibility"]["score"] == p2["evaluation"]["feasibility"]["score"]
    assert p1["evaluation"]["runtime"]["score"] == p2["evaluation"]["runtime"]["score"]
    assert p1["failure_analysis"] == p2["failure_analysis"]
