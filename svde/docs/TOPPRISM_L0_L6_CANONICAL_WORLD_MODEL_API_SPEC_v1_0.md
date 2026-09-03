---
**Status:** HISTORICAL SNAPSHOT — NOT THE CURRENT CANONICAL STRUCTURE
**MIGRATED-TO:** `svde/docs/TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md`
**Reason:** 本文档采用 L0-L6（6 层）或 Pre-L0-L7 编号；当前提议中的 Canonical 分层已扩展为 L0-L7（7 层）。
**Date:** 2026-08-25

> 本状态为 **PROPOSED CANONICAL / PARTIALLY ALIGNED**；待 Phase 0 完成全仓 4 类分类文档迁移。

---

# TopPrism L0-L6 Canonical World Model API 详细规范 v1.0

**Document ID:** TOPPRISM-L0-L6-WORLD-MODEL-API-SPEC-v1.0  
**Version:** **v1.0-draft.5.2 (Preflight Final Synced Draft)**  
**Date:** 2026-08-24  
**Status:** **API DESIGN DRAFT — Preflight Synced (NOT YET FROZEN)**  
**上游约束:** `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`  
**配套规范:** `CANONICAL_TYPE_REGISTRY.md` (权威类型登记册)

**本轮修正 (Preflight Final Polish)**:
1. 确立授权唯一术语为 **四状态生命周期 (Four-State Lifecycle)**，澄清 `ROLLED_BACK` 为废弃终态（重试需申请新授权）；
2. 确立 **Storage CAS 唯一信任模型**：服务端绝不信任客户端传入的 `status` 声明，直接以 Storage CAS 校验为准；
3. 补充完整的 **RFC 8785 跨语言输入类型转换矩阵与序列化规范**；
4. 修复 `deep_freeze()` 递归栈与 `date` 无 tzinfo 异常，增加 `math.copysign` 拒绝 `-0.0`，禁止 `complex`；
5. 同步 `DECISION_ENGINE_BOUNDARY.md` 与全仓接口签名至 `v1.0-draft.5.2`。

---

## 一、API 设计总体原则

1. **深度不可变性**: 所有返回值通过 `deep_freeze()` 递归强制冻结；
2. **最小只读暴露**: API 只返回当前决策所需的最小字段切片；
3. **纯函数式与可重放**: 相同输入 + 显式时间参数 $\implies$ 100% 确定性输出；
4. **时间参数强制显式**: 严禁 naive datetime，所有业务时间显式传参；
5. **错误码标准化**: 异常继承 `WorldModelError` 并统一使用 `default_code` 属性；
6. **集中上下文**: 所有调用通过 `ApiRequestContext` 携带 `api_version`, `request_id`, `timezone`；
7. **服务端防伪指纹**: 服务端基于 RFC 8785 生成 `RequestFingerprint`，客户端不可伪造；
8. **四状态授权事务**: 授权凭证通过 Storage CAS 严格原子流转。

---

## 二、共享上下文与指纹规范 (RFC 8785 跨语言序列化矩阵)

### 2.1 `ApiRequestContext`

```python
@dataclass(frozen=True)
class ApiRequestContext:
    api_version: str                  # 必填，如 "WM-API-v1.0-draft.5.2"
    request_id: str                   # 必填，UUID 全局唯一
    caller_id: str                    # 必填
    source_system: str                # 必填
    timezone: str                     # 必填，无默认值 (如 "Asia/Shanghai")

    def __post_init__(self):
        if not self.timezone:
            raise MissingTimezone("timezone is REQUIRED")
        if not self.api_version:
            raise MissingApiVersion("api_version is REQUIRED")
```

### 2.1.1 不可变值联合类型（引用）

**权威定义**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`
- `FrozenScalar`: §17
- `FrozenValue`: §18

（本节仅引用，不重复定义。）

### 2.1.2 规划器节点拓扑类型（引用）

**权威定义**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` §25 `PlannerNodeTopology`（本节仅引用，不重复定义。）

### 2.2 RFC 8785 跨语言类型转换与序列化矩阵

