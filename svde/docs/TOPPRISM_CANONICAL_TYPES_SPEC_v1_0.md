# TopPrism Canonical Types 规范 v1.0

**Document ID:** TOPPRISM-CANONICAL-TYPES-SPEC-v1_0  
**Version:** **v1.0**  
**Date:** 2026-08-24  
**Status:** **CANONICAL TYPES DEFINITION — Phase 7 Single Source of Truth**  
**上游约束:** `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`

---

## 一、规范目的与双层权威声明

类型权威采用 **两层结构 (Two-Tier Authority)**：

| 层级 | 权威文档 | 覆盖类型 |
| :--- | :--- | :--- |
| **Tier 1: 领域类型** | 本文档 (`TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`) | §1~§35 全部业务领域类型、支撑枚举与支撑容器 |
| **Tier 2: API 基础设施类型** | `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` | `ApiRequestContext` (§2.1)、`RequestFingerprint` (§2.2)、`WorkflowContext` (§5.2.1)、`PartialProjectionAuthorization` (§4.2)、`WorldModelError` 及 16 子类 (§6.0) |

**本文档是领域类型的唯一事实源**；API 基础设施类型（请求上下文、指纹、异常体系）不属于领域类型，其权威定义在主 API 规范，本文档不重复定义。`CANONICAL_TYPE_REGISTRY.md` 中的每个条目必须标注所属层级并引用唯一章节锚点。

---

## 二、时间与空间基础类型

### §1 `BitemporalPeriod` (双时态周期)

```python
@dataclass(frozen=True)
class BitemporalPeriod:
    """双时态时间戳 (Valid Time 业务生效 vs Transaction Time 系统记录)"""
    valid_from: datetime.datetime          # 业务生效起始
    valid_to: datetime.datetime            # 业务生效结束
    transaction_from: datetime.datetime    # 系统记录入库时刻
    transaction_to: Optional[datetime.datetime] = None  # 系统废弃时刻
```

### §2 `GeoCoordinate` (WGS-84 地理坐标)

```python
@dataclass(frozen=True)
class GeoCoordinate:
    """WGS-84 地理坐标 (经度, 纬度)"""
    longitude: float
    latitude: float
```

### §3 `DerivedDepotEstimate` (派生基地推断)

```python
@dataclass(frozen=True)
class DerivedDepotEstimate:
    """派生推断的代表基地坐标 (严禁冒充物理存在)"""
    rep_id: str
    inferred_centroid: GeoCoordinate
    sample_points_count: int
    confidence_score: float
    derivation_algorithm: str = "Geometric_Centroid_v1"
    category: CognitiveCategory = CognitiveCategory.DERIVED_ESTIMATE
```

---

## 三、客户与代表实体

### §4 `OperationalCustomer` (客户实体)

```python
@dataclass(frozen=True)
class OperationalCustomer:
    """零售终端门店实体 (Canonical Type ID: OperationalCustomer)"""
    store_code: str
    store_name: str
    tier: str  # Key / A / B / C / D
    ka_name: str
    district: str
    location: Optional[GeoCoordinate]
    geo_quality: GeoQualityStatus
    fulfillment_class: FulfillmentClass
    account_hierarchy_ref: Optional[str] = None
    supply_node_ref: Optional[str] = None
    product_line_scope_refs: Tuple[str, ...] = ()
    address: Optional[str] = None
    category: CognitiveCategory = CognitiveCategory.OBSERVATION

    @property
    def is_plannable(self) -> bool:
        return self.geo_quality == GeoQualityStatus.EXACT_MATCH and self.location is not None
```

### §5 `OperationalResource` (代表实体)

```python
@dataclass(frozen=True)
class OperationalResource:
    """销售代表实体 (Canonical Type ID: OperationalResource)"""
    rep_id: str
    rep_name: str
    region: str
    sub_region: str
    city: str
    depot_estimate: DerivedDepotEstimate
    assigned_store_codes: Tuple[str, ...]
    max_daily_stops: int = 6
    max_daily_workload_min: float = 480.0
    category: CognitiveCategory = CognitiveCategory.OBSERVATION
```

