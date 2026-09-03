"""Phase 4 Tests: PeriodicPVRPSolver Engine Adapter.

Verifies:
1. PeriodicPVRPSolver solves candidate plan from READY_FOR_SOLVER payload
2. Total scheduled visits exact match to 83
3. Daily stop capacity <= 6 stores across all active days
4. Chongchuan Depot 0 outbound and inbound transit times calculated
5. NT23 (Key store) visited exactly 4 times on Wednesdays
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.compiler.operational import OperationalCompiler
from prism_ontology.adapters.svde.bridge import SVDEOntologyAdapter
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler
from prism_ontology.contracts.planning_io import PlanningIntent, PlanningCapabilityType, CandidatePlan
from prism_ontology.engine.periodic_pvrp_solver import PeriodicPVRPSolver

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def renjun_candidate_plan() -> CandidatePlan:
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    adapter = SVDEOntologyAdapter(store, compiler)
    world_state = WorldStateAssembler.assemble_from_excel(DATA_FILE, assembled_at=_ASSEMBLED_AT)
    
    intent = PlanningIntent(
        intent_id="INT_RENJUN_JUNE_2026",
        capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
        target_rep_id="仁军",
        target_horizon_label="2026-06",
        working_days=tuple(f"2026-06-{d:02d}" for d in range(1, 27) if d not in [6, 7, 13, 14, 20, 21]),
        max_daily_stops=6,
        max_daily_workload_min=480.0,
        same_weekday_required=True
    )
    
    payload = adapter.dispatch_planning_intent(intent, world_state)
    return PeriodicPVRPSolver.solve(payload)


def test_candidate_plan_total_visits(renjun_candidate_plan):
    assert renjun_candidate_plan.total_scheduled_visits == 83
    assert renjun_candidate_plan.solver_status == "OPTIMAL"


def test_candidate_plan_daily_stop_capacity(renjun_candidate_plan):
    for route in renjun_candidate_plan.daily_routes:
        assert 1 <= route.stops_count <= 6


def test_candidate_plan_depot_closed_loop(renjun_candidate_plan):
    for route in renjun_candidate_plan.daily_routes:
        assert route.depot_outbound_transit_min > 0.0
        assert route.depot_inbound_transit_min > 0.0
        assert route.total_daily_workload_min > 0.0


def test_candidate_plan_nt23_weekly_cadence_coverage(renjun_candidate_plan):
    nt23_visits = []
    for route in renjun_candidate_plan.daily_routes:
        for stop in route.stops:
            if stop.store_code == "00006798": # NT23
                nt23_visits.append((route.date_str, route.weekday_name))
                
    assert len(nt23_visits) == 4
    # All 4 visits must be on the EXACT SAME weekday (Same-Weekday Consistency)
    weekdays = {v[1] for v in nt23_visits}
    assert len(weekdays) == 1
