"""Plan vs Actual 数据契约 (Phase 1, Task 6) — 版本化计划与执行账本。

所有类型为 frozen dataclass，与 svde Canonical Types 设计纪律一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ============================================================================
# 计划版本
# ============================================================================
@dataclass(frozen=True)
class PlanVersion:
    """版本化计划 — 每个版本代表一次完整的排程输出（含人工调整）。

    Fields:
        plan_id: 计划实例标识（如 "PLAN_RENJUN_2026-06"）
        version: 版本号（单调递增）
        planning_horizon_start: 规划期起始日期
        planning_horizon_end: 规划期结束日期（含）
        representative_id: 销售代表标识
        policy_version: 所用 PlanningPolicy 的版本引用
        solver_run_id: 产生此版本的求解器运行 ID（可空，人工计划或手动调整时为空）
        status: draft → reviewed → published → superseded
        created_at: 创建时间（带时区）
        published_at: 发布时间（带时区，status=published 时必填）
    """
    plan_id: str
    version: int
    planning_horizon_start: date
    planning_horizon_end: date
    representative_id: str
    policy_version: str
    solver_run_id: str | None = None
    status: str = "draft"
    created_at: datetime | None = None
    published_at: datetime | None = None

    def __post_init__(self):
        if self.planning_horizon_end < self.planning_horizon_start:
            raise ValueError("规划期结束日期不得早于起始日期")
        if self.status not in ("draft", "reviewed", "published", "superseded"):
            raise ValueError(f"非法状态: {self.status!r}")
        if self.status == "published" and self.published_at is None:
            raise ValueError("published 状态必须指定 published_at")


# ============================================================================
# 计划拜访
# ============================================================================
@dataclass(frozen=True)
class PlannedVisit:
    """计划拜访 — 属于某个 PlanVersion 的单次拜访条目。

    Fields:
        plan_version_id: 所属计划版本
        visit_id: 拜访实例标识（全局唯一，如 "VISIT_PLAN_001"）
        customer_id: 客户标识
        planned_date: 计划拜访日期
        sequence: 当日拜访顺序（1-based）
        planned_arrival_window: 计划到达时间窗口（如 "09:00-10:00"）
        estimated_travel_minutes: 预计在途时间（分钟）
        estimated_service_minutes: 预计在店时间（分钟）
        priority_score: 优先级分数（越高越优先，Phase 2 启用）
        is_locked: 是否被经理锁定（锁定后重算时不移动）
        reason_codes: 创建/修改此拜访的原因代码列表（如 ["FREQUENCY", "CAPACITY"]）
    """
    plan_version_id: str
    visit_id: str
    customer_id: str
    planned_date: date
    sequence: int
    planned_arrival_window: str = ""
    estimated_travel_minutes: float = 0.0
    estimated_service_minutes: float = 0.0
    priority_score: float = 0.0
    is_locked: bool = False
    reason_codes: tuple[str, ...] = ()


# ============================================================================
# 实际拜访
# ============================================================================
@dataclass(frozen=True)
class ActualVisit:
    """实际拜访 — 执行后的事实记录（来自 GPS/打卡/ERP 等外部系统）。

    Fields:
        actual_id: 实际拜访记录标识
        plan_version_id: 关联的计划版本（可为空，临时追加拜访无对应计划）
        planned_visit_id: 关联的计划拜访标识（可为空）
        customer_id: 客户标识
        actual_date: 实际拜访日期
        actual_arrival_at: 实际到达时间
        actual_departure_at: 实际离开时间
        actual_travel_minutes: 实际在途时间（分钟）
        service_minutes: 实际在店时间（分钟）
        outcome_code: 执行结果码（如 COMPLETED / CANCELLED / PARTIAL / MISSED）
        source_system: 数据来源系统（如 "GPS" / "MANUAL" / "ERP"）
        override_ref: 人工调整引用（若此拜访由 ManualOverride 产生）
    """
    actual_id: str
    customer_id: str
    actual_date: date
    actual_arrival_at: datetime | None = None
    actual_departure_at: datetime | None = None
    actual_travel_minutes: float = 0.0
    service_minutes: float = 0.0
    outcome_code: str = "COMPLETED"
    source_system: str = ""
    plan_version_id: str | None = None
    planned_visit_id: str | None = None
    override_ref: str | None = None


# ============================================================================
# 人工调整
# ============================================================================
@dataclass(frozen=True)
class ManualOverride:
    """人工调整记录 — 每次经理手动修改求解器输出的快照。

    不覆盖原始求解结果，只记录差异。原始值始终在 PlanVersion 中可追溯。
    """
    override_id: str
    plan_version_id: str
    actor_id: str
    created_at: datetime
    before_value: str
    after_value: str
    reason_code: str
    reason_text: str = ""
    affected_customer_ids: tuple[str, ...] = ()
    affect_plan_version: str = ""


# ============================================================================
# 决策证据
# ============================================================================
@dataclass(frozen=True)
class DecisionEvidence:
    """每次求解/决策的可审计元数据（与求解结果一并返回，机器可读）。"""
    solver_run_id: str
    policy_version: str
    input_version: str
    optimality_scope: str  # "restricted_column_pool" / "global"
    status: str            # "FEASIBLE" / "OPTIMAL" / "INFEASIBLE" / "TIME_LIMIT"
    n_columns: int = 0
    n_constraints: int = 0
    solve_seconds: float = 0.0
    lp_obj: float | None = None
    ip_obj: float | None = None
    mip_gap: float | None = None
    warnings: tuple[str, ...] = ()
    # 与当前计划相比的变化
    n_changes: int = 0
    change_details: tuple[dict, ...] = ()

# ============================================================================
# CoveragePolicy (图 5.2) — 带时间范围的拜访覆盖政策
# 将 Customer.frequency 从"客户固有属性"迁移为独立的时间范围政策。
# ============================================================================
@dataclass(frozen=True)
class CoveragePolicy:
    """拜访覆盖政策 — 客户在特定时间窗口内的目标频次与服务等级。

    Fields:
        id: 政策标识
        customer_id: 客户标识
        required_visits: 规划期内目标拜访次数
        horizon_start: 政策生效起始日期
        horizon_end: 政策生效结束日期（含）
        min_spacing_days: 最小重访间隔天数
        service_level: 服务等级 (priority / standard / economy)
        rationale: 制定依据 (emerging_opportunity / contract_obligation / retention_risk 等)
        approved_by: 审批人
        version: 版本号（单调递增）
        created_at: 创建时间
    """
    id: str
    customer_id: str
    required_visits: int
    horizon_start: date
    horizon_end: date
    min_spacing_days: int = 0
    service_level: str = "standard"
    rationale: str = ""
    approved_by: str = ""
    version: int = 1
    created_at: datetime | None = None

    def __post_init__(self):
        if self.required_visits < 0:
            raise ValueError("required_visits 必须 >= 0")
        if self.horizon_end < self.horizon_start:
            raise ValueError("horizon_end 不得早于 horizon_start")


# ============================================================================
# BusinessSignal (图 5.3) — 可追溯的业务信号（模型输出/推断结果）
# 所有信号带 kind/source/confidence/model_version 标签，可区分事实与推断。
# ============================================================================
@dataclass(frozen=True)
class BusinessSignal:
    """可追溯业务信号 — 模型推断或观察结果，不伪装成稳定事实。

    Fields:
        id: 信号标识
        subject_type: 信号主体类型 (customer / representative / territory)
        subject_id: 信号主体标识
        signal_type: 信号类型 (access_probability / response_momentum / strategic_priority / service_risk / travel_time_residual / service_time_residual / visit_acceptance_probability)
        value: 信号值（字符串表示，如 "rising" / "0.82"）
        numeric_value: 数值版本（如有）
        kind: 信号性质 (fact / inferred / policy / outcome)
        source: 来源 (CRM / SFA / GPS / model / manager / import)
        model_version: 产生此信号的模型版本（inferred 时必填）
        confidence: 置信度 [0, 1]（inferred 时必填）
        observed_at: 观测时间
        valid_from: 有效起始时间
        valid_to: 有效结束时间（None = 持续有效）
    """
    id: str
    subject_type: str
    subject_id: str
    signal_type: str
    value: str
    numeric_value: float | None = None
    kind: str = "observed"
    source: str = ""
    model_version: str = ""
    confidence: float = 1.0
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self):
        if self.kind not in ("fact", "observed", "inferred", "policy", "outcome"):
            raise ValueError(f"kind 非法: {self.kind!r}")
        if self.kind == "inferred" and not self.model_version:
            raise ValueError("inferred 信号必须指定 model_version")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"confidence 必须在 [0, 1], 实际 {self.confidence}")


# ============================================================================
# WorldSnapshot (图 7) — 版本化世界快照，求解器唯一输入
# 求解器不读实时表，只读这个时间点冻结的快照。
# ============================================================================
@dataclass(frozen=True)
class WorldSnapshot:
    """版本化世界快照 — 求解器在该时间点看到的锁定事实。

    Fields:
        id: 快照标识
        as_of: 快照时间点
        customers_version: 客户数据版本
        signals_version: 信号数据版本
        outcomes_until: 结果数据截止时间
        active_commitments_version: 活跃承诺版本
        calibration_version: 校准参数版本
        policy_version: 生效策略版本
        scenario_id: 情景标识
    """
    id: str
    as_of: datetime
    customers_version: str = ""
    signals_version: str = ""
    outcomes_until: datetime | None = None
    active_commitments_version: str = ""
    calibration_version: str = ""
    policy_version: str = ""
    scenario_id: str = ""

    def __post_init__(self):
        if not self.id:
            raise ValueError("snapshot_id 必填")


# ============================================================================
# StrategyScenario (图 5.5) — 某次规划应用的策略偏好
# 同一世界状态 + 不同策略 = 不同情景结果
# ============================================================================
@dataclass(frozen=True)
class StrategyScenario:
    """策略情景 — 表达一组资源配置偏好。

    Fields:
        id: 情景标识
        name: 情景名称 (baseline / efficiency_first / value_first / stability_first / balanced / manager_adjusted)
        objective_profile: 目标偏好字典 (value_coverage / travel_workload / plan_stability / workload_equity → maximize / minimize / medium)
        opportunity_threshold: 机会价值阈值 (低于此值的客户不优先考虑)
        required_policy_id: 关联的 PlanningPolicy 标识
        approved_by: 审批人
        version: 版本号
        created_at: 创建时间
    """
    id: str
    name: str
    objective_profile: dict | None = None
    opportunity_threshold: float = 0.0
    required_policy_id: str = ""
    approved_by: str = ""
    version: int = 1
    created_at: datetime | None = None

    def __post_init__(self):
        valid_names = ("baseline", "efficiency_first", "value_first", "stability_first", "balanced", "manager_adjusted")
        if self.name not in valid_names:
            raise ValueError(f"name 必须是 {valid_names} 之一, 实际 {self.name!r}")
        if self.opportunity_threshold < 0.0 or self.opportunity_threshold > 1.0:
            raise ValueError(f"opportunity_threshold 必须在 [0, 1], 实际 {self.opportunity_threshold}")