| 输入 Python 类型 | 规范化转换规则 (Canonicalization Rule) | RFC 8785 JSON 表示形式 | 异常处理 |
| :--- | :--- | :--- | :--- |
| `str`, `bool`, `int`, `None` | 原样保留 | JSON String / Boolean / Number / null | 正常处理 |
| `datetime` (aware) | 转换至 UTC，格式化为 `YYYY-MM-DDTHH:MM:SSZ` | JSON String (ISO 8601 UTC) | 正常处理 |
| `datetime` (naive) | **严禁传入** | — | 抛出 `TimeContractViolation` |
| `date` | 格式化为 `YYYY-MM-DD` 纯日期字符串 | JSON String | 正常处理 |
| `time` (aware) | 保留 tzinfo，不做 UTC 换算（time-of-day 跨日需结合日期上下文） | JSON String (HH:MM:SS±HHMM) | 正常处理 |
| `time` (naive) | **严禁传入** | — | 抛出 `TimeContractViolation` |
| `float` (有效) | 校验非 NaN / 非 Inf / 非 -0.0，按 RFC 8785 规则转换为无多余指数的十进制字符 | JSON Number | 正常处理 |
| `float` (`NaN`, `±Inf`) | **严禁传入** | — | 抛出 `TimeContractViolation` |
| `float` (`-0.0`) | `math.copysign(1.0, x) < 0.0` 检测判定 | — | 抛出 `TimeContractViolation` |
| `Decimal` | 转换为无尾随零的标准十进制字符串 | JSON String (精确字符) | 正常处理 |
| `UUID` | 转为标准 36 字符小写连字符形式 `str(u)` | JSON String | 正常处理 |
| `Enum` | 取 `e.value` 字符串 | JSON String | 正常处理 |
| `tuple`, `list`, `set` | 递归规范化其内部每个元素，转为 JSON Array | JSON Array `[...]` | 顺序保留（tuple/list） |
| `dict`, `MappingProxy` | 键名必须为 `str`，按 RFC 8785 §3.2.2 **UTF-16 code unit** 字典序严格升序排列（不要求 NFC 归一化） | JSON Object `{...}` | 非 str 键抛 `TypeError` |
| `frozen dataclass` | 按 `dataclasses.fields()` 转换为字典，键名字典序排序 | JSON Object `{...}` | `init=False` 抛 `TypeError` |
| `complex`, `bytearray` | **严禁传入** | — | 抛出 `TypeError` |

### 2.3 服务端指纹计算函数 (INTERNAL IMPLEMENTATION — NOT Canonical API)

**重要声明**: `compute_request_fingerprint()` 是 **WorldModel 内部实现函数**，严禁作为公开 API 在跨模块直接调用，严禁 `Any` 跨 API 边界传递。`request_body` 必须满足 `FrozenValue` 不可变语义。

```python
def compute_request_fingerprint(
    context: ApiRequestContext,
    operation: str,
    request_body: FrozenValue,    # 严禁 Any；必须是不可变联合类型
    expected_snapshot_version: Optional[int] = None
) -> str:
    """
    Server-side deterministic RFC 8785 canonical hash.
    expected_snapshot_version is ONLY included for state-mutation operations.
    """
    normalized_dict = {
        "operation": operation,
        "api_version": context.api_version,
        "caller_id": context.caller_id,
        "source_system": context.source_system,
        "request_body": canonicalize_to_rfc8785_dict(request_body)
    }
    if expected_snapshot_version is not None:
        normalized_dict["expected_snapshot_version"] = expected_snapshot_version
        
    canonical_bytes = rfc8785_encode(normalized_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()
```

---

## 三、`deep_freeze()` 深度冻结算法规范

