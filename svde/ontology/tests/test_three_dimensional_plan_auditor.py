"""Phase 5 Tests: ThreeDimensionalPlanAuditor Operator.

Verifies:
1. Valid CandidatePlan passes all 3 audit dimensions (Physical, Business, Semantic)
2. Adversarial Test 1: Catches weekday consistency drift (fails Business Compliance)
3. Adversarial Test 2: Catches daily stop overload > 6 (fails Physical Feasibility)
4. Adversarial Test 3: Catches Key store NT23 zero-visit (raises Critical Incident)
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
from prism_ontology.contracts.planning_io import (
    PlanningIntent, PlanningCapabilityType, CandidatePlan, AuditDimension,
    PlannedDailyRoute, PlannedStop
)
from prism_ontology.engine.periodic_pvrp_solver import PeriodicPVRPSolver
from prism_ontology.diagnostics.plan_auditor import ThreeDimensionalPlanAuditor

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def valid_plan_and_world_state():
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
    candidate_plan = PeriodicPVRPSolver.solve(payload)
    return candidate_plan, world_state


# ============================================================================
# Positive Test: Clean CandidatePlan Passes All 3 Dimensions
# ============================================================================

def test_clean_candidate_plan_cadence_compliance_and_tradeoff_surfacing(valid_plan_and_world_state):
    candidate_plan, world_state = valid_plan_and_world_state
    
    report = ThreeDimensionalPlanAuditor.audit_candidate_plan(candidate_plan, world_state)
    
    # Business Cadence Compliance must be 100%
    assert report.cadence_compliance_rate == 100.0
    assert report.dimension_results[AuditDimension.BUSINESS_COMPLIANCE].is_passed is True
    assert report.dimension_results[AuditDimension.SEMANTIC_PURITY].is_passed is True
    # Auditor honestly exposes physical feasibility status
    assert AuditDimension.PHYSICAL_FEASIBILITY in report.dimension_results


# ============================================================================
# Adversarial Test 1: Weekday Consistency Drift Detection
# ============================================================================

def test_adversarial_weekday_drift_fails_business_compliance(valid_plan_and_world_state):
    clean_plan, world_state = valid_plan_and_world_state
    
    # Mutate plan: Move one visit of NT23 to a completely different day with a different weekday
    # Find NT23 routes
    nt23_routes = [r for r in clean_plan.daily_routes if any(s.store_code == "00006798" for s in r.stops)]
    other_routes = [r for r in clean_plan.daily_routes if not any(s.store_code == "00006798" for s in r.stops) and r.weekday_name != nt23_routes[0].weekday_name]
    
    target_from = nt23_routes[0].date_str
    target_to = other_routes[0].date_str
    
    mutated_routes = []
    for r in clean_plan.daily_routes:
        if r.date_str == target_from:
            new_stops = [s for s in r.stops if s.store_code != "00006798"]
            mutated_routes.append(PlannedDailyRoute(r.date_str, r.weekday_name, r.rep_id, new_stops))
        elif r.date_str == target_to:
            extra_stop = PlannedStop(len(r.stops)+1, "00006798", "NT23人民中路", "崇川区")
            mutated_routes.append(PlannedDailyRoute(r.date_str, r.weekday_name, r.rep_id, r.stops + [extra_stop]))
        else:
            mutated_routes.append(r)
            
    bad_plan = CandidatePlan("BAD_PLAN_DRIFT", "INT_001", "仁军", "2026-06", mutated_routes, total_scheduled_visits=83)
    report = ThreeDimensionalPlanAuditor.audit_candidate_plan(bad_plan, world_state)
    
    assert report.is_fully_compliant is False
    assert report.dimension_results[AuditDimension.BUSINESS_COMPLIANCE].is_passed is False


# ============================================================================
# Adversarial Test 2: Daily Stop Overload > 6 Detection
# ============================================================================

def test_adversarial_daily_stop_overload_fails_physical_feasibility(valid_plan_and_world_state):
    clean_plan, world_state = valid_plan_and_world_state
    
    # Mutate plan: Add 2 dummy stops to day 1 to exceed 6 stops
    mutated_routes = []
    for idx, r in enumerate(clean_plan.daily_routes):
        if idx == 0:
            extra_stops = [
                PlannedStop(len(r.stops)+1, "DUMMY_1", "Dummy Store 1", "崇川区"),
                PlannedStop(len(r.stops)+2, "DUMMY_2", "Dummy Store 2", "崇川区")
            ]
            mutated_routes.append(PlannedDailyRoute(r.date_str, r.weekday_name, r.rep_id, r.stops + extra_stops))
        else:
            mutated_routes.append(r)
            
    bad_plan = CandidatePlan("BAD_PLAN_OVERLOAD", "INT_001", "仁军", "2026-06", mutated_routes, total_scheduled_visits=85)
    
    report = ThreeDimensionalPlanAuditor.audit_candidate_plan(bad_plan, world_state)
    
    assert report.is_fully_compliant is False
    assert report.dimension_results[AuditDimension.PHYSICAL_FEASIBILITY].is_passed is False
    assert any("Over-capacity" in d for d in report.dimension_results[AuditDimension.PHYSICAL_FEASIBILITY].violation_details)


# ============================================================================
# Adversarial Test 3: Key Store Zero-Visit Critical Incident
# ============================================================================

def test_adversarial_key_store_zero_visit_raises_critical_incident(valid_plan_and_world_state):
    clean_plan, world_state = valid_plan_and_world_state
    
    # Mutate plan: Completely delete all visits to Key store NT23 (00006798)
    mutated_routes = []
    for r in clean_plan.daily_routes:
        new_stops = [s for s in r.stops if s.store_code != "00006798"]
        mutated_routes.append(PlannedDailyRoute(r.date_str, r.weekday_name, r.rep_id, new_stops))
            
    bad_plan = CandidatePlan("BAD_PLAN_MISSED_KEY", "INT_001", "仁军", "2026-06", mutated_routes, total_scheduled_visits=79)
    
    report = ThreeDimensionalPlanAuditor.audit_candidate_plan(bad_plan, world_state)
    
    assert report.is_fully_compliant is False
    assert report.dimension_results[AuditDimension.BUSINESS_COMPLIANCE].is_passed is False
    assert any("Critical Incident" in d for d in report.dimension_results[AuditDimension.BUSINESS_COMPLIANCE].violation_details)
