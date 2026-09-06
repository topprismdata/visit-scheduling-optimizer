"""Sprint 2.4 Acceptance Test: Benchmark Robustness & Multi-Tier Separation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from svdebench.agents.baseline import (
    GeneralizedPureSolverAgent,
    ConstraintAwareAgent,
    GeneralizedSemanticAwareAgent,
    GeneralizedFullDecisionAgent,
)
from svdebench.agents.baseline.memory_ablation_agents import (
    FullDecisionAgentWithoutMemory,
    StaleMemoryAgent,
    WeakEvidenceMemoryAgent,
)

CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"


def test_four_tier_agent_continuum():
    """Task 1: Validates continuum across 4 Agent archetypes (Pure -> Constraint -> Semantic -> Full)."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    
    for c in ["D01", "D03", "D04", "D05", "D07"]:
        case_dir = CASES_DIR / c
        out_pure = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedPureSolverAgent)
        out_ca = pipeline.run_case_dir(case_dir, agent_cls=ConstraintAwareAgent)
        out_sem = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedSemanticAwareAgent)
        out_full = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedFullDecisionAgent)

        # Pure solver fails semantic
        assert out_pure["profile"]["evaluation"]["semantic"]["score"] == 0.0
        # Constraint aware honors physical rules
        assert out_ca["profile"]["evaluation"]["feasibility"]["score"] == 0.0
        # Semantic aware and Full decision pass semantic
        assert out_sem["profile"]["evaluation"]["semantic"]["score"] == 1.0
        assert out_full["profile"]["evaluation"]["semantic"]["score"] == 1.0


def test_memory_ablation_comparison():
    """Task 3: FullDecisionAgent with Memory vs without Memory ablation test."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    case_dir = CASES_DIR / "D09"

    out_with_mem = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedFullDecisionAgent)
    out_no_mem = pipeline.run_case_dir(case_dir, agent_cls=FullDecisionAgentWithoutMemory)

    prof_with = out_with_mem["profile"]
    prof_no = out_no_mem["profile"]

    # Both have high semantic and runtime scores
    assert prof_with["evaluation"]["semantic"]["score"] == 1.0
    assert prof_no["evaluation"]["semantic"]["score"] == 1.0

    # With memory produces PROMOTED artifact; without memory is NONE_REQUIRED
    assert prof_with["evaluation"]["memory"]["admitted_memory"]["promotion_status"] == "PROMOTED"
    assert prof_no["evaluation"]["memory"]["admitted_memory"]["promotion_status"] == "NONE_REQUIRED"


def test_memory_multi_outcome_categories():
    """Task 4: Validates multi-category memory outcomes (PROMOTED / REJECTED / CANDIDATE)."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    case_dir = CASES_DIR / "D10"

    out_promoted = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedFullDecisionAgent)
    out_rejected = pipeline.run_case_dir(case_dir, agent_cls=StaleMemoryAgent)
    out_candidate = pipeline.run_case_dir(case_dir, agent_cls=WeakEvidenceMemoryAgent)

    status_p = out_promoted["profile"]["evaluation"]["memory"]["admitted_memory"]["promotion_status"]
    status_r = out_rejected["profile"]["evaluation"]["memory"]["admitted_memory"]["promotion_status"]
    status_c = out_candidate["profile"]["evaluation"]["memory"]["admitted_memory"]["promotion_status"]

    assert status_p == "PROMOTED", f"Expected PROMOTED, got {status_p}"
    assert status_r == "REJECTED", f"Expected REJECTED, got {status_r}"
    assert status_c == "CANDIDATE", f"Expected CANDIDATE, got {status_c}"

    # Scores reflect outcome quality
    assert out_promoted["profile"]["evaluation"]["memory"]["score"] >= 0.95
    assert out_rejected["profile"]["evaluation"]["memory"]["score"] == 0.0
    assert out_candidate["profile"]["evaluation"]["memory"]["score"] == 0.50