```python
import math
from datetime import datetime, date, time, timezone
from decimal import Decimal
from uuid import UUID
from enum import Enum
from types import MappingProxyType
from typing import Any, Optional, Tuple, Mapping

def deep_freeze(obj: Any, _path_stack: Optional[Tuple[int, ...]] = None) -> Any:
    """
    Recursively deep-freeze an object for API boundary output.
    
    Invariants:
    1. Scalar types (None, bool, int, str, bytes, UUID, Enum, Decimal): return as-is
    2. datetime.datetime: MUST have tzinfo AND tzinfo.utcoffset() is not None; naive -> TimeContractViolation. datetime.time: MUST have tzinfo AND tzinfo.utcoffset() is not None; naive -> TimeContractViolation; aware time keeps original tzinfo without UTC conversion
    3. datetime.date: return as-is (date has no tzinfo, do NOT inspect tzinfo)
    3a. datetime.time: aware required (tzinfo + utcoffset() not None); preserve tzinfo, NO UTC conversion
    4. float: NaN / Infinity / -0.0 -> TimeContractViolation
    5. complex: FORBIDDEN -> TypeError
    6. bytearray: REJECTED (avoid silent semantic shift; caller must convert explicitly) -> raise TypeError("bytearray forbidden at API boundary")
    7. tuple / list: recurse -> return tuple(...); set / frozenset: REJECTED (non-deterministic order → fingerprint drift)
    8. dict / Mapping: recurse -> return MappingProxyType(...)
    9. frozen dataclass: REBUILD instance with deep-frozen fields (init=True only)
    10. Cycle detection via recursion path stack (clean stack unwind)
    """
    if _path_stack is None:
        _path_stack = ()

    # 1. Direct Immutable Scalars
    if obj is None or isinstance(obj, (bool, int, str, bytes, UUID, Enum, Decimal)):
        return obj

    # 2. Date & Time Types (Strict separation)
    if isinstance(obj, datetime):
        # Strict aware check: tzinfo present AND can compute UTC offset
        if obj.tzinfo is None or obj.tzinfo.utcoffset(obj) is None:
            raise TimeContractViolation("naive datetime not allowed at API boundary; must include tzinfo with computable utcoffset")
        return obj.astimezone(timezone.utc)  # NORMALIZE to UTC (deterministic fingerprint)
    if isinstance(obj, time):
        # Strict aware check: tzinfo present AND can compute UTC offset (time-of-day UTC offset may be None for fixed-offset zones)
        if obj.tzinfo is None or obj.tzinfo.utcoffset(None) is None:
            raise TimeContractViolation("naive time not allowed at API boundary; must include tzinfo with computable utcoffset")
        return obj  # aware time: keep original tzinfo WITHOUT UTC conversion (time-of-day cannot be UTC-normalized standalone)
    if isinstance(obj, date):
        return obj

    # 3. Float with Strict Numerical Invariants
    if isinstance(obj, float):
        if obj != obj:
            raise TimeContractViolation("NaN float not allowed at API boundary")
        if obj == float('inf') or obj == float('-inf'):
            raise TimeContractViolation("Infinity float not allowed at API boundary")
        if obj == 0.0 and math.copysign(1.0, obj) < 0.0:
            raise TimeContractViolation("Negative zero (-0.0) not allowed at API boundary")
        return obj

    # 4. Forbidden Types at Public Boundary
    if isinstance(obj, complex):
        raise TypeError("complex numbers are forbidden at public API boundary (RFC 8785 incompatible)")

    # 5. Bytearray: REJECTED (avoid silent semantic shift to bytes; caller must convert explicitly)

    # 6. Cycle Detection via Path Stack
    obj_id = id(obj)
    if obj_id in _path_stack:
        raise TypeError(f"Circular reference detected in deep_freeze: {type(obj).__name__}")
    new_path = _path_stack + (obj_id,)

    # 7. Container Types (set / frozenset explicitly rejected — non-deterministic order)
    if isinstance(obj, (set, frozenset)):
        raise TypeError(f"set/frozenset forbidden at API boundary (non-deterministic iteration order): {type(obj).__name__}")
    if isinstance(obj, (tuple, list)):
        return tuple(deep_freeze(e, new_path) for e in obj)
    if isinstance(obj, (dict, Mapping)):
        return MappingProxyType({k: deep_freeze(v, new_path) for k, v in obj.items()})

    # 8. Frozen Dataclass Recursive Rebuild
    if hasattr(obj, '__dataclass_fields__'):
        params = getattr(obj, '__dataclass_params__', None)
        if not params or not params.frozen:
            raise TypeError(f"Non-frozen dataclass cannot be deep_freeze'd: {type(obj).__name__}")
        
        frozen_kwargs = {}
        for field_name, field_def in obj.__dataclass_fields__.items():
            if not field_def.init:
                raise TypeError(f"Field '{field_name}' in {type(obj).__name__} has init=False; deep_freeze requires init=True")
            val = getattr(obj, field_name)
            frozen_kwargs[field_name] = deep_freeze(val, new_path)
        try:
            return type(obj)(**frozen_kwargs)
        except TypeError as e:
            raise TypeError(f"Cannot rebuild frozen dataclass {type(obj).__name__}: {e}")

    raise TypeError(f"Non-freezable type for API boundary: {type(obj).__name__}")
```

