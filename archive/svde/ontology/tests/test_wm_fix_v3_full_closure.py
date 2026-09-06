"""WM-FIX v3.0 Tests: Full Guards, Mandatory GPS, DeferralPolicy E, Persistent Transitions."""

import sys
import pytest
from pathlib import Path
import datetime

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.world_model.state_snapshot import (
    OperationalDecisionWorldState, BitemporalPeriod, CognitiveCategory,
    LifecycleStatus, GeoCoordinate, DerivedDepotEstimate, OperationalCustomer,
    OperationalResource, OperationalVisitPolicy, OperationalCommitment,
    OperationalVisitLifecycleRecord, SourceManifest, GeoQualityStatus,
    FulfillmentClass, PolicyRegistry, InStoreActionFact, InStoreActionType,
    ActualVisitEvent, DeferralPolicy
)
from prism_ontology.world_model.transition_engine import (
    StateTransitionEngine, StateTransitionRecord, _deterministic_hash
)


def make_bitemporal() -> BitemporalPeriod:
    return BitemporalPeriod(
        valid_from=datetime.datetime(2025, 8, 1),
        valid_to=datetime.datetime(2026, 7, 31),
        transaction_from=datetime.datetime.now(),
        transaction_to=None
    )


def make_manifest() -> SourceManifest:
    return SourceManifest("mock.xlsx", "a" * 64, assembled_at=datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc))


def make_store(code="1001"):
    return OperationalCustomer(
        store_code=code, store_name=f"Store_{code}", tier="Key", ka_name="孩子王",
        district="崇川区", location=GeoCoordinate(120.88, 32.02),
        geo_quality=GeoQualityStatus.EXACT_MATCH,
        fulfillment_class=FulfillmentClass.REQUIRED, address="Test Addr"
    )


def make_rep(rep_id="REP_001", codes=("1001",)):
    depot_est = DerivedDepotEstimate(rep_id, GeoCoordinate(120.89, 32.01), len(codes), 0.95)
    return OperationalResource(
        rep_id=rep_id, rep_name=rep_id, region="东区", sub_region="南通", city="南通",
        depot_estimate=depot_est, assigned_store_codes=codes
    )


def make_policy(code, freq, ctype="STRICT_WEEKLY"):
    return OperationalVisitPolicy(
        policy_id=f"POL_{code}", policy_version="v2.0", store_code=code,
        target_frequency_per_month=freq, cadence_type=ctype, same_weekday_locked=True,
        bitemporal=make_bitemporal(), approved_by="DIRECTOR"
    )


@pytest.fixture
def mock_state():
    s1 = make_store()
    s2 = make_store(code="1002")
    r1 = make_rep("REP_001", ("1001", "1002"))
    r2 = make_rep("REP_002", ())
    
    pol_dict = {"1001": make_policy("1001", 2, "STRICT_BIWEEKLY"),
                "1002": make_policy("1002", 4, "STRICT_WEEKLY")}
    
    # DeferralPolicy for Guard E
    pol_def = {
        "DEF_STANDARD": DeferralPolicy(
            policy_id="DEF_STANDARD", max_deferrals_per_month=2,
            allowed_deferral_window_days=7, requires_approval=True,
            approver_role="REP_MANAGER"
        )
    }
    
    policies = PolicyRegistry(
        cadence_rules={
            "RULE_STRICT_WEEKLY": type('CR', (), {
                'rule_id': 'RULE_STRICT_WEEKLY', 'target_frequency_per_month': 4,
                'cadence_type': 'STRICT_WEEKLY', 'exact_interval_days': 7, 'same_weekday_locked': True
            })()
        },
        ownership_map={"1001": "REP_001", "1002": "REP_001"},
        operational_policies=pol_dict,
        deferral_policies=pol_def
    )
    
    rec1 = OperationalVisitLifecycleRecord("V_001", "1002", "REP_001",
        datetime.date(2026, 6, 5), LifecycleStatus.PLANNED, [])
    
    return OperationalDecisionWorldState(
        snapshot_id="SNAP_TEST", bitemporal=make_bitemporal(), manifest=make_manifest(),
        customers={"1001": s1, "1002": s2}, resources={"REP_001": r1, "REP_002": r2},
        account_hierarchies={}, product_line_scopes={}, supply_nodes={},
        policies=policies, commitments={},
        visit_lifecycle_records={"V_001": rec1},
        transition_records=()
    )


# ====================================================================
# P1-1: Mandatory explicit time
# ====================================================================

def test_transition_rejects_implicit_time_defaults(mock_state):
    with pytest.raises(ValueError, match="P1-1 Violation"):
        StateTransitionEngine.transition_visit_status(
            mock_state, "V_001", LifecycleStatus.COMMITTED,
            triggering_event_ref="EVT", event_time=None, transaction_time=None,
            approver_id="DIR"
        )


