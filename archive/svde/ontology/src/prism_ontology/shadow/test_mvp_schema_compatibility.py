"""MVP 输出 schema ↔ Shadow 工具链消费契约回归测试.

背景 (2026-08 真实数据回放事故):
  vertical_slice_mvp._summarize_plan 产物键为 daily_routes_summary / daily_routes_count,
  而 shadow.metrics / shadow.compare 曾只读 daily_routes —— 既有测试 fixture
  恰好手写 daily_routes 键, 全绿掩盖了真实链路 plan 恒为 0 的静默失败。

本测试用 MVP 真实 _summarize_plan 产物喂给 metrics/compare, 防止 schema 再漂移。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # svde/ontology/src

from prism_ontology.engine.vertical_slice_mvp import VerticalSliceRunner
from prism_ontology.engine.periodic_pvrp_solver import CandidatePlan, PlannedDailyRoute, PlannedStop
from prism_ontology.shadow.metrics import compute_replay_metrics
from prism_ontology.shadow.compare import compare_mvp_vs_actual


def _plan_with_two_routes(rep_id: str = "R1") -> CandidatePlan:
    def _route(date_str, stores):
        stops = [PlannedStop(stop_idx=i + 1, store_code=c, store_name=f"S{c}",
                             district="D", planned_service_min=50.0,
                             leg_distance_from_prev_km=1.0, leg_transit_from_prev_min=5.0)
                 for i, c in enumerate(stores)]
        return PlannedDailyRoute(
            date_str=date_str, weekday_name="周一", rep_id=rep_id, stops=stops,
            depot_outbound_transit_min=5.0, depot_inbound_transit_min=5.0,
            total_daily_distance_km=3.0, total_daily_transit_min=15.0,
            total_daily_service_min=50.0 * len(stores),
            total_daily_workload_min=50.0 * len(stores) + 15.0)

    return CandidatePlan(
        plan_id="P1", intent_id="I1", rep_id=rep_id, period_label="2026-07",
        daily_routes=[_route("2026-07-01", ["C1", "C2"]), _route("2026-07-02", ["C3"])],
        solver_name="t", solver_status="FEASIBLE",
        total_scheduled_visits=3, total_monthly_transit_min=45.0,
        total_monthly_distance_km=9.0)


class _MVPResultShim:
    """仅承载 metrics/compare 消费所需字段 (candidate_plan_summary 等)."""

    def __init__(self, candidate_plan_summary):
        self.candidate_plan_summary = candidate_plan_summary
        self.target_rep_id = "R1"
        self.period_label = "2026-07"


class _WSWithFacts:
    def __init__(self, facts):
        from types import SimpleNamespace
        self.execution_fact_stream = facts
        self.policies = SimpleNamespace(operational_policies={})
        self.snapshot_id = "SNAP_TEST"


def _fact(store_code, day, dur=10.0):
    import datetime as _dt
    from prism_ontology.world_model.state_snapshot import ActualVisitEvent
    return ActualVisitEvent(
        event_id=f"E_{store_code}_{day}", store_code=store_code, rep_id="R1",
        visit_date=_dt.date(2026, 7, day), service_duration_min=dur,
        transit_duration_min=0.0, is_line_internal=True)


def test_metrics_consumes_real_mvp_summary_schema():
    """真实 _summarize_plan 键 (daily_routes_summary) 必须产出非零 stops."""
    summary = VerticalSliceRunner._summarize_plan(_plan_with_two_routes())
    assert "daily_routes_summary" in summary  # MVP 真实键
    assert "daily_routes" not in summary
    mvp = _MVPResultShim(summary)
    ws = _WSWithFacts([_fact("C1", 1), _fact("C9", 3)])
    report = compute_replay_metrics(mvp, ws)
    assert report.total_stops == 3
    assert report.total_routes == 2
    assert report.unique_customers_visited == 3


def test_compare_consumes_real_mvp_summary_schema():
    summary = VerticalSliceRunner._summarize_plan(_plan_with_two_routes())
    mvp = _MVPResultShim(summary)
    ws = _WSWithFacts([_fact("C1", 1), _fact("C2", 1), _fact("C3", 2)])
    report = compare_mvp_vs_actual(mvp, ws, rep_id="R1", period="2026-07")
    assert report.plan_total_stops == 3
    assert report.actual_total_stops == 3
    assert report.match_rate == 1.0
    assert report.status == "PASS"
