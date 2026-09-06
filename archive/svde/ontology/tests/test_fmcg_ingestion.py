"""Phase 5 tests for FMCG real data ingestion.

Tests:
- Load 6467 FMCG rows
- Verify all 7 reps present
- Verify field mapping to v0.3 objects
- Verify precheck detection
- Verify no fields beyond v0.3 schema are mapped
- Verify SOP-related fields NOT created
"""
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.reference.store import ReferenceOntologyStore
from prism_ontology.real_data.fmcg_ingestor import (
    FMCGRealDataIngestor, FMCG_TO_V03_FIELD_MAP, FMCG_TIER_MAP
)

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def ingestor() -> FMCGRealDataIngestor:
    store = ReferenceOntologyStore()
    ingestor = FMCGRealDataIngestor(DATA_FILE, store)
    ingestor.load()
    return ingestor


# ============================================================================
# Loading
# ============================================================================

def test_data_file_exists():
    assert DATA_FILE.exists(), f"FMCG data file missing: {DATA_FILE}"


def test_load_ingests_6467_rows(ingestor):
    assert len(ingestor.raw_rows) == 6467


def test_load_preserves_all_53_columns(ingestor):
    if not ingestor.raw_rows:
        pytest.skip("No data")
    assert len(ingestor.raw_rows[0]) == 53


# ============================================================================
# 7 Sales Reps (per user "7 persons")
# ============================================================================

def test_seven_sales_reps_present(ingestor):
    reps = {r.get("门店负责人") for r in ingestor.raw_rows if r.get("门店负责人")}
    assert len(reps) == 7, f"Expected 7 reps, got {len(reps)}: {reps}"
    expected_reps = {"静", "欣", "许强", "晓敏", "仁军", "超", "佳佳"}
    assert reps == expected_reps


def test_per_rep_visit_count(ingestor):
    rep_counts = {}
    for r in ingestor.raw_rows:
        rep = r.get("门店负责人")
        if rep:
            rep_counts[rep] = rep_counts.get(rep, 0) + 1
    assert all(800 <= c <= 1100 for c in rep_counts.values()), f"Rep counts out of range: {rep_counts}"


# ============================================================================
# DataPrecheck (subset validation per v1.1 §6.1)
# ============================================================================

def test_precheck_passes(ingestor):
    report = ingestor.precheck()
    assert report["is_valid"] is True, f"Precheck issues: {report['issues']}"
    assert report["total_rows"] == 6467
    assert report["unique_reps"] == 7


def test_precheck_reports_date_range(ingestor):
    report = ingestor.precheck()
    start, end = report["date_range"]
    assert start is not None
    assert end is not None
    assert start != end


# ============================================================================
# Field mapping to v0.3 objects
# ============================================================================

def test_field_mapping_covers_customer_identity(ingestor):
    report = ingestor.field_mapping_report()
    assert "Customer" in report["v0_3_object_field_count"]
    # Customer should get at least: id, name, tier, location
    assert report["v0_3_object_field_count"]["Customer"] >= 4


def test_field_mapping_covers_resource_rep(ingestor):
    report = ingestor.field_mapping_report()
    assert "Resource" in report["v0_3_object_field_count"]
    # Resource: rep_id, region, sub_region
    assert report["v0_3_object_field_count"]["Resource"] >= 3


def test_field_mapping_covers_event_layer(ingestor):
    report = ingestor.field_mapping_report()
    # VisitEvent, PlannedVisit
    for obj in ["VisitEvent", "PlannedVisit"]:
        assert obj in report["v0_3_object_field_count"], f"Missing {obj}"


def test_field_mapping_covers_policy_layer(ingestor):
    report = ingestor.field_mapping_report()
    assert "OwnershipPolicy" in report["v0_3_object_field_count"]


def test_unmapped_columns_are_explicitly_listed(ingestor):
    report = ingestor.field_mapping_report()
    # Some columns (like 合同陈列目标数, 拜访小结, etc.) may not map to v0.3
    # The report MUST list them so business owner can decide future GAPs
    assert "unmapped_fmcg_columns" in report
    assert isinstance(report["unmapped_fmcg_columns"], list)


