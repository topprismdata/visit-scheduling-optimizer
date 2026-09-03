# SVDE 世界模型通用元模型规范 v1.0 (General Metamodel Specification)
**Document ID:** SVDE-WORLD-MODEL-METAMODEL-SPEC-v1.0  
**Date:** 2026-08-24  
**层级定位:** L1: 通用元模型层 (General Metamodel Layer)  
**前置基础:** `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` (L0)  
**设计原则:** 
1. **领域无关性 (Domain-Agnostic)**: 严禁出现特定行业词汇；
2. **严格正交与闭合**: 消除概念重叠，所有上层 L2/L3/L6 概念必须在此元模型中找到唯一合法特化根源。

---

## 1. 通用元模型顶层元类型体系 (Core Meta-Type Taxonomy)

L1 通用元模型由 **8 个基础元类型 (Foundational Meta-Types)** 与 **3 个衍生操作元类型 (Derived Operational Meta-Types)** 严格构成：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 L1 通用元模型拓扑结构                                  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【基础元类型 (Foundational)】                                                          │
│  1. MetaEntity (实体)        ── 物理/逻辑存在的主体 (Agent / Target / Facility / Org)  │
│  2. MetaRelation (关系)      ── 实体间的定向语义拓扑 (AssignedTo / SuppliedBy / Owns)  │
│  3. MetaPolicy (政策)        ── 企业治理规则 (应该怎样，含版本与生效期)                │
│  4. MetaDemand (需求)        ── 触发服务诉求的业务意图 (含履约等级 REQUIRED / OPTIONAL) │
│  5. MetaCommitment (承诺)    ── 对外锁定的刚性约定 (FREE / DAY_LOCKED / SEQUENCE_LOCKED)│
│  6. MetaAction (动作)        ── Agent 执行的具体作业任务原子 (维修 / 盘点 / 谈判)       │
│  7. MetaEvent (事件)         ── 时空状态改变事实 (打卡进出 / 缺货 / 状态转移事件)      │
│  8. MetaObservation (观测)   ── 客观感知原始数据 (GPS打点 / 拍照 / 计量读数)           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【衍生操作元类型 (Derived & Operational)】                                             │
│  9. MetaDerivedEstimate      ── 算法对未知量的显式推断 (质心 / 预测通行时间 / 期望工时) │
│ 10. MetaPlan                 ── 运筹引擎输出的决策方案 (CandidatePlan / DailyRoute)    │
│ 11. MetaScenario             ── 反事实推演分支沙箱 (What-if Simulation Branch)         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 基础元类型形式化规范 (Formal Specifications)

### 2.1 实体元类型 (`MetaEntity`)
- **定义**: 业务世界中具备全局唯一标识（URI）与独立生命周期的主体。
- **核心元属性**:
  - `entity_id: URI` (全局唯一标识)
  - `spatial_extent: Optional[MetaSpatialGeometry]` (点、线、面空间坐标)
  - `temporal_extent: BitemporalPeriod` (Valid Time 业务生效期 vs Transaction Time 记录时间)
  - `dynamic_attributes: Dict[str, Any]` (扩展动态属性)
- **通用特化子类 (MetaEntity Subtypes)**:
  - `AgentEntity`: 具备执行能力与工时约束的行动主体（如员工、车辆）；
  - `TargetEntity`: 被服务的客户/站点主体（如门店、患者、设备）；
  - `FacilityEntity`: 物理节点与物流基地（如仓库、办事处、充电站）；
  - `HierarchicalOrgEntity`: 树状或网格状组织层级主体（如连锁总部、大区、片区）。

---

### 2.2 关系元类型 (`MetaRelation`)
- **定义**: 连接实体间的有向语义关系。
- **核心元属性**:
  - `source_entity_ref: URI`
  - `target_entity_ref: URI`
  - `relation_type: str` (如 `ASSIGNED_TO`, `SUPPLIED_BY`, `AGGREGATES_BRANCHES`, `PRECEDES`)
  - `cardinality: str` (`ONE_TO_ONE`, `ONE_TO_MANY`, `MANY_TO_MANY`)
  - `bitemporal: BitemporalPeriod`

---

