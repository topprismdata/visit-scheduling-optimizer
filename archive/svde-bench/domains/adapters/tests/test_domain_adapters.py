"""Sprint 5.1 Acceptance Test: Explicit Domain Adapters & Decoupled Context Mapping."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from svdebench.core import DecisionCase
from domains.adapters.delivery_adapter import DeliveryDomainAdapter
from domains.adapters.visit_adapter import VisitDomainAdapter
from domains.adapters.registry import ADAPTER_REGISTRY
from tools.decision_runtime.decision_context import DecisionContext
from tools.case_generator.pipeline_runner import FullPipelineRunner

DELIVERY_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "delivery"
VISIT_CASES_DIR = Path(__file__).resolve().parents[3] / "cases" / "extended" / "visit"


def test_delivery_domain_adapter_mapping():
    """Validates DeliveryDomainAdapter correctly translates fleet, payload, and cold chain into canonical context."""
    adapter = DeliveryDomainAdapter()
    case = DecisionCase.from_dict({
        "metadata": {"id": "D01-TEST", "domain": "delivery", "name": "Delivery Test", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "minimize_cost"},
        "world_state": {
            "fleet": [
                {"id": "V1", "type": "COLD_REFRIGERATED", "capacity_kg": 1000, "status": "AVAILABLE"},
                {"id": "V2", "type": "STANDARD_VAN", "capacity_kg": 800, "status": "BROKEN_DOWN"}
            ],
            "orders": [
                {"id": "O1", "weight_kg": 300, "req_cold": True, "is_locked": True, "tw_early": 60, "tw_late": 180},
                {"id": "O2", "weight_kg": 200, "req_cold": False, "is_locked": False, "tw_early": 0, "tw_late": 360}
            ]
        },
        "semantic_contract": {"constraints": []}
    })

    ctx = adapter.to_decision_context(case)
    assert ctx.domain == "delivery"
    assert ctx.active_resource_count == 1
    assert ctx.total_active_capacity == 1000.0
    assert ctx.total_task_demand == 500.0
    assert ctx.has_hard_commitments is True
    assert ctx.has_competency_constraints is True  # Cold chain
    assert ctx.has_resource_failure is True

    # Solution back-mapping
    sol = adapter.adapt_solution_to_domain({"V1": ["O1", "O2"]}, case)
    assert sol["dispatch_type"] == "FLEET_DELIVERY_ROUTING"
    assert sol["total_orders_dispatched"] == 2


def test_visit_domain_adapter_mapping_with_genuine_skills():
    """Validates VisitDomainAdapter correctly translates sales reps (Specialist/Senior), visit duration, and skill requirements."""
    adapter = VisitDomainAdapter()
    case = DecisionCase.from_dict({
        "metadata": {"id": "V03-TEST", "domain": "visit", "name": "Visit Test", "created_at": "2026-08-24", "tags": []},
        "intent": {"primary_objective": "sla_compliance"},
        "world_state": {
            "fleet": [
                {"id": "REP_SPEC_01", "type": "SPECIALIST_REP", "capacity_kg": 480, "status": "AVAILABLE"},
                {"id": "REP_JUN_02", "type": "JUNIOR_REP", "capacity_kg": 420, "status": "AVAILABLE"}
            ],
            "orders": [
                {"id": "VISIT_ONCOLOGY", "weight_kg": 90, "required_skill": "SPECIALIST", "is_locked": True, "is_vip": True},
                {"id": "VISIT_CLINIC", "weight_kg": 30, "required_skill": "JUNIOR", "is_locked": False, "is_vip": False}
            ]
        },
        "semantic_contract": {"constraints": []}
    })

    ctx = adapter.to_decision_context(case)
    assert ctx.domain == "visit"
    assert ctx.active_resource_count == 2
    assert ctx.total_active_capacity == 900.0
    assert ctx.total_task_demand == 120.0
    assert ctx.has_hard_commitments is True
    assert ctx.has_competency_constraints is True
    assert ctx.resources[0].resource_class == "SPECIALIST_REP"
    assert ctx.tasks[0].required_competency == "SPECIALIST"

    # Solution back-mapping
    sol = adapter.adapt_solution_to_domain({"REP_SPEC_01": ["VISIT_ONCOLOGY"], "REP_JUN_02": ["VISIT_CLINIC"]}, case)
    assert sol["dispatch_type"] == "FIELD_SALES_VISIT_SCHEDULE"
    assert sol["total_reps_deployed"] == 2


def test_registry_integration_and_context_delegation():
    """Validates ADAPTER_REGISTRY routes domains cleanly and DecisionContext.from_decision_case delegates properly."""
    pipeline = FullPipelineRunner(oracle_timeout_sec=30)
    
    # Ingest D01 through registry
    res_d = pipeline.run_case_dir(DELIVERY_CASES_DIR / "D01")
    assert res_d["ok"] is True

    # Ingest V01 through registry
    res_v = pipeline.run_case_dir(VISIT_CASES_DIR / "V01")
    assert res_v["ok"] is True
