"""Canonical WorldState API 包装层 (v1.0-draft.5.2 draft-implementation)

状态声明 (五级成熟度):
- 本模块是 TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md (v1.0-draft.5.2) 的
  **draft-implementation**: 代码已实现 + 单元测试已验证, 但 API 冻结仍 BLOCKED
  (等待 BIZ-01~08 业务签署 + TECH-01~07 技术签署), 签署后如有语义变更需返工。
- 不代表生产可用, 不代表真实业务已验证。

职责 (单一事实入口, 零业务规则):
- L0-L4 查询: get_worldstate_view / query_customer_universe_view /
  resolve_active_policies / get_ownership_conflicts
- L3 状态转移: request_transition (薄适配 StateTransitionEngine, 不改 engine)
- L4 反馈闭环: submit_execution_feedback (只写回执, 不自动 transition — 解耦红线)
- L5 情景推演: request_scenario_rollout (**诚实未实现**: 抛 L5NotImplemented, 不伪造结果)
- L6 规划器投影: compile_planner_projection (薄适配 PlannerStateProjectionCompiler)

规范缺口闭合 (v1.0-draft.5.2 修订):
- WorkflowContext 与 RequestFingerprint 此前为悬空引用 (仅 API 签名无类型定义),
  已在主 API 规范 §5.2.1 按 Registry 权威字段登记补全; 本模块实现与 §5.2.1 对齐,
  待技术架构签署 (TECH-08) 确认。

严格红线:
- 类型封闭: 公共 API 字段严禁 Any
- 时间契约: 所有时间参数必须显式传入且带时区 (违者抛 TimeContractViolation)
- 零 BIZ: 不加载业务规则, 不做频次/顺延/审批等业务判断
"""
import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from prism_ontology.world_model.state_snapshot import (
    OperationalDecisionWorldState,
    OperationalCustomer,
    OperationalVisitPolicy,
    OwnershipConflictRecord,
    ActualVisitEvent,
    LifecycleStatus,
)
from prism_ontology.world_model.transition_engine import (
    StateTransitionEngine,
    StateTransitionRecord,
)
from prism_ontology.world_model.planner_projection import (
    PlannerStateProjectionCompiler,
    PlannerStateProjection,
)


# ============================================================================
# 异常体系 (规范 §6.0, 16 子类精确对齐) + 实现状态标记
# ============================================================================
class WorldModelError(Exception):
    default_code: str = "WM-UNKNOWN"

    def __init__(self, message: str, context: Optional[Dict[str, str]] = None):
        super().__init__(f"[{self.default_code}] {message}")
        self.code = self.default_code
        self.context: Dict[str, str] = {} if context is None else context


class SnapshotNotFound(WorldModelError):
    default_code = "WM-SNAPSHOT-NOT-FOUND"


class SnapshotArchived(WorldModelError):
    default_code = "WM-SNAPSHOT-ARCHIVED"


class ScopeNotPermitted(WorldModelError):
    default_code = "WM-SCOPE-NOT-PERMITTED"


class VersionMismatch(WorldModelError):
    default_code = "WM-VERSION-MISMATCH"


class IdempotencyConflict(WorldModelError):
    default_code = "WM-IDEMPOTENCY-CONFLICT"


class GuardRejected(WorldModelError):
    default_code = "WM-GUARD-REJECTED"


class ProjectionCompilationError(WorldModelError):
    default_code = "WM-PROJECTION-FAILED"


class PolicyNotFound(WorldModelError):
    default_code = "WM-POLICY-NOT-FOUND"


class DeferralPolicyNotFound(WorldModelError):
    default_code = "WM-DEFER-POLICY-NOT-FOUND"


class DeferralQuotaExceeded(WorldModelError):
    default_code = "WM-DEFER-QUOTA-EXCEEDED"


class DeferralWindowExceeded(WorldModelError):
    default_code = "WM-DEFER-WINDOW-EXCEEDED"


class ImmutableViolation(WorldModelError):
    default_code = "WM-IMMUTABLE-VIOLATION"


