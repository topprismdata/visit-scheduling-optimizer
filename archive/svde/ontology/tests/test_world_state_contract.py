"""Phase 0 Tests: WorldState v1.1 and Planning I/O Contracts.

Verifies:
1. Immutability of WorldState and Core Entities
2. Customer Universe Left-Join and un-filtered extraction
3. SourceManifest and DCR Entity sets in WorldState
4. PlanningIntent -> CandidatePlan -> PlanAuditReport -> DecisionArtifact pipeline
"""
import sys
import pytest
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.contracts.world_state import (
    BitemporalPeriod,
    DerivedDepotEstimate,
    WorldState, SourceManifest, CustomerEntity, ResourceEntity, GeoCoordinate,
    GeoQualityStatus, PolicyRegistry, CadenceRule, SupplyNodeEntity, FulfillmentClass
)
from prism_ontology.contracts.planning_io import (
    PlanningIntent, PlanningCapabilityType, CandidatePlan,
    PlannedDailyRoute, PlannedStop, PlanAuditReport, DimensionAuditResult,
    AuditDimension, DecisionArtifact
)


@pytest.fixture
def sample_world_state() -> WorldState:
    depot = GeoCoordinate(120.8943, 32.0084)
    
    # 2 Customer entities
    c1 = CustomerEntity(
        store_code="1001",
        store_name="孩子王南通万达",
        tier="Key",
        ka_name="孩子王",
        district="崇川区",
        location=GeoCoordinate(120.88, 32.02),
        geo_quality=GeoQualityStatus.EXACT_MATCH,
        planned_frequency=2,
        fulfillment_class=FulfillmentClass.REQUIRED
    )
    c2 = CustomerEntity(
        store_code="1002",
        store_name="NT23爱婴室人民中路",
        tier="Key",
        ka_name="爱婴室",
        district="崇川区",
        location=GeoCoordinate(120.86, 32.01),
        geo_quality=GeoQualityStatus.EXACT_MATCH,
        planned_frequency=4,
        fulfillment_class=FulfillmentClass.REQUIRED
    )
    
    # 1 Resource entity
    depot_est = DerivedDepotEstimate("REP_001", depot, 2, 0.99)
    r1 = ResourceEntity(
        rep_id="REP_001",
        rep_name="仁军",
        region="东区",
        sub_region="南通",
        city="南通",
        depot_estimate=depot_est,
        assigned_store_codes=("1001", "1002")
    )
    
    # Policies
    pol = PolicyRegistry(
        cadence_rules={
            "RULE_4W": CadenceRule("RULE_4W", 4, "STRICT_WEEKLY", 7, True),
            "RULE_2W": CadenceRule("RULE_2W", 2, "STRICT_BIWEEKLY", 14, True)
        },
        ownership_map={"1001": "REP_001", "1002": "REP_001"}
    )
    
    manifest = SourceManifest(
        source_file_path="mock_path.xlsx",
        source_file_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        assembled_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc)
    )
    
    return WorldState(
        snapshot_id="SNAP_20260824_001",
        bitemporal=BitemporalPeriod(
            valid_from=datetime.datetime(2025, 8, 1, tzinfo=datetime.timezone.utc),
            valid_to=datetime.datetime(2026, 7, 31, tzinfo=datetime.timezone.utc),
            transaction_from=datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc),
            transaction_to=None
        ),
        manifest=manifest,
        customers={"1001": c1, "1002": c2},
        resources={"REP_001": r1},
        account_hierarchies={},
        product_line_scopes={},
        supply_nodes={},
        policies=pol,
        commitments={}
    )


# ============================================================================
# WorldState Immutability and Universe Integrity
# ============================================================================

def test_world_state_is_immutable(sample_world_state):
    with pytest.raises(Exception):
        sample_world_state.snapshot_id = "MUTATED"


def test_customer_universe_extraction_returns_full_assigned_stores(sample_world_state):
    rep_universe = sample_world_state.get_rep_universe("REP_001")
    assert len(rep_universe) == 2
    assert "1001" in rep_universe
    assert "1002" in rep_universe
    assert rep_universe["1002"].store_name == "NT23爱婴室人民中路"


def test_customer_universe_for_unknown_rep_returns_empty(sample_world_state):
    rep_universe = sample_world_state.get_rep_universe("UNKNOWN_REP")
    assert rep_universe == {}


# ============================================================================
# Planning I/O Pipeline Contracts
# ============================================================================

def test_planning_intent_contract():
    intent = PlanningIntent(
        intent_id="INT_001",
        capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
        target_rep_id="REP_001",
        target_horizon_label="2026-06",
        working_days=("2026-06-01", "2026-06-02", "2026-06-03"),
        max_daily_stops=6,
        max_daily_workload_min=480.0,
        same_weekday_required=True
    )
    assert intent.capability_type == PlanningCapabilityType.PERIODIC_VISIT_PLANNING
    assert intent.same_weekday_required is True
    assert len(intent.working_days) == 3


def test_candidate_plan_and_audit_report_pipeline():
    stop1 = PlannedStop(1, "1002", "NT23人民中路", "崇川区", 50.0, 5.2, 12.0)
    route1 = PlannedDailyRoute(
        date_str="2026-06-03",
        weekday_name="周三",
        rep_id="REP_001",
        stops=[stop1],
        total_daily_distance_km=10.4,
        total_daily_transit_min=24.0,
        total_daily_service_min=50.0,
        total_daily_workload_min=74.0
    )
    
    candidate = CandidatePlan(
        plan_id="PLAN_001",
        intent_id="INT_001",
        rep_id="REP_001",
        period_label="2026-06",
        daily_routes=[route1],
        total_scheduled_visits=1
    )
    assert candidate.total_scheduled_visits == 1
    assert candidate.daily_routes[0].stops_count == 1

    dim_phys = DimensionAuditResult(AuditDimension.PHYSICAL_FEASIBILITY, True, 0)
    dim_biz = DimensionAuditResult(AuditDimension.BUSINESS_COMPLIANCE, True, 0)
    dim_sem = DimensionAuditResult(AuditDimension.SEMANTIC_PURITY, True, 0)
    
    audit_report = PlanAuditReport(
        plan_id="PLAN_001",
        is_fully_compliant=True,
        cadence_compliance_rate=100.0,
        dimension_results={
            AuditDimension.PHYSICAL_FEASIBILITY: dim_phys,
            AuditDimension.BUSINESS_COMPLIANCE: dim_biz,
            AuditDimension.SEMANTIC_PURITY: dim_sem
        },
        summary_message="All 3 dimensions verified."
    )
    assert audit_report.is_fully_compliant is True
    assert audit_report.cadence_compliance_rate == 100.0