# ====================================================================
# P0-1: Guard E DeferralPolicy real enforcement
# ====================================================================

def test_guard_e_missing_deferral_policy_id_blocks(mock_state):
    s1, _, _ = StateTransitionEngine.transition_visit_status(
        mock_state, "V_001", LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT_APPROVE", event_time=datetime.datetime(2026, 6, 4),
        transaction_time=datetime.datetime(2026, 6, 4, 9), approver_id="DIR"
    )
    with pytest.raises(ValueError, match="Guard E Failed.*deferral_policy_id is required"):
        StateTransitionEngine.transition_visit_status(
            s1, "V_001", LifecycleStatus.DEFERRED,
            triggering_event_ref="EVT_DEFER", event_time=datetime.datetime(2026, 6, 5, 18),
            transaction_time=datetime.datetime(2026, 6, 5, 18), approver_id="MGR"
        )


def test_guard_e_valid_deferral_succeeds(mock_state):
    s1, _, _ = StateTransitionEngine.transition_visit_status(
        mock_state, "V_001", LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT_APPROVE", event_time=datetime.datetime(2026, 6, 4),
        transaction_time=datetime.datetime(2026, 6, 4, 9), approver_id="DIR"
    )
    s2, rec2, tr = StateTransitionEngine.transition_visit_status(
        s1, "V_001", LifecycleStatus.DEFERRED,
        triggering_event_ref="EVT_DEFER", event_time=datetime.datetime(2026, 6, 5, 18),
        transaction_time=datetime.datetime(2026, 6, 5, 18), approver_id="MGR",
        deferral_policy_id="DEF_STANDARD"
    )
    assert rec2.current_status == LifecycleStatus.DEFERRED
    assert tr.to_status == LifecycleStatus.DEFERRED


# ====================================================================
# P0-2: Guard C mandatory GPS (None -> Fail-Closed)
# ====================================================================

def test_guard_c_missing_gps_blocks(mock_state):
    s1, _, _ = StateTransitionEngine.transition_visit_status(
        mock_state, "V_001", LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT_APPROVE", event_time=datetime.datetime(2026, 6, 4),
        transaction_time=datetime.datetime(2026, 6, 4, 9), approver_id="DIR"
    )
    with pytest.raises(ValueError, match="Guard C Failed.*Missing GPS evidence"):
        StateTransitionEngine.transition_visit_status(
            s1, "V_001", LifecycleStatus.IN_PROGRESS,
            triggering_event_ref="EVT_CHECKIN", event_time=datetime.datetime(2026, 6, 5, 9),
            transaction_time=datetime.datetime(2026, 6, 5, 9),
            gps_deviation_meters=None  # FIXED: must fail
        )


def test_guard_c_excessive_gps_blocks(mock_state):
    s1, _, _ = StateTransitionEngine.transition_visit_status(
        mock_state, "V_001", LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT_APPROVE", event_time=datetime.datetime(2026, 6, 4),
        transaction_time=datetime.datetime(2026, 6, 4, 9), approver_id="DIR"
    )
    with pytest.raises(ValueError, match="Guard C Failed.*exceeds"):
        StateTransitionEngine.transition_visit_status(
            s1, "V_001", LifecycleStatus.IN_PROGRESS,
            triggering_event_ref="EVT_CHECKIN", event_time=datetime.datetime(2026, 6, 5, 9),
            transaction_time=datetime.datetime(2026, 6, 5, 9),
            gps_deviation_meters=800.0
        )


# ====================================================================
# P1-2: Persistent StateTransitionRecord
# ====================================================================

def test_transition_persists_record_in_worldstate(mock_state):
    s1, _, transition_record = StateTransitionEngine.transition_visit_status(
        mock_state, "V_001", LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT_APPROVE", event_time=datetime.datetime(2026, 6, 4),
        transaction_time=datetime.datetime(2026, 6, 4, 9), approver_id="DIR_GHB",
        policy_version_snapshot="v2.0", evidence_refs=["DOC_001", "LOGIN_TRACE_004"]
    )
    # FIX-3 v3: Records are stored persistently
    assert len(s1.transition_records) == 1
    assert s1.transition_records[0].to_status == LifecycleStatus.COMMITTED
    assert s1.transition_records[0].approver_id == "DIR_GHB"
    assert len(s1.transition_records[0].evidence_refs) == 2
    assert s1.transition_records[0].record_hash != ""
    assert len(s1.transition_records[0].record_hash) == 64  # Full SHA-256


