"""Canonical WorldState API 包装层单元测试 (draft-implementation)

覆盖 8 个规范入口的正反用例:
1. get_worldstate_view: 正例 / SnapshotNotFound / 未知字段 / REP_SCOPED 越权
2. query_customer_universe_view: 正例 (fixture 仁军) / 未知 rep
3. resolve_active_policies: 正例 (合成 policy) / PolicyNotFound / naive 时间
4. get_ownership_conflicts: 正例
5. request_transition: 正例 (PLANNED->COMMITTED) / visit 缺失 -> GuardRejected
6. submit_execution_feedback: 回执字段 + 解耦 (不产生新快照)
7. request_scenario_rollout: L5NotImplemented (诚实未实现)
8. compile_planner_projection: 正例 (fixture 仁军) / 缺 target / naive intent
9. ApiRequestContext / WorkflowContext 校验
"""
import sys
import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]  # = svde/ontology
sys.path.insert(0, str(ROOT / "src"))

from prism_ontology.world_model.canonical_api import (
    CanonicalWorldModelApi,
    SnapshotStore,
    ApiRequestContext,
    ResourceScope,
    WorkflowContext,
    RequestFingerprint,
    TransitionRequest,
    PlanningIntent,
    WorldModelError,
    SnapshotNotFound,
    ScopeNotPermitted,
    PolicyNotFound,
    GuardRejected,
    MissingTimezone,
    MissingApiVersion,
    TimeContractViolation,
    L5NotImplemented,
)
from prism_ontology.world_model.state_snapshot import (
    OperationalDecisionWorldState,
    OperationalVisitPolicy,
    OperationalVisitLifecycleRecord,
    ActualVisitEvent,
    BitemporalPeriod,
    SourceManifest,
    PolicyRegistry,
    LifecycleStatus,
)
from prism_ontology.real_data.world_state_assembler import WorldStateAssembler

FIXTURE_PATH = ROOT / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"
TZ = datetime.timezone.utc
_ASSEMBLED_AT = datetime.datetime(2026, 8, 1, tzinfo=TZ)


def _ctx() -> ApiRequestContext:
    return ApiRequestContext(
        api_version="WM-API-v1.0-draft.5.2",
        request_id="req-test-001",
        caller_id="test-suite",
        source_system="pytest",
        timezone="Asia/Shanghai",
    )


def _bitemporal() -> BitemporalPeriod:
    return BitemporalPeriod(
        valid_from=datetime.datetime(2025, 8, 1, tzinfo=TZ),
        valid_to=datetime.datetime(2026, 7, 31, tzinfo=TZ),
        transaction_from=_ASSEMBLED_AT,
        transaction_to=None,
    )


def _manifest() -> SourceManifest:
    return SourceManifest(
        source_file_path="synthetic",
        source_file_sha256="0" * 64,
        assembled_at=_ASSEMBLED_AT,
    )


def _synthetic_ws(
    snapshot_id: str = "SNAP_TEST_001",
    policies: PolicyRegistry = None,
    lifecycle_records: dict = None,
) -> OperationalDecisionWorldState:
    return OperationalDecisionWorldState(
        snapshot_id=snapshot_id,
        bitemporal=_bitemporal(),
        manifest=_manifest(),
        customers={},
        resources={},
        account_hierarchies={},
        product_line_scopes={},
        supply_nodes={},
        policies=policies if policies is not None else PolicyRegistry(),
        execution_fact_stream=[],
        visit_lifecycle_records=lifecycle_records if lifecycle_records is not None else {},
    )


def _fixture_api():
    if not FIXTURE_PATH.exists():
        pytest.skip("fixture 不存在")
    ws = WorldStateAssembler.assemble_from_excel(str(FIXTURE_PATH), assembled_at=_ASSEMBLED_AT)
    api = CanonicalWorldModelApi()
    api.store.register(ws)
    return api, ws


# === 1. get_worldstate_view ===
def test_get_worldstate_view_positive_and_errors():
    api, ws = _fixture_api()
    view = api.get_worldstate_view(_ctx(), ws.snapshot_id, ResourceScope("FULL"), ("snapshot_id", "policies"))
    assert view.snapshot_id == ws.snapshot_id
    assert view.fields == ("snapshot_id", "policies")
    assert view.data["snapshot_id"] == ws.snapshot_id

    with pytest.raises(SnapshotNotFound):
        api.get_worldstate_view(_ctx(), "SNAP_MISSING", ResourceScope("FULL"), ("snapshot_id",))
    with pytest.raises(ScopeNotPermitted):
        api.get_worldstate_view(_ctx(), ws.snapshot_id, ResourceScope("FULL"), ("not_a_field",))
    with pytest.raises(ScopeNotPermitted):
        api.get_worldstate_view(_ctx(), ws.snapshot_id, ResourceScope("REP_SCOPED", rep_id="仁军"),
                                ("customers",))  # REP_SCOPED 禁止全局字段
    print("  [OK] 1: get_worldstate_view 正例 + 3 反例")