class MissingTimezone(WorldModelError):
    default_code = "WM-MISSING-TIMEZONE"


class MissingApiVersion(WorldModelError):
    default_code = "WM-MISSING-API-VERSION"


class TimeContractViolation(WorldModelError):
    default_code = "WM-TIME-CONTRACT"


class PartialAuthorizationReplay(WorldModelError):
    default_code = "WM-PARTIAL-AUTH-REPLAY"


class L5NotImplemented(WorldModelError):
    """实现状态标记 (非业务语义): L5 Scenario Engine 仅有设计规范, 无代码。"""
    default_code = "WM-L5-NOT-IMPLEMENTED"


# ============================================================================
# 共享上下文与基础设施类型 (规范 §2)
# ============================================================================
@dataclass(frozen=True)
class ApiRequestContext:
    """API 请求上下文 (规范 §2.1)"""
    api_version: str                  # 必填, 如 "WM-API-v1.0-draft.5.2"
    request_id: str                   # 必填, UUID 全局唯一
    caller_id: str                    # 必填
    source_system: str                # 必填
    timezone: str                     # 必填, 无默认值 (如 "Asia/Shanghai")

    def __post_init__(self):
        if not self.api_version:
            raise MissingApiVersion("api_version 必填 (如 'WM-API-v1.0-draft.5.2')")
        if not self.timezone:
            raise MissingTimezone("timezone 必填, 无默认值 (如 'Asia/Shanghai')")
        if not self.request_id or not self.caller_id or not self.source_system:
            raise WorldModelError("request_id / caller_id / source_system 必填")


@dataclass(frozen=True)
class ResourceScope:
    """资源访问范围 (规范 §5.1 get_worldstate_view 参数)"""
    level: str                        # "FULL" / "REP_SCOPED" / "STORE_SCOPED"
    rep_id: Optional[str] = None      # REP_SCOPED 时必填

    def __post_init__(self):
        if self.level not in ("FULL", "REP_SCOPED", "STORE_SCOPED"):
            raise ScopeNotPermitted(
                f"level 必须是 FULL/REP_SCOPED/STORE_SCOPED, 实际: {self.level!r}"
            )
        if self.level == "REP_SCOPED" and not self.rep_id:
            raise ScopeNotPermitted("REP_SCOPED 范围必须提供 rep_id")


@dataclass(frozen=True)
class RequestFingerprint:
    """服务端防伪指纹 (规范 §5.2.1 / 原则 7: 服务端基于 RFC 8785 生成, 客户端不可伪造)"""
    request_id: str                   # 对应 ApiRequestContext.request_id
    algorithm: str                    # 固定 "RFC8785-SHA256"
    digest: str                       # 256-bit SHA-256 digest represented as 64 hexadecimal characters
    computed_at: datetime.datetime    # 必须带时区
    server_computed: bool = True      # 恒为 True; 客户端传入 False -> PartialAuthorizationReplay

    def __post_init__(self):
        if not self.request_id:
            raise WorldModelError("RequestFingerprint.request_id 必填")
        if self.algorithm != "RFC8785-SHA256":
            raise WorldModelError(f"algorithm 必须是 RFC8785-SHA256, 实际: {self.algorithm!r}")
        if len(self.digest) != 64:
            raise WorldModelError("digest 必须是 64 hex 字符")
        if self.computed_at.tzinfo is None:
            raise TimeContractViolation(
                f"RequestFingerprint.computed_at 必须带时区, 实际 naive: {self.computed_at!r}"
            )


@dataclass(frozen=True)
class WorkflowContext:
    """工作流上下文 (规范 §5.2.1; 字段对齐 CANONICAL_TYPE_REGISTRY.md 权威登记)"""
    expected_snapshot_version: str    # 必填, 乐观并发控制 (期望的基础快照版本)
    idempotency_key: str              # 必填, 幂等键 (同键重放 -> IdempotencyConflict)
    fingerprint: RequestFingerprint   # 必填, 服务端防伪指纹

    def __post_init__(self):
        if not self.expected_snapshot_version or not self.idempotency_key:
            raise WorldModelError("expected_snapshot_version / idempotency_key 必填")
        if not isinstance(self.fingerprint, RequestFingerprint):
            raise WorldModelError(
                f"fingerprint 必须是 RequestFingerprint, 实际: {type(self.fingerprint).__name__}"
            )


