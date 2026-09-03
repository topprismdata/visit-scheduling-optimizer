"""Phase 3 Tests — SVDE DecisionGate Bridge."""
import pytest
from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.compiler.operational import OperationalCompiler
from prism_ontology.adapters.svde import (
    SVDEOntologyAdapter,
    BusinessDecisionIntent,
    BusinessQuestion,
    ValidationReport,
)


@pytest.fixture
def adapter() -> SVDEOntologyAdapter:
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    return SVDEOntologyAdapter(store, compiler)


def test_adapter_diagnose_route_question_routes_to_daily(adapter):
    intent = adapter.diagnose("今天这8家店怎么排更顺路")
    assert isinstance(intent, BusinessDecisionIntent)
    assert intent.primary_decision_level == BusinessQuestion.DAILY_ROUTE_SEQUENCE
    assert intent.confidence > 0
    assert "daily_route_optimization" in intent.candidate_capabilities


def test_adapter_diagnose_territory_routes_to_territory(adapter):
    intent = adapter.diagnose("客户被分错了代表")
    assert intent.primary_decision_level == BusinessQuestion.TERRITORY_ALIGNMENT
    assert "territory_alignment" in intent.candidate_capabilities


def test_adapter_diagnose_periodic_routes_to_periodic(adapter):
    intent = adapter.diagnose("四周拜访频次不均匀")
    assert intent.primary_decision_level == BusinessQuestion.PERIODIC_COVERAGE
    assert "periodic_visit_planning" in intent.candidate_capabilities


def test_adapter_diagnose_unrelated_routes_to_unclassified(adapter):
    intent = adapter.diagnose("今天天气不错")
    assert intent.primary_decision_level == BusinessQuestion.UNCLASSIFIED
    assert intent.needs_clarification is True
    assert intent.candidate_capabilities == []


def test_adapter_returns_required_objects_for_decision(adapter):
    intent = adapter.diagnose("今天这8家店怎么排更顺路")
    assert "PlannedVisit" in intent.required_objects
    assert "TravelCostMatrix" in intent.required_objects
    assert "Commitment" in intent.required_objects


def test_adapter_honest_capability_availability(adapter):
    """All Sales Visit capabilities are PLANNED, none claimed IMPLEMENTED."""
    intent = adapter.diagnose("客户被分错了代表")
    for cap, status in intent.capability_availability.items():
        assert status == "PLANNED", f"{cap} must be PLANNED, not {status}"


def test_adapter_provides_operational_schemas(adapter):
    intent = adapter.diagnose("今天这8家店怎么排更顺路")
    assert "PlannedVisit" in intent.operational_schemas
    schema = intent.operational_schemas["PlannedVisit"]
    assert schema.to_dict()["$id"] == "prism:schema:PlannedVisit"


def test_adapter_hard_constraints_for_daily_route(adapter):
    intent = adapter.diagnose("今天这8家店怎么排更顺路")
    assert "customer_set_must_be_FIXED" in intent.hard_constraints_to_confirm
    assert "every_customer_served_within_time_window" in intent.hard_constraints_to_confirm


def test_adapter_validate_clean_mapping_passes(adapter):
    clean_mapping = {obj.object_id: obj.object_id for obj in adapter.store.objects.values()}
    report = adapter.validate(clean_mapping)
    assert isinstance(report, ValidationReport)
    assert report.is_valid is True
    assert report.fold_violation_count == 0
    assert report.gate_passed is True


def test_adapter_validate_detects_fold_violation(adapter):
    bad_mapping = {
        "Customer": "COMMITTED_TASK",
        "PlannedVisit": "RouteStop",
    }
    report = adapter.validate(bad_mapping)
    assert report.is_valid is False
    assert report.fold_violation_count >= 2
    assert "Customer" in report.blocking_issues
    assert "PlannedVisit" in report.blocking_issues


def test_adapter_emits_evidence_sources_in_validation(adapter):
    report = adapter.validate({obj.object_id: obj.object_id for obj in adapter.store.objects.values()})
    assert any("REF-PTV" in s for s in report.evidence_sources), f"Expected PTV evidence source, got {report.evidence_sources}"
    assert "REF-002" in report.evidence_sources
    assert "GAP-6-PERMANENTLY-CLOSED" in report.evidence_sources


def test_adapter_lifecycle_state_progression_referenced(adapter):
    report = adapter.validate({obj.object_id: obj.object_id for obj in adapter.store.objects.values()})
    assert "FROZEN" in report.lifecycle_state_progression
    assert "BUSINESS_APPROVED" in report.lifecycle_state_progression


def test_adapter_diagnose_rolling_routes_to_rolling(adapter):
    intent = adapter.diagnose("临时新增一个高价值门店，触发滚动重排")
    assert intent.primary_decision_level == BusinessQuestion.ROLLING_REPLAN
    assert len(intent.candidate_capabilities) >= 2


def test_adapter_diagnose_distance_tradeoff(adapter):
    intent = adapter.diagnose("时间与拜访次数之间如何做权衡")
    assert intent.primary_decision_level == BusinessQuestion.DISTANCE_TIME_TRADEOFF
    assert "daily_route_optimization" in intent.candidate_capabilities


def test_adapter_diagnose_includes_downstream_advice(adapter):
    intent = adapter.diagnose("今天这8家店怎么排更顺路")
    assert isinstance(intent.downstream_advice, str)
    assert len(intent.downstream_advice) > 0


def test_adapter_validate_blocks_on_fold(adapter):
    bad = {"Customer": "COMMITTED_TASK"}
    report = adapter.validate(bad)
    assert report.gate_passed is False
    assert "Customer" in report.blocking_issues
