"""Canonical Operational Decision WorldState v1.1.

The SINGLE, CANONICAL WorldState implementation for SVDE Enterprise Decision System.
Strictly implements L4 World State Snapshot and L5 Scenario Branching.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Set
import datetime


class CognitiveCategory(str, Enum):
    OBSERVATION = "OBSERVATION"                 # 客观观测
    DERIVED_ESTIMATE = "DERIVED_ESTIMATE"       # 派生推断 (显式标注，绝不冒充物理事实)
    POLICY = "POLICY"                           # 业务政策
    COMMITMENT = "COMMITMENT"                   # 锁定承诺
    PLAN_INTENT = "PLAN_INTENT"                 # 规划意图
    EXECUTION_EVENT = "EXECUTION_EVENT"         # 执行事实
    SCENARIO = "SCENARIO"                       # 反事实推演情景


class FulfillmentClass(str, Enum):
    REQUIRED = "REQUIRED"      # Key / A 级核心大店 (违背即事故)
    COMMITTED = "COMMITTED"    # B / C 级常规店 (承诺履约)
    OPTIONAL = "OPTIONAL"      # D 级与长尾店 (弹性维护)


class GeoQualityStatus(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"        # 精确坐标 (可参与路线规划)
    UNMAPPED = "UNMAPPED"              # 坐标缺失 (不可参与路线规划，触发门禁)


class ChannelTier(str, Enum):
    NKA = "NKA"                        # 全国连锁 (孩子王、爱婴室等)
    RKA = "RKA"                        # 区域连锁 (婴知岛、启东金晶等)
    LOCAL_KEY = "LOCAL_KEY"
    TRADITIONAL = "TRADITIONAL"


class InStoreActionType(str, Enum):
    EXPIRY_RISK_AUDIT = "EXPIRY_RISK_AUDIT"             # 效期防损 (基线: 45.7 min)
    OUT_OF_STOCK_REMEDY = "OUT_OF_STOCK_REMEDY"         # 缺货补货 (基线: 54.0 min)
    STORE_MANAGER_NEGOTIATION = "STORE_MANAGER_NEGOTIATION" # 店长客情 (基线: 54.5 min)
    NEW_CUSTOMER_SAMPLING = "NEW_CUSTOMER_SAMPLING"     # 开新派样 (基线: 55.0 min)
    PLANOGRAM_DISPLAY_AUDIT = "PLANOGRAM_DISPLAY_AUDIT" # 陈列核销 (基线: 61.5 min)


class LifecycleStatus(str, Enum):
    PROPOSED = "PROPOSED"                       # 意图提出
    PLANNED = "PLANNED"                         # 规划就绪 (待审批)
    COMMITTED = "COMMITTED"                     # 锁定承诺 (已审批下发)
    IN_PROGRESS = "IN_PROGRESS"                 # 执行中
    COMPLETED = "COMPLETED"                     # 履约完成
    MISSED = "MISSED"                           # 违规失访
    DEFERRED = "DEFERRED"                       # 经审批顺延
    CANCELLED = "CANCELLED"                     # 撤销


@dataclass(frozen=True)
class BitemporalPeriod:
    """双时态时间戳 (Snodgrass 1999)"""
    valid_from: datetime.datetime               # 业务事实在真实世界中生效的开始时间 (Valid Time)
    valid_to: datetime.datetime                 # 业务事实在真实世界中失效的结束时间
    transaction_from: datetime.datetime         # 系统记录入库时刻 (Transaction Time)
    transaction_to: Optional[datetime.datetime] = None # 系统废弃/更新时刻


@dataclass(frozen=True)
class GeoCoordinate:
    longitude: float
    latitude: float


@dataclass(frozen=True)
class DerivedDepotEstimate:
    """派生推断的基地坐标 (显式标注 category=DERIVED_ESTIMATE)"""
    rep_id: str
    inferred_centroid: GeoCoordinate
    sample_points_count: int
    confidence_score: float                     # 0.0 ~ 1.0
    derivation_algorithm: str = "Geometric_Centroid_of_Assigned_Stores"
    category: CognitiveCategory = CognitiveCategory.DERIVED_ESTIMATE


@dataclass(frozen=True)
class AccountHierarchyEntity:
    """连锁大客户总部实体 (Woodburn 2002/2014)"""
    account_id: str
    account_name: str
    channel_tier: ChannelTier
    parent_account_ref: Optional[str] = None
    contract_summary: str = "全国性陈列与供货协议"


@dataclass(frozen=True)
class ProductLineScopeEntity:
    """多产品线组合实体 (Johnston & Marshall 2016)"""
    brand_id: str
    brand_name: str
    strategic_role: str                         # CASH_COW / STRATEGIC_GROWTH
    default_action_types: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class SupplyNodeEntity:
    """供应链大仓实体 (Shanahan 2007/2019)"""
    dc_id: str
    dc_name: str
    served_ka_names: tuple = field(default_factory=tuple)
    delivery_status: str = "UNCALIBRATED"       # 显式标注配送日历未校准，绝不使用虚假默认值


@dataclass(frozen=True)
class InStoreActionFact:
    """现场具体动作事实 (Zoltners et al. 2006)"""
    action_type: InStoreActionType
    estimated_duration_min: float
    action_notes: str = ""


@dataclass(frozen=True)
class MerchandisingComplianceFact:
    """合同陈列对赌量化核销事实 (Anderson & Stern 2004)"""
    contract_target_units: int
    actual_compliant_units: int
    compliance_ratio: float
    has_oos_risk: bool = False


@dataclass(frozen=True)
class OperationalCustomer:
    """零售终端门店实体 (Canonical Customer Entity - OBSERVATION ONLY)"""
    store_code: str
    store_name: str
    tier: str                                   # Key / A / B / C / D
    ka_name: str
    district: str
    location: Optional[GeoCoordinate]
    geo_quality: GeoQualityStatus
    fulfillment_class: FulfillmentClass = FulfillmentClass.REQUIRED
    planned_frequency: Optional[int] = None   # DEPRECATED: Kept for back-compat. Source must be PolicyRegistry, not observation.
    account_hierarchy_ref: Optional[str] = None
    supply_node_ref: Optional[str] = None
    product_line_scope_refs: tuple = field(default_factory=tuple)
    address: Optional[str] = None
    category: CognitiveCategory = CognitiveCategory.OBSERVATION

    @property
    def is_plannable(self) -> bool:
        return self.geo_quality == GeoQualityStatus.EXACT_MATCH and self.location is not None


# DTO Aliases for backward compatibility
CustomerEntity = OperationalCustomer


@dataclass(frozen=True)
class OperationalResource:
    """销售代表实体 (Canonical Resource Entity)"""
    rep_id: str
    rep_name: str
    region: str                                 # 东区
    sub_region: str                             # 苏州北 / 苏州南 / 常州 / 南通
    city: str                                   # 苏州 / 常州 / 南通
    depot_estimate: DerivedDepotEstimate        # 显式派生推断对象
    assigned_store_codes: tuple = field(default_factory=tuple)
    max_daily_stops: int = 6
    max_daily_workload_min: float = 480.0
    category: CognitiveCategory = CognitiveCategory.OBSERVATION

    @property
    def home_depot_coord(self) -> GeoCoordinate:
        return self.depot_estimate.inferred_centroid


ResourceEntity = OperationalResource


@dataclass(frozen=True)
class CadenceRule:
    rule_id: str
    target_frequency_per_month: int
    cadence_type: str                           # STRICT_WEEKLY / STRICT_BIWEEKLY / STRICT_MONTHLY
    exact_interval_days: int                    # 7 / 14 / 28
    same_weekday_locked: bool = True


@dataclass(frozen=True)
class OperationalVisitPolicy:
    policy_id: str
    policy_version: str                         # 如 "v2.0"
    store_code: str
    target_frequency_per_month: int
    cadence_type: str
    same_weekday_locked: bool
    bitemporal: BitemporalPeriod
    approved_by: str
    category: CognitiveCategory = CognitiveCategory.POLICY


@dataclass(frozen=True)
class OperationalCommitment:
    commitment_id: str
    store_code: str
    rep_id: str
    locked_date: datetime.date
    locked_time_window: Optional[Tuple[str, str]] = None
    lock_level: str = "DAY_LOCKED"              # FREE / DAY_LOCKED / SEQUENCE_LOCKED
    category: CognitiveCategory = CognitiveCategory.COMMITMENT


@dataclass(frozen=True)
class DeferralPolicy:
    """Business policy governing when a visit can be deferred (P0-1 fix)."""
    policy_id: str
    max_deferrals_per_month: int = 2
    allowed_deferral_window_days: int = 7
    requires_approval: bool = True
    approver_role: str = "REP_MANAGER"
    category: CognitiveCategory = CognitiveCategory.POLICY


@dataclass(frozen=True)
class OwnershipConflictRecord:
    store_code: str
    store_name: str
    conflicting_reps: tuple
    resolution_status: str = "FLAGGED_FOR_REVIEW"


@dataclass(frozen=True)
class PolicyRegistry:
    cadence_rules: Dict[str, CadenceRule] = field(default_factory=dict)
    ownership_map: Dict[str, str] = field(default_factory=dict) # store_code -> rep_id
    ownership_conflicts: List[OwnershipConflictRecord] = field(default_factory=list)
    operational_policies: Dict[str, OperationalVisitPolicy] = field(default_factory=dict) # FIX-1: Versioned policies
    deferral_policies: Dict[str, DeferralPolicy] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationalVisitLifecycleRecord:
    visit_id: str
    store_code: str
    rep_id: str
    scheduled_date: datetime.date
    current_status: LifecycleStatus
    status_history: list = field(default_factory=list)
    actual_arrival: Optional[datetime.time] = None
    actual_departure: Optional[datetime.time] = None
    service_duration_min: float = 0.0


@dataclass(frozen=True)
class ActualVisitEvent:
    event_id: str
    store_code: str
    rep_id: str
    visit_date: datetime.date
    service_duration_min: float
    transit_duration_min: float
    is_line_internal: bool
    actions: tuple = field(default_factory=tuple)
    merchandising_compliance: Optional[MerchandisingComplianceFact] = None
    summary: str = ""


@dataclass(frozen=True)
class SourceManifest:
    source_file_path: str
    source_file_sha256: str
    assembled_at: datetime.datetime  # 必填, 显式传入, 必须带时区 (严禁 naive datetime / datetime.now() 默认值)
    loader_version: str = "CanonicalWorldState_v1.1"
    raw_rows_count: int = 6467
    valid_facts_count: int = 6374
    excluded_rows_count: int = 93
    exclusion_reason: str = "93 rows excluded due to missing store_code in master data"

    def __post_init__(self):
        if self.assembled_at.tzinfo is None:
            raise ValueError(
                f"SourceManifest.assembled_at 必须带时区 (timezone-aware), 实际 naive: {self.assembled_at!r}"
            )


@dataclass(frozen=True)
class OperationalDecisionWorldState:
    """Canonical L4/L5 Operational Decision WorldState Snapshot."""
    snapshot_id: str
    bitemporal: BitemporalPeriod
    manifest: SourceManifest
    customers: Dict[str, OperationalCustomer]
    resources: Dict[str, OperationalResource]
    account_hierarchies: Dict[str, AccountHierarchyEntity]
    product_line_scopes: Dict[str, ProductLineScopeEntity]
    supply_nodes: Dict[str, SupplyNodeEntity]
    policies: PolicyRegistry
    commitments: Dict[str, OperationalCommitment] = field(default_factory=dict)
    visit_lifecycle_records: Dict[str, OperationalVisitLifecycleRecord] = field(default_factory=dict)
    transition_records: tuple = field(default_factory=tuple)  # P1-2: Persistent structured transitions
    execution_fact_stream: List[ActualVisitEvent] = field(default_factory=list)
    active_scenario_branches: Dict[str, Any] = field(default_factory=dict)

    # Universal accessors
    @property
    def customer_universe(self) -> Dict[str, OperationalCustomer]:
        return self.customers

    def get_rep_universe(self, rep_id: str) -> Dict[str, OperationalCustomer]:
        res = self.resources.get(rep_id)
        if not res:
            return {}
        return {code: self.customers[code] for code in res.assigned_store_codes if code in self.customers}

    @property
    def total_stores_count(self) -> int:
        return len(self.customers)

    @property
    def total_reps_count(self) -> int:
        return len(self.resources)


# Canonical Alias
WorldState = OperationalDecisionWorldState
WorldStateSnapshot = OperationalDecisionWorldState
