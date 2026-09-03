"""Phase 3 Tests: SVDEOntologyAdapter Planning Intent Dispatch.

Verifies:
1. SVDEOntologyAdapter correctly dispatches PlanningIntent against WorldState
2. Complete 36 assigned stores extracted for Renjun (Iron Rule 1: No survivor bias)
3. Strict pattern space P_i generated for all 36 stores
4. Chongchuan Depot coordinate passed correctly
5. Exception raised on unassigned rep ID
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
from prism_ontology.contracts.planning_io import PlanningIntent, PlanningCapabilityType

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def adapter_and_world_state():
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    adapter = SVDEOntologyAdapter(store, compiler)
    world_state = WorldStateAssembler.assemble_from_excel(DATA_FILE, assembled_at=_ASSEMBLED_AT)
    return adapter, world_state


def test_adapter_dispatches_renjun_intent_successfully(adapter_and_world_state):
    adapter, world_state = adapter_and_world_state
    
    intent = PlanningIntent(
        intent_id="INT_RENJUN_JUNE_2026",
        capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
        target_rep_id="仁军",
        target_horizon_label="2026-06",
        working_days=("2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"),
        max_daily_stops=6,
        max_daily_workload_min=480.0,
        same_weekday_required=True
    )
    
    payload = adapter.dispatch_planning_intent(intent, world_state)
    
    assert payload["dispatch_status"] == "READY_FOR_SOLVER"
    assert payload["rep_id"] == "仁军"
    assert payload["assigned_stores_count"] == 36
    assert len(payload["pattern_space"]) == 36
    assert "00006798" in payload["pattern_space"] # NT23 is present
    
    # NT23 (人民中路, 4 times / month) -> must have 5 weekly patterns
    assert len(payload["pattern_space"]["00006798"]) == 5
    
    # Depot coordinate is Chongchuan Center
    depot = payload["depot_coordinate"]
    assert 120.0 < depot.longitude < 121.5 # Dynamic centroid
    assert 31.0 < depot.latitude < 32.5 # Dynamic centroid


def test_adapter_dispatch_raises_on_unknown_rep(adapter_and_world_state):
    adapter, world_state = adapter_and_world_state
    
    intent = PlanningIntent(
        intent_id="INT_UNKNOWN",
        capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
        target_rep_id="NON_EXISTENT_REP",
        target_horizon_label="2026-06",
        working_days=()
    )
    
    with pytest.raises(ValueError, match="No assigned Customer Universe"):
        adapter.dispatch_planning_intent(intent, world_state)
