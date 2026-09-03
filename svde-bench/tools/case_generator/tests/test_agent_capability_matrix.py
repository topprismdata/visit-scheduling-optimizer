"""Sprint 2.3 Acceptance Test: 3 Agents x 10 Cases Decision Capability Matrix & Separation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from svdebench.agents.baseline import (
    GeneralizedPureSolverAgent,
    GeneralizedSemanticAwareAgent,
    GeneralizedFullDecisionAgent,
)

CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"


def test_decision_capability_matrix_separation():
    """Validates clear separation across Semantic, Runtime, and Memory dimensions for 3 Agent archetypes."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    
    # Run all 10 cases across the 3 baseline agents
    for i in range(1, 11):
        case_dir = CASES_DIR / f"D{i:02d}"
        
        out_pure = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedPureSolverAgent)
        out_aware = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedSemanticAwareAgent)
        out_full = pipeline.run_case_dir(case_dir, agent_cls=GeneralizedFullDecisionAgent)

        prof_pure = out_pure["profile"]
        prof_aware = out_aware["profile"]
        prof_full = out_full["profile"]

        # 1. Semantic separation: PureSolver drops commitments -> Semantic score 0.0 vs SemanticAware 1.0
        assert prof_pure["evaluation"]["semantic"]["score"] == 0.0, f"PureSolver should fail semantic in D{i:02d}"
        assert prof_aware["evaluation"]["semantic"]["score"] == 1.0, f"SemanticAware should pass semantic in D{i:02d}"
        assert prof_full["evaluation"]["semantic"]["score"] == 1.0, f"FullDecision should pass semantic in D{i:02d}"

        # 2. Runtime separation: PureSolver drops commitments -> Commitment survival 0.0 vs 1.0
        assert prof_pure["evaluation"]["runtime"]["score"] == 0.0
        assert prof_aware["evaluation"]["runtime"]["score"] == 1.0
        assert prof_full["evaluation"]["runtime"]["score"] == 1.0

        # 3. Memory dimension: FullDecisionAgent admits validated memory (confidence > 0.95)
        assert prof_full["evaluation"]["memory"]["score"] >= 0.95
        assert prof_full["evaluation"]["memory"]["admitted_memory"]["promotion_status"] == "PROMOTED"

        # 4. Overall Grade differentiation (except D02 which is mathematically INFEASIBLE by design)
        if f"D{i:02d}" != "D02":
            assert prof_pure["overall"]["grade"] == "F"
            assert prof_aware["overall"]["grade"] == "A"
            assert prof_full["overall"]["grade"] == "A"
        else:
            # D02 capacity strictly exceeded -> All agents reflect INFEASIBLE grade F
            assert prof_pure["overall"]["grade"] == "F"
            assert prof_aware["overall"]["grade"] == "F"
            assert prof_full["overall"]["grade"] == "F"
