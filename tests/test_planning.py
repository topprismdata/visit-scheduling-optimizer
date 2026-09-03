"""planning.py 与 plan_vs_actual.py 单元测试 (Phase 1)。"""

import sys
from pathlib import Path
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "algos"))

from pvrp_cg.planning import (
    ActualVisit,
    DecisionEvidence,
    ManualOverride,
    PlanVersion,
    PlannedVisit,
)
from pvrp_cg.plan_vs_actual import compute_plan_vs_actual


class TestPlanVersion:
    def test_minimal_ok(self):
        pv = PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0")
        assert pv.plan_id == "P1"
        assert pv.status == "draft"

    def test_horizon_end_before_start_raises(self):
        with pytest.raises(ValueError, match="结束日期"):
            PlanVersion("P1", 1, date(2026, 7, 1), date(2026, 6, 30), "仁军", "v1.0")

    def test_published_needs_published_at(self):
        with pytest.raises(ValueError, match="published"):
            PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0",
                        status="published")

    def test_published_with_timestamp_ok(self):
        pv = PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0",
                         status="published",
                         published_at=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc))
        assert pv.published_at is not None


class TestPlannedVisit:
    def test_minimal_ok(self):
        pv = PlannedVisit("P1@v1", "V001", "C001", date(2026, 6, 15), 1)
        assert pv.priority_score == 0.0

    def test_defaults(self):
        pv = PlannedVisit("P1@v1", "V001", "C001", date(2026, 6, 15), 1)
        assert pv.reason_codes == ()


class TestActualVisit:
    def test_minimal_ok(self):
        av = ActualVisit("A001", "C001", date(2026, 6, 15))
        assert av.outcome_code == "COMPLETED"

    def test_can_trace_to_plan(self):
        av = ActualVisit("A001", "C001", date(2026, 6, 15),
                         plan_version_id="P1@v1", planned_visit_id="V001")
        assert av.plan_version_id == "P1@v1"


class TestDecisionEvidence:
    def test_minimal_ok(self):
        de = DecisionEvidence("RUN001", "v1.0", "2026-08-27T09:00:00Z",
                              "restricted_column_pool", "FEASIBLE")
        assert de.status == "FEASIBLE"


class TestManualOverride:
    def test_minimal_ok(self):
        mo = ManualOverride("O001", "P1@v1", "manager1",
                           datetime(2026, 6, 10, tzinfo=timezone.utc),
                           "2026-06-15", "2026-06-16", "CUSTOMER_REQUEST")
        assert mo.actor_id == "manager1"


class TestCoveragePolicy:
    def test_minimal_ok(self):
        from pvrp_cg.planning import CoveragePolicy
        from datetime import date
        cp = CoveragePolicy("CP-1", "C001", 2, date(2026, 7, 1), date(2026, 9, 30))
        assert cp.required_visits == 2
        assert cp.service_level == "standard"

    def test_negative_visits_raises(self):
        from pvrp_cg.planning import CoveragePolicy
        from datetime import date
        import pytest
        with pytest.raises(ValueError, match="required_visits"):
            CoveragePolicy("CP-1", "C001", -1, date(2026, 1, 1), date(2026, 1, 31))


class TestBusinessSignal:
    def test_inferred_requires_model_version(self):
        from pvrp_cg.planning import BusinessSignal
        from datetime import datetime, timezone
        import pytest
        with pytest.raises(ValueError, match="model_version"):
            BusinessSignal("SIG-1", "customer", "C001", "response_momentum", "rising",
                           kind="inferred", confidence=0.5)

    def test_fact_ok_without_model(self):
        from pvrp_cg.planning import BusinessSignal
        from datetime import datetime, timezone
        bs = BusinessSignal("SIG-2", "customer", "C001", "service_risk", "low",
                           kind="fact", source="CRM", observed_at=datetime.now(timezone.utc))
        assert bs.kind == "fact"

    def test_confidence_range(self):
        from pvrp_cg.planning import BusinessSignal
        import pytest
        with pytest.raises(ValueError, match="confidence"):
            BusinessSignal("SIG-3", "customer", "C001", "access_probability", "0.5",
                           kind="fact", confidence=1.5)


class TestWorldSnapshot:
    def test_minimal_ok(self):
        from pvrp_cg.planning import WorldSnapshot
        from datetime import datetime, timezone
        ws = WorldSnapshot("SNAP-001", datetime(2026, 8, 27, tzinfo=timezone.utc))
        assert ws.id == "SNAP-001"

    def test_empty_id_raises(self):
        from pvrp_cg.planning import WorldSnapshot
        from datetime import datetime, timezone
        import pytest
        with pytest.raises(ValueError, match="snapshot_id"):
            WorldSnapshot("", datetime(2026, 8, 27, tzinfo=timezone.utc))


class TestPlanVsActualMetrics:
    def test_on_plan_match(self):
        plan = PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0")
        planned = [
            PlannedVisit("P1@v1", "V001", "C001", date(2026, 6, 15), 1,
                         estimated_travel_minutes=30.0, estimated_service_minutes=60.0),
            PlannedVisit("P1@v1", "V002", "C002", date(2026, 6, 16), 1,
                         estimated_travel_minutes=20.0, estimated_service_minutes=45.0),
        ]
        actual = [
            ActualVisit("A001", "C001", date(2026, 6, 15),
                        plan_version_id="P1@v1", planned_visit_id="V001",
                        actual_travel_minutes=28.0, service_minutes=58.0,
                        outcome_code="COMPLETED"),
            ActualVisit("A002", "C002", date(2026, 6, 16),
                        plan_version_id="P1@v1", planned_visit_id="V002",
                        actual_travel_minutes=22.0, service_minutes=47.0,
                        outcome_code="COMPLETED"),
        ]
        metrics = compute_plan_vs_actual(plan, planned, actual)
        assert metrics.n_completed == 2
        assert metrics.completion_rate == 1.0
        assert metrics.travel_time_deviation_min == pytest.approx(2.0)
        assert metrics.service_time_deviation_min == pytest.approx(2.0)

    def test_partial_completion(self):
        plan = PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0")
        planned = [PlannedVisit("P1@v1", "V001", "C001", date(2026, 6, 15), 1)]
        actual = [
            ActualVisit("A001", "C001", date(2026, 6, 15),
                        plan_version_id="P1@v1", planned_visit_id="V001",
                        outcome_code="MISSED"),
        ]
        metrics = compute_plan_vs_actual(plan, planned, actual)
        assert metrics.n_completed == 0
        assert metrics.deviation_reasons.get("MISSED") == 1

    def test_ad_hoc_visit_detected(self):
        plan = PlanVersion("P1", 1, date(2026, 6, 1), date(2026, 6, 30), "仁军", "v1.0")
        planned = []
        actual = [ActualVisit("A001", "C001", date(2026, 6, 15), outcome_code="COMPLETED")]
        metrics = compute_plan_vs_actual(plan, planned, actual)
        assert metrics.n_ad_hoc == 1