def test_deterministic_hash_is_stable_across_calls():
    """P1-3: Hash must be deterministic given identical inputs."""
    r1 = StateTransitionRecord(
        transition_id="", visit_id="V_001", base_snapshot_id="SNAP_A",
        from_status=LifecycleStatus.PLANNED, to_status=LifecycleStatus.COMMITTED,
        event_time=datetime.datetime(2026, 6, 4, 9), transaction_time=datetime.datetime(2026, 6, 4, 9),
        triggering_event_ref="EVT_APPROVE", approver_id="DIR",
        gps_deviation_meters=120.0, service_duration_min=45.0,
        policy_version_snapshot="v2.0", evidence_refs=["DOC_001"]
    )
    h1 = _deterministic_hash(r1)
    h2 = _deterministic_hash(r1)
    assert h1 == h2
    # Different inputs -> different hash
    r2 = StateTransitionRecord(
        transition_id="", visit_id="V_002", base_snapshot_id="SNAP_A",
        from_status=LifecycleStatus.PLANNED, to_status=LifecycleStatus.COMMITTED,
        event_time=datetime.datetime(2026, 6, 4, 9), transaction_time=datetime.datetime(2026, 6, 4, 9),
        triggering_event_ref="EVT_APPROVE", approver_id="DIR",
        gps_deviation_meters=120.0, service_duration_min=45.0,
        policy_version_snapshot="v2.0", evidence_refs=["DOC_001"]
    )
    assert _deterministic_hash(r1) != _deterministic_hash(r2)


# ====================================================================
# P0-3: Scenario Rollout inherits operational_policies and deferral_policies
# ====================================================================

def test_rollout_inherits_baseline_operational_policies(mock_state):
    # Baseline has 2 policies in operational_policies
    assert len(mock_state.policies.operational_policies) == 2
    
    branched = StateTransitionEngine.rollout_reallocation_scenario(
        base_state=mock_state, scenario_id="SCEN_TEST",
        store_code="1001", from_rep_id="REP_001", to_rep_id="REP_002",
        scenario_timestamp=datetime.datetime(2026, 8, 24, 12, 0, 0),
        transition_valid_from=datetime.date(2026, 6, 1)
    )
    # P0-3: Branch state must still have the 2 operational_policies
    assert len(branched.policies.operational_policies) == 2
    assert "1001" in branched.policies.operational_policies
    # Also inherit deferral_policies
    assert len(branched.policies.deferral_policies) == 1
    assert "DEF_STANDARD" in branched.policies.deferral_policies


# ====================================================================
# P1-4: True Capacity Rollout Computation
# ====================================================================

def test_rollout_computes_true_capacity_from_history(mock_state):
    # Add some execution_fact_stream entries so we have historical load data
    # P1-1: Create a NEW state instance with updated execution_fact_stream (FrozenInstance safe)
    import dataclasses
    mock_state = dataclasses.replace(
        mock_state,
        execution_fact_stream=list(mock_state.execution_fact_stream) + [
            ActualVisitEvent("EVT_001", "1001", "REP_001", datetime.date(2026, 5, 1), 55.0, 5.0, True, (), None, "history1"),
            ActualVisitEvent("EVT_002", "1001", "REP_001", datetime.date(2026, 5, 3), 50.0, 5.0, True, (), None, "history2"),
            ActualVisitEvent("EVT_003", "1002", "REP_001", datetime.date(2026, 6, 1), 60.0, 5.0, True, (), None, "planned1"),
        ]
    )
    
    branched = StateTransitionEngine.rollout_reallocation_scenario(
        base_state=mock_state, scenario_id="SCEN_TEST",
        store_code="1001", from_rep_id="REP_001", to_rep_id="REP_002",
        scenario_timestamp=datetime.datetime(2026, 8, 24, 12, 0, 0),
        transition_valid_from=datetime.date(2026, 6, 1)
    )
    cap_impact = branched.active_scenario_branches["SCEN_TEST"]["capacity_impact"]
    # P1-4: Computed from actual history, NOT hardcoded -1/+1
    assert "REP_001_workload_change_min" in cap_impact
    assert cap_impact["REP_001_workload_change_min"] == -105.0  # -55 -50 from history
    assert cap_impact["REP_002_workload_change_min"] == 105.0


# ====================================================================
# P1-4: Test multi-version policy selection (P2-1)
# ====================================================================

def test_resolve_active_policy_by_valid_time(mock_state):
    """P2-1: Multi-version policy selection by bitemporal check."""
    from prism_ontology.world_model.planner_projection import _resolve_active_frequency_v2
    # Baseline valid_from = 2025-08-01; policies active
    assert _resolve_active_frequency_v2(mock_state, "1001") == 2
    assert _resolve_active_frequency_v2(mock_state, "1002") == 4
    
    # When no policy exists, returns None
    assert _resolve_active_frequency_v2(mock_state, "NONE_STORE") is None