### 2.3 政策元类型 (`MetaPolicy`)
- **定义**: 企业管理层制定的规范性约束，表达“应该怎样”，必须具备版本号与审批来源。
- **核心元属性**:
  - `policy_id: URI`
  - `policy_version: str` (语义化版本，如 `v2.0`)
  - `target_scope_selector: Dict[str, Any]` (政策适用的实体选择器)
  - `rule_spec: Dict[str, Any]` (形式化规则参数)
  - `enforcement_level: str` (`HARD_INVIOLABLE` / `SOFT_PENALIZED`)
  - `authority_evidence_ref: str` (批准人或权威制度出处)
  - `bitemporal: BitemporalPeriod`

---

### 2.4 需求元类型 (`MetaDemand`)
- **定义**: 业务世界产生的服务请求或任务意图。
- **核心元属性**:
  - `demand_id: URI`
  - `target_entity_ref: URI`
  - `urgency_level: str` (`REQUIRED` 强履约 / `COMMITTED` 承诺 / `OPTIONAL` 弹性)
  - `required_frequency_per_cycle: int`
  - `cadence_policy_ref: str`

---

### 2.5 承诺元类型 (`MetaCommitment`)
- **定义**: 已经对外确认的刚性约定，锁定后续重排边界。
- **核心元属性**:
  - `commitment_id: URI`
  - `demand_ref: URI`
  - `assigned_agent_ref: URI`
  - `locked_time_slot: str` (如特定日期或时段)
  - `lock_level: str` (统一标准命名: `FREE` / `RESOURCE_LOCKED` / `DAY_LOCKED` / `SEQUENCE_LOCKED` / `COMPLETELY_LOCKED`)
  - `confirmed_by: str`
  - `confirmed_at: datetime.datetime`

---

### 2.6 动作与事件元类型 (`MetaAction` vs `MetaEvent`)
- **严格边界**:
  - `MetaAction`: Agent 在现场执行的**离散作业任务原子**（无独立物理时间戳，作为事件的构成部分）；
  - `MetaEvent`: 在物理世界中发生并被传感器/打卡系统捕获的**时空状态改变事实**。
- **`MetaAction` 属性**:
  - `action_type: str` (如 `INSPECTION`, `NEGOTIATION`, `REMEDY`, `RESTOCK`)
  - `standard_duration_min: float`
  - `is_mandatory: bool`
- **`MetaEvent` 属性**:
  - `event_id: URI`
  - `event_type: str` (如 `CHECK_IN`, `CHECK_OUT`, `OOS_ALERT`, `MISSED_FLAG`)
  - `agent_ref: URI`
  - `target_ref: URI`
  - `timestamp: datetime.datetime`
  - `geo_point: Optional[GeoCoordinate]`
  - `contained_actions: List[MetaAction]`
  - `raw_payload: Dict[str, Any]`

---

### 2.7 观测与派生推断元类型 (`MetaObservation` vs `MetaDerivedEstimate`)
- **严格边界**:
  - `MetaObservation`: 现场采集的原始数据；
  - `MetaDerivedEstimate`: 算法推断的估计值，**必须显式标注推断算法与置信度，严禁冒充物理实体**。
- **`MetaObservation` 特化类型**:
  - `ComplianceObservation`: 合同履约度量（如目标数、实际数、达成率）；
  - `DurationObservation`: 现场作业与路程时间观测；
  - `SpatialObservation`: GPS 轨迹打点。
- **`MetaDerivedEstimate` 属性**:
  - `estimate_id: URI`
  - `target_attribute: str`
  - `inferred_value: Any`
  - `confidence_score: float` (0.0 ~ 1.0)
  - `derivation_model: str` (如 `Geometric_Centroid_v1`, `Historical_Mean_v2`)
  - `source_observation_refs: List[URI]`

---

### 2.8 规划与决策产物元类型 (`MetaPlan`)
- **定义**: 运筹引擎输出或人工审批的行动方案。
- **核心属性**:
  - `plan_id: URI`
  - `plan_version: str`
  - `agent_ref: URI`
  - `scheduled_routes: List[Dict[str, Any]]`
  - `audit_report_ref: Optional[URI]`
  - `approval_status: str` (`PENDING_APPROVAL` / `APPROVED_FOR_EXECUTION`)

---

### 2.9 反事实推演情景元类型 (`MetaScenario`)
- **定义**: 用于 What-if 评估的分支沙箱。
- **核心属性**:
  - `scenario_id: URI`
  - `base_snapshot_ref: URI`
  - `perturbation_events: List[MetaEvent]`
  - `branched_at: datetime.datetime`
  - `rollout_result_metrics: Dict[str, float]`