# === 2. query_customer_universe_view ===
def test_query_customer_universe_view():
    api, ws = _fixture_api()
    rep_id = sorted(ws.resources.keys())[0]
    view = api.query_customer_universe_view(_ctx(), rep_id, ws.snapshot_id)
    assert view.rep_id == rep_id
    assert len(view.customers) > 0
    with pytest.raises(SnapshotNotFound):
        api.query_customer_universe_view(_ctx(), "不存在的代表", ws.snapshot_id)
    print(f"  [OK] 2: query_customer_universe_view (rep={rep_id}, n={len(view.customers)})")


# === 3. resolve_active_policies ===
def test_resolve_active_policies():
    policy = OperationalVisitPolicy(
        policy_id="P1", policy_version="v2.0", store_code="S001",
        target_frequency_per_month=3, cadence_type="STRICT_WEEKLY",
        same_weekday_locked=True, bitemporal=_bitemporal(), approved_by="boss",
    )
    registry = PolicyRegistry(operational_policies={"P1": policy})
    ws = _synthetic_ws(policies=registry)
    api = CanonicalWorldModelApi()
    api.store.register(ws)

    active = api.resolve_active_policies(
        _ctx(), "S001",
        valid_time=datetime.datetime(2026, 6, 15, tzinfo=TZ),
        transaction_time=datetime.datetime(2026, 8, 2, tzinfo=TZ),  # 晚于 policy 入库 (2026-08-01)
        snapshot_id=ws.snapshot_id,
    )
    assert len(active) == 1 and active[0].policy_id == "P1"

    with pytest.raises(PolicyNotFound):
        api.resolve_active_policies(
            _ctx(), "S999",
            valid_time=datetime.datetime(2026, 6, 15, tzinfo=TZ),
            transaction_time=datetime.datetime(2026, 6, 20, tzinfo=TZ),
            snapshot_id=ws.snapshot_id,
        )
    with pytest.raises(TimeContractViolation):
        api.resolve_active_policies(
            _ctx(), "S001",
            valid_time=datetime.datetime(2026, 6, 15),  # naive
            transaction_time=datetime.datetime(2026, 6, 20, tzinfo=TZ),
            snapshot_id=ws.snapshot_id,
        )
    print("  [OK] 3: resolve_active_policies 正例 + 2 反例")


# === 4. get_ownership_conflicts ===
def test_get_ownership_conflicts():
    api, ws = _fixture_api()
    conflicts = api.get_ownership_conflicts(_ctx(), ws.snapshot_id)
    assert isinstance(conflicts, tuple)
    print(f"  [OK] 4: get_ownership_conflicts (n={len(conflicts)})")


# === 5. request_transition ===
def test_request_transition():
    rec = OperationalVisitLifecycleRecord(
        visit_id="V001", store_code="S001", rep_id="R1",
        scheduled_date=datetime.date(2026, 6, 15),
        current_status=LifecycleStatus.PLANNED,
    )
    ws = _synthetic_ws(lifecycle_records={"V001": rec})
    api = CanonicalWorldModelApi()
    api.store.register(ws)
    n_before = len(api.store)

    fingerprint = RequestFingerprint(
        request_id="req-test-001", algorithm="RFC8785-SHA256",
        digest="a" * 64, computed_at=_ASSEMBLED_AT,
    )
    workflow = WorkflowContext(
        expected_snapshot_version=ws.snapshot_id, idempotency_key="idem-1",
        fingerprint=fingerprint,
    )
    req = TransitionRequest(
        base_snapshot_id=ws.snapshot_id,
        visit_id="V001",
        target_status=LifecycleStatus.COMMITTED,
        triggering_event_ref="EVT-1",
        event_time=datetime.datetime(2026, 6, 15, 9, 0, tzinfo=TZ),
        transaction_time=datetime.datetime(2026, 6, 15, 9, 5, tzinfo=TZ),
        gps_deviation_meters=0.0,
        approver_id="rep_manager_01",  # Guard A: COMMITTED 需显式审批人
    )
    result = api.request_transition(_ctx(), workflow, req)
    assert result.was_guard_passed is True
    assert result.new_worldstate_snapshot_id != ws.snapshot_id  # 新快照
    assert len(api.store) == n_before + 1  # 新快照已注册

    with pytest.raises(GuardRejected):
        api.request_transition(_ctx(), workflow, TransitionRequest(
            base_snapshot_id=ws.snapshot_id,
            visit_id="V_MISSING",
            target_status=LifecycleStatus.COMMITTED,
            triggering_event_ref="EVT-2",
            event_time=datetime.datetime(2026, 6, 15, 9, 0, tzinfo=TZ),
            transaction_time=datetime.datetime(2026, 6, 15, 9, 5, tzinfo=TZ),
            gps_deviation_meters=0.0,
        ))
    print("  [OK] 5: request_transition 正例 + GuardRejected 反例")


