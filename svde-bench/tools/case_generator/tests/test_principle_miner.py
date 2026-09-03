"""Sprint 3.4-A Acceptance Test: Offline Decision Principle Mining & Evidence Traceability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.principle_miner import DecisionPrincipleMiner, CandidatePrinciple
from svdebench.agents.baseline import (
    GeneralizedPureSolverAgent,
    GeneralizedSemanticAwareAgent,
    GeneralizedFullDecisionAgent,
)

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_offline_principle_mining_from_delivery_and_visit_profiles():
    """Validates that candidate decision principles are mined blindly from execution profiles with traceable evidence."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    miner = DecisionPrincipleMiner()

    # 1. Ingest Delivery profiles across 3 agents
    for i in range(1, 11):
        case_dir = DELIVERY_CASES_DIR / f"D{i:02d}"
        for ag_cls in [GeneralizedPureSolverAgent, GeneralizedSemanticAwareAgent, GeneralizedFullDecisionAgent]:
            res = pipeline.run_case_dir(case_dir, agent_cls=ag_cls)
            miner.ingest_profile(res["profile"], case_id=f"D{i:02d}", domain="delivery")

    # 2. Ingest Visit profiles across 3 agents
    for i in range(1, 11):
        case_dir = VISIT_CASES_DIR / f"V{i:02d}"
        for ag_cls in [GeneralizedPureSolverAgent, GeneralizedSemanticAwareAgent, GeneralizedFullDecisionAgent]:
            res = pipeline.run_case_dir(case_dir, agent_cls=ag_cls)
            miner.ingest_profile(res["profile"], case_id=f"V{i:02d}", domain="visit")

    assert len(miner.raw_profiles) == 60  # 20 cases * 3 agents

    # 3. Mine candidate principles
    principles = miner.mine_candidate_principles()
    assert len(principles) >= 3, f"Expected >= 3 principles, mined {len(principles)}"

    # 4. Verify properties of mined principles
    for p in principles:
        assert isinstance(p, CandidatePrinciple)
        assert p.principle_id.startswith("DISC-PRIN-")
        assert len(p.dilemma_archetype) > 0
        assert len(p.abstract_governing_rule) > 0
        assert len(p.tradeoff_sacrifice) > 0  # MP-G3 non-triviality check
        assert len(p.invalidation_boundary) > 0  # MP-G2 boundary check
        assert p.semantic_preservation_score >= 0.90  # MP-G6 semantic preservation check
        assert len(p.supporting_episodes) >= 2  # Bidirectional evidence traceability
        
        # Verify evidence traceability links back to real case IDs
        for ep in p.supporting_episodes:
            assert "case_id" in ep
            assert "domain" in ep