# ============================================================================
# 视图类型 (只读投影, 规范 §5.1 返回类型)
# ============================================================================
@dataclass(frozen=True)
class ReadOnlyWorldStateView:
    """WorldState 只读视图 (仅暴露请求的 fields)"""
    snapshot_id: str
    fields: Tuple[str, ...]
    data: Mapping[str, object]


@dataclass(frozen=True)
class FrozenCustomerUniverseView:
    """代表客户宇宙只读视图"""
    rep_id: str
    snapshot_id: str
    customers: Tuple[OperationalCustomer, ...]


# ============================================================================
# L4 反馈回执 (Canonical Types §33)
# ============================================================================
@dataclass(frozen=True)
class ExecutionFeedbackReceipt:
    event_id: str
    new_snapshot_id: str
    transition_required: bool
    evidence_status: str
    receipt_message: str = ""


# ============================================================================
# Snapshot Store (in-memory, snapshot_id -> WorldState)
# ============================================================================
class SnapshotStore:
    """内存快照存储 (单进程用途; 生产需替换为持久 CAS 存储)"""

    def __init__(self):
        self._snapshots: Dict[str, OperationalDecisionWorldState] = {}

    def register(self, worldstate: OperationalDecisionWorldState) -> str:
        self._snapshots[worldstate.snapshot_id] = worldstate
        self._latest_snapshot_id: str = worldstate.snapshot_id
        return worldstate.snapshot_id

    @property
    def latest_snapshot_id(self) -> Optional[str]:
        return getattr(self, "_latest_snapshot_id", None)

    def get(self, snapshot_id: str) -> OperationalDecisionWorldState:
        if snapshot_id not in self._snapshots:
            raise SnapshotNotFound(
                f"snapshot_id {snapshot_id!r} 不在 Store 中",
                context={"snapshot_id": snapshot_id},
            )
        return self._snapshots[snapshot_id]

    def __contains__(self, snapshot_id: str) -> bool:
        return snapshot_id in self._snapshots

    def __len__(self) -> int:
        return len(self._snapshots)


# ============================================================================
# Canonical API Facade
# ============================================================================
_ALLOWED_VIEW_FIELDS = frozenset({
    "snapshot_id", "bitemporal", "manifest", "customers", "resources",
    "account_hierarchies", "product_line_scopes", "supply_nodes",
    "policies", "execution_fact_stream", "visit_lifecycle_records",
})


def _require_tz(value: datetime.datetime, name: str) -> None:
    """时间契约: 显式传入且带时区"""
    if not isinstance(value, datetime.datetime):
        raise TimeContractViolation(f"{name} 必须是 datetime.datetime, 实际: {type(value).__name__}")
    if value.tzinfo is None:
        raise TimeContractViolation(
            f"{name} 必须带时区 (timezone-aware), 实际 naive: {value!r}"
        )


