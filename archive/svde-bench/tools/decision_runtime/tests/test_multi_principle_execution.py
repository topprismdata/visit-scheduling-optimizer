"""Sprint 4.3 Acceptance Test: Multi-Principle Co-Activation, Conflict Arbitration & Feedback."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from svdebench.core import DecisionCase
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.decision_runtime.decision_context import DecisionContext
from tools.decision_runtime.principle_store import PrincipleStore, StoredPrinciple
from tools.decision_runtime.principle_matcher import PrincipleMatcher
from tools.decision_runtime.arbitration_engine import ArbitrationEngine, TierBasedArbitrationPolicy, ContextualArbitrationPolicy
from tools.decision_runtime.lifecycle_manager import PrincipleLifecycleManager
from tools.decision_runtime.governed_principle_agent import GovernedPrincipleDecisionAgent

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_multi_principle_co_activation():
    """Test 1: Case D03 (Breakdown + Cold-chain + Locked SLA) triggers co-activation of 3 principles."""
    matcher = PrincipleMatcher()
    
    # Context simulating simultaneous vehicle failure + cold chain + locked SLA commitments
    ctx = DecisionContext.from_decision_case(DecisionCase.from_dict({
        "metadata": {"id": "D03-MULTI", "domain": "delivery", "name": "Multi-Trigger Case", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla_protection"},
        "world_state": {
            "fleet": [
                {"id": "V1", "type": "COLD_REFRIGERATED", "capacity_kg": 1000, "status": "AVAILABLE"},
                {"id": "V2", "type": "STANDARD_VAN", "capacity_kg": 800, "status": "BROKEN_DOWN"}
            ],
            "orders": [
                {"id": "O1", "weight_kg": 200, "req_cold": True, "is_locked": True},
                {"id": "O2", "weight_kg": 300, "req_cold": False, "is_locked": True}
            ]
        },
        "semantic_contract": {"constraints": []}
    }))

    principles, trace = matcher.match_with_trace(ctx)

    # All 3 principles must be co-activated simultaneously
    activated_ids = [p.principle_id for p in principles]
    assert "DISC-PRIN-001" in activated_ids  # SLA commitment
    assert "DISC-PRIN-002" in activated_ids  # Cold-chain certification match
    assert "DISC-PRIN-003" in activated_ids  # Sudden resource failure handoff
    assert len(trace.activated_principles) == 3


def test_principle_conflict_arbitration_hierarchy():
    """Test 2: Precedence arbitration ensures Tier 3 (Cold/Safety) strictly dominates Tier 2 (SLA) and Tier 1 (Handoff)."""
    matcher = PrincipleMatcher()
    
    ctx = DecisionContext.from_decision_case(DecisionCase.from_dict({
        "metadata": {"id": "D03-CONFLICT", "domain": "delivery", "name": "Conflict Case", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla"},
        "world_state": {
            "fleet": [
                {"id": "V1", "type": "COLD_REFRIGERATED", "capacity_kg": 1000, "status": "AVAILABLE"},
                {"id": "V2", "type": "STANDARD_VAN", "capacity_kg": 800, "status": "BROKEN_DOWN"}
            ],
            "orders": [
                {"id": "O1", "weight_kg": 200, "req_cold": True, "is_locked": True},
                {"id": "O2", "weight_kg": 300, "req_cold": False, "is_locked": True}
            ]
        },
        "semantic_contract": {"constraints": []}
    }))

    principles, trace = matcher.match_with_trace(ctx)
    arbitrated = trace.arbitrated_precedence

    # Strict hierarchy: DISC-PRIN-002 (Tier 3) > DISC-PRIN-001 (Tier 2) > DISC-PRIN-003 (Tier 1)
    assert arbitrated[0] == "DISC-PRIN-002"
    assert arbitrated[1] == "DISC-PRIN-001"
    assert arbitrated[2] == "DISC-PRIN-003"


def test_runtime_complete_trace_and_rejected_reasons():
    """Test 3: Confirms that final DecisionArtifact includes complete trace of active and rejected principles with boundary reasons."""
    agent = GovernedPrincipleDecisionAgent()
    case = DecisionCase.from_dict({
        "metadata": {"id": "D01-TRACE", "domain": "delivery", "name": "Trace Case", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla"},
        "world_state": {
            "fleet": [{"id": "V1", "type": "STANDARD_VAN", "capacity_kg": 1000, "status": "AVAILABLE"}],
            "orders": [{"id": "O1", "weight_kg": 400, "is_locked": True, "req_cold": False}]
        },
        "semantic_contract": {"constraints": []}
    })

    artifact = agent.solve(case)
    trace_dict = artifact.explanation.get("runtime_trace", {})

    assert "activated_principles" in trace_dict
    assert "rejected_principles" in trace_dict
    assert len(trace_dict["activated_principles"]) >= 1
    assert len(trace_dict["rejected_principles"]) >= 1

    # Rejected principles must explain boundary reason
    rej = trace_dict["rejected_principles"][0]
    assert "reason" in rej
    assert "boundary" in rej


def test_runtime_feedback_logging():
    """Test 4: Confirms runtime agent logs execution feedback across sequential case decisions."""
    agent = GovernedPrincipleDecisionAgent()
    case1 = DecisionCase.from_dict({
        "metadata": {"id": "FB-01", "domain": "delivery", "name": "FB1", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla"},
        "world_state": {"fleet": [{"id": "V1", "capacity_kg": 1000}], "orders": [{"id": "O1", "weight_kg": 200, "is_locked": True}]},
        "semantic_contract": {"constraints": []}
    })
    case2 = DecisionCase.from_dict({
        "metadata": {"id": "FB-02", "domain": "visit", "name": "FB2", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "cadence"},
        "world_state": {"fleet": [{"id": "REP1", "capacity_kg": 480}], "orders": [{"id": "V1", "weight_kg": 60, "is_locked": True}]},
        "semantic_contract": {"constraints": []}
    })

    agent.solve(case1)
    agent.solve(case2)

    assert len(agent.runtime_feedback_log) == 2
    assert agent.runtime_feedback_log[0]["case_id"] == "FB-01"
    assert agent.runtime_feedback_log[1]["case_id"] == "FB-02"
    assert agent.runtime_feedback_log[0]["sla_honored"] is True
    assert agent.runtime_feedback_log[1]["sla_honored"] is True