---

## 四、供应链与政策类型

### §6 `SupplyNodeEntity` (供应链大仓实体)

```python
@dataclass(frozen=True)
class SupplyNodeEntity:
    """供应链大仓实体 (Canonical Type ID: SupplyNodeEntity)"""
    dc_id: str
    dc_name: str
    served_ka_names: Tuple[str, ...]
    delivery_status: str = "UNCALIBRATED"
    category: CognitiveCategory = CognitiveCategory.OBSERVATION
```

### §7 `OperationalVisitPolicy` (版本化拜访政策)

```python
@dataclass(frozen=True)
class OperationalVisitPolicy:
    """版本化拜访政策 (Canonical Type ID: OperationalVisitPolicy)"""
    policy_id: str
    policy_version: str
    store_code: str
    target_frequency_per_month: int
    cadence_type: str
    same_weekday_locked: bool
    bitemporal: BitemporalPeriod
    approved_by: str
    category: CognitiveCategory = CognitiveCategory.POLICY
```

> **重构方向 (v1.0 修订, 证据源: TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 3):**
> `policy_version` 多版本对象模式命中 Time Machine 反模式 (架构基线 §12.2)。
> 目标形态: 单一当前 policy 对象 + linked `PolicyAmendment` 修订链 (本规范 §37)。
> `policy_version` 字段过渡保留; 代码迁移待双轨签署后执行。

### §8 `DeferralPolicy` (顺延政策)

```python
@dataclass(frozen=True)
class DeferralPolicy:
    """顺延政策 (Canonical Type ID: DeferralPolicy)"""
    policy_id: str
    policy_version: str
    store_code: str
    bitemporal: BitemporalPeriod
    max_deferrals_per_period: int
    max_deferral_window_days: int
    requires_approval: bool
    approver_role: str
    business_penalty_min_per_deferral: float
    escalation_policy_ref: Optional[str] = None
    category: CognitiveCategory = CognitiveCategory.POLICY
```

### §9 `OperationalCommitment` (锁定承诺实体)

```python
@dataclass(frozen=True)
class OperationalCommitment:
    """锁定承诺实体 (Canonical Type ID: OperationalCommitment)"""
    commitment_id: str
    store_code: str
    rep_id: str
    locked_date: datetime.date
    locked_time_window: Optional[Tuple[datetime.time, datetime.time]] = None
    lock_level: str = "DAY_LOCKED"
    category: CognitiveCategory = CognitiveCategory.COMMITMENT
```

---

## 五、现场动作与度量类型

### §10 `InStoreActionFact` (现场作业动作事实)

```python
@dataclass(frozen=True)
class InStoreActionFact:
    """现场作业动作事实 (Canonical Type ID: InStoreActionFact)"""
    action_type: str
    estimated_duration_min: float
    action_notes: str = ""
    category: CognitiveCategory = CognitiveCategory.OBSERVATION
```

### §11 `MerchandisingComplianceFact` (合同陈列对赌核销)

```python
@dataclass(frozen=True)
class MerchandisingComplianceFact:
    """合同陈列对赌核销事实 (Canonical Type ID: MerchandisingComplianceFact)"""
    contract_target_units: int
    actual_compliant_units: int
    compliance_ratio: float
    has_oos_risk: bool = False
    category: CognitiveCategory = CognitiveCategory.EXECUTION_EVENT
```

### §12 `OperationalVisitLifecycleRecord` (拜访生命周期记录)

