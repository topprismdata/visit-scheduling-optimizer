"""Sprint 5.4 Acceptance Test: Data-Driven Principle Mining v2 & Contrastive Induction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.principle_miner_v2 import DataDrivenPrincipleMinerV2
from tools.case_generator.principle_governance import PrincipleGovernancePipeline
from agents.real.llm_agent import LLMDecisionAgent
from agents.real.solver_agent import ConstrainedSolverAgent
from svdebench.agents.baseline import GeneralizedPureSolverAgent

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_data_driven_principle_miner_v2_contrastive_induction():
    """Validates that DataDrivenPrincipleMinerV2 calculates mutual information and induces principles from contrastive execution traces."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    miner_v2 = DataDrivenPrincipleMinerV2()

    # Ingest profiles across D01-D08 and V01-V05
    for i in range(1, 9):
        d_path = DELIVERY_CASES_DIR / f"D{i:02d}"
        
        # 1. Pure solver (Negative contrastive examples: drops commitments)
        res_pure_d = pipeline.run_case_dir(d_path, agent_cls=GeneralizedPureSolverAgent)
        miner_v2.ingest_profile(res_pure_d["profile"], case_id=f"D{i:02d}-PURE", domain="delivery")

        # 2. Solver agent (Positive contrastive examples: preserves commitments)
        res_solver_d = pipeline.run_case_dir(d_path, agent_cls=ConstrainedSolverAgent)
        miner_v2.ingest_profile(res_solver_d["profile"], case_id=f"D{i:02d}-SOLVER", domain="delivery")

    for i in range(1, 6):
        v_path = VISIT_CASES_DIR / f"V{i:02d}"
        # 3. LLM agent on visit
        res_llm_v = pipeline.run_case_dir(v_path, agent_cls=LLMDecisionAgent)
        miner_v2.ingest_profile(res_llm_v["profile"], case_id=f"V{i:02d}-LLM", domain="visit")

    assert len(miner_v2.profile_vectors) == 21  # 8*2 + 5 = 21 vectors

    # Calculate contrastive mutual information
    mi_commitment = miner_v2.compute_mutual_information("action_preserved_commitments", "semantic_pass")
    assert mi_commitment > 0.10, f"Expected significant MI for commitment preservation, got {mi_commitment}"

    # Induce candidate principles
    inducted_principles = miner_v2.induce_governing_principles()
    assert len(inducted_principles) >= 2

    # Verify induced principles pass MDVL governance
    gov = PrincipleGovernancePipeline(min_evidence_traces=2, min_semantic_preservation=0.90)
    decisions = gov.evaluate_batch(inducted_principles)

    promoted = [d for d in decisions if d.status == "PROMOTED"]
    assert len(promoted) >= 2
    assert any(p.principle_id == "DISC-PRIN-001" for p in promoted)
