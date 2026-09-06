"""Sprint 4.2 Acceptance Test: Observability Trace, Arbitration Engine & Lifecycle Control."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from svdebench.core import DecisionCase
from tools.case_generator.pipeline_runner import FullPipelineRunner
from tools.decision_runtime.decision_context import DecisionContext
from tools.decision_runtime.principle_trace import PrincipleRuntimeTrace
from tools.decision_runtime.principle_store import PrincipleStore, StoredPrinciple
from tools.decision_runtime.principle_matcher import PrincipleMatcher
from tools.decision_runtime.arbitration_engine import ArbitrationEngine, ContextualArbitrationPolicy
from tools.decision_runtime.lifecycle_manager import PrincipleLifecycleManager
from tools.decision_runtime.governed_principle_agent import GovernedPrincipleDecisionAgent

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_test1_principle_activation_observability():
    """Test 1: Input D01 -> Explains WHY DISC-PRIN-001 was activated with trigger details."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    agent = GovernedPrincipleDecisionAgent()

    res = pipeline.run_case_dir(DELIVERY_CASES_DIR / "D01", agent_cls=lambda: agent)
    assert res["ok"] is True

    # Run matcher directly on normalized DecisionContext to assert activation trace details
    matcher = PrincipleMatcher()
    ctx = DecisionContext.from_decision_case(DecisionCase.from_dict({
        "metadata": {"id": "D01", "domain": "delivery", "name": "D01", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla"},
        "world_state": {"fleet": [{"id": "V1", "capacity_kg": 1000}], "orders": [{"id": "O1", "is_locked": True, "weight_kg": 200}]},
        "semantic_contract": {"constraints": []}
    }))
    principles, trace = matcher.match_with_trace(ctx)

    assert any(p.principle_id == "DISC-PRIN-001" for p in principles)
    assert len(trace.activated_principles) >= 1
    act_record = next(a for a in trace.activated_principles if a.principle_id == "DISC-PRIN-001")
    assert "Resource contention" in act_record.activation_reason
    assert "has_hard_commitments=True" in act_record.verified_conditions


def test_test2_boundary_rejection_trace():
    """Test 2: Input D10 / Homogeneous context -> Explains WHY specific principles were rejected with boundary conditions."""
    matcher = PrincipleMatcher()
    
    # Context with zero locked commitments (ambient only)
    ctx = DecisionContext.from_decision_case(DecisionCase.from_dict({
        "metadata": {"id": "D10-TEST", "domain": "delivery", "name": "D10", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "cost"},
        "world_state": {"fleet": [{"id": "V1", "capacity_kg": 1000}], "orders": [{"id": "O1", "is_locked": False, "weight_kg": 200}]},
        "semantic_contract": {"constraints": []}
    }))
    principles, trace = matcher.match_with_trace(ctx)

    # DISC-PRIN-001 must be rejected due to boundary check
    assert not any(p.principle_id == "DISC-PRIN-001" for p in principles)
    assert len(trace.rejected_principles) >= 1
    rej_record = next(r for r in trace.rejected_principles if r.principle_id == "DISC-PRIN-001")
    assert "zero_locked_commitments" in rej_record.failed_boundary_check


def test_test3_principle_lifecycle_management():
    """Test 3: Validates lifecycle manager state transitions, deprecations, and rejection."""
    store = PrincipleStore()
    mgr = PrincipleLifecycleManager(store)

    # 1. Deprecate principle
    assert mgr.deprecate_outdated_principle("DISC-PRIN-003", "Replaced by automated fleet controller")
    assert store.principles["DISC-PRIN-003"].status == "DEPRECATED"
    assert len(mgr.transition_history) == 1

    # 2. Reject principle
    assert mgr.reject_flawed_principle("DISC-PRIN-003", "Violates updated safety rule")
    assert store.principles["DISC-PRIN-003"].status == "REJECTED"


def test_test4_contextual_arbitration_engine():
    """Test 4: Validates extensible arbitration policies (TierBased vs Contextual)."""
    store = PrincipleStore()
    ctx_extreme = DecisionContext(
        case_id="EXTREME-01",
        domain="delivery",
        primary_objective="sla",
        resource_contention_ratio=2.5,
        has_hard_commitments=True,
        has_competency_constraints=True
    )

    promoted = store.get_promoted_principles()

    # Tier-based: Tier 3 (DISC-PRIN-002) > Tier 2 (DISC-PRIN-001)
    engine_tier = ArbitrationEngine()
    arbitrated_tier = engine_tier.arbitrate(ctx_extreme, promoted)
    assert arbitrated_tier[0].precedence_tier >= arbitrated_tier[-1].precedence_tier

    # Contextual: Under extreme contention, policy dynamically boosts commitment priority
    engine_ctx = ArbitrationEngine(policy=ContextualArbitrationPolicy())
    arbitrated_ctx = engine_ctx.arbitrate(ctx_extreme, promoted)
    assert len(arbitrated_ctx) == len(promoted)
