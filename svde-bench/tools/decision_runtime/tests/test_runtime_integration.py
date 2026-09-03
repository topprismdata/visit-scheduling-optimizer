"""Sprint 4.1 Acceptance Test: Runtime Principle Integration & Negative Transfer Defense."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.case_generator.blind_generalization_runner import RawEpisodeMemoryAgent
from tools.decision_runtime.principle_store import PrincipleStore, StoredPrinciple
from tools.decision_runtime.principle_matcher import PrincipleMatcher
from tools.decision_runtime.governed_principle_agent import GovernedPrincipleDecisionAgent
from tools.decision_runtime.decision_context import DecisionContext
from svdebench.core import DecisionCase

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_principle_store_and_matcher():
    """Validates that PrincipleStore loads defaults and PrincipleMatcher matches cases by features."""
    store = PrincipleStore()
    promoted = store.get_promoted_principles()
    assert len(promoted) == 3
    assert any(p.principle_id == "DISC-PRIN-001" for p in promoted)

    matcher = PrincipleMatcher(store)
    
    # Create test DecisionCase with locked commitments & realistic contention (> 0.2)
    test_case = DecisionCase.from_dict({
        "metadata": {"id": "TEST-D01", "domain": "delivery", "name": "Test", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "test"},
        "world_state": {
            "fleet": [{"id": "V1", "capacity_kg": 500, "status": "AVAILABLE"}],
            "orders": [
                {"id": "O1", "weight_kg": 250, "is_locked": True},
                {"id": "O2", "weight_kg": 150, "is_locked": False}
            ]
        },
        "semantic_contract": {"constraints": []}
    })

    ctx = DecisionContext.from_decision_case(test_case)
    matched, trace = matcher.match_with_trace(ctx)
    assert len(matched) >= 1
    assert matched[0].principle_id == "DISC-PRIN-001"


def test_governed_principle_agent_runtime_execution():
    """Validates GovernedPrincipleDecisionAgent execution through the benchmark pipeline."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    agent = GovernedPrincipleDecisionAgent()

    for c_dir in [DELIVERY_CASES_DIR / "D01", VISIT_CASES_DIR / "V01", DELIVERY_CASES_DIR / "D03", VISIT_CASES_DIR / "V04"]:
        res = pipeline.run_case_dir(c_dir, agent_cls=lambda: agent)
        assert res["ok"] is True
        assert res["profile"]["overall"]["grade"] == "A"
        assert res["profile"]["evaluation"]["semantic"]["score"] == 1.0


def test_governed_principle_agent_outperforms_raw_episode_on_negative_transfer():
    """
    Core Sprint 4.1 Requirement:
    Proves GovernedPrincipleDecisionAgent (Grade A) strictly outperforms RawEpisodeMemoryAgent (Grade F)
    on D10 and V10 negative transfer cases.
    """
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    gov_agent = GovernedPrincipleDecisionAgent()
    raw_agent = RawEpisodeMemoryAgent(raw_episodes=[{"source": "stale_history"}])

    for c_dir in [DELIVERY_CASES_DIR / "D10", VISIT_CASES_DIR / "V10"]:
        res_gov = pipeline.run_case_dir(c_dir, agent_cls=lambda: gov_agent)
        res_raw = pipeline.run_case_dir(c_dir, agent_cls=lambda: raw_agent)

        prof_gov = res_gov["profile"]
        prof_raw = res_raw["profile"]

        # Governed Principle resists poison and achieves Grade A
        assert prof_gov["overall"]["grade"] == "A", f"Governed Principle should achieve Grade A on {c_dir.name}"
        assert prof_gov["evaluation"]["semantic"]["score"] == 1.0

        # Raw Episode Memory blindly imitates stale avoidance -> Grade F
        assert prof_raw["overall"]["grade"] == "F", f"Raw Episode should fail on {c_dir.name}"
        assert prof_raw["evaluation"]["semantic"]["score"] == 0.0