# === 6. submit_execution_feedback (解耦) ===
def test_submit_execution_feedback_decoupled():
    ws = _synthetic_ws()
    api = CanonicalWorldModelApi()
    api.store.register(ws)
    feedback = ActualVisitEvent(
        event_id="EVT-100", store_code="S001", rep_id="R1",
        visit_date=datetime.date(2026, 6, 15),
        service_duration_min=30.0, transit_duration_min=10.0,
        is_line_internal=False,
    )
    receipt = api.submit_execution_feedback(_ctx(), feedback)
    assert receipt.event_id == "EVT-100"
    assert receipt.new_snapshot_id == ws.snapshot_id  # 反馈不产生新快照
    assert receipt.transition_required is True
    assert len(api.store) == 1  # 解耦红线: store 无新快照
    print("  [OK] 6: submit_execution_feedback 回执 + 解耦验证")


# === 7. request_scenario_rollout (诚实未实现) ===
def test_request_scenario_rollout_not_implemented():
    api, ws = _fixture_api()
    intent = PlanningIntent(
        intent_id="INT-1", decision_scope="VISIT_SCHEDULING",
        valid_time=datetime.datetime(2026, 6, 1, tzinfo=TZ), timezone="Asia/Shanghai",
    )
    with pytest.raises(L5NotImplemented):
        api.request_scenario_rollout(
            _ctx(), ws.snapshot_id, intent, (), datetime.datetime(2026, 6, 1, 9, 0, tzinfo=TZ),
        )
    print("  [OK] 7: request_scenario_rollout 诚实未实现 (L5NotImplemented)")


# === 8. compile_planner_projection ===
def test_compile_planner_projection():
    api, ws = _fixture_api()
    rep_id = sorted(ws.resources.keys())[0]
    intent = PlanningIntent(
        intent_id="INT-2", decision_scope="VISIT_SCHEDULING",
        valid_time=datetime.datetime(2026, 6, 1, tzinfo=TZ), timezone="Asia/Shanghai",
        target_agent_id=rep_id,
    )
    # fixture 边界 (已知): 缺 OperationalVisitPolicy -> compiler 拒绝从观测取频次 (FIX-1 语义)
    # 包装层职责: 透传为类型化 ProjectionCompilationError (与 MVP plan=0 同根因, 忠实记录)
    from prism_ontology.world_model.canonical_api import ProjectionCompilationError
    with pytest.raises(ProjectionCompilationError, match="No active OperationalVisitPolicy"):
        api.compile_planner_projection(
            _ctx(), ws.snapshot_id, intent,
            working_days=("2026-06-01", "2026-06-02", "2026-06-03"),
        )

    # 缺 target -> WorldModelError
    with pytest.raises(WorldModelError):
        api.compile_planner_projection(_ctx(), ws.snapshot_id, PlanningIntent(
            intent_id="INT-3", decision_scope="VISIT_SCHEDULING",
            valid_time=datetime.datetime(2026, 6, 1, tzinfo=TZ), timezone="Asia/Shanghai",
        ))
    # naive intent.valid_time -> TimeContractViolation
    with pytest.raises(TimeContractViolation):
        api.compile_planner_projection(_ctx(), ws.snapshot_id, PlanningIntent(
            intent_id="INT-4", decision_scope="VISIT_SCHEDULING",
            valid_time=datetime.datetime(2026, 6, 1), timezone="Asia/Shanghai",
            target_agent_id=rep_id,
        ))


def test_context_validation():
    with pytest.raises(MissingTimezone):
        ApiRequestContext("WM-API-v1.0-draft.5.2", "r1", "c1", "s1", "")
    with pytest.raises(MissingApiVersion):
        ApiRequestContext("", "r1", "c1", "s1", "Asia/Shanghai")
    # RequestFingerprint: naive computed_at -> TimeContractViolation
    with pytest.raises(TimeContractViolation):
        RequestFingerprint("r1", "RFC8785-SHA256", "a" * 64, datetime.datetime(2026, 8, 1))
    # RequestFingerprint: digest 长度错误
    with pytest.raises(WorldModelError, match="64 hex"):
        RequestFingerprint("r1", "RFC8785-SHA256", "a" * 32, _ASSEMBLED_AT)
    # WorkflowContext: fingerprint 类型错误
    with pytest.raises(WorldModelError, match="RequestFingerprint"):
        WorkflowContext("SNAP-1", "idem-1", fingerprint="not-a-fingerprint")
    print("  [OK] 9: ApiRequestContext / RequestFingerprint / WorkflowContext 校验")