```python
@dataclass(frozen=True)
class OperationalVisitLifecycleRecord:
    """拜访生命周期记录 (Canonical Type ID: OperationalVisitLifecycleRecord)"""
    visit_id: str
    store_code: str
    rep_id: str
    scheduled_date: datetime.date
    current_status: LifecycleStatus
    status_history: Tuple[StatusTransitionEntry, ...] = ()  # 定义见 §35.6
    actual_arrival: Optional[datetime.time] = None
    actual_departure: Optional[datetime.time] = None
    service_duration_min: float = 0.0
```

### §13 `ActualVisitEvent` (实际执行事件)

```python
@dataclass(frozen=True)
class ActualVisitEvent:
    """实际执行事件 (Canonical Type ID: ActualVisitEvent)"""
    # === 必填字段（无默认值）—— 必须在所有可选字段之前 ===
    event_id: str
    store_code: str
    rep_id: str
    visit_date: datetime.date
    occurred_at: datetime.datetime
    timezone: str
    captured_at: datetime.datetime
    transaction_time: datetime.datetime
    valid_time: datetime.datetime
    source_system: str
    idempotency_key: str
    service_duration_min: float
    transit_duration_min: float
    is_line_internal: bool
    # === 可选字段（有默认值）—— 必须在所有必填字段之后 ===
    evidence_refs: Tuple[str, ...] = ()
    quality_status: str = "VALID"
    actions: Tuple[InStoreActionFact, ...] = ()  # 引用 §10 InStoreActionFact
    merchandising_compliance: Optional[MerchandisingComplianceFact] = None
    summary: str = ""
```

### §14 `OperationalDecisionWorldState` (Canonical WorldState)

```python
from types import MappingProxyType
from typing import Mapping, Tuple

@dataclass(frozen=True)
class OperationalDecisionWorldState:
    """企业运营决策世界状态 (Canonical Type ID: OperationalDecisionWorldState)"""
    snapshot_id: str
    bitemporal: BitemporalPeriod
    manifest: SourceManifest
    # 全部使用不可变 Mapping（非可变 Dict）
    customers: Mapping[str, OperationalCustomer]
    resources: Mapping[str, OperationalResource]
    account_hierarchies: Mapping[str, AccountHierarchyEntity]
    product_line_scopes: Mapping[str, ProductLineScopeEntity]
    supply_nodes: Mapping[str, SupplyNodeEntity]
    policies: PolicyRegistry
    commitments: Mapping[str, OperationalCommitment]
    visit_lifecycle_records: Mapping[str, OperationalVisitLifecycleRecord]
    # 全部使用不可变 Tuple（非可变 List）
    transition_records: Tuple[StateTransitionRecord, ...] = ()
    execution_fact_stream: Tuple[ActualVisitEvent, ...] = ()
    # 严禁 Any —— 使用 FrozenValue 联合类型
    active_scenario_branches: Mapping[str, FrozenValue] = MappingProxyType({})
```

---

## 六、组织与产品策略类型

### §15 `AccountHierarchyEntity` (连锁大客户总部)

```python
@dataclass(frozen=True)
class AccountHierarchyEntity:
    """连锁大客户总部实体 (Canonical Type ID: AccountHierarchyEntity)"""
    account_id: str
    account_name: str
    channel_tier: ChannelTier
    parent_account_ref: Optional[str] = None
    contract_summary: str = "全国性陈列与供货协议"
    category: CognitiveCategory = CognitiveCategory.OBSERVATION
```

### §16 `ProductLineScopeEntity` (产品线策略实体)

```python
@dataclass(frozen=True)
class ProductLineScopeEntity:
    """产品线策略实体 (Canonical Type ID: ProductLineScopeEntity)"""
    brand_id: str
    brand_name: str
    strategic_role: str
    default_action_types: Tuple[str, ...] = ()
    category: CognitiveCategory = CognitiveCategory.OBSERVATION
```

---

## 七、定义来源铁律

