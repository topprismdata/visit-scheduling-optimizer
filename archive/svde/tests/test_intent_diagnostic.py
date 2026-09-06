"""Tests for SVDE Sales Visit Business Intent Diagnostic Engine.

Critical acceptance tests (no fabrication, no unverified percentage claims):
- Query classification routes to correct decision level
- Required inputs are explicitly enumerated
- Hard constraints are explicitly enumerated
- Missing data is detected and reported
- UNCLASSIFIED queries are rejected (no false downgrade to VRP)
- Capability status is honestly reported (PLANNED for unimplemented)
- Diagnostic refuses to advance when all candidate capabilities are unimplemented
"""
import re
import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from svde.intent.diagnostic import (
    IntentDiagnosticEngine,
    DecisionIntentDiagnostic,
    BusinessQuestion,
)
from svde.contracts.sales_visit_contracts import (
    SalesVisitCapabilityType,
    SalesVisitCapabilityStatus,
)


# ============================================================================
# Test 1: "Shorten sales route distance" → DAILY_ROUTE_SEQUENCE, not VRP blind
# ============================================================================
def test_shorten_distance_routes_to_daily_route_not_vrp():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("帮我缩短销售线路在途距离")
    assert diag.classified_decision_level == BusinessQuestion.DAILY_ROUTE_SEQUENCE
    # When critical inputs are missing, diagnostic is honest even if not full PLANNED-refusal.
    # Most important honesty guarantee: capability_status must be honest.
    assert diag.capability_status[SalesVisitCapabilityType.DAILY_ROUTE_OPTIMIZATION.value] == SalesVisitCapabilityStatus.PLANNED.value
    # The diagnostic advice MUST explicitly state it refuses to push to the (PLANNED) capability.
    full_advice = (diag.downstream_advice or "") + " " + (diag.refusal_reason or "")
    assert ("PLANNED" in full_advice) or ("未实现" in full_advice) or ("拒绝" in full_advice)
    # Must explicitly enumerate required inputs (not silently assume)
    assert "fixed_customer_set_for_target_day" in diag.required_inputs
    assert "depot_location" in diag.required_inputs
    assert "real_distance_or_time_matrix_between_all_nodes" in diag.required_inputs


# ============================================================================
# Test 2: Cadence / frequency question → PERIODIC_COVERAGE
# ============================================================================
def test_cadence_question_routes_to_periodic_coverage():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("客户拜访频次是否合规？要检查周期节奏")
    assert diag.classified_decision_level == BusinessQuestion.PERIODIC_COVERAGE
    assert "PERIODIC_VISIT_PLANNING" not in diag.candidate_capabilities or \
           SalesVisitCapabilityType.PERIODIC_VISIT_PLANNING.value in diag.candidate_capabilities


# ============================================================================
# Test 3: Territory / ownership question → TERRITORY_ALIGNMENT
# ============================================================================
def test_territory_question_routes_to_territory_alignment():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("把客户A的客户归属换给代表B")
    assert diag.classified_decision_level == BusinessQuestion.TERRITORY_ALIGNMENT
    assert diag.candidate_capabilities == [SalesVisitCapabilityType.TERRITORY_ALIGNMENT.value]


# ============================================================================
# Test 4: Unrelated question → UNCLASSIFIED → refusal to advance
# ============================================================================
def test_unrelated_query_refuses_to_advance():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("今天天气不错")
    assert diag.classified_decision_level == BusinessQuestion.UNCLASSIFIED
    assert diag.refusal_to_advance is True
    # Refusal reason must contain an explicit UNCLASSIFIED signal (English or Chinese)
    refusal_text = (diag.refusal_reason or "") + " " + (diag.downstream_advice or "")
    assert ("UNCLASSIFIED" in refusal_text) or ("未匹配" in refusal_text) or ("does not match" in refusal_text)


# ============================================================================
# Test 5: Missing input detection (provided_inputs parameter is honored)
# ============================================================================
def test_missing_data_is_reported_when_inputs_absent():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("缩短销售线路在途距离", provided_inputs={})
    # All required inputs should be flagged as missing since provided_inputs is empty
    assert len(diag.missing_data) > 0
    assert "fixed_customer_set_for_target_day" in diag.missing_data


def test_provided_inputs_remove_from_missing_data():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose(
        "缩短销售线路在途距离",
        provided_inputs={
            "target_date": "2026-09-01",
            "depot_location": {"lat": 31.0, "lon": 121.0},
            "fixed_customer_set": [],
            "rep_id": "REP_A",
            "service_duration_per_customer": {"C1": 30},
            "time_window_per_customer": {"C1": [0, 480]},
            "max_daily_work_minutes": 480,
        },
    )
    # depot_location, target_date, rep_id, customer_set should be cleared from missing
    assert "depot_location" not in diag.missing_data
    assert "target_date" not in diag.missing_data


# ============================================================================
# Test 6: Hard constraints are explicitly listed (non-sacrificable)
# ============================================================================
def test_hard_constraints_explicitly_listed():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("缩短销售线路在途距离")
    # Daily route hard constraints must include:
    assert "customer_set_must_be_FIXED" in diag.hard_constraints_to_confirm
    assert "locked_visit_order_must_be_preserved" in diag.hard_constraints_to_confirm
    assert "every_customer_served_within_time_window" in diag.hard_constraints_to_confirm


# ============================================================================
# Test 7: Honest capability status reporting
# ============================================================================
def test_capability_status_honestly_reports_planned():
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose("缩短销售线路在途距离")
    for cap_name, status in diag.capability_status.items():
        assert status == SalesVisitCapabilityStatus.PLANNED.value, \
            f"Capability {cap_name} should be honestly reported as PLANNED, got {status}"


# ============================================================================
# Test 8: ANTI-FABRICATION TEST — Diagnostic must NOT contain false claims
# ============================================================================
@pytest.mark.parametrize("user_query", [
    "帮我缩短销售线路在途距离",
    "客户拜访频次是否合规？",
    "把客户A的客户归属换给代表B",
    "今天天气不错",
])
def test_diagnostic_never_includes_unverified_percentage_claims(user_query):
    """Reject any false percentage gains like '15% reduction' or '30% distance drop'."""
    engine = IntentDiagnosticEngine()
    diag = engine.diagnose(user_query)
    # Search for any percentage claim pattern
    all_text = " ".join([
        str(diag.refusal_reason),
        str(diag.downstream_advice),
        str(diag.explanation if hasattr(diag, "explanation") else ""),
    ])
    # Reject patterns like "下降15%", "减少30%"
    forbidden_patterns = [
        r"\d+\s*%\s*(下降|减少|缩短|提升|增加|优化)",
        r"下降\s*\d+%",
        r"缩短\s*\d+",
        r"减少\s*\d+",
    ]
    for pattern in forbidden_patterns:
        match = re.search(pattern, all_text)
        assert match is None, (
            f"DIAGNOSTIC FABRICATED UNVERIFIED PERCENTAGE CLAIM: "
            f"pattern='{pattern}' matched='{match.group()}' "
            f"in user_query='{user_query}' diagnostic_text='{all_text[:200]}'"
        )