---

## 四、授权凭证四状态生命周期与 Storage CAS 信任模型

### 4.1 授权凭证四状态生命周期 (Four-State Lifecycle)

```
             ┌────────────────────────────────────────────────────────┐
             │                      AVAILABLE                         │ (初始已签发可用状态)
             └──────────────────────────┬─────────────────────────────┘
                                        │ reserve_authorization() [Storage CAS]
                                        ▼
             ┌────────────────────────────────────────────────────────┐
             │                      RESERVED                          │ (请求独占锁定中)
             └─────────────┬───────────────────────────┬──────────────┘
                           │                           │
          [编译成功]       │                           │ [编译异常 / 超时 / 校验失败]
          commit_auth()    │                           │ rollback_auth()
          [Storage CAS]    ▼                           ▼ [Storage CAS]
             ┌────────────────────────┐  ┌────────────────────────┐
             │       CONSUMED         │  │      ROLLED_BACK       │ (废弃终态)
             │      (终态已核销)       │  │ (不可复用，需重新申请) │
             └────────────────────────┘  └────────────────────────┘
```

### 4.2 Storage CAS 唯一信任模型 (Storage Trust Model)
- **客户端不可信原则**: 调用方传入的 `PartialProjectionAuthorization.status` 仅作声明；
- **唯一事实来源**: `compile_planner_projection(context, snapshot_id, intent, partial_auth)` 必须直接调用 `auth_storage.reserve_authorization(...)` 进行原子 CAS 查询；
- **重试语义明确**: 编译失败触发 `rollback_authorization` 后，状态变为 `ROLLED_BACK`（废弃终态）。调用方**不能复用该凭证重试，必须由授权人重新签发新授权凭证**。

```python
class AuthorizationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"       # 可用
    RESERVED = "RESERVED"         # 锁定中
    CONSUMED = "CONSUMED"         # 已核销终态
    ROLLED_BACK = "ROLLED_BACK"   # 废弃终态 (不可复用)

@dataclass(frozen=True)
class PartialProjectionAuthorization:
    authorization_id: str
    actor_id: str
    reason: str
    approved_by: str
    scope: Tuple[str, ...]
    snapshot_id: str
    intent_id: str
    issued_at: datetime
    expires_at: datetime
    nonce: str
    purpose: str
    status: AuthorizationStatus   # 声明字段，服务端以 Storage CAS 为准
    audit_record_ref: str
```

---

## 五、规范化核心 API 契约列表

### 5.1 L0-L4 核心查询
- `get_worldstate_view(context: ApiRequestContext, snapshot_id: str, scope: ResourceScope, fields: Tuple[str, ...]) -> ReadOnlyWorldStateView`
- `query_customer_universe_view(context: ApiRequestContext, rep_id: str, snapshot_id: str) -> FrozenCustomerUniverseView`
- `resolve_active_policies(context: ApiRequestContext, store_code: str, valid_time: datetime, transaction_time: datetime, snapshot_id: str) -> Tuple[OperationalVisitPolicy, ...]`
- `get_ownership_conflicts(context: ApiRequestContext, snapshot_id: str) -> Tuple[OwnershipConflictRecord, ...]`