class CanonicalWorldModelApi:
    """L0-L6 Canonical World Model API 单一事实入口 (draft-implementation)"""

    def __init__(self, store: Optional[SnapshotStore] = None):
        self.store = store if store is not None else SnapshotStore()

    # -- 内部校验 --
    @staticmethod
    def _check_context(context: ApiRequestContext) -> None:
        if not isinstance(context, ApiRequestContext):
            raise WorldModelError(f"context 必须是 ApiRequestContext, 实际: {type(context).__name__}")
        if not context.api_version:
            raise MissingApiVersion("context.api_version 为空")
        if not context.timezone:
            raise MissingTimezone("context.timezone 为空")

    # ================================================================
    # 5.1 L0-L4 核心查询
    # ================================================================
    def get_worldstate_view(
        self,
        context: ApiRequestContext,
        snapshot_id: str,
        scope: ResourceScope,
        fields: Tuple[str, ...],
    ) -> ReadOnlyWorldStateView:
        self._check_context(context)
        ws = self.store.get(snapshot_id)  # SnapshotNotFound
        unknown = [f for f in fields if f not in _ALLOWED_VIEW_FIELDS]
        if unknown:
            raise ScopeNotPermitted(
                f"请求了未许可的 fields: {unknown}",
                context={"unknown_fields": ",".join(unknown)},
            )
        if scope.level == "REP_SCOPED":
            # REP_SCOPED 只允许访问非全局字段 (排除跨代表全局集合)
            forbidden = {"customers", "resources", "account_hierarchies",
                         "product_line_scopes", "supply_nodes"}
            violated = forbidden & set(fields)
            if violated:
                raise ScopeNotPermitted(
                    f"REP_SCOPED 范围禁止访问全局字段: {sorted(violated)}",
                    context={"rep_id": scope.rep_id or ""},
                )
        data: Dict[str, object] = {f: getattr(ws, f) for f in fields}
        return ReadOnlyWorldStateView(snapshot_id=snapshot_id, fields=tuple(fields), data=data)

    def query_customer_universe_view(
        self,
        context: ApiRequestContext,
        rep_id: str,
        snapshot_id: str,
    ) -> FrozenCustomerUniverseView:
        self._check_context(context)
        ws = self.store.get(snapshot_id)
        universe = ws.get_rep_universe(rep_id)
        if not universe:
            raise SnapshotNotFound(
                f"rep_id {rep_id!r} 不存在或无分配门店",
                context={"rep_id": rep_id, "snapshot_id": snapshot_id},
            )
        return FrozenCustomerUniverseView(
            rep_id=rep_id,
            snapshot_id=snapshot_id,
            customers=tuple(universe[code] for code in sorted(universe)),
        )

    def resolve_active_policies(
        self,
        context: ApiRequestContext,
        store_code: str,
        valid_time: datetime.datetime,
        transaction_time: datetime.datetime,
        snapshot_id: str,
    ) -> Tuple[OperationalVisitPolicy, ...]:
        self._check_context(context)
        _require_tz(valid_time, "valid_time")
        _require_tz(transaction_time, "transaction_time")
        ws = self.store.get(snapshot_id)
        active: List[OperationalVisitPolicy] = []
        for policy in ws.policies.operational_policies.values():
            if policy.store_code != store_code:
                continue
            b = policy.bitemporal
            # valid time 窗口 + transaction time 窗口双时态过滤
            if not (b.valid_from <= valid_time <= b.valid_to):
                continue
            if b.transaction_from > transaction_time:
                continue
            active.append(policy)
        if not active:
            raise PolicyNotFound(
                f"store_code {store_code!r} 在双时态窗口内无 active policy",
                context={"store_code": store_code, "snapshot_id": snapshot_id},
            )
        return tuple(active)

    def get_ownership_conflicts(
        self,
        context: ApiRequestContext,
        snapshot_id: str,
    ) -> Tuple[OwnershipConflictRecord, ...]:
        self._check_context(context)
        ws = self.store.get(snapshot_id)
        return tuple(ws.policies.ownership_conflicts)

    # ================================================================
    # 5.2 L3 状态转移 (薄适配 StateTransitionEngine)
    # ================================================================
    def request_transition(
        self,
        context: ApiRequestContext,
        workflow: WorkflowContext,
        transition_request: "TransitionRequest",
    ) -> "TransitionResult":
        self._check_context(context)
        if not isinstance(workflow, WorkflowContext):
            raise WorldModelError(f"workflow 必须是 WorkflowContext, 实际: {type(workflow).__name__}")
        _require_tz(transition_request.event_time, "transition_request.event_time")
        _require_tz(transition_request.transaction_time, "transition_request.transaction_time")
        ws = self.store.get(transition_request.base_snapshot_id)
        try:
            new_ws, _lifecycle_rec, transition_rec = StateTransitionEngine.transition_visit_status(
                base_state=ws,
                visit_id=transition_request.visit_id,
                target_status=transition_request.target_status,
                triggering_event_ref=transition_request.triggering_event_ref,
                event_time=transition_request.event_time,
                transaction_time=transition_request.transaction_time,
                approver_id=transition_request.approver_id,
                gps_deviation_meters=transition_request.gps_deviation_meters,
                service_duration_min=transition_request.service_duration_min,
                evidence_refs=list(transition_request.evidence_refs),
                policy_version_snapshot=transition_request.policy_version_snapshot,
                deferral_policy_id=transition_request.deferral_policy_id,
            )
        except KeyError as e:
            raise GuardRejected(
                f"状态转移被拒绝 (visit 记录缺失): {e}",
                context={"visit_id": transition_request.visit_id},
            )
        except (ValueError, ImmutableViolation) as e:
            raise GuardRejected(
                f"状态转移被拒绝: {e}",
                context={"visit_id": transition_request.visit_id},
            )
        self.store.register(new_ws)
        return TransitionResult(
            new_worldstate_snapshot_id=new_ws.snapshot_id,
            transition_record=transition_rec,
            audit_hash=transition_rec.record_hash,
            was_guard_passed=True,
        )

    # ================================================================
    # 5.3 L4 反馈闭环 (Feedback 与 Transition 解耦: 只写回执, 不自动 transition)
    # ================================================================
    def submit_execution_feedback(
        self,
        context: ApiRequestContext,
        feedback: ActualVisitEvent,
        snapshot_id: Optional[str] = None,
    ) -> ExecutionFeedbackReceipt:
        self._check_context(context)
        if not isinstance(feedback, ActualVisitEvent):
            raise WorldModelError(
                f"feedback 必须是 ActualVisitEvent, 实际: {type(feedback).__name__}"
            )
        # 规范签名 (context, feedback); snapshot_id 可选, 默认最新注册快照
        effective_snapshot_id = snapshot_id or self.store.latest_snapshot_id
        if effective_snapshot_id is None:
            raise SnapshotNotFound("Store 为空且未显式传入 snapshot_id")
        # 解耦红线: feedback 仅产生回执; 状态转移必须显式调用 request_transition()
        return ExecutionFeedbackReceipt(
            event_id=feedback.event_id,
            new_snapshot_id=effective_snapshot_id,  # 反馈不产生新快照 (转移才产生)
            transition_required=True,
            evidence_status="RECEIVED_PENDING_VERIFICATION",
            receipt_message="反馈已接收; 状态转移需显式调用 request_transition (解耦红线)",
        )

    # ================================================================
    # 5.4 L5 情景推演 (诚实未实现)
    # ================================================================
    def request_scenario_rollout(
        self,
        context: ApiRequestContext,
        base_snapshot_id: str,
        intent: "PlanningIntent",
        perturbation_events: tuple,
        simulation_time: datetime.datetime,
    ) -> None:
        """L5 Scenario Engine 仅有设计规范 (TOPPRISM_L5_..._SPEC_v1_0.md), 无代码实现。

        诚实失败: 抛 L5NotImplemented, 不伪造 ScenarioResult。
        """
        self._check_context(context)
        _require_tz(simulation_time, "simulation_time")
        self.store.get(base_snapshot_id)  # 快照存在性先行校验
        raise L5NotImplemented(
            "L5 Scenario Engine 未实现 (仅设计规范); 等待 Phase 实施计划",
            context={"base_snapshot_id": base_snapshot_id, "intent_id": intent.intent_id},
        )

    # ================================================================
    # 5.5 L6 规划器投影 (薄适配 PlannerStateProjectionCompiler)
    # ================================================================
    def compile_planner_projection(
        self,
        context: ApiRequestContext,
        snapshot_id: str,
        intent: "PlanningIntent",
        partial_auth: Optional["PartialProjectionAuthorization"] = None,
        working_days: Optional[Tuple[str, ...]] = None,
    ) -> PlannerStateProjection:
        self._check_context(context)
        _require_tz(intent.valid_time, "intent.valid_time")
        if partial_auth is not None and not isinstance(partial_auth, PartialProjectionAuthorization):
            raise WorldModelError(
                f"partial_auth 必须是 PartialProjectionAuthorization, 实际: {type(partial_auth).__name__}",
                context={"intent_id": intent.intent_id},
            )
        ws = self.store.get(snapshot_id)
        target_rep = intent.target_agent_id
        if not target_rep:
            raise WorldModelError(
                "intent.target_agent_id 必填 (投影目标代表)",
                context={"intent_id": intent.intent_id},
            )
        try:
            return PlannerStateProjectionCompiler.compile_projection(
                world_state=ws,
                target_rep_id=target_rep,
                allow_partial_projection=False,
                working_days=list(working_days) if working_days else None,
                # 投影标识时刻取意图有效时间 (确定性, 无 datetime.now(); Storage CAS 授权校验属 Phase 7)
                generated_at=intent.valid_time,
            )
        except KeyError as e:
            raise ProjectionCompilationError(
                f"投影编译失败 (实体缺失): {e}",
                context={"intent_id": intent.intent_id, "snapshot_id": snapshot_id},
            )
        except Exception as e:
            if isinstance(e, ProjectionCompilationError):
                raise
            raise ProjectionCompilationError(
                f"投影编译失败: {e}",
                context={"intent_id": intent.intent_id, "snapshot_id": snapshot_id},
            )