# ============================================================================
# v1.1 §6.1 Anti-Promotion Guard
# ============================================================================

def test_no_sop_objects_in_mapping():
    """GAP-6 closed: NO SOP objects (SOPPolicy, CustomerSOPBinding, etc.) in field map."""
    sop_keywords = ["SOP", "StandardOperating"]
    for fmcg_field, v03_field in FMCG_TO_V03_FIELD_MAP.items():
        assert "SOP" not in fmcg_field, f"FMCG field '{fmcg_field}' suggests SOP"
        assert "SOP" not in v03_field, f"v0.3 field '{v03_field}' is SOP"
        assert "StandardOperating" not in fmcg_field
        assert "StandardOperating" not in v03_field


def test_no_algorithm_concepts_in_field_map():
    """Algorithm concepts (CG, LNS, Tabu, etc.) MUST NOT enter business ontology field map."""
    algo_keywords = ["ColumnGen", "LNS", "Tabu", "Simplex", "BigM", "Solver"]
    for fmcg_field, v03_field in FMCG_TO_V03_FIELD_MAP.items():
        for kw in algo_keywords:
            assert kw not in fmcg_field, f"Algorithm keyword '{kw}' in {fmcg_field}"
            assert kw not in v03_field, f"Algorithm keyword '{kw}' in {v03_field}"


def test_no_channel_hierarchy_in_field_map():
    """Channel hierarchy (Kotler 4P) is REJECTED per v0.3 §3 anti-promotion."""
    channel_keywords = ["Channel", "渠道层级"]
    for fmcg_field in FMCG_TO_V03_FIELD_MAP:
        # The FMCG data has 主数据_KA渠道 (KA channel name) — this is operational data, NOT a hierarchy
        # But we should not create a "ChannelHierarchy" object
        for kw in channel_keywords:
            if kw in fmcg_field and fmcg_field != "主数据_KA渠道":
                pytest.fail(f"Suspicious channel field: {fmcg_field}")


def test_no_sales_incentive_in_field_map():
    """Sales force incentive is REJECTED per v0.3 §3 anti-promotion."""
    for fmcg_field in FMCG_TO_V03_FIELD_MAP:
        assert "激励" not in fmcg_field, f"Sales incentive field: {fmcg_field}"
        assert "Incentive" not in fmcg_field


def test_no_mega_project_cba_in_field_map():
    """Mega-project CBA methodology is REJECTED."""
    for fmcg_field in FMCG_TO_V03_FIELD_MAP:
        assert "CBA" not in fmcg_field, f"CBA field: {fmcg_field}"


# ============================================================================
# Tier Mapping
# ============================================================================

def test_tier_map_covers_all_fmcg_tiers():
    assert "Key" in FMCG_TIER_MAP
    assert "A" in FMCG_TIER_MAP
    assert "B" in FMCG_TIER_MAP
    assert "C" in FMCG_TIER_MAP


def test_projection_records_v03_aligned_fields(ingestor):
    mapped = ingestor.project_to_v03()
    assert len(mapped) == 6467
    sample = mapped[0]
    # Should contain v0.3 field names (with dots)
    v03_field_count = sum(1 for k in sample.keys() if "." in k and k != "source_row_ref")
    assert v03_field_count > 0, f"No v0.3 fields projected: {list(sample.keys())[:10]}"


# ============================================================================
# Reversibility (raw data preserved)
# ============================================================================

def test_projection_preserves_raw_reference(ingestor):
    mapped = ingestor.project_to_v03()
    # Every mapped row has a source_row_ref pointing back to raw
    assert all("source_row_ref" in r for r in mapped[:100])


def test_raw_rows_unchanged_after_projection(ingestor):
    raw_snapshot = dict(ingestor.raw_rows[0])
    ingestor.project_to_v03()
    # Verify raw row contents NOT mutated
    assert ingestor.raw_rows[0] == raw_snapshot
