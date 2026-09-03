"""Sprint 3.4-B Acceptance Test: Principle Governance Pipeline & Counterfactual Validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.principle_miner import DecisionPrincipleMiner, CandidatePrinciple
from tools.case_generator.principle_governance import PrincipleGovernancePipeline, GovernanceDecision
from tools.case_generator.pipeline_runner import FullPipelineRunner
from svdebench.agents.baseline import GeneralizedFullDecisionAgent

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_candidate_principles_governance_evaluation():
    """Validates that mined candidate principles undergo complete MP-G1..G6 governance and counterfactual validation."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    miner = DecisionPrincipleMiner()

    # Ingest profiles across full D01-D10 and V01-V10 to cover all 3 dilemma archetypes
    for i in range(1, 11):
        d_res = pipeline.run_case_dir(DELIVERY_CASES_DIR / f"D{i:02d}", agent_cls=GeneralizedFullDecisionAgent)
        v_res = pipeline.run_case_dir(VISIT_CASES_DIR / f"V{i:02d}", agent_cls=GeneralizedFullDecisionAgent)
        miner.ingest_profile(d_res["profile"], case_id=f"D{i:02d}", domain="delivery")
        miner.ingest_profile(v_res["profile"], case_id=f"V{i:02d}", domain="visit")

    candidates = miner.mine_candidate_principles()
    assert len(candidates) >= 3

    # Run Governance Pipeline
    gov = PrincipleGovernancePipeline(min_evidence_traces=2, min_semantic_preservation=0.90)
    decisions = gov.evaluate_batch(candidates)
    assert len(decisions) == len(candidates)

    for dec in decisions:
        assert isinstance(dec, GovernanceDecision)
        assert dec.status in ["PROMOTED", "CANDIDATE", "REJECTED"]
        assert "MP-G1_EvidenceSufficiency" in dec.gate_results
        assert "MP-G2_ContextBoundary" in dec.gate_results
        assert "MP-G3_NonVacuity" in dec.gate_results
        assert "MP-G4_FalsificationIntegrity" in dec.gate_results
        assert "MP-G5_NegativeTransferResistance" in dec.gate_results
        assert "MP-G6_SemanticPreservation" in dec.gate_results
        assert dec.counterfactual_test_passed is True
        assert dec.conflict_resolution_tier in [1, 2, 3]


def test_governance_rejects_flawed_candidate_principles():
    """Falsification Check: Confirms that vacuous, unbounded, or low-evidence principles are strictly rejected/held."""
    gov = PrincipleGovernancePipeline(min_evidence_traces=3, min_semantic_preservation=0.90)

    # 1. Tautological / Vacuous candidate (fails MP-G3)
    vacuous_candidate = CandidatePrinciple(
        principle_id="DISC-VACUOUS",
        dilemma_archetype="TAUTOLOGY",
        trigger_condition={},
        abstract_governing_rule="Always find a feasible solution to satisfy all stakeholders.",
        tradeoff_sacrifice="", # No sacrifice declared
        invalidation_boundary="Never invalid",
        supporting_episodes=[{"case_id": "D01", "domain": "delivery"}] * 3,
        semantic_preservation_score=1.0
    )
    dec_vacuous = gov.evaluate_candidate_principle(vacuous_candidate)
    assert dec_vacuous.status == "REJECTED"
    assert any("MP-G3" in r for r in dec_vacuous.rejection_reasons)

    # 2. Over-generalized wildcard boundary candidate (fails MP-G2)
    unbounded_candidate = CandidatePrinciple(
        principle_id="DISC-UNBOUNDED",
        dilemma_archetype="UNBOUNDED",
        trigger_condition={},
        abstract_governing_rule="Prioritize commitments across all domains.",
        tradeoff_sacrifice="Accepts overtime cost.",
        invalidation_boundary="*", # Wildcard scope
        supporting_episodes=[{"case_id": "D01", "domain": "delivery"}] * 3,
        semantic_preservation_score=1.0
    )
    dec_unbounded = gov.evaluate_candidate_principle(unbounded_candidate)
    assert dec_unbounded.status == "REJECTED"
    assert any("MP-G2" in r for r in dec_unbounded.rejection_reasons)

    # 3. Low evidence trace candidate (fails MP-G1 -> CANDIDATE)
    low_evidence_candidate = CandidatePrinciple(
        principle_id="DISC-LOW-EV",
        dilemma_archetype="PRELIMINARY",
        trigger_condition={},
        abstract_governing_rule="Specialist reps must visit hospitals.",
        tradeoff_sacrifice="Accepts transit expense.",
        invalidation_boundary="Invalid when zero hospital visits exist.",
        supporting_episodes=[{"case_id": "V03", "domain": "visit"}], # Only 1 trace < 3 threshold
        semantic_preservation_score=0.95
    )
    dec_low_ev = gov.evaluate_candidate_principle(low_evidence_candidate)
    assert dec_low_ev.status == "CANDIDATE"
    assert dec_low_ev.confidence_score == 0.60