# ============================================================================
# L3 / L5 / L6 请求与意图类型 (Canonical Types §20/§21/§26; 本模块尾部定义避免循环引用)
# ============================================================================
@dataclass(frozen=True)
class TransitionRequest:
    """状态转移请求 (Canonical Types §20)"""
    base_snapshot_id: str
    visit_id: str
    target_status: LifecycleStatus
    triggering_event_ref: str
    event_time: datetime.datetime
    transaction_time: datetime.datetime
    approver_id: Optional[str] = None
    gps_deviation_meters: Optional[float] = None
    service_duration_min: Optional[float] = None
    policy_version_snapshot: Optional[str] = None
    deferral_policy_id: Optional[str] = None
    evidence_refs: Tuple[str, ...] = ()

    def __post_init__(self):
        _require_tz(self.event_time, "TransitionRequest.event_time")
        _require_tz(self.transaction_time, "TransitionRequest.transaction_time")


@dataclass(frozen=True)
class TransitionResult:
    """状态转移结果 (Canonical Types §21)"""
    new_worldstate_snapshot_id: str
    transition_record: StateTransitionRecord
    audit_hash: str
    was_guard_passed: bool
    rejection_reason: Optional[str] = None
    idempotency_replay_detected: bool = False


@dataclass(frozen=True)
class PlanningIntent:
    """规划意图 (Canonical Types §26)"""
    intent_id: str
    decision_scope: str
    valid_time: datetime.datetime
    timezone: str
    target_agent_id: Optional[str] = None
    target_store_id: Optional[str] = None
    objectives: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()
    allowed_actions: Tuple[str, ...] = ()

    def __post_init__(self):
        if not self.intent_id or not self.decision_scope:
            raise WorldModelError("intent_id / decision_scope 必填")
        if not self.timezone:
            raise MissingTimezone("PlanningIntent.timezone 必填")
        _require_tz(self.valid_time, "PlanningIntent.valid_time")


@dataclass(frozen=True)
class PartialProjectionAuthorization:
    """部分投影授权凭证 (规范 §4.2 / Registry 字段登记; Storage CAS 校验属 Phase 7)"""
    authorization_id: str
    actor_id: str
    scope: str
    snapshot_id: str
    intent_id: str
    nonce: str
    status: str                       # AVAILABLE / RESERVED / CONSUMED / ROLLED_BACK

    def __post_init__(self):
        if not self.authorization_id or not self.actor_id or not self.nonce:
            raise WorldModelError("authorization_id / actor_id / nonce 必填")
        if self.status not in ("AVAILABLE", "RESERVED", "CONSUMED", "ROLLED_BACK"):
            raise WorldModelError(
                f"status 必须是四状态生命周期之一, 实际: {self.status!r}"
            )