1. **领域类型**必须在本文档中有完整 `class` 定义（含 §35 支撑类型）；
2. **API 基础设施类型**（见 §一 Tier 2 清单）以主 API 规范为唯一权威，本文档不重复定义；
3. 其他规范文档 (主 API、L3/L5/L7) 只允许引用，严禁重复定义；
4. `CANONICAL_TYPE_REGISTRY.md` 每个条目必须指向唯一章节锚点（如 `§4`、`§12`、`§35.6`）；
5. **注解求值约定**：本文档全部代码块合并为单一模块时，模块首行必须为 `from __future__ import annotations`（PEP 563），使前向类型引用惰性求值；
6. **加载顺序约定**：枚举默认值为急切求值，实现期加载顺序必须为：§35.1~§35.5 五个枚举最先加载，其余类型按依赖序加载。本文档章节编号仅为阅读顺序，不构成加载顺序。


---

## 八、不可变值联合类型 (§17-§18)

### §17 `FrozenScalar` (不可变标量联合类型)

```python
from typing import Union, Tuple, Mapping
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from enum import Enum

FrozenScalar = Union[
    str, int, float, bool, bytes, None,
    datetime, date, time, Decimal, UUID, Enum
]
```

### §18 `FrozenValue` (递归不可变值联合类型)

```python
FrozenValue = Union[
    FrozenScalar,
    Tuple['FrozenValue', ...],
    Mapping[str, 'FrozenValue']
]
# 注：set / frozenset / bytearray / complex / NaN / Infinity / -0.0 / naive datetime / naive time
#     均**不属于** FrozenValue 集合；在 deep_freeze() 构造边界显式拒绝。

```

---

## 九、L3 状态转移类型 (§19-§21)

### §19 `StateTransitionRecord`

```python
@dataclass(frozen=True)
class StateTransitionRecord:
    transition_id: str
    visit_id: str
    base_snapshot_id: str
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    event_time: datetime.datetime
    transaction_time: datetime.datetime
    triggering_event_ref: str
    approver_id: Optional[str]
    gps_deviation_meters: Optional[float]
    service_duration_min: Optional[float]
    policy_version_snapshot: Optional[str]
    evidence_refs: Tuple[str, ...]
    transition_model_version: str = 'TransitionEngine_v3.0'
    record_hash: str = ''
```

### §20 `TransitionRequest`

```python
@dataclass(frozen=True)
class TransitionRequest:
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
```

### §21 `TransitionResult`

```python
@dataclass(frozen=True)
class TransitionResult:
    new_worldstate_snapshot_id: str
    transition_record: StateTransitionRecord
    audit_hash: str
    was_guard_passed: bool
    rejection_reason: Optional[str] = None
    idempotency_replay_detected: bool = False
```

---

## 十、L5 情景推演类型 (§22-§24)

### §22 `PerturbationEvent`

```python
@dataclass(frozen=True)
class PerturbationEvent:
    perturbation_id: str
    perturbation_type: str
    affected_entity_refs: Tuple[str, ...]
    payload: Mapping[str, FrozenValue]
```

### §23 `StateDelta`

```python
@dataclass(frozen=True)
class StateDelta:
    changed_fields: Mapping[str, Tuple[FrozenValue, FrozenValue]]
    aggregate_metrics_before: Mapping[str, float]
    aggregate_metrics_after: Mapping[str, float]
```

### §24 `ScenarioResult`

```python
@dataclass(frozen=True)
class ScenarioResult:
    base_snapshot_id: str
    scenario_id: str
    branch_hash: str
    delta_state: StateDelta
    aggregate_metrics_delta: Mapping[str, float]
    guard_violations_count: int
    convergence_status: str
    capacity_impact_summary: Mapping[str, float]
```

---

## 十一、L6/L7 规划器与决策类型 (§25-§30)

### §25 `PlannerNodeTopology`

```python
@dataclass(frozen=True)
class PlannerNodeTopology:
    node_index: int
    domain_entity_id: str
    spatial_coordinate: Tuple[float, float]
    service_duration_min: float
    is_depot: bool = False
```

### §26 `PlanningIntent`