#### 5.1.1 查询视图与范围类型定义 (v1.0-draft.5.2 修订补全)

```python
@dataclass(frozen=True)
class ResourceScope:
    """资源访问范围 (get_worldstate_view 参数)"""
    level: str                        # "FULL" / "REP_SCOPED" / "STORE_SCOPED"
    rep_id: Optional[str] = None      # REP_SCOPED 时必填

    def __post_init__(self):
        if self.level not in ("FULL", "REP_SCOPED", "STORE_SCOPED"):
            raise ScopeNotPermitted(f"level 非法: {self.level!r}")
        if self.level == "REP_SCOPED" and not self.rep_id:
            raise ScopeNotPermitted("REP_SCOPED 必须提供 rep_id")


@dataclass(frozen=True)
class ReadOnlyWorldStateView:
    """WorldState 只读视图 (仅暴露请求的 fields; REP_SCOPED 禁止全局集合字段)"""
    snapshot_id: str
    fields: Tuple[str, ...]
    data: Mapping[str, object]


@dataclass(frozen=True)
class FrozenCustomerUniverseView:
    """代表客户宇宙只读视图"""
    rep_id: str
    snapshot_id: str
    customers: Tuple[OperationalCustomer, ...]
```

*(实现注: REP_SCOPED 禁止访问 customers/resources/account_hierarchies/product_line_scopes/supply_nodes 全局字段; 违者 ScopeNotPermitted。参考实现见 `world_model/canonical_api.py`。)*

### 5.2 L3 状态转移
- `request_transition(context: ApiRequestContext, workflow: WorkflowContext, transition_request: TransitionRequest) -> TransitionResult`

#### 5.2.1 `WorkflowContext` 与 `RequestFingerprint` 类型定义

```python
@dataclass(frozen=True)
class RequestFingerprint:
    """服务端防伪指纹 (原则 7: 服务端基于 RFC 8785 生成, 客户端不可伪造)"""
    request_id: str                   # 对应 ApiRequestContext.request_id
    algorithm: str                    # 固定 "RFC8785-SHA256"
    digest: str                       # 256-bit SHA-256 digest represented as 64 hexadecimal characters
    computed_at: datetime             # 必须带时区 (naive -> TimeContractViolation)
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
    """工作流上下文 (字段对齐 CANONICAL_TYPE_REGISTRY.md 权威登记)"""
    expected_snapshot_version: str    # 必填, 乐观并发控制 (期望的基础快照版本)
    idempotency_key: str              # 必填, 幂等键 (同键重放 -> IdempotencyConflict)
    fingerprint: RequestFingerprint   # 必填, 服务端防伪指纹 (§2.2 / 原则 7)

    def __post_init__(self):
        if not self.expected_snapshot_version or not self.idempotency_key:
            raise WorldModelError("expected_snapshot_version / idempotency_key 必填")
        if not isinstance(self.fingerprint, RequestFingerprint):
            raise WorldModelError(
                f"fingerprint 必须是 RequestFingerprint, 实际: {type(self.fingerprint).__name__}"
            )
```

*(注：本定义为 v1.0-draft.5.2 的修订补充 — 此前 Registry 与 Canonical Types Spec §30 均引用
"权威定义 = 主 API 规范 §5.2"，但 §5.2 仅有 API 签名，`WorkflowContext` 与
`RequestFingerprint` 类型从未定义。现按 `CANONICAL_TYPE_REGISTRY.md` 权威字段登记
`(expected_snapshot_version, idempotency_key, fingerprint)` 对齐补全，
待技术架构签署 (TECH-08) 确认后随 API 一并冻结。幂等重放的 Storage CAS 级检测
属 Phase 7 存储层实现，本规范仅约束类型形态。)*

### 5.3 L4 反馈闭环
- `submit_execution_feedback(context: ApiRequestContext, feedback: ActualVisitEvent) -> ExecutionFeedbackReceipt`
  - *(实现注: 参考实现另接受可选 `snapshot_id` (默认最新注册快照); 回执 `new_snapshot_id` 语义 = 反馈所针对的快照, 反馈不产生新快照)*

