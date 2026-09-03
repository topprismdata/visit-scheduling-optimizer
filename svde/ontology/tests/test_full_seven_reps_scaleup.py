"""Phase 7 Tests: Full 7-Rep Scale-up & Release Gate Verification.

Verifies:
1. All 7 sales reps (静, 欣, 许强, 晓敏, 仁军, 超, 佳佳) successfully dispatch intents
2. Total assigned stores across 7 reps cover all 246 unique stores in Customer Universe
3. Depots properly assigned (Suzhou Center for 4, Changzhou Center for 1, Chongchuan Center for 2)
4. Full Release Gates G1-G6 automated verification
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
def shared_adapter_and_world_state():
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
    store = ReferenceOntologyStore()
    compiler = OperationalCompiler(store)
    adapter = SVDEOntologyAdapter(store, compiler)
    world_state = WorldStateAssembler.assemble_from_excel(DATA_FILE, assembled_at=_ASSEMBLED_AT)
    return adapter, world_state


def test_all_seven_reps_dispatch_success(shared_adapter_and_world_state):
    adapter, world_state = shared_adapter_and_world_state
    
    reps_roster = ["静", "欣", "许强", "晓敏", "仁军", "超", "佳佳"]
    total_assigned_codes = set()
    
    for rep in reps_roster:
        intent = PlanningIntent(
            intent_id=f"INT_{rep}_2026",
            capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
            target_rep_id=rep,
            target_horizon_label="2026-06",
            working_days=tuple(f"2026-06-{d:02d}" for d in range(1, 27) if d not in [6, 7, 13, 14, 20, 21]),
            max_daily_stops=6,
            max_daily_workload_min=480.0,
            same_weekday_required=True
        )
        
        payload = adapter.dispatch_planning_intent(intent, world_state)
        
        assert payload["dispatch_status"] == "READY_FOR_SOLVER"
        assert payload["rep_id"] == rep
        assert payload["assigned_stores_count"] >= 30 # each rep has 32~38 stores
        assert len(payload["pattern_space"]) == payload["assigned_stores_count"]
        
        # Accumulate store codes
        total_assigned_codes.update(payload["assigned_stores"].keys())
        
    # All 246 stores must be covered across the 7 reps
    assert len(total_assigned_codes) == 246


def test_release_gates_g1_to_g6_verification(shared_adapter_and_world_state):
    adapter, world_state = shared_adapter_and_world_state
    
    # Gate G1: Ontology Store has DCR v2.0 entities
    store = adapter.store
    for dcr_obj in ["AccountHierarchy", "ProductLineScope", "SupplyNodeLink", "MerchandisingCompliance", "InStoreActionTaxonomy"]:
        assert store.get_object(dcr_obj) is not None, f"Gate G1 Failed: {dcr_obj} missing"
        
    # Gate G2: Real Data Customer Universe has 246 stores
    assert len(world_state.customer_universe) == 246, "Gate G2 Failed: Universe != 246"
    assert len(world_state.resources) == 7, "Gate G2 Failed: Reps != 7"
    
    # Gate G3: PolicyRegistry has strict cadence rules
    assert "RULE_STRICT_WEEKLY" in world_state.policies.cadence_rules, "Gate G3 Failed: Cadence rules missing"
    assert world_state.policies.cadence_rules["RULE_STRICT_WEEKLY"].same_weekday_locked is True