```python
@dataclass(frozen=True)
class PlanningIntent:
    # === 必填字段 ===
    intent_id: str
    decision_scope: str
    valid_time: datetime.datetime
    timezone: str
    # === 可选字段 ===
    target_agent_id: Optional[str] = None
    target_store_id: Optional[str] = None
    objectives: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()
    allowed_actions: Tuple[str, ...] = ()
```

### §27 `PlannedStop`

```python
@dataclass(frozen=True)
class PlannedStop:
    stop_idx: int
    store_code: str
    store_name: str
    district: str
    planned_service_min: float
    leg_distance_from_prev_km: float = 0.0
    leg_transit_from_prev_min: float = 0.0
```

### §28 `PlannedDailyRoute`

```python
@dataclass(frozen=True)
class PlannedDailyRoute:
    date_str: str
    weekday_name: str
    rep_id: str
    stops: Tuple[PlannedStop, ...]
    depot_outbound_transit_min: float = 0.0
    depot_inbound_transit_min: float = 0.0
    total_daily_distance_km: float = 0.0
    total_daily_transit_min: float = 0.0
    total_daily_service_min: float = 0.0
    total_daily_workload_min: float = 0.0
```

### §29 `CandidatePlan`

```python
@dataclass(frozen=True)
class CandidatePlan:
    plan_id: str
    intent_id: str
    target_agent_id: str
    period_label: str
    daily_routes: Tuple[PlannedDailyRoute, ...]
    solver_name: str
    solver_status: str
    total_scheduled_visits: int
    total_monthly_transit_min: float
    total_monthly_distance_km: float
    trade_off_metrics: Mapping[str, float]
```

### §30 API 基础设施类型交叉引用 (非权威定义)

以下 API 基础设施类型属于 Tier 2，权威定义在主 API 规范，本节仅为交叉引用：
- `RequestFingerprint`: 权威定义 = 主 API 规范 §2.2
- `WorkflowContext`: 权威定义 = 主 API 规范 §5.2.1
- `RequestFingerprint`: 权威定义 = 主 API 规范 §5.2.1

（`ActualVisitEvent` 是领域类型，完整定义在本规范 §13。）

---

## 十二、审计与决策产物类型 (§31-§32)

### §31 `PlanAuditReport`

```python
@dataclass(frozen=True)
class PlanAuditReport:
    plan_id: str
    is_fully_compliant: bool
    cadence_compliance_rate: float
    physical_feasibility_passed: bool
    business_compliance_passed: bool
    semantic_purity_passed: bool
    violations: Tuple[str, ...] = ()
    summary_message: str = ''
```

### §32 `DecisionArtifact`

```python
@dataclass(frozen=True)
class DecisionArtifact:
    artifact_id: str
    candidate_plan_ref: str
    audit_report_ref: str
    approved_by: str
    approved_at: datetime.datetime
    published_schedule: Mapping[str, Tuple[str, ...]]
    status: str = 'APPROVED_FOR_EXECUTION'
    approval_notes: str = ''
```


---

## 十三、执行反馈与规划器投影类型 (§33-§34)

### §33 `ExecutionFeedbackReceipt` (执行反馈回执)

```python
@dataclass(frozen=True)
class ExecutionFeedbackReceipt:
    """执行反馈回执 (Canonical Type ID: ExecutionFeedbackReceipt)"""
    # === 必填字段 ===
    event_id: str
    new_snapshot_id: str
    transition_required: bool
    evidence_status: str
    # === 可选字段 ===
    receipt_message: str = ""
```

### §34 `PlannerStateProjection` (规划器状态投影)