### 5.4 L5 情景推演
- `request_scenario_rollout(context: ApiRequestContext, base_snapshot_id: str, intent: PlanningIntent, perturbation_events: Tuple[PerturbationEvent, ...], simulation_time: datetime.datetime) -> ScenarioResult`
  - *(实现注: 参考实现当前诚实未实现 — 抛 `L5NotImplemented`, 见 Canonical API 包装层; 本签名为目标契约)*
  - *(注：`simulation_time` 为强制显式仿真时钟（必须带时区）；分支状态的 `bitemporal.transaction_from` 严格等于 `simulation_time`；返回单值 `ScenarioResult`，其内部 `delta_state` 字段包含 `StateDelta`)*
  - *(注：返回单值 `ScenarioResult`，其内部 `delta_state` 字段包含 `StateDelta`)*

### 5.5 L6 规划器投影
- `compile_planner_projection(context: ApiRequestContext, snapshot_id: str, intent: PlanningIntent, partial_auth: Optional[PartialProjectionAuthorization] = None) -> PlannerStateProjection`
  - *(实现注: 参考实现另接受可选 `working_days`; `PartialProjectionAuthorization` 最小定义见包装层, Storage CAS 校验属 Phase 7)*

---

## 六、异常类体系

```python
class WorldModelError(Exception):
    default_code: str = "WM-UNKNOWN"
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{self.default_code}] {message}")
        self.code = self.default_code
        self.context = {} if context is None else context

class SnapshotNotFound(WorldModelError): default_code = "WM-SNAPSHOT-NOT-FOUND"
class SnapshotArchived(WorldModelError): default_code = "WM-SNAPSHOT-ARCHIVED"
class ScopeNotPermitted(WorldModelError): default_code = "WM-SCOPE-NOT-PERMITTED"
class VersionMismatch(WorldModelError): default_code = "WM-VERSION-MISMATCH"
class IdempotencyConflict(WorldModelError): default_code = "WM-IDEMPOTENCY-CONFLICT"
class GuardRejected(WorldModelError): default_code = "WM-GUARD-REJECTED"
class ProjectionCompilationError(WorldModelError): default_code = "WM-PROJECTION-FAILED"
class PolicyNotFound(WorldModelError): default_code = "WM-POLICY-NOT-FOUND"
class DeferralPolicyNotFound(WorldModelError): default_code = "WM-DEFER-POLICY-NOT-FOUND"
class DeferralQuotaExceeded(WorldModelError): default_code = "WM-DEFER-QUOTA-EXCEEDED"
class DeferralWindowExceeded(WorldModelError): default_code = "WM-DEFER-WINDOW-EXCEEDED"
class ImmutableViolation(WorldModelError): default_code = "WM-IMMUTABLE-VIOLATION"
class MissingTimezone(WorldModelError): default_code = "WM-MISSING-TIMEZONE"
class MissingApiVersion(WorldModelError): default_code = "WM-MISSING-API-VERSION"
class TimeContractViolation(WorldModelError): default_code = "WM-TIME-CONTRACT"
class PartialAuthorizationReplay(WorldModelError): default_code = "WM-PARTIAL-AUTH-REPLAY"
```

---

## 七、阶段状态声明

| 评估维度 | 当前级别 | 真实状态说明 |
| :--- | :--- | :--- |
| **设计完成度** | **高 (99%)** | RFC 8785 矩阵、深度冻结、Storage CAS 信任模型全部形式化闭合 |
| **接口草案** | **v1.0-draft.5.2** | Preflight Final Synced，达到冻结评审就绪标准 |
| **契约冻结 (Freeze)** | **⏳ 待签署** | 需等待业务方对 Phase 1 业务语义确认后正式冻结 |
| **代码实现** | **⛔ 暂不启动** | 严格遵守红线，冻结前不修改实现代码 |
| **生产可用性** | **⛔ 未验证** | 纯设计阶段，尚未进行生产环境验证 |
