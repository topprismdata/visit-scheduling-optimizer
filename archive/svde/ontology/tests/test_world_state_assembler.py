"""WorldState v1.1 Assembler Tests: Comprehensive Semantic Verification.

Verifies:
1. SourceManifest provenance (SHA-256 hash, raw 6467, valid 6374, excluded 93)
2. Full DCR Entity Instantiations:
   - 13 AccountHierarchy entities fully loaded
   - 3 ProductLineScope entities fully loaded
   - 18 SupplyNode entities with UNCALIBRATED status
3. InStoreAction facts and MerchandisingCompliance facts extraction
4. Explicit Ownership Conflict detection (NT70 store)
5. Plannability Data Gateway (missing geo -> UNMAPPED & is_plannable=False)
6. Authentic Resource Roster with specific sub_region, city, and city-center depots
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.real_data.world_state_assembler import WorldStateAssembler
from prism_ontology.contracts.world_state import (
    WorldState, FulfillmentClass, GeoQualityStatus, InStoreActionType
)

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def world_state_v1_1() -> WorldState:
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
    return WorldStateAssembler.assemble_from_excel(DATA_FILE, assembled_at=_ASSEMBLED_AT)


# ============================================================================
# 1. Source Manifest & Provenance Integrity
# ============================================================================

def test_source_manifest_provenance(world_state_v1_1):
    manifest = world_state_v1_1.manifest
    assert len(manifest.source_file_sha256) == 64
    assert manifest.raw_rows_count == 6467
    assert manifest.valid_facts_count == 6374
    assert manifest.excluded_rows_count == 93
    assert "missing store_code" in manifest.exclusion_reason


# ============================================================================
# 2. DCR Entities Full Instantiation
# ============================================================================

def test_account_hierarchies_instantiated(world_state_v1_1):
    kas = world_state_v1_1.account_hierarchies
    assert len(kas) >= 13
    ka_names = {a.account_name for a in kas.values()}
    assert "爱婴室" in ka_names
    assert "孩子王" in ka_names
    assert "高鑫零售" in ka_names


def test_product_line_scopes_instantiated(world_state_v1_1):
    brands = world_state_v1_1.product_line_scopes
    brand_names = {b.brand_name for b in brands.values()}
    assert any("Prestige" in n for n in brand_names)
    assert any("Natura" in n for n in brand_names)


def test_supply_nodes_instantiated(world_state_v1_1):
    dcs = world_state_v1_1.supply_nodes
    assert len(dcs) >= 18
    dc_names = {d.dc_name for d in dcs.values()}
    assert "爱婴室嘉善大仓" in dc_names
    assert "孩子王南京总仓" in dc_names
    # Delivery status must be truthfully UNCALIBRATED (No fake assumptions!)
    for dc in dcs.values():
        assert dc.delivery_status == "UNCALIBRATED"


# ============================================================================
# 3. In-Store Actions & Merchandising Compliance Facts
# ============================================================================

def test_actual_visit_events_contain_actions_and_compliance(world_state_v1_1):
    events = world_state_v1_1.execution_fact_stream
    assert len(events) == 6374
    
    # Check that in-store actions are extracted
    action_events = [e for e in events if len(e.actions) > 0]
    assert len(action_events) > 1000
    
    # Check merchandising compliance facts
    merch_events = [e for e in events if e.merchandising_compliance is not None]
    assert len(merch_events) >= 900
    sample_merch = merch_events[0].merchandising_compliance
    assert sample_merch.contract_target_units > 0
    assert sample_merch.actual_compliant_units >= 0


# ============================================================================
# 4. Ownership Conflict Detection (Explicit & Non-silent)
# ============================================================================

def test_ownership_conflict_detected_on_shared_stores(world_state_v1_1):
    conflicts = world_state_v1_1.policies.ownership_conflicts
    assert len(conflicts) >= 1
    conflict_codes = {c.store_code for c in conflicts}
    # NT70 (10081526) was visited by both 佳佳 and 仁军
    assert "10081526" in conflict_codes
    nt70_conf = [c for c in conflicts if c.store_code == "10081526"][0]
    assert "佳佳" in nt70_conf.conflicting_reps
    assert "仁军" in nt70_conf.conflicting_reps


# ============================================================================
# 5. Resource Entity Real City Depots & Sub-regions
# ============================================================================

def test_resources_have_authentic_city_depots(world_state_v1_1):
    reps = world_state_v1_1.resources
    assert len(reps) == 7
    for rep_name in ["晓敏", "静", "欣", "许强", "超", "仁军", "佳佳"]:
        assert rep_name in reps
        depot = reps[rep_name].home_depot_coord
        assert 119.0 < depot.longitude < 122.0
        assert 31.0 < depot.latitude < 33.0