```python
@dataclass(frozen=True)
class PlannerStateProjection:
    """规划求解器消费的确定性纯数学投影切片 (Canonical Type ID: PlannerStateProjection)"""
    # === 必填字段 ===
    projection_id: str
    target_agent_id: str
    time_slots_count: int
    # 纯数学节点拓扑（不可变）
    nodes: Tuple[PlannerNodeTopology, ...]
    node_index_lookup: Mapping[str, int]
    # 纯数学距离与通勤矩阵（不可变嵌套元组）
    travel_cost_matrix: Tuple[Tuple[float, ...], ...]
    travel_distance_matrix: Tuple[Tuple[float, ...], ...]
    # 严格候选模式空间 P_i（不可变嵌套）
    candidate_pattern_space: Mapping[int, Tuple[Tuple[Tuple[int, int], ...], ...]]
    # 刚性锁定掩码 (已承诺不可变时隙)
    locked_commitments_mask: Mapping[Tuple[int, int], Tuple[int, ...]]
    # === 可选字段 ===
    daily_stop_capacity: int = 6
    daily_workload_budget_min: float = 480.0
    is_projection_clean: bool = True
    unplannable_nodes_excluded: Tuple[str, ...] = ()
```

---

## 十四、支撑枚举与支撑容器类型 (§35)

本节闭合全部支撑类型引用。枚举值与 `svde/ontology/src/prism_ontology/world_model/state_snapshot.py` 中的现行代码保持一致。

### §35.1 `LifecycleStatus` (任务生命周期状态枚举)

```python
class LifecycleStatus(str, Enum):
    PROPOSED = "PROPOSED"          # 意图提出
    PLANNED = "PLANNED"            # 规划就绪 (待审批)
    COMMITTED = "COMMITTED"        # 锁定承诺 (已审批下发)
    IN_PROGRESS = "IN_PROGRESS"    # 执行中
    COMPLETED = "COMPLETED"        # 履约完成
    MISSED = "MISSED"              # 违规失访
    DEFERRED = "DEFERRED"          # 经审批顺延
    CANCELLED = "CANCELLED"        # 撤销
```

### §35.2 `CognitiveCategory` (认知类别枚举)

```python
class CognitiveCategory(str, Enum):
    OBSERVATION = "OBSERVATION"      # 客观观测
    DERIVED_ESTIMATE = "DERIVED_ESTIMATE"  # 派生推断 (显式标注，绝不冒充物理事实)
    POLICY = "POLICY"                # 业务政策
    COMMITMENT = "COMMITMENT"        # 锁定承诺
    PLAN_INTENT = "PLAN_INTENT"      # 规划意图
    EXECUTION_EVENT = "EXECUTION_EVENT"    # 执行事实
    SCENARIO = "SCENARIO"            # 反事实推演情景
```

### §35.3 `FulfillmentClass` (履约刚性等级枚举)

```python
class FulfillmentClass(str, Enum):
    REQUIRED = "REQUIRED"      # Key / A 级核心大店 (违背即事故)
    COMMITTED = "COMMITTED"    # B / C 级常规店 (承诺履约)
    OPTIONAL = "OPTIONAL"      # D 级与长尾店 (弹性维护)
```

### §35.4 `GeoQualityStatus` (地理坐标质量枚举)

```python
class GeoQualityStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"  # 精确坐标 (可参与路线规划)
    UNMAPPED = "UNMAPPED"        # 坐标缺失 (不可参与路线规划，触发门禁)
```

### §35.5 `ChannelTier` (渠道层级枚举)

```python
class ChannelTier(str, Enum):
    NKA = "NKA"                    # 全国连锁
    RKA = "RKA"                    # 区域连锁
    LOCAL_KEY = "LOCAL_KEY"        # 本地重点
    TRADITIONAL = "TRADITIONAL"    # 传统流通
```

### §35.6 `StatusTransitionEntry` (状态流转轻量条目)

```python
@dataclass(frozen=True)
class StatusTransitionEntry:
    """单个拜访的状态流转条目 (Canonical Type ID: StatusTransitionEntry)
    区别于 §19 StateTransitionRecord（全局审计记录，含快照引用）：本类型仅记录生命周期内部时间线。"""
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    changed_at: datetime.datetime   # 必须带时区 (aware)
    reason: str = ""
```

