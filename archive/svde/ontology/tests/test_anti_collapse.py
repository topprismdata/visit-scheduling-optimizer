"""Phase 0 Unit Tests — 8 Anti-Collapse Competency Questions (CQs)."""
import pytest
from prism_ontology.validator.cq_runner import CQRunner, ANTI_COLLAPSE_CQS
from prism_ontology.diagnostics.intent_router import IntentRouter


def test_cq_runner_registers_minimum_8_cqs():
    runner = CQRunner()
    cqs = runner.all()
    assert len(cqs) >= 8


def test_cq_t1_territory_alignment_not_daily_route():
    """CQ-T1: '客户被分错了代表' -> TERRITORY_ALIGNMENT (not daily route)."""
    router = IntentRouter()
    diag = router.route("客户被分错了代表")
    assert diag.primary_decision_level == "TERRITORY_ALIGNMENT"
    assert "DAILY_ROUTE_SEQUENCING" not in diag.secondary_decision_levels


def test_cq_t2_periodic_coverage_not_daily_route():
    """CQ-T2: '四周拜访频次不均匀' -> PERIODIC_COVERAGE (not daily route)."""
    router = IntentRouter()
    diag = router.route("四周拜访频次不均匀，需要调整周期节奏")
    assert diag.primary_decision_level == "PERIODIC_COVERAGE"


def test_cq_t3_daily_route_routing():
    """CQ-T3: '今天这8家店怎么排更顺路' -> DAILY_ROUTE_SEQUENCING."""
    router = IntentRouter()
    diag = router.route("今天这8家店怎么排更顺路")
    assert diag.primary_decision_level == "DAILY_ROUTE_SEQUENCING"


def test_cq_t4_locked_commitment_not_relaxable():
    """CQ-T4: Locked commitment cannot be relaxed (invariant checked in CQ registry)."""
    cq = next(c for c in ANTI_COLLAPSE_CQS if c["cq_id"] == "CQ-T4")
    assert "mustNotOverride" in cq["hard_constraint"]


def test_cq_t5_distance_cannot_reduce_coverage():
    """CQ-T5: Distance cannot override coverage compliance."""
    cq = next(c for c in ANTI_COLLAPSE_CQS if c["cq_id"] == "CQ-T5")
    assert "subordinateTo" in cq["hard_constraint"]


def test_cq_t6_sop_not_in_sales_visit_ontology():
    """CQ-T6: GAP-6 permanently closed — no SOP objects in ontology."""
    cq = next(c for c in ANTI_COLLAPSE_CQS if c["cq_id"] == "CQ-T6")
    assert "NOT in ontology" in cq["frozen_rule"]


def test_cq_t7_actual_visit_not_modify_planned_visit():
    """CQ-T7: ActualVisit must not overwrite PlannedVisit."""
    cq = next(c for c in ANTI_COLLAPSE_CQS if c["cq_id"] == "CQ-T7")
    assert "must NOT modify PlannedVisit" in cq["hard_constraint"]


def test_cq_t8_customer_not_folded_into_committed_task():
    """CQ-T8: Customer must not be folded into generic task."""
    cq = next(c for c in ANTI_COLLAPSE_CQS if c["cq_id"] == "CQ-T8")
    assert "fold-score" in cq["hard_constraint"]