### §35.7 `SourceManifest` (数据源清单)

```python
@dataclass(frozen=True)
class SourceManifest:
    """数据源清单 (Canonical Type ID: SourceManifest)
    注意：规范目标修正了代码中 assembled_at 使用系统当前时刻默认值的违规——
    本规范中 assembled_at 为必填字段、显式传入、必须带时区 (aware)，严禁默认值。"""
    source_file_path: str
    source_file_sha256: str          # 256-bit SHA-256 digest represented as 64 hexadecimal characters
    assembled_at: datetime.datetime  # 必填 (aware)，严禁 naive / 严禁 now() 默认值
    loader_version: str = "CanonicalWorldState_v1.1"
    raw_rows_count: int = 0
    valid_facts_count: int = 0
    excluded_rows_count: int = 0
    exclusion_reason: str = ""
```

### §35.8 `CadenceRule` (节奏规则)

```python
@dataclass(frozen=True)
class CadenceRule:
    """拜访节奏规则 (Canonical Type ID: CadenceRule)"""
    rule_id: str
    target_frequency_per_month: int
    cadence_type: str                # STRICT_WEEKLY / STRICT_BIWEEKLY / STRICT_MONTHLY
    exact_interval_days: int         # 7 / 14 / 28
    same_weekday_locked: bool = True
```

### §35.9 `OwnershipConflictRecord` (归属冲突记录)

```python
@dataclass(frozen=True)
class OwnershipConflictRecord:
    """门店归属冲突记录 (Canonical Type ID: OwnershipConflictRecord)"""
    store_code: str
    store_name: str
    conflicting_reps: Tuple[str, ...]
    resolution_status: str = "FLAGGED_FOR_REVIEW"
```

### §35.10 `PolicyRegistry` (政策注册表)

```python
from types import MappingProxyType

@dataclass(frozen=True)
class PolicyRegistry:
    """政策注册表 (Canonical Type ID: PolicyRegistry)
    规范目标：全部容器为不可变 Mapping/Tuple（代码现为 Dict/List，属实现期迁移目标）。"""
    cadence_rules: Mapping[str, CadenceRule] = MappingProxyType({})
    ownership_map: Mapping[str, str] = MappingProxyType({})            # store_code -> rep_id
    ownership_conflicts: Tuple[OwnershipConflictRecord, ...] = ()
    operational_policies: Mapping[str, OperationalVisitPolicy] = MappingProxyType({})
    deferral_policies: Mapping[str, DeferralPolicy] = MappingProxyType({})
```

## 十五、实体历史与归属修订类型 (§37-§38)

### §37 `PolicyAmendment` (政策修订记录) — v1.0 修订新增

```python
@dataclass(frozen=True)
class PolicyAmendment:
    """拜访政策修订记录 (Canonical Type ID: PolicyAmendment)

    历史建模纪律 (Time Machine 反模式禁令, 见架构基线 §12.2):
    实体级历史必须走 linked amendment 对象, 严禁为每个版本建独立 policy 对象。
    `OperationalVisitPolicy.policy_version` 字段为过渡保留 (DEPRECATED 方向),
    代码迁移后由单一当前 policy + 本修订记录链取代。
    """
    amendment_id: str
    policy_id: str                    # 指向被修订的 OperationalVisitPolicy.policy_id
    amended_at: datetime.datetime     # 必须带时区 (transaction time)
    field_name: str                   # 被修订字段 (如 target_frequency_per_month)
    previous_value: FrozenValue
    new_value: FrozenValue
    reason: str                       # 业务原因 (如 方案B 调整: 3次/月 -> 4次/月)
    approved_by: str
    bitemporal: BitemporalPeriod      # 修订自身的双时态
```

**历史建模纪律声明 (规范性, 适用于全部实体类型):**

1. 每个真实世界实体在本体中**只有一个当前对象**; 历史一律走 linked amendment/记录对象。
2. `WorldState` 全量快照链**不适用**本纪律: 快照是**决策检查点** (event-sourcing 语义),
   不是实体版本; 两者严禁混同。快照用于决策审计与场景基线, 不用于实体级历史查询。
3. 违例特征自查: 同一实体出现 `version`/`revision`/`isCurrent` 区分的多对象; 对象数随变更数
   (而非实体数) 增长; 引用方需要判断"该链接哪个版本"。

### §38 `OwnershipAssignment` (归属指派记录) — v1.0 修订新增

```python
@dataclass(frozen=True)
class OwnershipAssignment:
    """客户归属指派记录 (Canonical Type ID: OwnershipAssignment)

    设计依据 (TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 2):
    归属是带元数据的关联 (object-backed link), 不是无元数据映射。
    `PolicyRegistry.ownership_map: Dict[store_code, rep_id]` 降级为本类型的当前态投影
    (status=ACTIVE 的指派)。业务实证: 2026-08 方案B 归属调整 (门店摘牌/转移) 为高频动作,
    需要生效日期/原因/审批承载。
    """
    assignment_id: str
    store_code: str
    rep_id: str
    effective_from: datetime.date       # valid time 起
    effective_to: Optional[datetime.date] = None   # valid time 止 (None = 当前有效)
    reason: str = ''                    # 方案调整 / 摘牌 / 归属冲突裁决 / 新店开铺
    approved_by: str = ''
    transaction_from: Optional[datetime.datetime] = None  # 必须带时区 (入库时刻)
    status: str = 'ACTIVE'              # ACTIVE / SUPERSEDED
```

**与 `OwnershipConflictRecord` (§35.9) 的关系**: 冲突记录是裁决输入; 裁决产出一条
`OwnershipAssignment` (reason=归属冲突裁决) 并将落败方指派置为 SUPERSEDED。

---

## 十六、实现期类型加载顺序契约 (§36)

### §36 实现期加载顺序契约（规范性）

本契约是铁律 #5/#6 的实现级固化。违反本契约将导致枚举默认值在类创建期 NameError。

**模块划分（规范性）：**

| 模块 | 内容 | 加载顺序 |
| :--- | :--- | :--- |
| `prism_ontology/contracts/canonical_enums.py` | §35.1~§35.5 五个枚举 | **第 1 位（强制最先）** |
| `prism_ontology/contracts/canonical_types.py` | 其余全部类型（§1~§34、§35.6~§35.10、§37、§38） | 第 2 位 |

**canonical_types.py 内部生成顺序（拓扑序，规范性）：**

```text
1. FrozenScalar / FrozenValue 别名          (§17-§18)
2. 基础值类型                                (§1 BitemporalPeriod, §2 GeoCoordinate)
3. 支撑记录                                  (§19 StateTransitionRecord, §20, §21,
                                              §35.6 StatusTransitionEntry,
                                              §10 InStoreActionFact, §11 MerchandisingComplianceFact,
                                              §35.7 SourceManifest, §3 DerivedDepotEstimate,
                                              §35.8 CadenceRule, §35.9 OwnershipConflictRecord)
4. 枚举依赖实体                              (§4~§9, §12, §13, §15, §16)
5. 聚合根                                    (§14 OperationalDecisionWorldState,
                                              §35.10 PolicyRegistry —— 依赖 3 中 CadenceRule 等，
                                              必须晚于其全部被引用类型)
6. 规划与决策类型                            (§22~§29, §31~§34, §25~§26)
```

**CI 冒烟钩子（强制性）：**

持续集成必须包含以下三步冒烟验证，任一失败即阻断合入：

1. 按上述顺序拼接模块后 `ast.parse` 通过；
2. `exec` 执行无 NameError / TypeError；
3. 全部 dataclass 以最小合法参数实例化成功。
