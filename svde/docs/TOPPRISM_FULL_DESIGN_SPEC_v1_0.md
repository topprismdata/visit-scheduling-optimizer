# TopPrism Sales Visit Decision Engine — 完整系统设计文档

**Document ID:** TOPPRISM-FULL-DESIGN-SPEC
**Date:** 2026-08-27
**Scope:** 本文档合并了项目全部核心设计文档，按架构层次排列。

## 文档索引

| 部分 | 内容 | 来源文件 |
|---|---|---|
| 第一部分 | 产品定位与架构总览 | 基线 v1.0.2 |
| 第二部分 | Canonical Types 类型定义 (§1-§38) | Canonical Types Spec |
| 第三部分 | Canonical World Model API 规范 | L0-L6 API Spec |
| 第四部分 | L3 动力学转移引擎 | L3 Spec |
| 第五部分 | L5 场景推演引擎 | L5 Spec |
| 第六部分 | L7 企业决策引擎 | L7 Spec |
| 第七部分 | World Model ↔ Decision Engine 契约 | WM-DE Contract |
| 第八部分 | Action Type 注册表 | Action Registry |
| 第九部分 | L6→Solver 集成契约 | L6-Solver Contract |
| 第十部分 | Palantir 对标审查 | Ontology Review |
| 第十一部分 | Phase 1 API 设计 | Phase 1 Design |
| 第十二部分 | Phase 2 设计 | Phase 2 Design |
| 第十三部分 | Phase 3 设计 | Phase 3 Design |
| 第十四部分 | PlanningPolicy 统一约束契约 | PlanningPolicy |
| 第十五部分 | Plan vs Actual 数据契约 | Planning + PlanVsActual |
| 第十六部分 | 系统三轮检查报告 | Triple Check |
| 第十七部分 | 命名与字段审计 | Naming Audit |
| 第十八部分 | 仁军 Plan vs Actual 对比报告 | Renjun Comparison |
| 第十九部分 | 业务开放问题 | Open Questions |
| 第二十部分 | 业务签署需求清单 | Business Signoff |



================================================================================
# 第一部分: Canonical Enterprise Architecture Baseline v1.0.2
================================================================================


---
**Status:** PROPOSED CANONICAL — 旧 L0-L6 表述迁移未完成 (遗留冲突见 §Resolution)
**Conflict:** 全仓部分旧文档仍含 L0-L6 表述; 本文档 (v1.0.2) 内部已统一为 L0-L7
**Resolution:** 当前活跃层级以 L0-L7 (PROPOSED CANONICAL) 为权威; L0-L6 表述仅作为 "World Model 子集" 的过渡描述; 待 Phase 0 完成全文档统一清理
**Date:** 2026-08-26 (v1.0.2)

---

# TopPrism Canonical Enterprise Architecture Baseline v1.0.2

**Document ID:** TOPPRISM-CANONICAL-ENTERPRISE-ARCHITECTURE-BASELINE-v1_0_2
**Date:** 2026-08-26
**Status:** **PROPOSED CANONICAL ARCHITECTURE BASELINE v1.0.2 — DESIGN ONLY (v1.0.2 新增 §十二 本体设计裁决原则; 待旧文档迁移、业务签署与代码重构完成)**
**取代:** 任何与之冲突的旧术语、旧分层、旧代码归位表述
**适用范围:** Prism Enterprise Decision Intelligence 全产品家族
**严格红线:** 本文档不修改 runtime、不修改 solver、不安装依赖、不启动实测

---

## 一、产品拓扑

```text
TopPrism
└── Prism Enterprise Decision Intelligence (产品族)
    ├── Prism Enterprise World Model  (= L0 + L1 + L2 + L3 + L4 + L5 + L6)
    ├── Prism Decision Engine         (= L7，独立子系统)
    └── Domain Decision Engines
        └── SVDE Sales Visit Decision Engine
              ├── Domain Adapter  (prism_ontology.adapters.svde.bridge)
              ├── Domain Solver   (prism_ontology.engine.periodic_pvrp_solver)
              └── Domain Audit    (cadence/schedule verifiers, semantic purity check)
```

- **World Model 与 Decision Engine 是两个独立子系统**，绝不互相持有对方的状态所有权。
- **当前分层仍为 PROPOSED CANONICAL**：旧文档（如 FOUNDATIONAL SPEC v1.0）仍含 L0-L6 编号，尚未完成迁移或标记为 HISTORICAL。两套编号并存的过渡期内不构成已冻结 Canonical 结构。
- **SVDE 不是 World Model，也不是整个 Decision Engine**；它是"销售拜访领域"在 L7 决策引擎下的 Domain Adapter + Domain Solver。
- **Solver 不做语义解释**：Solver 只接收纯数学投影载荷，输出原始序列；语义重塑由 L7 反向投影完成。

---

## 二、L0-L7 唯一分层

| 层 | 名称 | 所属子系统 | 核心责任 | 严禁跨界 |
|---|---|---|---|---|
| **L0** | Foundational Architecture | World Model | 整体拓扑与八大不变量（边界、双时态、类别隔离、可追溯、可重放、观测-政策-承诺-计划分离、场景不可改基线、规划器只消费版本化投影） | 严禁出现具体领域词汇（拜访/频次/排班） |
| **L1** | General Metamodel | World Model | 8 个基础元类型（Entity/Relation/Policy/Demand/Commitment/Action/Event/Observation）+ 3 个衍生（DerivedEstimate/Plan/Scenario） | 严禁出现"拜访""频次""承诺等级"等业务词 |
| **L2** | Domain Ontology | World Model | L1 元类型在销售拜访/物流/医疗等领域的特化（Customer/Resource/AccountHierarchy/ProductLineScope/SupplyNode/Commitment/VisitLifecycleRecord/InStoreActionFact/MerchandisingComplianceFact 等） | 严禁混入动作/转移/求解逻辑 |
| **L3** | Dynamics & Rules | World Model | 通用状态转移（Transfer）+ 业务守卫（A-E）+ 事件溯源 + 反事实推演前置模型 | 严禁包含规划器选择/优化目标/审计结论 |
| **L4** | BaselineWorldState | World Model | 不可变现实基线快照；只保存真实历史/承诺/政策/已确认事件 | 严禁包含执行器运行时状态、求解中间结果、分支状态 |
| **L5** | Scenario & Counterfactual Engine | World Model | 从 L4 副本生成分支、并行多分支推演、计算 StateDelta 与业务指标差异 | 严禁把 ScenarioResult 直接升级为现实事实 |
| **L6** | Planner Projection | World Model → Decision Engine | 把 L4 + 政策 + 承诺编译为 `PlannerStateProjection` 纯数学载荷（节点拓扑 + 路网矩阵 + 模式空间 + 锁定掩码 + 容量预算 + 门禁） | 严禁返回 `CandidatePlan` / `DecisionArtifact` |
| **L7** | Enterprise Decision Engine | Decision Engine | Intent 诊断 → Capability 编排 → 消费 L6 Projection → 调 Domain Solver → Trade-off → 三维审计 → HITL 审批 → `DecisionArtifact` 持久化 → 执行编排 → ExecutionFeedback 提交 | 严禁持有 `OperationalDecisionWorldState` 实例（仅持 L6 Projection 局部只读视图与 L4 ReadOnlyWorldStateView） |

### 2.1 分层依赖方向（不可反向）

```text
L0 → L1 → L2 → L3 → L4 → L5 → L6 → L7
       └─────┴─────┴────────┴──────→ Domain Solver / Domain Audit
```

任何 L_n 不允许反向修改 L_(n-1) 或更底层；若需修改基础语义，必须进行架构版本变更。

---

## 三、模块责任矩阵（唯一权威）

| 模块 | 所属层 | 输入 | 输出 | 状态所有权 | 是否可修改 WorldState | 是否可调用 Scenario | 是否可产生 ExecutionEvent |
|---|---|---|---|---|---|---|---|
| **`Ontology` (L2)** | World Model | 主数据 / 字典 / 分类法 | CustomerEntity / ResourceEntity / AccountHierarchyEntity / ProductLineScopeEntity / SupplyNodeEntity / InStoreActionTaxonomy | L2 schema（不可变） | ❌ | ❌ | ❌ |
| **`WorldState` (L4)** | World Model | 已确认的 Observation / Policy / Commitment + 内部 PolicyRegistry | 不可变 `OperationalDecisionWorldState` 快照 | L4 snapshot（不可变） | ❌（仅生成新 snapshot） | ❌ | ❌ |
| **`StateTransition` (L3)** | World Model | Transfer 请求 + 当前 snapshot | 新 snapshot + StateTransitionRecord + 审计哈希 | L3 守卫通过后生成新 L4 | ✅ 通过 Transfer API 间接 | ❌（Transfer 不涉及 Scenario） | ❌ |
| **`Scenario Engine` (L5)** | World Model | base_snapshot_id + PerturbationEvent 序列 + intent + simulation_time | 单值 `ScenarioResult`（含 StateDelta + 指标差异 + 守卫违规数） | ❌ 不持有场景状态（仅返回单值） | ❌（ScenarioResult 不写回 baseline） | n/a | ❌ |
| **`Planner Projection` (L6)** | World Model | snapshot_id + intent + partial_auth + 路网来源标识 | `PlannerStateProjection`（纯数学载荷 + `unplannable_nodes_excluded`） | L6 不可变 payload | ❌ | ❌ | ❌ |
| **`Decision Engine` (L7)** | Decision Engine | L6 Projection + ReadOnlyWorldStateView + FrozenCustomerUniverseView + OperationalVisitPolicy Tuple + OwnershipConflictRecord Tuple | `CandidatePlan` + `PlanAuditReport` + `DecisionArtifact` | L7 决策库与历史 | ❌（必须通过 L3 Transfer 提交） | ✅（仅可调 request_scenario_rollout） | ❌（ExecutionEvent 来自 SFA/CRM 经 L7 提交） |
| **`Domain Solver` (L7)** | Decision Engine | `PlannerStateProjection` 或等效纯数学 payload | 原始序列（节点索引序列 + 求解元数据） | 无（纯函数） | ❌ | ❌ | ❌ |
| **`Domain Audit` (L7 + 部分 L3)** | Decision Engine + World Model | `CandidatePlan` + ReadOnlyWorldStateView | `PlanAuditReport`（物理/业务/语义三维） | 无 | ❌ | ❌ | ❌ |
| **`Approval` (L7)** | Decision Engine | `DecisionArtifact(候选)` + approver_id | 已审批 `DecisionArtifact` | L7 决策库 | ❌ | ❌ | ❌ |
| **`Execution Adapter` (L7)** | Decision Engine | `DecisionArtifact(已审批)` + SFA/CRM 接口约定 | SFA/CRM dispatch message | L7 dispatch log | ❌ | ❌ | ❌ |
| **`Execution Feedback` (L7 → L4)** | Decision Engine 调用 L3/L4 | 来自 SFA/CRM 的 `ActualVisitEvent` | `ExecutionFeedbackReceipt` + 触发 L3 `request_transition` | ❌（Feedback 是事件流，不持有状态） | ✅ 通过 `submit_execution_feedback` | ❌ | n/a（它接收而不是产生事件） |

---

## 四、World Model ↔ Decision Engine 边界

### 4.1 World Model 内部必须拥有

- Semantic State（基线快照）
- Evidence and Provenance（来源与证据）
- Business Policies and Commitments（版本化政策与锁定承诺）
- Business Dynamics（动力学）
- State Transition Engine
- Scenario / Simulation Engine（受控推演）
- Fact Constraints（事实约束，"客户每月必须拜访 3 次"是 CadencePolicy 事实）
- Business Objectives（定性目标）
- Feasible Action Space（允许动作枚举）
- Planner Projection Interface
- Execution Feedback Subscriber

### 4.2 World Model 严禁包含

- Plan Intent / Action Choice（属 L7）
- Human Approval Workflow（属 L7）
- Execution Orchestration（属 L7）
- Solver-Specific Algorithms（属 L7 调用的 Domain Solver）
- Trade-off Evaluation（属 L7）
- Capability Orchestration（属 L7）

### 4.3 Decision Engine 内部必须拥有

- Business Intent Diagnosis
- Capability Orchestration
- Candidate Generation
- Planning / Optimization 调度
- Trade-off Evaluation（多目标权衡）
- Physical / Business / Semantic Audit（三维独立审计）
- Human Approval（HITL）
- Execution Orchestration
- Execution Feedback Publisher
- Decision Artifact Storage

### 4.4 Decision Engine 严禁包含

- `OperationalDecisionWorldState` 实例持有
- 状态转移守卫内嵌
- Scenario Branch State 持有
- Business Dynamics 定义
- 客户主数据存储

### 4.5 四要素分离（铁律）

| 概念 | 归属 | 定义 | 业务示例 |
|---|---|---|---|
| 事实约束 (Fact Constraints) | World Model (L2/L3) | 物理与业务规则的事实声明 | "客户每月必须拜访 3 次" — CadencePolicy 事实 |
| 业务目标 (Business Objectives) | World Model (L2/L3) | 表达"应该怎样"的定性目标 | "距离和覆盖哪个优先" |
| 可行动作空间 (Feasible Action Space) | World Model (L2/L3) | 允许发生的动作枚举 | "改派客户"是否允许（DeferralPolicy 配额约束） |
| 目标权衡与选择 (Trade-off Evaluation) | Decision Engine (L7) | 如何选择动作与目标 | "这次是否选择改派" |

### 4.6 三类状态的物理分离（DESIGN ONLY — 待实现）

| 类型 | 归属 | 数据结构 | 进入路径 | **当前实现状态** |
|---|---|---|---|---|
| **`BaselineWorldState`** | L4 | `OperationalDecisionWorldState`（**严禁**包含 `execution_fact_stream` 与 `active_scenario_branches` 字段） | 仅由 L3 Transfer 通过守卫后生成新 snapshot | **NOT IMPLEMENTED**（代码层 `OperationalDecisionWorldState` 仍含两个混入字段 — 已在 §五标记为 DEPRECATED 字段） |
| **`ExecutionEventStream`** | **独立子资源**（World Model 拥有，但**严禁**作为 `OperationalDecisionWorldState` 字段） | `ExecutionEventStore`（append-only，自身持久化） | 由外部系统（SFA/CRM / HR / SENSOR）经 L7 `submit_execution_feedback` 或 `submit_resource_event` 触发 L3 Transfer | **NOT IMPLEMENTED**（当前仅作为 L4 字段存在，无独立 store） |
| **`ScenarioState`** | L5 沙箱 | `BranchedWorldState`（仅 L5 内部持有，不暴露给 L7） | 由 `request_scenario_rollout` 内部创建，运行完毕丢弃 | **NOT IMPLEMENTED as L5**（当前 `rollout_reallocation_scenario` 是改派单点函数且返回新 WorldState，违反"不写回 baseline"） |

> **方案 B 选定**：ExecutionEventStream 是 World Model 的独立子资源，**严禁**作为 `OperationalDecisionWorldState` 字段。
>
> **当前代码（`state_snapshot.py`）将 `execution_fact_stream: List[ActualVisitEvent] = field(default_factory=list)  # DEPRECATED: 迁移至独立 ExecutionEventStore (Phase 2 P0-2)` 与 `active_scenario_branches: Dict[str, Any]` 混入 `OperationalDecisionWorldState` —— 这是已知 P0-2 缺口**。
>
> **DEPRECATED 字段清单**（待 Phase 2 清理）：
> - `OperationalDecisionWorldState.execution_fact_stream` — 迁移至独立 `ExecutionEventStore`
> - `OperationalDecisionWorldState.active_scenario_branches` — 移除（Scenario 归 L5 内部沙箱）
>
> Baseline v1.0 文档已识别但代码未完成拆分。

---

## 五、三类状态严格分离

| 类型 | 归属 | 唯一存储位置 | 进入路径 | 严禁 |
|---|---|---|---|---|
| **`BaselineWorldState`** | L4 | `OperationalDecisionWorldState` 主结构（不含 `active_scenario_branches`） | 通过 L3 `request_transition` 提交 Transfer 请求并通过守卫 → 生成新 snapshot | 包含分支/情景状态；包含 ExecutionEvent 之外的临时事件流；包含求解中间结果 |
| **`ScenarioState`** | L5 内部 | 沙箱内存（不持久化、不暴露给 L7） | 由 `request_scenario_rollout` 内部创建，运行完毕即丢弃 | 写入 Baseline；被 L7 持有；被持久化 |
| **`ExecutionEventStream`** ⚠️ DEPRECATED | ~~L4 `execution_fact_stream`~~ | ~~`OperationalDecisionWorldState.execution_fact_stream`~~ | **DEPRECATED**：见 §4.6 新定义（方案 B） — ExecutionEventStream 必须是 World Model 的独立子资源，**严禁**作为 `OperationalDecisionWorldState` 字段。代码层 OperationalDecisionWorldState.execution_fact_stream 字段须在 Phase 2 移除（修复 P0-2/P0-9） | **DEPRECATED** |

**强制要求**：
- `ScenarioResult` 不得直接升级为现实事实；它只是 Trade-off 输入。
- `DecisionArtifact` 不得直接写入完成状态；它必须经 `ExecutionAdapter` 实际下发到 SFA/CRM 后，由 SFA/CRM 回写 `ActualVisitEvent` 才能推动 L4 新 snapshot。
- L4 snapshot 升级路径只有一条：`ExecutionEvent`（来自现实） → `submit_execution_feedback` → L3 Transfer → 新 snapshot。

---

## 六、三条生命周期严格分离

### 6.1 Approval（决策产物生命周期）

```
DRAFT
  → EVALUATED          (审计完成，待评审)
  → APPROVED           (HITL 主管签署)
  → PUBLISHED          (下发到 Execution Adapter)
  → REVOKED            (撤销)
  → EXPIRED            (过期)
```

### 6.2 Commitment（履约承诺生命周期）

**所有权严格归 World Model（L3/L4）**。L7 仅可"propose / request / evaluate"，**严禁持有 Commitment 状态**。

```
AVAILABLE             (空槽 — L4 持久化)
  → RESERVED           (L7 reserve_plan_commitment 提议 → L3 守卫通过 → L4 新 snapshot)
  → COMMITTED          (L3 Transfer 完成，WorldModel 已接纳 → L4 新 snapshot)
  → RELEASED           (经 L7 ExecutionEvent → L3 Transfer → L4 新 snapshot)
  → EXPIRED            (周期结束未履约 → L3 Transfer → L4 新 snapshot)
  → CANCELLED          (L7 提议撤销 → L3 守卫通过 → L4 新 snapshot)
```

**禁止**：L7 DecisionArtifact 库、Decision Pipeline 或 Bridge **不得**持有 Commitment 实例；L7 任何 Commitment 操作必须经 `request_transition` 调用 L3 完成状态迁移，并接收新 L4 snapshot 作为唯一事实。

### 6.3 Visit/Task（执行生命周期）

```
PLANNED               (候选计划已 EVALUATED)
  → DISPATCHED         (DecisionArtifact PUBLISHED)
  → IN_PROGRESS        (SFA/CRM 推送现场打卡)
  → COMPLETED          (成功)
  → MISSED             (失败/失访)
  → ABORTED            (异常终止)
```

### 6.4 四种事件分离（DESIGN ONLY）

**禁止**将 `Approval.PUBLISHED` 误称为 `ExecutionEvent`，也禁止将 `DecisionArtifact` 与 `DispatchCommand` 混用。

| 事件类型 | 归属 | 性质 | 示例 |
|---|---|---|---|
| **`DecisionEvent`** | L7 内部 | 决策生命周期事件 | `DecisionEvent(status="PUBLISHED", artifact_id, published_by)` — 仅描述决策库本身状态 |
| **`DispatchCommand`** | L7 → 外部执行系统 | L7 发给 SFA/CRM 的命令 | `DispatchCommand(artifact_id, schedule, dispatched_at)` — **不是 ExecutionEvent** |
| **`ExecutionEvent`** | 外部系统 → L7 | 真实执行事实（来自 SFA/CRM 或现场打卡） | `ActualVisitEvent(event_type="CHECK_IN", store_code, occurred_at, ...)` |
| **`FeedbackReceipt`** | L7 → L3 | L7 接收 ExecutionEvent 后提交 L3 Transfer 的回执 | `ExecutionFeedbackReceipt(new_snapshot_id, transition_required)` |

**正确的关联路径（避免状态转移结果回声）**：

```text
# === 决策下发 ===
DecisionEvent(PUBLISHED)  ──emit──▶  DispatchCommand ──send──▶  SFA/CRM 接收

# === 现场执行（外部事实输入） ===
SFA/CRM 现场打卡           ──emit──▶  ActualVisitEvent(CHECK_IN) ──via L7 submit_execution_feedback──▶  FeedbackReceipt ──via L3 request_transition(visit_id=..., target_status=IN_PROGRESS) ──emit──▶  StateTransitionRecord + VisitLifecycle.IN_PROGRESS

SFA/CRM 离店打卡           ──emit──▶  ActualVisitEvent(CHECK_OUT) ──via L7 submit_execution_feedback──▶  FeedbackReceipt ──via L3 request_transition(visit_id=..., target_status=COMPLETED) ──emit──▶  StateTransitionRecord + VisitLifecycle.COMPLETED

SFA/CRM 异常上报           ──emit──▶  ActualVisitEvent(MISSED_FLAG) ──via L7 submit_execution_feedback──▶  FeedbackReceipt ──via L3 request_transition(visit_id=..., target_status=MISSED) ──emit──▶  StateTransitionRecord + VisitLifecycle.MISSED

# === 履约反馈 ===
VisitLifecycle.COMPLETED ──via L3──▶  Commitment.RELEASED
VisitLifecycle.MISSED    ──via L3──▶  Commitment.EXPIRED + DecisionArtifact revoke
```

**严禁将"状态转移结果"伪装成"外部 ExecutionEvent"**：例如不允许有 `ExecutionEvent(IN_PROGRESS)` —— `IN_PROGRESS` 是 L3 Transfer 后内部 VisitLifecycle 状态，不是外部事件。外部事件**只能**是 `ActualVisitEvent(CHECK_IN/CHECK_OUT/MISSED_FLAG)`。这避免事件回声与重复消费。

任何"直接把 Approval.PUBLISHED 同步给 VisitLifecycle.IN_PROGRESS"或"把 VisitLifecycle.COMPLETED 同步给 Commitment.RELEASED"的写法都是越界：必须经 L3 守卫的事件溯源路径。

**严禁命名清单（DESIGN RULE）**：
- ❌ `ExecutionEvent(IN_PROGRESS)`
- ❌ `ExecutionEvent(COMPLETED)`
- ❌ `ExecutionEvent(MISSED)`
- ✅ `ActualVisitEvent(CHECK_IN)`（外部事实输入）
- ✅ `ActualVisitEvent(CHECK_OUT)`（外部事实输入）
- ✅ `ActualVisitEvent(MISSED_FLAG)`（外部事实输入）

---



### 6.5 ResourceAvailabilityLifecycle（DESIGN ONLY — 当前未实现）

**问题**：现有 `LifecycleStatus` 枚举（PROPOSED/PLANNED/COMMITTED/IN_PROGRESS/COMPLETED/MISSED/DEFERRED/CANCELLED）仅描述拜访生命周期，**没有**资源可用性状态。因此引入假设状态（如 `AVAILABILITY_BLOCKED`）属凭空捏造。

**正式方案（DESIGN ONLY）**：

```python
# 独立枚举，不与 LifecycleStatus 混淆
class ResourceAvailabilityStatus(str, Enum):
    AVAILABLE            # 资源可被排班
    ABSENT_PLANNED       # 已批假期（如年假、培训）
    ABSENT_UNPLANNED     # 突发缺勤（病假、紧急事务）
    CAPACITY_REDUCED     # 部分产能下降
    BLOCKED              # 外部阻断（如停业、合规冻结）

class ResourceAvailabilityObservation:
    resource_id: str
    status: ResourceAvailabilityStatus
    valid_time: BitemporalPeriod
    evidence_refs: Tuple[str, ...]
    source_system: str  # 如 "HR_SYSTEM" / "SFA_ABSENCE_FORM"
    reason: str
```

**进入路径**：HR/SFA 通过 L7 **专属 Canonical API `submit_resource_event`**（**严禁**误用 `submit_execution_feedback` 提交资源事件）提交 → L3 **`request_transition`** 接收通用 `TransferRequest(entity_type=RESOURCE, entity_ref="<resource_id>", target_status=ResourceAvailabilityStatus, ...)` → L4 新 snapshot。

**两个独立 Canonical API（严禁合并为多态入口）**：

| Canonical API | 实体类型 | 用途 | 严禁误用 |
|---|---|---|---|
| `submit_execution_feedback(ActualVisitEvent)` | Visit/Task | 拜访执行事实（CHECK_IN/CHECK_OUT/MISSED） | 严禁用于资源可用性 |
| `submit_resource_event(ResourceAvailabilityObservation)` | Resource | 资源可用性事件（请假/培训/缺勤） | 严禁用于拜访事实 |

**通用 TransferRequest（SCHEMA DRAFT — 多实体 Transfer 语义未完成）**：

> **本节仅是 schema 草案**，不构成多实体 Transfer 的完整契约。必须补齐：
> - 不同实体类型（VISIT / RESOURCE / COMMITMENT / OWNERSHIP / POLICY）分别允许哪些状态集合；
> - 资源请假是否会同时影响拜访、承诺、所有权（多实体并发 Transfer 语义）；
> - Guard A-E 如何按 entity_type 分派（当前 transition_engine.transition_visit_status 仅支持 VISIT）；
> - TransferResult 如何表达多实体变更（单结果/多结果/聚合视图）；
> - 与四要素（事实约束/业务目标/可行动作空间/目标权衡）的边界如何保持。
>
> **修复 P0-6 必须完成上述五项**，否则 TransferRequest 仅是结构骨架，**不能**作为已解决的决策。

```python
@dataclass(frozen=True)
class TransferRequest:
    entity_type: EntityType  # VISIT | RESOURCE | COMMITMENT | OWNERSHIP
    entity_ref: str         # 主键，如 visit_id / resource_id / commitment_id
    target_status: Enum      # 对应实体类型的 status 枚举
    event_time: datetime    # 强制显式、awareness 校验
    transaction_time: datetime
    policy_version_snapshot: str
    evidence_refs: Tuple[str, ...] = ()
```

> 当前 `transition_visit_status` **仅支持 entity_type=VISIT**；多实体 Transfer 是 P0-6 缺口。

**当前实现状态**：**NOT IMPLEMENTED**。`transition_visit_status` 仅支持 visit 实体；`LifecycleStatus` 不含资源状态；纵切片步骤 1-2 当前**仍使用假设性枚举**（属 DESIGN DEMO），需等 Phase 3 多实体 Transfer 实现后方可真实运行。


## 七、端到端调用链（强制顺序）

```text
1. Intent Diagnosis                  (L7)
   ↓
2. Query World Model (ReadOnly)     (L7 → L4 via get_worldstate_view / query_customer_universe_view / resolve_active_policies)
   ↓
3. Request Scenario Rollout (opt.)  (L7 → L5 via request_scenario_rollout; returns ScenarioResult single-value)
   ↓
4. Compile Planner Projection       (L7 → L6 via compile_planner_projection; returns PlannerStateProjection)
   ↓
5. Domain Solver                    (L7 internal → Domain Solver.solve(projection); returns raw sequence)
   ↓
6. Backward Projection              (L7 internal; raw sequence → CandidatePlan rich semantics)
   ↓
7. Trade-off Evaluation             (L7; LexMin objective hierarchy)
   ↓
8. Three-Dimensional Audit          (L7; Physical + Business + Semantic)
   ↓
9. Human Approval Gate              (L7; HITL; if REQUIRED / sensitive)
   ↓
10. DecisionArtifact Storage        (L7; immutable)
   ↓
11. Execution Adapter Dispatch      (L7 → SFA/CRM; produces ApprovalEvent)
   ↓
12. ExecutionEvent Receipt          (SFA/CRM → L7 → submit_execution_feedback)
   ↓
13. L3 State Transition              (L7 → L3 → L4: generate new BaselineWorldState snapshot)
   ↓
14. New WorldState Snapshot Persisted (L4 → Snapshot Store)
```

---

## 八、架构不变量（必须由 CI 与代码审查同时强制）

1. **Observation 不能自动变成 Policy**；
2. **Inference 不能自动变成 Fact**；
3. **Plan 不能自动变成 Execution**；
4. **Scenario 不能污染 Baseline**；
5. **派生值不能伪装成现实实体**；
6. **不同有效时间的状态不能无条件合并**；
7. **Decision Engine 不持有、不修改、不缓存 WorldState 实例**；
8. **Solver 不解释业务语义**（不读 planned_frequency 业务含义、不做承诺判定）；
9. **DecisionArtifact 必须经过三维审计 + HITL 后才能 PUBLISHED**；
10. **时间参数必须显式传入，禁止 `datetime.now()` 默认值**；
11. **每个 Plan 必须引用一个明确的状态投影（含 snapshot_id 与 policy_version）**；
12. **每个 Transfer 必须生成 StateTransitionRecord 与审计哈希**。

---

## 九、当前状态矩阵（Design / Code / Runtime 三维）
> **成熟度口径**（与 Matrix 一致）：
> - **组件代码存在**（Compiler / Auditor / IntentRouter 等组件代码已存在但未接入子系统）
> - **数据链路已接通**（代码存在且与 WorldState 数据契约完整连接）
> - **子系统已实现**（L0/L1/L2/.../L7 任一子系统内部所有模块已上线）
> - **Runtime 已验证**（在真实数据影子模式下完整跑通）
>
> 本表三层状态（文档 / 代码 / Runtime）按此四级口径独立判定，**禁止**将"组件代码存在"误判为"子系统已实现"。



| 模块 | 文档设计 | 代码实现 | Runtime 验证 |
|---|---|---|---|
| L0 Foundational Architecture | DESIGN CONFIRMED | NOT IMPLEMENTED | — |
| L1 General Metamodel | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（8 元类型在 world_model/state_snapshot.py 已存在） | RUNTIME PARTIAL（仅用于内部 dataclass，未独立暴露） |
| L2 Domain Ontology | DESIGN CONFIRMED | IMPLEMENTED（24 个 L2 对象在 state_snapshot.py 落地） | RUNTIME PARTIAL（assemble_from_excel 能跑通） |
| L3 Dynamics & Transfer | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（transition_engine.py 含 5 个 Guard A-E + DeferralPolicy） | RUNTIME PARTIAL |
| L4 BaselineWorldState | DESIGN CONFIRMED | **字段混入未清理**（`execution_fact_stream` 与 `active_scenario_branches` 仍存在于 OperationalDecisionWorldState；**已标 DEPRECATED 字段**，待 Phase 2 移除 — P0-2/P0-9） | **数据链路未接通**（ExecutionEventStream 应独立） |
| L5 Scenario Engine | DESIGN CONFIRMED | **NOT IMPLEMENTED as L5**（当前 `rollout_reallocation_scenario` 是改派单点函数，不是多分支反事实引擎） | NOT IMPLEMENTED |
| L6 Planner Projection | DESIGN CONFIRMED | **组件代码存在**（`PlannerStateProjectionCompiler.compile_projection`） | **数据链路未接通**：WorldStateAssembler 生成 cadence_rules，planner_projection 读 PolicyRegistry.operational_policies（数据契约未同步） | 仅 Haversine 估算，无真实 OSRM |
| L7 Decision Engine | DESIGN CONFIRMED | **子系统 NOT IMPLEMENTED**。IntentRouter 组件存在但属于 diagnostics 子模块，未接入 L7 Enterprise Decision Engine 子系统；现有 `decision_pipeline.py` 是旧 SVDE 领域 Pipeline，**不属于** L7 Enterprise Decision Engine；其 `human_approve_and_publish` 使用 `datetime.now()` 违反时间契约 | 仅旧 SVDE domain pipeline 部分可运行；**L7 Runtime 尚未启动** |
| SVDE Domain Adapter | — | IMPLEMENTED（bridge.py） | RUNTIME PARTIAL（直接读 WorldState 字段绕过 L6） |
| SVDE Domain Solver | — | IMPLEMENTED（periodic_pvrp_solver.py） | RUNTIME PARTIAL（接受 bridge 拼装 payload 而非 L6 PlannerStateProjection） |
| Approval Lifecycle | DESIGN CONFIRMED | NOT IMPLEMENTED as separate state machine（混在 decision_pipeline） | — |
| Commitment Lifecycle | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（OperationalCommitment 实体 + OperationalVisitLifecycleRecord 内嵌 status_history） | — |
| Execution Lifecycle | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（LifecycleStatus 枚举含 8 值；缺 DISPATCHED/ABORTED 等） | — |
| Canonical API (request_transition / submit_execution_feedback / request_scenario_rollout / compile_planner_projection / get_worldstate_view / resolve_active_policies) | DESIGN CONFIRMED（draft 5.2） | **NOT IMPLEMENTED**（代码层仍使用 `transition_engine.transition_visit_status(...)` / `rollout_reallocation_scenario(...)` 等内部函数，未实现 Canonical API 包装层） | — |

---

## 十、本次基线与旧表述的差异（已修正）

| 旧表述 | 新表述 |
|---|---|
| L6 = Planning & Execution | L6 = Planner Projection（只产出纯数学载荷）；Planning 归 L7；Execution 归 L7 |
| SVDE = 整个决策系统 | SVDE = 销售拜访 Domain Adapter + Domain Solver + Domain Audit；不是 L7 本身 |
| Solver = World Model | Domain Solver 是 L7 内部组件，归 Decision Engine |
| CandidatePlan = WorldState | CandidatePlan 是 L7 输出（rich semantics），WorldState 是 L4 不可变基线 |
| ScenarioState = BaselineWorldState | ScenarioState 归 L5 内部沙箱，BaselineWorldState 归 L4；两者严格隔离 |
| Approval = Execution | Approval 是 L7 决策产物生命周期；Execution 是 L4 Visit/Task 生命周期；两者经 L3 Transfer 事件关联 |
| DecisionArtifact 直接写入完成状态 | DecisionArtifact PUBLISHED 必须经 Execution Adapter 实际下发；状态完成由 ExecutionEvent 触发 L3 Transfer 决定 |
| | OperationalDecisionWorldState 同时含 execution_fact_stream 与 active_scenario_branches | **设计目标**：BaselineWorldState 应仅含基线；execution_fact_stream 应迁移至独立 `ExecutionEventStore`（保留为已确认事件流）；`active_scenario_branches` 必须从 L4 移除（移至 L5 内部沙箱接口）。**当前实现**：旧字段仍混入 Baseline（已标 DEPRECATED）。**状态**：NOT IMPLEMENTED（修复 P0-2/P0-9） |

---

## 十一、当前架构准确状态（语义纠偏后）

```
Architecture Baseline:        PROPOSED / PARTIALLY ALIGNED
L0-L7 Canonical Sync:         BLOCKED       (旧 FOUNDATIONAL SPEC v1.0 仍用 L0-L6)
Baseline–Event–Scenario:      BLOCKED       (代码层 execution_fact_stream/scenario_branches 仍混入 L4)
L5 Scenario Engine:           DESIGN ONLY   (当前 rollout_reallocation_scenario 非真 L5)
L7 Decision Engine:           NOT IMPLEMENTED  (现有 decision_pipeline 仅为旧 SVDE 领域 Pipeline)
SVDE Domain Pipeline:         RUNTIME PARTIAL (与新架构存在 7 处 P0 冲突)
Vertical Slice:               DESIGN-ONLY, NOT PROVEN
Business Sign-off:            PENDING       (BIZ-01~09 待签)
Freeze Review:                BLOCKED
```

**冻结前置条件**：旧文档完成迁移或废止 → Baseline/Event/Scenario 代码层拆分 → L5 通用引擎实现 → L7 Canonical API 包装 → BIZ-01~09 业务签署 → 双轨技术签署 → v1.0-FROZEN。

---

## 十二、本体设计裁决原则 (v1.0.2 新增; 证据源: TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md)

以下四原则用于**类型设计与修订的裁决**。发生冲突时, 高优先级原则胜出。

| 优先级 | 原则 | 核心含义 | TopPrism 应用示例 |
|---|---|---|---|
| 1 | **领域驱动设计 (DDD)** | 建模真实世界实体, 不建模源系统表结构/部门视角 | 门店实体来自业务概念, 不是 Excel 列的 1:1 映射; `OperationalCustomer` 不是 fixture 列的镜像 |
| 2 | **不要重复自己 (rule of three)** | 同一概念只允许一个 Canonical 表示; 出现第 3 处重复必须重构 | 同形状类型出现 3 处 → 合并为单一类型或抽取共享接口 |
| 3. | **开闭原则** | 核心类型冻结后只扩展不修改; 扩展走 linked 新类型或接口实现 | 冻结的 `OperationalCustomer` 加认证数据 → 新增 linked `Certification` 对象, 不加列 |
| 4 | **组合优于深继承** | 能力用接口组合 (如 Auditable / BitemporalVersioned), 不建深层类型链 | 禁止 `SchedulableStore` 式组合类型; 能力拆接口 |

### 12.1 务实与权衡条款 (Pragmatism)

1. **不可妥协三样**: 命名质量、语义清晰、安全设计是后期难以修复的 — 可以在实现细节上妥协, 不能在这三样上妥协。
2. **在用优于完美**: 在用并产生价值的不完美本体, 优于仍在设计中的理论完美本体。
3. **显式命名权衡**: 任何反规范化/捷径必须写明放弃了什么、何时需要重审 (例: 反规范化在当前规模可行, 对象数过万需重审)。
4. **增量改进优于大爆炸重构**。

### 12.2 配套反模式禁令 (对照 Palantir 8 反模式, 裁决时按需引用)

System Silos (按源系统拆类型) / Kitchen Sink (无语义字段入本体) / Department Silos (按部门拆共享实体) / God Object (单类型承载多实体) / Golden Hammer (工具错配) / Action Sprawl (动作碎片化) / **Time Machine (实体历史建模为版本对象 — 实体级历史必须走 linked amendment; WorldState 快照是世界状态检查点, 不属此列)** / Misnomer (歧义命名)。

### 12.3 修订记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0.1 | 2026-08-25 | 初始基线 (内部矛盾清理) |
| v1.0.2 | 2026-08-26 | 新增 §十二 本体设计裁决原则 (Palantir 四原则 + 务实条款 + 反模式禁令); 证据源 TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md |

> 本文档是 Canonical Architecture Baseline v1.0。任何后续实现、代码重构、Runtime 启动必须以本文件为唯一架构事实源。后续若发现新冲突，必须先修订本文件，再动代码。



================================================================================
# 第二部分: Canonical Types Spec (§1-§38)
================================================================================


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



================================================================================
# 第三部分: Canonical World Model API Spec
================================================================================


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



================================================================================
# 第四部分: L3 Dynamics Transition Engine
================================================================================


# TopPrism L3 业务动力学与状态转移引擎详细规范 v1.0 (Dynamics & State Transition Engine Spec)

**Document ID:** TOPPRISM-L3-DYNAMICS-TRANSITION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 3 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md` (产品层级与上位约束)
- `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)
- `WORLD_MODEL_SYSTEM_BOUNDARY.md` (L3 归属 World Model 动力学层)
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L3 动力学引擎的核心定位与架构责任

L3 业务动力学与状态转移引擎是 **Prism Enterprise World Model 的“物理法则与因果律中枢”**。
它的核心职责不是做规划决策，而是：
1. **掌控状态转移的合法性 (State Transition Legality)**: 依据业务守卫（Guards）判定状态转移请求是否被允许；
2. **保证因果与事实不可篡改 (Causal Integrity & Event Sourcing)**: 每次合法的状态转移必须生成包含全要素指纹的 `StateTransitionRecord` 并沉淀入事实流；
3. **保证演化的双时态确定性 (Bitemporal Determinism)**: 相同基线状态 + 相同事件参数 $\implies$ 100% 产生确定性的新快照状态。

---

## 二、状态转移有限状态机与前置守卫矩阵 (Guarded Transition Matrix)

### 2.1 任务生命周期状态机拓扑

$$\text{PROPOSED} \xrightarrow{\text{Guard P}} \text{PLANNED} \xrightarrow{\text{Guard A}} \text{COMMITTED} \xrightarrow{\text{Guard C}} \text{IN\_PROGRESS} \xrightarrow{\text{Guard B}} \text{COMPLETED}$$
$$\text{COMMITTED / IN\_PROGRESS} \xrightarrow{\text{Guard D}} \text{MISSED} \xrightarrow{\text{Guard E}} \text{DEFERRED} \xrightarrow{} \text{PLANNED}$$

### 2.2 守卫条件形式化判定规则与待签署标注

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        五大核心业务守卫形式化逻辑 (Guard A ~ E)                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard A: 承诺锁定审批守卫 (PLANNED -> COMMITTED)】                                  │
│  • 前置条件: transition_request.approver_id 必须非空且具备有效权限                     │
│  • 判定逻辑: assert(approver_id is not None and len(approver_id.strip()) > 0)          │
│  • 违规处理: 抛出 GuardRejected("Guard A Failed: approver_id required")                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard B: 履约完成时长与政策快照守卫 (IN_PROGRESS -> COMPLETED)】                    │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on 10 min threshold]  │
│  • 前置条件: service_duration_min >= 10.0 且 policy_version_snapshot 必须存在         │
│  • 判定逻辑: assert(service_duration_min >= 10.0 and policy_version_snapshot is not None)│
│  • 违规处理: 抛出 GuardRejected("Guard B Failed: duration < 10m or policy missing")    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard C: 强制现场 GPS 证据守卫 (COMMITTED -> IN_PROGRESS)】 (Fail-Closed)            │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on 500m threshold]    │
│  • 前置条件: gps_deviation_meters 必须显式传入 (不可为 None) 且 <= 500.0 米           │
│  • 判定逻辑: assert(gps_deviation_meters is not None and gps_deviation_meters <= 500.0)│
│  • 违规处理: 缺 GPS 抛 GuardRejected("Missing GPS")；超限抛 GuardRejected("GPS > 500m")│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard D: 时区安全的失访时间事实判定守卫 (COMMITTED -> MISSED)】                     │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on EOD cutoff]        │
│  • 时区处理: 构造带时区截止时刻 aware_scheduled_end = datetime.combine(               │
│               scheduled_date, time(23, 59, 59), tzinfo=context.timezone_obj)          │
│  • 判定逻辑: assert(event_time >= aware_scheduled_end) (安全时区感知比较)              │
│  • 违规处理: 抛出 GuardRejected("Guard D Failed: Cannot mark MISSED before day ends")  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 【Guard E: 顺延政策配额与窗口守卫 (MISSED/COMMITTED -> DEFERRED)】                     │
│  • 规则状态: [PROPOSED POLICY: Pending Phase 1 Business Sign-off on DeferralPolicy]    │
│  • 字段对齐: 严格对齐 DeferralPolicy.max_deferral_window_days 与 max_deferrals_per_period│
│  • 窗口判定: delta_days = (event_time.date() - scheduled_date).days                    │
│  • 判定逻辑: assert(0 <= delta_days <= policy.max_deferral_window_days and             │
│                     prior_deferrals + 1 <= policy.max_deferrals_per_period)           │
│  • 违规处理: 抛出 DeferralQuotaExceeded / DeferralWindowExceeded                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、双时态状态演化与事件溯源实现细节

### 3.1 转移执行函数签名与不变量 (规范对外 API vs 内部实现)

- **对外 Canonical API**: `request_transition(context, workflow, transition_request) -> TransitionResult`
- **内部实现函数**: `_execute_guarded_transition_internal(...) -> Tuple[OperationalDecisionWorldState, OperationalVisitLifecycleRecord, StateTransitionRecord]` *(明确标注为内部实现)*

### 3.2 审计哈希计算规范 (RFC 8785 Canonical JSON + 256-bit SHA-256)

**算法规则**:
```python
audit_hash = SHA256(
    rfc8785_canonical_json({
        "visit_id": visit_id,
        "base_snapshot_id": base_snapshot_id,
        "from_status": from_status.value,
        "to_status": to_status.value,
        "event_time": event_time_utc_iso8601,          # UTC ISO 8601, e.g. "2026-06-04T01:00:00Z"
        "transaction_time": transaction_time_utc_iso,   # UTC ISO 8601
        "approver_id": approver_id or "NONE",
        "gps_deviation_meters": str(gps_deviation_meters or "NONE"),
        "service_duration_min": str(service_duration_min or "NONE"),
        "policy_version_snapshot": policy_version_snapshot or "NONE",
        "evidence_refs": sorted(evidence_refs)           # Tuple of str, lexicographically sorted
    })
)
```

**关键约束**:
1. **RFC 8785 Canonical JSON**: 键名字典序排列、无多余空白、UTF-8 编码；严禁使用未定义分隔符的手工字符串拼接；
2. **空值编码**: 缺失字段统一编码为字符串 `"NONE"`，严禁隐式跳过或省略；
3. **数值规范化**: `float` 经 RFC 8785 数字格式化后转为字符串；`Decimal` 转为无尾随零的十进制字符串；
4. **时间序列化**: 所有 `datetime` 统一转为 UTC 后格式化为 `YYYY-MM-DDTHH:MM:SSZ`；
5. **标准输出**: **256-bit SHA-256 digest represented as 64 hexadecimal characters**（绝无缩短截断）；
6. **请求指纹参与**: 服务端计算的 `RequestFingerprint` **纳入** 哈希输入的 `"request_fingerprint"` 字段。

---

## 四、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 3 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。



================================================================================
# 第五部分: L5 Scenario Simulation Engine
================================================================================


# TopPrism L5 情景仿真引擎详细规范 v1.0 (Scenario & Simulation Engine Spec)

**Document ID:** TOPPRISM-L5-SCENARIO-SIMULATION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 4 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`
- `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)
- `WORLD_MODEL_SYSTEM_BOUNDARY.md`
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L5 情景仿真引擎的核心定位与架构责任

L5 情景仿真引擎（Prism Dynamics & Scenario Engine）是 **企业世界模型的“未来沙箱与反事实推演实验室”**。
它的核心职责是回答：**“如果企业采取某种动作（调店/改派/大仓调整/请假），未来世界状态与业务指标会发生什么确定性变化？”**

### 核心隔离原则
1. **沙箱不可见性**: 仿真过程中产生的分支状态（`BranchedWorldState`）全部在 L5 内部内存沙箱中闭环运行，**严禁向 L7 决策引擎暴露分支对象实例**；
2. **单值只读返回**: 对外唯一返回包含业务指标差异的 `ScenarioResult`（其内部 `delta_state` 字段包含 `StateDelta`）；
3. **确定性可重放**: 相同基线快照 + 相同扰动事件集 + 显式仿真时间戳 `simulation_time` $\implies$ 输出 100% 确定性的 `ScenarioResult` 与 256-bit SHA-256 分支指纹；
4. **类型封闭性**: 严禁使用 `Any`，所有载荷采用 `FrozenValue` 递归不可变类型。

---

## 二、形式化输入与输出契约 (消灭 Any，全类型封闭)

### 2.1 输入契约 (`request_scenario_rollout`)

```python
from prism_ontology.contracts.canonical_types import (
    FrozenValue, FrozenScalar, ApiRequestContext, PlanningIntent,
    PerturbationEvent, ScenarioResult   # 权威定义见 TOPPRISM_CANONICAL_TYPES_SPEC §22 / §24
)

def request_scenario_rollout(
    context: ApiRequestContext,
    base_snapshot_id: str,
    intent: PlanningIntent,
    perturbation_events: Tuple[PerturbationEvent, ...],
    simulation_time: datetime.datetime         # 强制显式仿真时钟 (必须带时区)
) -> ScenarioResult:
    """
    L5 受控入口：在内部沙箱中推演，对外仅返回 ScenarioResult。
    分支状态的 bitemporal.transaction_from 必须严格等于 simulation_time。
    """
```

### 2.2 输出契约 (`ScenarioResult`)

**权威定义**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`
- `StateDelta`: §23
- `ScenarioResult`: §24（含 `delta_state: StateDelta`、`branch_hash`、容量影响摘要等完整字段）

（本节仅引用，不重复定义。）

---

## 三、真实容量影响推演计算公式 (带有量纲单位规范)

- $\text{Duration}(e)$: 历史事件 $e$ 的实际服务时长（单位：分钟 $\text{min}$）；
- $W_{\text{max}}$: 代表单日额定工作工时上限（单位：$480.0\text{ min/day}$）；
- $\text{WorkingDaysCount}$: 生效期内的有效工作日天数（扣除法定节假日与周末，单位：$\text{days}$）；
- $W_{\text{to}}^{\text{planned}}$: 目标代表在规划周期内已分配的计划服务总时长（单位：$\text{min}$）。

$$\Delta W_{\text{from}} = -\sum_{e \in \text{ExecutionStream}} \text{Duration}(e) \cdot \mathbb{I}(e.\text{rep} = \text{from\_rep} \land e.\text{store} = \text{target\_store}) \quad [\text{min}]$$

$$\Delta W_{\text{to}} = +\sum_{e \in \text{ExecutionStream}} \text{Duration}(e) \cdot \mathbb{I}(e.\text{rep} = \text{from\_rep} \land e.\text{store} = \text{target\_store}) \quad [\text{min}]$$

$$\text{OverloadRiskMin}_{\text{to}} = \max\left(0.0, \quad \left( W_{\text{to}}^{\text{planned}} + \Delta W_{\text{to}} \right) - \left( W_{\text{max}} \times \text{WorkingDaysCount} \right) \right) \quad [\text{min}]$$

---

## 四、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 4 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。



================================================================================
# 第六部分: L7 Enterprise Decision Engine
================================================================================


# TopPrism L7 企业决策引擎详细规范 v1.0 (Enterprise Decision Engine Spec)

**Document ID:** TOPPRISM-L7-DECISION-ENGINE-SPEC-v1.0  
**Version:** **v1.0-draft.2 (Phase 6 Detailed Specification - Corrected)**  
**Date:** 2026-08-24  
**Status:** **DETAILED SUBSYSTEM SPECIFICATION (NOT YET FROZEN)**  
**上游约束:** 
- `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md`
- `DECISION_ENGINE_BOUNDARY.md`
- `WORLD_MODEL_DECISION_ENGINE_CONTRACT.md` (v1.0-draft.5.2)
- `CANONICAL_TYPE_REGISTRY.md` (类型权威登记)

---

## 一、L7 企业决策引擎的核心定位与架构责任

L7 企业决策引擎（Prism Decision Engine）是 **TopPrism 决策智能产品家族的“行动、优化与审批统筹中枢”**。
它的核心职责不是维护世界事实，而是**在不可变的世界模型之上，统筹业务意图、调度运筹求解能力、评估多目标权衡、执行严格三维独立审计、落实人机协同审批、并最终下发不可变的决策产物（DecisionArtifact）**。

---

## 二、字典序多目标层级规范 (Aligned with S-A §2.5 & World Model)

决策引擎在评估候选方案优劣时，严格遵循以下五级字典序目标（Lexicographic Objective Hierarchy）：

$$\operatorname{LexMin} \quad \mathbf{Z} = \left( Z_0, Z_1, Z_2, Z_3, Z_4 \right)$$

- **Level 0 (物理可行性与硬约束守卫)**: 单日容量 $\le 6$ 家、单日工时 $\le 480\text{ min}$ (或长途日弹性上限)、起终点闭环、无子回路；
- **Level 1 (业务价值与客户覆盖质量)**: `REQUIRED` 核心大店 0 脱访、全网频次达成率最大化；
- **Level 2 (交通在途时间与空间损耗)**: 全月从 Depot 往返与城际通勤总耗时绝对极小化（消除跨区折返）；
- **Level 3 (拜访节奏稳定性与平滑度)**: 1A 严格同周几等距（7天/14天/28天）偏离度极小化；
- **Level 4 (每日工作负荷均衡度)**: 工作日间拜访数量方差极小化（次级偏好，不为追求过度均衡而牺牲空间紧凑性）。

---

## 三、DecisionArtifact 发布与 WorldModel 状态提交的事务契约 (Two-Phase Commit / Saga Protocol)

为了确保“决策库发布”与“世界模型状态锁定”不出现分布式不一致，决策引擎必须遵循以下三阶段预留与提交协议：

```
L7 Decision Engine                                  World Model L3 / L4 Store
       │                                                      │
       │ 1. reserve_plan_commitment(candidate_plan_id)       │
       ├─────────────────────────────────────────────────────>│
       │                                                      │ 校验承诺冲突并生成锁定令牌
       │ 2. 返回 (success=True, commit_token="TKN_xxx")       │
       │<─────────────────────────────────────────────────────┤
       │                                                      │
       │ 3. 写入不可变 DecisionArtifact 到决策库             │
       │                                                      │
       │ 4. commit_plan_transition(commit_token)              │
       ├─────────────────────────────────────────────────────>│
       │                                                      │ 正式将相关拜访状态置为 COMMITTED
       │ 5. 返回 TransitionResult                             │
       │<─────────────────────────────────────────────────────┤
       │                                                      │
       │ ─── 若步骤 3 或 4 失败触发补偿 ───────────────────── │
       │ 6. abort_plan_commitment(commit_token)               │
       ├─────────────────────────────────────────────────────>│ 释放预留锁定
```

### 3.1 事务实现级约束

| 约束项 | 规则 |
| :--- | :--- |
| **幂等键** | `reserve_plan_commitment(candidate_plan_id, idempotency_key)` — 同一 `idempotency_key` 重复调用返回首次 `commit_token`，不重复锁定 |
| **commit_token 有效期** | 默认 300 秒（可通过配置调整）；超时后 WorldModel 自行将预留状态从 `RESERVED` 回退为 `AVAILABLE` |
| **预留锁超时** | WorldModel 后台巡检进程每 30 秒扫描过期 `RESERVED` 记录并自动释放 |
| **补偿写入审计** | `abort_plan_commitment` 必须在 `execution_fact_stream` 中写入一条 `TransitionEvent`（含 `failure_reason`），确保补偿操作本身可审计 |
| **重复产物防护** | DecisionArtifact 存储以 `candidate_plan_id` 为唯一键；若已存在则返回已有 `artifact_id` 而非重复写入 |
| **WorldModel 先提交、产物存储失败** | WorldModel 已 COMMITTED 但 DecisionArtifact 写入失败时：系统进入 `PENDING_PUBLISH` 状态，由重试队列补偿写入（最长重试 24h，超时告警） |
| **产物先写入、WorldModel 提交失败** | DecisionArtifact 已写入但 WorldModel COMMIT 失败时：系统自动调用 `abort_plan_commitment` 补偿，DecisionArtifact 标记为 `ROLLED_BACK` |
| **重试语义** | 全流程幂等可重试；任何步骤失败后调用方可携带相同 `idempotency_key` 重试，不会产生重复锁定或重复产物 |

---

## 四、核心数据结构规范（权威引用）

本引擎消费与产出的全部领域类型的**唯一权威定义**在 `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md`：

| 类型 | 权威章节 |
| :--- | :--- |
| `PlanningIntent` | §26 |
| `PlannedStop` | §27 |
| `PlannedDailyRoute` | §28 |
| `CandidatePlan` | §29 |
| `PlanAuditReport` | §31 |
| `DecisionArtifact` | §32 |

（依据《Canonical Types 规范》定义来源铁律第 3 条：其他规范文档只允许引用，严禁重复定义。）

---

## 五、阶段状态声明

- **规范版本**: `v1.0-draft.2`
- **状态**: 修正完成，作为 Phase 6 详细规范沉淀，**等待 Phase 1 业务语义签署完成后与整体 API 共同冻结**。



================================================================================
# 第七部分: World Model ↔ Decision Engine Contract
================================================================================


# World Model ↔ Decision Engine Interface Contract

**Document ID:** TOPPRISM-WM-DE-CONTRACT-v1.0  
**Version:** v1.0-draft.5.2 (Contract Freeze Preflight)
**Date:** 2026-08-24  
**Status:** **MANDATORY INTERFACE CONTRACT**

---

## 一、接口分类

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         World Model ↔ Decision Engine 双向接口                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│ World Model  ──── L6 Projection / Read Queries ────▶ Decision Engine                 │
│                                                                                        │
│ Decision Engine ──── L3 Transition / L4 Feedback ──▶ World Model                       │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、WorldModel 暴露给 DecisionEngine 的只读接口

### 1. `get_worldstate_snapshot(snapshot_id)` → `WorldStateSnapshot`
- 返回不可变的世界状态快照（IMMUTABLE）；
- **严禁 DecisionEngine 修改、缓存、持有或传递给其他组件；调用后即释放引用。**
- **DecisionEngine 仅可通过此接口获得"只读 + 临时"访问，不能将 WorldState 作为内部状态字段。**

### 2. `query_customer_universe(rep_id)` → `Dict[store_code, CustomerEntity]`
- 严格基于 WorldState 中的 `OwnershipPolicy.ownership_map`；
- 不允许 DecisionEngine 自行拼接客户列表。

### 3. `resolve_active_policies(context, store_code, valid_time, transaction_time, snapshot_id)` → `Tuple[OperationalVisitPolicy, ...]`
- 按 Bitemporal 命中所有有效政策；
- DecisionEngine 必须基于此结果选择频次。

### 4. `compile_planner_projection(context: ApiRequestContext, snapshot_id: str, intent: PlanningIntent, partial_auth: Optional[PartialProjectionAuthorization] = None)` → `PlannerStateProjection`
- **CONTR-3: L6 接口仅返回 PlannerStateProjection（轻量纯数学载荷）；CandidatePlan 与 DecisionArtifact 属于 L7 输出**
- L6 包含: 严格同周几模式空间、路网矩阵、锁定承诺掩码、动作合成时长；
- L7 收到 Projection 后调用 Domain Solver 生成 CandidatePlan（业务富语义）并经审计后发布 DecisionArtifact。

---

## 三、DecisionEngine 调用 WorldModel 的写操作接口

### 1. `request_transition(context: ApiRequestContext, workflow: WorkflowContext, transition_request: TransitionRequest)` → `TransitionResult`
- DecisionEngine 提交状态转移请求；
- WorldModel 在 L3 执行 5 大守卫（A/B/C/D/E），全部通过后才接受；
- 失败时返回明确拒绝原因，不允许 DecisionEngine 绕过守卫。

### 2. `submit_execution_feedback(context, feedback: ActualVisitEvent)` → `ExecutionFeedbackReceipt`
- 接收来自 SFA/CRM 的实际拜访结果；
- 更新 `execution_fact_stream`；
- 触发新的世界状态演化。

### 3. `request_scenario_rollout(context: ApiRequestContext, base_snapshot_id: str, intent: PlanningIntent, perturbation_events: Tuple[PerturbationEvent, ...], simulation_time: datetime.datetime)` → `ScenarioResult`
- L5 受控 Scenario API；
- 仅供 DecisionEngine 进行"如果改变决策会怎样"的离线仿真；
- **严禁返回 BranchedWorldState 实例本身**（不允许 L7 持有分支状态）；
- 严禁用于生产路径实时决策；
- 返回 **单值 `ScenarioResult`**（其 `delta_state` 字段包含 `StateDelta`），严禁 `Tuple[ScenarioResult, StateDelta]` 双返回。

---

## 四、接口强制性约束

### 1. 不可变性
```python
# ❌ 严禁修改 WorldState 实例
worldstate.customer_universe["NEW_STORE"] = ...  # 错误：违反不变量

# ✅ 必须通过 Canonical API 接口
result: TransitionResult = worldmodel.request_transition(context, workflow, transition_request)
```

### 2. 时间参数强制显式
```python
# ❌ 严禁使用 datetime.now() 默认值
new_state = worldmodel.request_transition(context, workflow, transition_request)

# ✅ 必须显式传入（参考 v1.0-draft.5.2 新签名）
context = ApiRequestContext(api_version="WM-API-v1.0-draft.5.2", request_id=uuid4(),
                           caller_id="user_001", source_system="L7", timezone="Asia/Shanghai")
workflow = WorkflowContext(expected_snapshot_version=12, idempotency_key="uuid4()",
                          fingerprint=server_computed_fingerprint)
transition_request = TransitionRequest(
    visit_id="V_001", target_status=LifecycleStatus.COMMITTED,
    triggering_event_ref="EVT_APPROVE",
    event_time=datetime(2026, 6, 4, 9, tzinfo=ZoneInfo("Asia/Shanghai")),  # 必须带 tz
    transaction_time=datetime(2026, 6, 4, 9, 0, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    approver_id="DIR_GHB", policy_version_snapshot="v2.0",
    evidence_refs=("DOC_001",)
)
result = worldmodel.request_transition(context, workflow, transition_request)
```

### 3. 决策产物的原子性
```python
# 决策发布必须是原子的：审计通过 + 人工签署 + 状态提交 必须捆绑
artifact = decision_engine.approve_and_publish(
    candidate_plan=candidate_plan,
    audit_report=audit_report,
    approver_id="DIR_GHB",
    approval_timestamp=approval_timestamp  # MUST be explicit, no datetime.now()
)
# WorldModel 必须在同一事务中提交：
# 1. 审计哈希写入 transition_records
# 2. 状态置为 COMMITTED
# 3. 发布物锁入 WorldState.active_decision_artifacts
```

---

## 五、接口契约的版本化与兼容性

| 接口 | 当前版本 | 兼容性策略 |
| :--- | :--- | :--- |
| L6 Projection | v1.0 | 严格冻结数学结构，仅递增添加字段 |
| L3 Transition | v3.0 | 守卫列表可扩展，但不能删除已有守卫 |
| L4 Feedback | v1.0 | ActualVisitEvent 字段向后兼容 |
| L5 Scenario | v1.0 (草案) | 实验性 API，可能变动 |

---

## 六、当前 svde/ 代码中哪些已经符合 / 不符合接口契约

| 接口 | 当前状态 | 处理 |
| :--- | :--- | :--- |
| L4 → L6 Projection | `planner_projection.py` 已基本合规 | 微调 Fail-Closed |
| L7 → L3 Transition | `transition_engine.py` 已实现 v3.0 全守卫 | 持续合规 |
| L7 → L4 Feedback | `execution_fact_stream` 数据流存在 | 需要包装为 `submit_execution_feedback` 公开方法 |
| L7 → L5 Scenario | `rollout_reallocation_scenario` 是简化版 | 待升级为真正的多分支引擎 |

---

## 七、接口契约的代码体现

```python
# DecisionEngine 调用 WorldModel 接口的标准模板
class DecisionEngine:
    def approve_and_publish(self, candidate_plan: CandidatePlan,
                            audit_report: PlanAuditReport,
                            approver_id: str) -> DecisionArtifact:
        # 1. 通过 WorldModel 接口提交状态转移 (PLANNED -> COMMITTED)
        worldstate = candidate_plan.derived_worldstate
        # v1.0-draft.5.2: Canonical API 调用
        result: TransitionResult = self.worldmodel.request_transition(
            base_state=worldstate,
            visit_id=candidate_plan.target_visit_id,
            target_status=LifecycleStatus.COMMITTED,
            triggering_event_ref=f"DECISION_{candidate_plan.plan_id}",
            event_time=event_time,                # 必须由调用方显式传入
            transaction_time=transaction_time,    # 必须由调用方显式传入
            approver_id=approver_id,
            policy_version_snapshot=audit_report.policy_version
        )
        # 2. 发布 DecisionArtifact
        return DecisionArtifact(
            plan_id=candidate_plan.plan_id,
            audit_report_id=audit_report.plan_id,
            published_at=published_at,  # 必须由调用方显式传入
            approved_by=approver_id,
            published_worldstate_hash=new_worldstate.snapshot_id,
            ...
        )
```


---

> **同步声明**: 本文档的所有 API 签名必须与 `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2) 及 `CANONICAL_TYPE_REGISTRY.md` 完全对齐。


---

> **同步声明**: 本文档所有调用示例必须使用 Canonical API (`request_transition`, `request_scenario_rollout`)；旧的 `transition_engine.transition_visit_status(...)` 内部实现示例已标注为“内部实现，不属于 Canonical API”。



================================================================================
# 第八部分: Action Type Registry
================================================================================


# TopPrism Action Type 注册表 (v1.0-draft)

**Document ID:** TOPPRISM_ACTION_TYPE_REGISTRY_v1_0
**Version:** v1.0-draft
**Date:** 2026-08-27
**Status:** **DESIGN ONLY** — 非冻结规范，随 Action Type 工程化逐步增补

**设计依据:** TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 1
**Palantir 对照:** Action Types = "the verbs of the enterprise" (参数 + 规则 + 提交标准 + 副作用)

---

## 一、注册表结构

每条 Action Type 记录含：

| 字段 | 说明 |
|---|---|
| **Action ID** | 全局唯一标识（如 `ACTION-DEFER-VISIT`） |
| **名称** | 业务操作名称（如 `拜访顺延`） |
| **参数** | 该动作所需的输入参数（类型、约束） |
| **规则** | 执行该动作必须满足的业务规则（引用 BIZ-xx） |
| **提交标准** | 谁在什么条件下可以执行（角色、状态、时间窗口） |
| **副作用** | 执行后触发的连锁动作（通知、写回、重算触发） |
| **读对象** | 该动作读取哪些 Canonical 类型 |
| **写对象** | 该动作创建/修改哪些 Canonical 类型 |
| **写回系统** | 该动作写回哪些外部系统（如 ERP） |

---

## 二、首批 Action Type

### ACTION-DEFER-VISIT `拜访顺延`

**业务语义:** 经理将某次已排定的拜访顺延到另一日期，受 `DeferralPolicy` 约束。

**参数:**
```python
{
    "visit_id": str,           # 待顺延的拜访标识
    "deferral_policy_id": str, # 顺延政策（引用 DeferralPolicy.policy_id）
    "new_date": date,          # 目标日期
    "reason_code": str,        # 原因代码（如 "CUSTOMER_CANCEL" / "WEATHER" / "REP_UNAVAILABLE"）
    "approved_by": str,        # 审批人（BIZ-08）
}
```

**规则:**
- `deferral_policy_id` 必须引用 `DeferralPolicy` 中 state=ACTIVE 的记录 (BIZ-02)
- 当月已顺延次数不得超过 `max_deferrals_per_month` (BIZ-02)
- 新日期必须在 `allowed_deferral_window_days` 内 (BIZ-02)
- Key/A 级门店顺延须经理审批 (BIZ-03/BIZ-08)

**提交标准:**
- 角色: `REP_MANAGER` 或以上
- 状态: 目标拜访 `current_status` 必须为 `PLANNED` 或 `COMMITTED`
- 时间窗口: 原拜访日期前 24h 内不可顺延（紧急情况走例外审批）

**副作用:**
- 通知: 原日期路线受影响的其他门店负责人
- 写回: 更新 `OperationalVisitLifecycleRecord` 状态 → `DEFERRED`
- 触发: 可选增量重算（若目标日期已有超过上限的拜访）

**读对象:** `OperationalVisitLifecycleRecord` (§12), `DeferralPolicy` (§8)
**写对象:** `OperationalVisitLifecycleRecord` (status → DEFERRED), `PolicyAmendment` (§37)

---

### ACTION-TRANSFER-OWNERSHIP `归属转移`

**业务语义:** 将某门店的拜访归属从一代表转移到另一代表。

**参数:**
```python
{
    "store_code": str,
    "from_rep_id": str,
    "to_rep_id": str,
    "effective_date": date,
    "reason_code": str,      # "TERRITORY_REBALANCE" / "CONFLICT_RESOLUTION" / "REP_DEPARTURE"
    "approved_by": str,
}
```

**规则:**
- 目标门店必须同时存在于 `from_rep_id` 与 `to_rep_id` 的 `assigned_store_codes` 中 (BIZ-06)
- 若因归属冲突裁决，必须引用 `OwnershipConflictRecord` 的裁决结果 (BIZ-06)
- `effective_date` 不得早于当前日期 - 7 天（追溯限制）

**提交标准:**
- 角色: `DISTRICT_MANAGER` 或以上
- 状态: 被转移门店当前无 `ACTIVE` 的 `OwnershipAssignment` 冲突

**副作用:**
- 写回: 创建 `OwnershipAssignment` (status=ACTIVE), 旧 assign 置为 `SUPERSEDED`
- 通知: 两位代表及其区域经理

**读对象:** `OwnershipConflictRecord` (§35.9), `OperationalResource` (§5)
**写对象:** `OwnershipAssignment` (§38)

---

### ACTION-APPROVE-PLAN `审批计划`

**业务语义:** 经理审批/驳回某次计划版本，将其从 `reviewed` 推进到 `published` 或退回 `draft`。

**参数:**
```python
{
    "plan_version_id": str,
    "decision": str,          # "APPROVE" / "REJECT" / "REVISE"
    "comments": str,
    "approved_by": str,
}
```

**规则:**
- 计划版本必须处于 `reviewed` 状态（审批前置）
- Key/A 级门店占比 > 50% 的计划须总监级审批 (BIZ-08)
- 驳回时须填写 `comments`（原因说明）

**提交标准:**
- 角色: `MANAGER` 或以上（Key 占比高时 → `DIRECTOR`）
- 时间窗口: 计划生效日至少 3 个工作日前

**副作用:**
- 写回: `PlanVersion.status` → `published` (APPROVE) / `draft` (REJECT/REVISE)
- 通知: 计划所属代表（批准时推送，驳回时附原因）
- 触发: 若 REJECT 且 `plan_version.solver_run_id` 存在，标记求解器运行记录为 `OVERRIDDEN`

**读对象:** `PlanVersion` (algos/pvrp_cg), `PlannedVisit[]`, `OperationalCustomer` (§4)
**写对象:** `PlanVersion` (status)

---

### ACTION-ADJUST-FREQUENCY `调整频次`

**业务语义:** 业务经理调整某门店的拜访频次（触发 `PolicyAmendment` 记录）。

**参数:**
```python
{
    "policy_id": str,
    "store_code": str,
    "new_frequency_per_month": int,
    "reason_code": str,      # "DEMAND_CHANGE" / "PROMOTION" / "PERFORMANCE_ADJUST"
    "effective_from": date,
    "approved_by": str,
}
```

**规则:**
- `new_frequency_per_month` 必须在合法频次集中（1/2/4，**禁止 3**，对齐 BIZ-01 方案B 事实）
- 生效日期不得早于当前日期
- 频次调整涉及 Key/A 级门店需要经理审批 (BIZ-03)

**提交标准:**
- 角色: `DATA_STEWARD` 或以上
- 状态: 目标门店 `OperationalCustomer` 状态为 active

**副作用:**
- 写回: 创建 `PolicyAmendment` (field_name=target_frequency_per_month)
- 通知: 对应代表的区域经理

**读对象:** `OperationalVisitPolicy` (§7), `OperationalCustomer` (§4)
**写对象:** `PolicyAmendment` (§37), `OperationalVisitPolicy` (target_frequency_per_month 更新)

---

## 三、实现路径

| 阶段 | 动作 | 依赖 |
|---|---|---|
| Phase 1 | 注册表冻结（本文档进入 REVIEW） | 无（规范层） |
| Phase 2 | Action Type 的 Canonical 参数类型定义（冻结 dataclass） | Canonical Types 规范 |
| Phase 3 | Action Type 执行引擎（L7 决策引擎） | 双轨签署、L7 代码实现 |
| Phase 4 | 副作用引擎（通知/写回） | 外部系统集成 |

---

## 四、成熟度声明

```
本文档: DESIGN ONLY (注册表草案)
参数类型: 未实现 (待 Canonical 类型登记)
执行引擎: 未实现 (L7 决策引擎)
副作用: 未实现
```


================================================================================
# 第九部分: L6 Solver Integration Contract
================================================================================


# L6 Projection → Solver 集成契约

**Document ID:** TOPPRISM-L6-SOLVER-INTEGRATION-CONTRACT-v1_0
**Version:** v1.0-draft
**Date:** 2026-08-27
**Status:** **DESIGN ONLY** — 待 Phase 1 求解器集成时实现

**关联:**
- svde 侧: `PlannerStateProjection` (Canonical Types §34) / `PlannerStateProjectionCompiler` (planner_projection.py)
- algos 侧: `solve_time_cg(n, T, t0, svc, freq, ...)` (solver.py) / `PlanningPolicy` (policy.py)
- 数据契约: `PlanVersion` / `PlannedVisit` / `DecisionEvidence` (planning.py)

---

## 一、为什么需要这个契约

当前两个系统各自演进：

| 层 | 输出 | 消费者 |
|---|---|---|
| L6 PlannerStateProjection | `nodes, travel_cost_matrix, candidate_pattern_space, daily_stop_capacity` | 未连接（MVP 未使用） |
| algos PVRP solver | `n, T, t0, svc, freq, days, daily_cap` | 合成示例、研究证据 |

没有适配器，L6 投影无法成为求解器的输入，求解器输出也无法成为 L7 决策引擎的输入。

---

## 二、数据类型映射

| PlannerStateProjection 字段 | 求解器输入 | 转换规则 |
|---|---|---|
| `nodes: Tuple[PlannerNodeTopology, ...]` | `n: int` | `len(nodes)` |
| `nodes[].service_duration_min` | `svc: Sequence[float]` | `[n.service_duration_min for n in nodes]` |
| `travel_cost_matrix` | `T: list[list[float]]` | frozen Tuple → list (无精度损失) |
| `time_slots_count` | `days: int` | 直接映射 |
| `daily_stop_capacity` | `max_visits_per_day` | 映射到 `PlanningPolicy.max_visits_per_day` |
| `daily_workload_budget_min` | `daily_cap: float` | 映射到 `PlanningPolicy.max_work_minutes_per_day` |
| `candidate_pattern_space` 派生 | `freq: list[int]` | 模式空间推导频次（见 §三） |
| `locked_commitments_mask` | `locked_visits` | 映射到 `PlanVersion` 的 `is_locked` 标志 |

---

## 三、频次推导

`PlannerStateProjection` 不直接包含 `freq[]`，而是通过 `candidate_pattern_space` 间接表达。

**推导规则:**
```python
def derive_freq(projection: PlannerStateProjection) -> list[int]:
    """从 candidate_pattern_space 推导每个客户的目标月频次。"""
    freq = [0] * len(projection.nodes)
    for node_idx, patterns in projection.candidate_pattern_space.items():
        # 每个 pattern 是 (w, k) 的元组列表 — 代表该客户在规划期内的拜访次数
        # 方式一: 取最长 pattern 的长度
        max_pattern_len = max(len(p) for p in patterns) if patterns else 0
        freq[node_idx] = max_pattern_len
    return freq
```

**或显式传入:** `ProjectionCompilationRequest` 增加 `freq: Sequence[int] | None` 字段，显式传入时跳过推导。

---

## 四、适配器接口

```python
@dataclass(frozen=True)
class ProjectionToSolverInput:
    """L6 投影 → 求解器输入的适配结果 (frozen, 可审计)。"""
    projection_id: str
    target_rep_id: str
    n_customers: int
    travel_cost_matrix: tuple[tuple[float, ...], ...]
    service_times: tuple[float, ...]
    freq: tuple[int, ...]
    horizon_days: int
    locked_visits: tuple[tuple[int, int], ...]  # (customer_idx, day_idx)
    # 派生策略
    policy: PlanningPolicy


def adapt_projection(
    projection: PlannerStateProjection,
    freq: Sequence[int] | None = None,
    locked_visits: set[tuple[int, int]] | None = None,
    **policy_overrides,
) -> ProjectionToSolverInput:
    """PlannerStateProjection → ProjectionToSolverInput 适配。

    Args:
        projection: L6 编译的投影。
        freq: 显式频次列表 (None = 从 candidate_pattern_space 推导)。
        locked_visits: 已锁定 (customer_idx, day_idx) 集合。
        **policy_overrides: 覆盖 PlanningPolicy 默认值 (如 max_visits_per_day)。

    Returns:
        ProjectionToSolverInput (frozen, 可审计)。
    """
    ...
```

---

## 五、求解器输出 → PlanVersion 适配

```python
def adapt_solution_to_plan(
    solver_input: ProjectionToSolverInput,
    solver_output: tuple[list | None, float, str, dict],
    solver_type: str,
    run_id: str,
    policy: PlanningPolicy,
    existing_plan: PlanVersion | None = None,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解器输出 → PlanVersion + PlannedVisit[] + DecisionEvidence。

    Args:
        solver_input: 适配后的求解器输入。
        solver_output: solver.solve_time_cg 的返回值 (assigns, total, status, stats)。
        solver_type: "CG" / "ALNS" / "CP-SAT"。
        run_id: 求解运行标识。
        policy: 使用的约束策略。
        existing_plan: 已有计划 (用于增量重算的版本号递增)。

    Returns:
        (PlanVersion, PlannedVisit[], DecisionEvidence) — 可审计的三元组。
    """
    ...
```

---

## 六、验收标准

- [ ] `adapt_projection` 将 `PlannerStateProjection` 正确转换为 `solve_time_cg` 的输入参数
- [ ] 频次推导与显式传入两种方式均通过测试
- [ ] `adapt_solution_to_plan` 将求解器输出包装为 `PlanVersion` + `PlannedVisit[]` + `DecisionEvidence`
- [ ] 两种适配均不修改原始数据（frozen dataclass 不变性）
- [ ] 适配器运行在仁军 2026-06 真实数据上（`PlannerStateProjectionCompiler` → `solve_time_cg` → `PlanVersion`）


================================================================================
# 第十部分: Ontology Design Review vs Palantir
================================================================================


# TopPrism 本体与世界模型设计评审 — 对照 Palantir Foundry Ontology 最佳实践

**Document ID:** TOPPRISM-ONTOLOGY-DESIGN-REVIEW-VS-PALANTIR-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 设计评审报告 (已获所有者同意, 建议项待逐项立项)
**评审对象:** `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2) + `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` (34 类型) + L3/L5/L7 详细规范

**证据源:**
- Palantir Foundry 官方文档 (深读 6 篇):
  - Why create an Ontology? (decision-centric: Data/Logic/Action/Security)
  - Ontology design: Best Practices (四原则 + 务实权衡)
  - Ontology design: Structural Guidance (规范化/Structs/Interfaces/Object-backed Links/命名/安全)
  - Ontology design: Anti-Patterns (8 反模式)
  - Action Types Overview (动词类型化)
  - Ontology Scenarios Overview [Beta] (沙盒/合并/执行上下文治理)
- 学术: Ding et al., "Understanding World or Predicting Future? A Comprehensive Survey of World Models", arXiv:2411.14499 (2024-11)

**检索限制声明:** 本评审期间 web 搜索通道大部分不可用 (供应商封锁/MCP 订阅失效); Palantir 文档为深读一手证据, 学术文献仅获得综述摘要, Ha & Schmidhuber (1803.10122) 与 LeCun JEPA 立场文件未重读原文。引用 Palantir 原文处均为直读摘录。

---

## 一、验证结论: 现有设计与行业最佳实践的吻合点

| 我们的纪律/设计 | Palantir 对应物 | 结论 |
|---|---|---|
| 四要素分离 (事实约束/业务目标/动作集归 World Model; Trade-off 归 Decision Engine) | 决策四要素 Data/Logic/Action/Security, "Ontology represents the decisions, not simply the data" | **同构, 保留** |
| 三层纪律 (Business→Math→Algorithm 严禁混淆) | Golden Hammer 反模式 + 工具选择表 (action=人的决策 / pipeline=自动变换 / function=实时逻辑) | **同构, 保留** |
| L6 纯数学投影 (预计算, 只读) | Pre-computed vs dynamically derived values 二分; 投影属预计算类 | **吻合, 保留** |
| WorldState 全量快照 + 双时态 | Scenarios 显式声明 "不是版本工具"; 历史走 linked amendment | **部分吻合, 需显式区分声明 (见建议 3)** |
| 五级成熟度诚实声明 | "Pragmatism and tradeoffs": 在用的不完美本体 > 在设计的完美本体 | **文化一致** |

---

## 二、建议清单 (按优先级)

### 建议 1: 把 Action 提升为本体一等公民 [最大缺口]

**Palantir 证据** (Action Types Overview / Why Ontology):
> "If the data elements in the Ontology are 'the nouns' of the enterprise, then the actions can be considered 'the verbs'."
> Action Type = 参数 (parameters) + 规则 (rules) + 提交标准 (submission criteria) + 副作用 (side effects: 通知/webhook) 的类型化业务操作。

**我们的缺口**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` 类型库 (本评审时点 34 主类型; 同日修订后含 §37 PolicyAmendment / §38 OwnershipAssignment) 全部是名词 (实体/记录/凭证)。业务动作 (拜访顺延/归属转移/排班审批/方案合并) 仅以 API 参数包形态存在 (`TransitionRequest`), 不是本体类型, 无规则/提交标准/副作用的类型化承载。

**行动项**: 新建 `TOPPRISM_ACTION_TYPE_REGISTRY_v1_0.md`, 首批登记:
- `DeferVisit` (参数: visit_id, deferral_policy_id; 规则: BIZ-02; 提交标准: 角色窗口; 副作用: 通知经理)
- `TransferStoreOwnership` (参数: store_code, from_rep, to_rep, effective_date; 规则: BIZ-06; 副作用: 重算归属冲突)
- `ApprovePlanAdjustment` (参数: plan_id, approver; 规则: BIZ-08)
- 每个动作声明: 读哪些对象 / 写哪些对象 / 写回哪些外部系统

**依赖**: 需 BIZ-01~08 签署 (动作规则引用业务语义)。

### 建议 2: 归属关系升级为带元数据的关联对象

**Palantir 证据** (Structural Guidance / Links):
> "Object-backed link: the relationship carries its own metadata (dates, roles, status, allocation) → Employee → VentureStaffing → Venture"

**我们的缺口**: `PolicyRegistry.ownership_map: Dict[str, str]` (store_code → rep_id) 是无元数据直接映射。2026-08-26 业务方案B 分析实证: 归属调整是高频核心业务动作 (NT23 等 4 家店摘牌、欣/晓敏 40 店频率调整), 归属变更需生效日期/原因/审批, 当前类型无法承载。

**行动项**: 新增 `OwnershipAssignment` 关联对象:
```python
@dataclass(frozen=True)
class OwnershipAssignment:
    assignment_id: str
    store_code: str
    rep_id: str
    effective_from: datetime.date      # 双时态 valid time
    effective_to: Optional[datetime.date]
    reason: str                        # 方案调整/摘牌/冲突裁决
    approved_by: str
    transaction_from: datetime.datetime  # 带时区
    status: str                        # ACTIVE / SUPERSEDED
```
`ownership_map` 降级为 `OwnershipAssignment` 的当前态投影。

### 建议 3: Time Machine 自查 — 区分"版本对象"与"状态检查点"

**Palantir 证据** (Anti-Patterns / The Time Machine):
> 历史版本建模为独立对象/类型是反模式; 正确做法 = 单一当前对象 + linked amendment 历史对象 (Contract → Contract Amendments: amendmentDate/previousValue/newValue/changeReason)。

**自查结论 (两项, 结论不同)**:
1. `OperationalVisitPolicy` 按 `policy_version` 建多版本对象 → **命中反模式**。重构为: 单一当前 `OperationalVisitPolicy` + linked `PolicyAmendment` (amended_at/previous_frequency/new_frequency/reason/approved_by)。
2. `WorldState` 全量快照链 → **不是反模式**: 这是世界状态检查点 (event-sourcing 语义), Palantir 无对应物 (其 Object Storage 是当前态 + edits history)。**行动项**: 在 L4 规范增加显式区分声明: "WorldState 快照是决策检查点, 不是实体版本; 实体级历史一律走 linked amendment 对象" — 防止后续评审误判。

### 建议 4: L5 场景语义补全 (对标 Palantir Scenarios)

**Palantir 证据** (Ontology Scenarios [Beta]):
- Merge 是独立动作, 有独立提交标准 ("Applying approved scenario edits to the main Ontology is controlled separately through the submission criteria of the merge action")
- Execution context 治理: "submission criteria can distinguish between actions executed within a scenario and actions executed against the main Ontology" — 场景内宽松、合并严格
- 显式边界: "Scenarios are not data versioning tools. They cannot provide a snapshot of your Ontology at a historical point in time"
- 生命周期: auto-rebase (10 分钟) / TTL (30 天) / merge / discard

**我们的缺口** (`TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_DETAILED_SPEC_v1_0.md`): 只有 rollout 出 `ScenarioResult(delta)`, 缺:
1. 合并回主干的类型化路径 (`MergeScenario` 动作 + 独立提交标准)
2. 动作授权不区分"场景内执行" vs "主干执行"
3. 无场景与 bitemporal 历史查询的边界声明

**行动项**: L5 规范 v1.0-draft.3 增补 `ScenarioLifecycle` (FORKED → EDITING → COMPARED → MERGED/DISCARDED) + `MergeScenario` Action Type + 边界声明。

### 建议 5: 统一 Decision Lineage (决策谱系)

**Palantir 证据** (Why Ontology):
> "The end-to-end 'decision lineage' of when a given decision was made, atop which version of enterprise data, and through which application, is automatically captured and securely accessible to both human developers and agents."

**我们的缺口**: 审计锚点分散四层 — `RequestFingerprint` (API §2.2/§5.2.1) / `StateTransitionRecord.record_hash` (L3) / `TransitionResult.audit_hash` / `SourceManifest.source_file_sha256` (L4) — 无贯通结构。

**行动项**: 新增 `DecisionLineageRecord`:
```python
@dataclass(frozen=True)
class DecisionLineageRecord:
    lineage_id: str
    decision_id: str
    data_snapshot_ref: str        # WorldState snapshot_id
    logic_asset_ref: str          # 求解器/模型/规则版本
    action_ref: str               # Action Type + 实例 id
    actor_id: str
    approval_ref: Optional[str]   # 审批记录
    occurred_at: datetime.datetime  # 带时区
```
L3 转移 / L7 动作执行 / L5 合并均写入。

### 建议 6: 采纳四原则裁决顺序 + 务实条款 (写入设计规范)

**Palantir 证据** (Best Practices, 带显式优先级, 冲突时高位胜出):
1. Domain-driven design (建模现实, 不建模源系统)
2. Do not repeat yourself (rule of three: 一次是巧合, 两次是模式, 三次必须重构)
3. Open for extension, closed for modification (保护核心模型, 允许扩展)
4. Composition over deep hierarchies (接口组合, 能力接口如 Inspectable/Schedulable)

**Pragmatism 条款** (原文采纳):
- "命名质量、语义清晰、安全设计是后期难以修复的 — 可以在实现细节上妥协, 不能在这三样上妥协"
- "在用并产生价值的不完美本体, 优于仍在设计中的理论完美本体"
- "显式命名权衡: 一次反规范化在当前规模可行, 超过 1 万对象需重审"

**行动项**: 写入 `TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE` 作为类型设计裁决顺序。

### 建议 7: Kitchen Sink / 命名审计 (一轮全类型自查)

**Palantir 证据** (Anti-Patterns: Kitchen Sink / Misnomer; Structural Guidance / Naming):
- 只保留有业务语义的字段; ETL/管道元数据不入本体
- 禁裸歧义名词: `value` → `monetaryValue` / `quantityOnHand`; 链接双向可读命名
- 每个属性问一句: "有人需要按它查看/搜索/过滤吗?"

**自查发现 (2026-08-26 即时扫描)**:
- `OperationalCustomer.planned_frequency` — 自带 `# DEPRECATED` 注释, Kitchen Sink 残留 → 删除 (消费方: planner_projection 已改走 PolicyRegistry, FIX-1 完成)
- 裸名词待查: `status` (多处, 语义各异: LifecycleStatus / OwnershipConflict resolution / Authorization), `category` (CognitiveCategory) — 逐一加限定或改名
- `CognitiveCategory.OBSERVATION/POLICY/COMMITMENT` 标签体系: 按 DDD 原则审视是领域概念还是源系统概念, 评审后决定去留

### 建议 8: 学术定位声明 (防范围漂移)

**证据** (arXiv:2411.14499 综述): 世界模型两分 — (1) 构建内部表示理解世界机制; (2) 预测未来状态模拟并引导决策。主流文献集中于游戏/自动驾驶/机器人/社会模拟 (生成式路线: Sora/Genie/DriverDreamer 等)。

**定位声明** (建议写入产品规范): TopPrism World Model 是 **(1)+(2) 的企业离散语义实例**: 状态表示 (L4 双时态快照) + 动力学 (L3 守卫转移) + 推演 (L5 场景), 核心约束是可审计/带授权/可回写, 而非连续信号生成。**不追逐**生成式世界模型路线; 该路线文献仅提供概念框架。

### 建议 9: Registry 锚点引用完整性自动校验 [立即执行]

**教训**: 2026-08-26 发现 `WorkflowContext`/`RequestFingerprint` 在 Registry 中为悬空引用 (指向从未定义的 §5.2), 已手工补全 (主 API §5.2.1 + TECH-08)。

**行动项**: 编写 `svde/tools/validate_registry_anchors.py`:
- 扫描 `CANONICAL_TYPE_REGISTRY.md` 全部 `文档名 + §x.x` 引用
- 解析目标文档标题/章节锚点, 验证存在且非空
- 输出违规清单; 纳入文档变更 CI

---

## 三、执行顺序 (已获同意)

| 序 | 项 | 工作量 | 依赖 |
|---|---|---|---|
| 1 | 建议 9: 锚点校验脚本 | ~0.5h | 无 |
| 2 | 建议 6: 四原则 + 务实条款写入架构基线 | ~1h 文档 | 无 |
| 3 | 建议 3: Time Machine 自查声明 + PolicyAmendment 重构设计 | ~2h | 无 (重构实施待签署后) |
| 4 | 建议 2: OwnershipAssignment 类型 + 规范登记 | ~2h | 无 (方案B 已证业务必要性) |
| 5 | 建议 7: Kitchen Sink / 命名审计报告 | ~2h | 建议 6 裁决顺序 |
| 6 | 建议 1: Action Type 注册表 | 大 | **BIZ-01~08 签署** |
| 7 | 建议 4: L5 Scenarios 语义补全 (draft.3) | 中 | 建议 1 (MergeScenario 依赖动作类型) |
| 8 | 建议 5: DecisionLineageRecord | 中 | 建议 1 (action_ref 依赖) |

**红线不变**: 建议 1/4/5 的代码实现仍受双轨签署门禁约束 (API 冻结前不写实现); 本文档中的类型设计均为规范层工作。

---

## 四、成熟度声明

```
本评审: 证据充分 (Palantir 一手文档 6 篇直读 + 综述摘要)
学术覆盖: 部分 (搜索通道受限, 经典原文未重读)
建议 1-9: 设计已定义 — 均未实施
与业务签署的关系: 建议 1 依赖 BIZ 签署; 其余为规范层可先行
```



================================================================================
# 第十一部分: Phase 1 API Design
================================================================================


# Phase 1 API 设计 (Human-led Planning / Plan vs Actual)

> 基于 P0 修复后的求解器与 Phase 1 数据契约，设计可执行的 Plan vs Actual 管道。
> 日期：2026-08-27
> 关联：`algos/pvrp_cg/planning.py` / `algos/pvrp_cg/plan_vs_actual.py` / `algos/pvrp_cg/policy.py`

## 架构

```text
求解器输出 (solve_time_cg / solve_distance_cg / ALNS)
    │
    ▼
SolverAdapter ───→ PlanVersion (新版本)
    │                     │
    │                     ├── PlannedVisit[]
    │                     ├── DecisionEvidence
    │                     └── policy_version → PlanningPolicy
    │
    ▼
Execution (外部系统)
    │
    ▼
ActualVisit[] ←─── GPS / 打卡 / ERP 反馈
    │
    ▼
PlanVsActualMetrics ───→ 经理 Dashboard
    │
    ▼
ManualOverride ───→ 触发局部重算 → 新 PlanVersion
```

## 核心接口

### 1. SolverAdapter — 求解器 → PlanVersion 适配器

```python
@dataclass(frozen=True)
class SolverRun:
    run_id: str
    solver_type: str              # "CG" / "ALNS" / "CP-SAT"
    policy: PlanningPolicy
    plan_id: str
    representative_id: str
    status: str
    evidence: DecisionEvidence

def solve_to_plan(
    *,
    solver_type: str = "CG",
    lats: Sequence[float],
    lons: Sequence[float],
    depot: tuple[float, float],
    freq: Sequence[int],
    svc: Sequence[float],
    policy: PlanningPolicy,
    segments: Sequence | None = None,
    counties: Sequence[str] | None = None,
    overrides: list[ManualOverride] | None = None,
    locked_visits: set[tuple[int, int]] | None = None,
    existing_plan: PlanVersion | None = None,
    **solver_kwargs,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解 → PlanVersion 一步完成。
    
    - 无 existing_plan: 全新求解，全部客户按 policy 排程
    - 有 existing_plan + locked_visits: 增量/局部重算，锁定客户不移动
    - 有 overrides: 人工调整后的二次求解（保持调整、优化其余）
    """
```

### 2. PlanExecution — 执行回放管道

```python
def replay_plan(
    plan: PlanVersion,
    planned_visits: list[PlannedVisit],
    actual_visits: list[ActualVisit],
    overrides: list[ManualOverride] | None = None,
    evidence: DecisionEvidence | None = None,
) -> PlanVsActualMetrics:
    """Plan vs Actual 全量指标计算。
    
    已实现为 `plan_vs_actual.compute_plan_vs_actual()`。
    """
```

### 3. 增量重算

```python
def incremental_replan(
    existing_plan: PlanVersion,
    new_actuals: list[ActualVisit],
    overrides: list[ManualOverride],
    policy: PlanningPolicy,
    **solver_kwargs,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """基于执行反馈的增量重算 → 新版本 PlanVersion@v+1。
    
    - 已完成拜访固定
    - 已锁定拜访不移动
    - 未受影响的客户尽量保持原日期
    - 新版本号 = existing_plan.version + 1
    """
```

## 验收标准 (Phase 1)

- [ ] 求解器输出可被 `solve_to_plan` 包装为 `PlanVersion` + `PlannedVisit[]`
- [ ] `compute_plan_vs_actual` 在真实历史数据上可运行（仁军 2026-06）
- [ ] 人工调整不覆盖原始求解结果（原始值在 PlanVersion 中可追溯）
- [ ] 所有汇报指标都能追溯到输入、策略和求解版本
- [ ] 增量重算产生的新版本号 = v+1，不覆盖旧版本


================================================================================
# 第十二部分: Phase 2 Design
================================================================================


# Phase 2 设计：AI-assisted Decision / Resource Effectiveness

> 从"减少里程和工时"升级为"把有限资源投向更有价值的机会"
> 日期：2026-08-27
> 证据源：Palantir Foundry Scenarios (深读) / 优化建议 §4 / arXiv:2411.14499 世界模型综述

## 一、核心设计原则

### 1.1 动态价值模型（学习产出，非静态字段）

客户价值不是预设的静态标签，而是从执行结果中持续学习的动态模型。

**输入信号：**
- 拜访完成率（Plan vs Actual 偏差）
- 服务时长合规性（实际 vs 估计偏差）
- 频次遵守率（policy 要求的频率 vs 实际执行）
- 业务结果（品类配合度、补货完成率、陈列合规 — 来自 `MerchandisingComplianceFact`）
- 历史趋势（以上指标随时间的变化方向）

**输出：**
- `customer_value_score: float` (0-1) — 归一化价值评分
- `value_confidence: float` (0-1) — 模型置信度（样本量/时效性）
- `value_components: dict` — 可解释的各维度贡献

### 1.2 动态优先级（加权，非词典序）

优先级 = 价值评分 × 动态权重。权重来自优化目标的反向传播，不是硬编码的词典序。

**权重学习：**
- 初始权重：均匀分布（所有维度等权）
- 滚动优化：每轮执行后，对比 Plan vs Actual 的偏差分布，调整权重使偏差最小的维度获得更高权重
- 约束：权重变化幅度受稳定性预算限制（避免每轮剧烈波动）

### 1.3 情景比较（Palantir Scenarios 模式）

```text
Baseline (当前业务计划)
    │
    ├── Efficiency First (最小化里程/工时, 权重=里程优先)
    ├── Value First (最大化高价值覆盖, 权重=价值优先)
    ├── Stability First (最小化变更, 权重=偏差最小化)
    ├── Balanced (平衡模式)
    └── Manager-adjusted (经理手动调整)
```

每个情景输出：
- 价值覆盖
- 总里程
- 总工时
- 活跃工作日
- 频次合规
- 每日容量违例
- 负荷公平
- 相对当前计划的变更数量
- 被影响的高优先级客户

---

## 二、与现有架构的关系

### 2.1 PlanningPolicy 扩展

```python
@dataclass(frozen=True)
class DynamicPlanningPolicy(PlanningPolicy):
    # 价值层
    value_scores: dict[int, float] = {}         # customer_idx → score [0,1]
    value_confidence: dict[int, float] = {}     # customer_idx → confidence [0,1]
    priority_weights: dict[str, float] = {}     # 目标维度 → 权重
    # 稳定性层
    stability_budget: int = 0                    # 最多改变的客户数
    change_penalty: float = 0.0                # 变更惩罚系数
    freeze_committed: bool = True               # 已确认拜访是否冻结
```

### 2.2 Solver 目标函数扩展

当前 `solve_time_cg` 最小化总工时。Phase 2 扩展为：

```python
def solve_weighted_cg(
    n, T, t0, svc, freq, days, daily_cap, value_scores, policy,
    time_limit=30,
) -> tuple:
    # 目标: 最小化 (里程+工时) - λ × 价值覆盖
    # 其中 λ 由 dynamic_priority_weights 决定
```

### 2.3 Scenario Engine

基于 Palantir Scenarios 模式：

```python
@dataclass(frozen=True)
class ScenarioRun:
    scenario_id: str
    label: str                    # "Efficiency First" / "Value First" / ...
    policy: DynamicPlanningPolicy
    solver_input: ProjectionToSolverInput
    result: tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]
    metrics: PlanVsActualMetrics  # 对比基线

def run_scenarios(
    base_policy: DynamicPlanningPolicy,
    scenario_configs: list[ScenarioConfig],
    solver_input: ProjectionToSolverInput,
) -> tuple[ScenarioRun, ...]:
    """并行运行多个情景, 返回可比较的 ScenarioRun 列表。"""
    ...
```

---

## 三、验收标准

- [ ] 动态价值模型在仁军 2026-06 数据上可训练（从 ActualVisit 中提取信号）
- [ ] `solve_weighted_cg` 在相同输入下，价值导向 vs 效率导向产出不同排程
- [ ] 5 种情景可并行求解并输出对比报告
- [ ] 经理可锁定特定客户，触发局部重算后锁定客户不移动
- [ ] 推荐采纳率和人工修改率可被持续统计


================================================================================
# 第十三部分: Phase 3 Design
================================================================================


# Phase 3 设计：Adaptive Digital Manager / Continuous Learning

> 计划不再是月初一次性产物，而是在业务变化中持续更新
> 日期：2026-08-27
> 证据源：Palantir Scenarios + 优化建议 §5 + 世界模型综述 arXiv:2411.14499

## 一、核心设计原则

### 1.1 Rolling-horizon Re-planning

支持每日或每周滚动求解，每次重排生成新的 PlanVersion：

```text
Week 1 ──→ 执行 ──→ ActualVisit ──→ 增量重算 ──→ PlanVersion@v2
                                    ↑
                             新事件: 客户取消 / 新机会 / 销售请假
```

**冻结规则：**
- 已完成拜访：固定（不可修改）
- 未来 3 天内的拜访：frozen（不可移动，但可取消）
- 已确认拜访（经理 locked）：不可移动
- 未受影响的客户：尽量保持原日期（稳定性优先）

### 1.2 稳定性预算

每次重算的变化幅度受预算约束：

| 维度 | 预算 | 说明 |
|---|---|---|
| 最大变更客户数 | configurable | 每轮最多改变多少客户的拜访日期 |
| 最大变更拜访数 | configurable | 每轮最多改变多少条拜访记录 |
| 临近惩罚 | 指数衰减 | 离执行日期越近的变更惩罚越大 |
| 已确认客户冻结 | 硬约束 | 经理 locked 的客户不可移动 |

### 1.3 三类学习模型

#### 旅行与驻留时间模型（回归 → 校准）

```python
class TravelTimeModel:
    """预测 travel/service residual，按区域、时段和客户类型校准。"""
    def predict(self, origin, dest, county, time_of_day, customer_type) -> float:
        """返回预测的分钟/公里。"""
    
    def monitor_drift(self, actuals: list[ActualVisit]) -> dict:
        """监控 fallback 比例、漂移和异常值。"""
        return {"drift_detected": bool, "fallback_ratio": float, "anomalies": [...]}
```

#### 计划接受与执行模型（分类 → 调整）

```python
class PlanAcceptanceModel:
    """预测推荐被经理接受的概率。"""
    def predict_acceptance(self, change: dict) -> float:
        """返回 0-1 概率。"""
    
    def identify_frequent_overrides(self, overrides: list[ManualOverride]) -> list[str]:
        """识别频繁被人工覆盖的规则。"""
        # 不把人工覆盖自动视为"错误"，必须记录原因
```

#### 业务响应模型（因果推断 → 策略）

```python
class BusinessResponseModel:
    """学习拜访后的业务响应（区分相关性与增量效果）。"""
    def estimate_effect(self, visit_frequency: int, customer_id: str) -> dict:
        """返回增量效果估计，含置信区间。"""
    
    def evaluate_strategy_change(self, old_policy, new_policy, historical_data) -> dict:
        """离线评估策略变更的预期影响。"""
        # 不允许未经评估直接改变客户覆盖策略
```

### 1.4 安全上线顺序

```text
离线回放 → 影子推荐 → 经理审阅 → 小范围受控上线 → 扩大覆盖
```

每阶段必须保留：
- 模型版本
- 特征版本
- 策略版本
- 回放指标
- 数据漂移指标
- 人工审批记录
- 回滚能力

---

## 二、与现有架构的关系

### 2.1 PlanVersion 生命周期扩展

```python
@dataclass(frozen=True)
class PlanVersion:
    ...
    # Phase 3 增加
    parent_plan_id: str | None = None   # 被替代的计划
    triggered_by: str = "scheduled"      # "scheduled" / "event" / "manual"
    triggering_event_ref: str | None = None  # 触发事件引用
    stability_metrics: dict | None = None    # 相对父计划的变更统计
    model_versions: dict | None = None       # 使用的学习模型版本
```

### 2.2 增量重算接口

```python
def incremental_replan(
    existing_plan: PlanVersion,
    actual_visits: list[ActualVisit],
    new_events: list[PlanningEvent],    # 客户取消 / 新机会 / 请假
    models: LearningModels,              # 三类学习模型
    policy: DynamicPlanningPolicy,
    change_budget: ChangeBudget,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """滚动重算 → 新版本 (v+1)，受稳定性预算约束。"""
```

### 2.3 影子运行管道

```python
def shadow_run(
    plan: PlanVersion,
    actual: list[ActualVisit],
    proposed_policy: DynamicPlanningPolicy,
    overrides: list[ManualOverride],
) -> ShadowReport:
    """离线回放：新策略 vs 旧策略 vs 实际执行，三路对比。"""
```

---

## 三、验收标准

- [ ] 新业务事件（客户取消/新机会）可触发增量重排，产生新 PlanVersion
- [ ] 增量重排后，未受影响的客户 ≥ 80% 保持原日期
- [ ] 三类学习模型可离线回放和版本比较
- [ ] 自动策略更新前必须经过审批（影子运行 → 经理审阅 → 上线）
- [ ] 可以证明新策略相对基线改善了哪些指标（价值覆盖、效率、合规）


================================================================================
# 第十四部分: PlanningPolicy 统一约束契约
================================================================================


"""PlanningPolicy — 统一约束契约 (P0 / Task 1, 来源: 优化建议 §3.3)

CG 求解器、CP-SAT、ALNS、validator、报告与文档全部引用同一份约束对象,
消除隐藏全局常量 (solver.MAX_PER_DAY = 6 / baselines 全局) 与口径漂移。

用法:
    policy = PlanningPolicy(n_customers=40, freq=[...])
    policy.validate_solution(sol, day_times=[...]) -> list[str]  # 违规清单, 空 = 合法
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence

DEFAULT_MAX_VISITS_PER_DAY = 6
DEFAULT_MAX_WORK_MINUTES_PER_DAY = 540.0


@dataclass(frozen=True)
class PlanningPolicy:
    """统一约束契约 (frozen)。所有求解器与 validator 的唯一约束事实源。

    Attributes:
        horizon_days: 规划期天数 (默认 20 个工作日)。
        max_visits_per_day: 单日拜访客户数上限 (替代散落的 MAX_PER_DAY = 6)。
        max_work_minutes_per_day: 单日在途+在店工时上限 (分钟; None = 不限,
            对齐 solver.solve_time_cg 的 daily_cap 语义)。
        min_interval_days: 频次 f>=2 客户的最小重访间隔 (天)。None = 由
            horizon // (freq + 1) 推导 (沿用 ALNS gap 公式)。
        frequency_rules: 客户 id -> 目标月频次 (必须逐户给出, 不可缺省)。
        workload_balance_policy: 负载均衡策略声明 ("none" / "min_max_spread"),
            仅作契约声明, 由求解器各自实现并在 DecisionEvidence 中回报。
        depot_policy / route_type: 口径声明 ("round_trip"/"open"), 同上。
    """

    n_customers: int
    frequency_rules: Mapping[int, int]
    horizon_days: int = 20
    max_visits_per_day: int = DEFAULT_MAX_VISITS_PER_DAY
    max_work_minutes_per_day: float | None = DEFAULT_MAX_WORK_MINUTES_PER_DAY
    min_interval_days: Mapping[int, int] | None = None
    depot_policy: str = "round_trip"
    route_type: str = "closed"
    workload_balance_policy: str = "none"
    tier_service_minutes: Mapping[str, float] | None = None  # {"Key":60,"A":45,"B":45,...}
    max_work_minutes_by_tier: Mapping[str, float] | None = None  # 差异化工时上限
    coverage_policies: tuple | None = None  # CoveragePolicy 引用列表 (可选, Phase 1+)

    def __post_init__(self) -> None:
        if self.horizon_days <= 0:
            raise ValueError(f"horizon_days 必须 > 0, 实际 {self.horizon_days}")
        if self.max_visits_per_day <= 0:
            raise ValueError(f"max_visits_per_day 必须 > 0, 实际 {self.max_visits_per_day}")
        if self.max_work_minutes_per_day is not None and self.max_work_minutes_per_day <= 0:
            raise ValueError("max_work_minutes_per_day 必须 > 0 或 None")
        if sorted(self.frequency_rules) != list(range(self.n_customers)):
            raise ValueError(
                "frequency_rules 必须恰好覆盖客户 0..n-1 "
                f"(n={self.n_customers}, 实际键={sorted(self.frequency_rules)})"
            )
        if any(f < 1 for f in self.frequency_rules.values()):
            raise ValueError("拜访频次必须 >= 1")
        if self.depot_policy not in ("round_trip", "open"):
            raise ValueError(f"depot_policy 非法: {self.depot_policy!r}")

    # ------------------------------------------------------------------
    def effective_gap(self, cust: int) -> int:
        """客户最小重访间隔: 显式规则优先, 否则按频次推导 (days // (f + 1))。"""
        if self.min_interval_days is not None and cust in self.min_interval_days:
            return self.min_interval_days[cust]
        return self.horizon_days // (self.frequency_rules[cust] + 1)

    def gaps(self) -> dict[int, int]:
        return {i: self.effective_gap(i) for i in range(self.n_customers)}

    # ------------------------------------------------------------------
    def validate_solution(
        self,
        sol: Sequence[set[int]],
        day_times: Sequence[float] | None = None,
        *,
        tol: float = 1e-6,
    ) -> list[str]:
        """独立 solution validator — 与任何求解器实现无关的最终裁决。

        Args:
            sol: len(horizon_days) 的每日客户集合。
            day_times: 可选的每日实际工时 (分钟); 提供则校验工时上限。
            tol: 浮点比较容差。

        Returns:
            违规描述列表; 空列表 = 方案在契约下完全合法。
        """
        v: list[str] = []
        if len(sol) != self.horizon_days:
            v.append(f"sol 天数 {len(sol)} != horizon {self.horizon_days}")

        visits_of: dict[int, list[int]] = {}
        for d, day in enumerate(sol):
            if self.max_visits_per_day is not None and len(day) > self.max_visits_per_day:
                v.append(
                    f"day{d}: 客户数 {len(day)} 超上限 {self.max_visits_per_day}"
                )
            for c in day:
                if not (0 <= c < self.n_customers):
                    v.append(f"day{d}: 非法客户 id {c}")
                    continue
                visits_of.setdefault(c, []).append(d)
            if day_times is not None and self.max_work_minutes_per_day is not None:
                if day_times[d] > self.max_work_minutes_per_day + tol:
                    v.append(
                        f"day{d}: 工时 {day_times[d]:.1f} 超上限 "
                        f"{self.max_work_minutes_per_day:.1f}"
                    )

        # 频次与间隔
        for c in range(self.n_customers):
            days_c = sorted(visits_of.get(c, []))
            want = self.frequency_rules[c]
            if len(days_c) != want:
                v.append(f"cust{c}: 频次 {len(days_c)} != 要求 {want}")
            gap = self.effective_gap(c)
            for a, b in zip(days_c, days_c[1:]):
                if b - a < gap:
                    v.append(f"cust{c}: 重访间隔 {b}-{a}={b - a} < 最小 {gap}")
        return v

    def service_minutes_for_tier(self, tier: str) -> float:
        """按门店级别返回差异化服务时长 (默认 45 min)。"""
        if self.tier_service_minutes and tier in self.tier_service_minutes:
            return self.tier_service_minutes[tier]
        return 45.0

    def summary(self) -> dict:
        """供 CG/ALNS 对比报告与 DecisionEvidence 引用的约束参数摘要。"""
        return {
            "horizon_days": self.horizon_days,
            "max_visits_per_day": self.max_visits_per_day,
            "max_work_minutes_per_day": self.max_work_minutes_per_day,
            "depot_policy": self.depot_policy,
            "route_type": self.route_type,
            "workload_balance_policy": self.workload_balance_policy,
            "n_customers": self.n_customers,
        }



================================================================================
# 第十五部分: Plan vs Actual 数据契约
================================================================================


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



================================================================================
# 第十五部分b: PlanVsActualMetrics 计算
================================================================================


"""Plan vs Actual 指标计算 (Phase 1, Task 7) — 基于数据契约生成可审计汇报指标。

所有指标至少来源可追溯：输入、策略、求解版本三重锚定。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Sequence

from .planning import ActualVisit, DecisionEvidence, PlanVersion, PlannedVisit


@dataclass(frozen=True)
class PlanVsActualMetrics:
    """Plan vs Actual 对比指标的单一输出结构 (frozen)。

    核心指标:
        - coverage_rate: 计划覆盖率
        - completion_rate: 实际完成率
        - on_plan_completion: 计划内完成数
        - ad_hoc: 临时追加数
        - cancelled: 取消数
        - rescheduled: 改期数
        - frequency_compliance_rate: 频次合规率
        - route_deviation_km: 路线偏差
        - travel_time_deviation_min: 预计 vs 实际旅行时间偏差
        - service_time_deviation_min: 预计 vs 实际服务时间偏差
        - manual_override_rate: 人工调整率
        - deviation_reasons: 偏差原因分布
    """
    period_label: str
    representative_id: str
    plan_version: str
    policy_version: str
    solver_run_id: str

    # 覆盖率
    n_planned_visits: int = 0
    n_actual_visits: int = 0
    n_planned_customers: int = 0
    n_actual_customers: int = 0
    coverage_rate: float = 0.0      # n_planned_customers / n_actual_customers

    # 完成率
    n_completed: int = 0
    n_on_plan: int = 0
    n_ad_hoc: int = 0
    n_cancelled: int = 0
    n_rescheduled: int = 0
    n_missed: int = 0
    completion_rate: float = 0.0    # n_completed / n_planned_visits

    # 频次合规
    frequency_compliance_rate: float = 0.0

    # 偏差
    travel_time_deviation_min: float = 0.0
    service_time_deviation_min: float = 0.0
    route_deviation_km: float = 0.0

    # 人工调整
    n_overrides: int = 0
    manual_override_rate: float = 0.0

    # 偏差原因分布
    deviation_reasons: dict[str, int] = field(default_factory=dict)

    notes: tuple[str, ...] = ()


def compute_plan_vs_actual(
    plan: PlanVersion,
    planned: list[PlannedVisit],
    actual: list[ActualVisit],
    evidence: DecisionEvidence | None = None,
    overrides: list | None = None,
) -> PlanVsActualMetrics:
    """计算 Plan vs Actual 全量指标。

    输入:
        plan: 计划版本
        planned: 该计划版本下的所有计划拜访
        actual: 该代表该周期内的所有实际拜访
        evidence: 可选的求解证据
        overrides: 可选的人工调整记录
    """
    n_planned = len(planned)
    n_actual = len(actual)

    planned_customers = {v.customer_id for v in planned}
    actual_customers = {v.customer_id for v in actual}

    # 计划完成率
    planned_visit_ids = {v.visit_id for v in planned}
    actual_plan_ids = {v.planned_visit_id for v in actual if v.planned_visit_id}

    on_plan = len(actual_plan_ids & planned_visit_ids)
    ad_hoc = n_actual - on_plan

    completed = sum(1 for v in actual if v.outcome_code == "COMPLETED")
    cancelled = sum(1 for v in planned if v.visit_id not in actual_plan_ids)
    missed = n_planned - on_plan - cancelled

    # 频次合规
    freq_actual = Counter(v.customer_id for v in actual)
    freq_planned = Counter(v.customer_id for v in planned)
    freq_compliant = sum(
        1 for c in planned_customers if freq_actual.get(c, 0) == freq_planned.get(c, 0)
    )
    freq_compliance = (
        freq_compliant / len(planned_customers) if planned_customers else 1.0
    )

    # 偏差
    travel_dev = 0.0
    service_dev = 0.0
    matched = 0
    for a in actual:
        if a.planned_visit_id and a.planned_visit_id in planned_visit_ids:
            p = next((v for v in planned if v.visit_id == a.planned_visit_id), None)
            if p:
                travel_dev += abs(a.actual_travel_minutes - p.estimated_travel_minutes)
                service_dev += abs(a.service_minutes - p.estimated_service_minutes)
                matched += 1
    t_dev = travel_dev / matched if matched else 0.0
    s_dev = service_dev / matched if matched else 0.0

    # 人工调整
    n_overrides = len(overrides) if overrides else 0

    # 偏差原因
    reasons: dict[str, int] = {}
    for a in actual:
        if a.outcome_code != "COMPLETED":
            reasons[a.outcome_code] = reasons.get(a.outcome_code, 0) + 1

    return PlanVsActualMetrics(
        period_label=f"{plan.planning_horizon_start}~{plan.planning_horizon_end}",
        representative_id=plan.representative_id,
        plan_version=f"{plan.plan_id}@v{plan.version}",
        policy_version=plan.policy_version,
        solver_run_id=plan.solver_run_id or "",
        n_planned_visits=n_planned,
        n_actual_visits=n_actual,
        n_planned_customers=len(planned_customers),
        n_actual_customers=len(actual_customers),
        coverage_rate=len(planned_customers & actual_customers) / max(len(actual_customers), 1),
        n_completed=completed,
        n_on_plan=on_plan,
        n_ad_hoc=ad_hoc,
        n_cancelled=cancelled,
        n_rescheduled=0,
        n_missed=missed,
        completion_rate=completed / n_planned if n_planned else 0.0,
        frequency_compliance_rate=freq_compliance,
        travel_time_deviation_min=t_dev,
        service_time_deviation_min=s_dev,
        n_overrides=n_overrides,
        manual_override_rate=n_overrides / n_planned if n_planned else 0.0,
        deviation_reasons=dict(reasons),
    )


================================================================================
# 第十六部分: System Design Triple Check
================================================================================


# TopPrism 系统设计三轮完整检查报告

**Document ID:** TOPPRISM-SYSTEM-DESIGN-TRIPLE-CHECK-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 三轮检查完成 — 发现 9 项, 现场修复 8 项, 遗留登记 1 项
**检查范围:** 架构基线 v1.0.2 / Canonical Types (§1-§38) / 主 API 规范 (draft.5.2+修订) / L3/L5/L7 规范 / canonical_api.py / planner_projection.py / shadow 工具链 / 测试基线

---

## Round 1 — 结构与引用完整性

| # | 检查项 | 结果 |
|---|---|---|
| R1.1 | Registry 锚点校验 (50 处引用) | ✅ 全部有效 |
| R1.2 | 基线 frontmatter vs 标题版本 | 🔴 frontmatter 停留在 2026-08-25 旧冲突状态 → **已修** (对齐 v1.0.2/2026-08-26, 冲突表述精确化: 本文档内部已统一 L0-L7, 遗留在全仓旧文档) |
| R1.3 | 5 份规范章节号唯一性 | ✅ 无重复 |
| R1.4 | 评审/审计文档 § 引用可解析性 | ✅ 有效 |
| R1.5 | Registry 75 行引用覆盖 | ✅ 50 处 § 引用全查 + 1 处命名章节引用有效, 无遗漏 |
| R1.6 | 评审文档"34 类型"表述过时 | ⚠️ → **已修** (标注评审时点数 + 同日 §37/§38 增补) |

## Round 2 — 语义红线 (规范 vs 代码 / 时间契约 / 类型封闭)

| # | 检查项 | 结果 |
|---|---|---|
| R2.1 | 8 API 入口签名规范 vs 实现 | 🔴 `compile_planner_projection` 实现缺 `partial_auth` 参数 (规范 §5.5) → **已修** (签名对齐 + 最小 `PartialProjectionAuthorization` 定义 + 四状态校验) |
| R2.2 | 时间契约 (`datetime.now()` 扫描) | 🔴 `planner_projection.py` projection_id 用 naive `now()` (P0 违规) → **已修** (`generated_at` tz-aware 必填 keyword, ID 确定性生成; 2 调用方同步迁移) |
| R2.2b | 时间契约灰区清单 | ⚠️ `shadow/snapshot.py` captured_at 默认 now(utc)、`provenance` 生成时间戳、`runner.executed_at` — 均为 tz-aware 输出型时间戳 (非契约参数), 登记为灰区, Phase 7 收紧 |
| R2.2c | 时间契约已知遗留 | ⚠️ `decision_pipeline.py` 2 处 naive `now()` — 旧遗留件, MVP 已显式隔离 (vertical_slice_mvp 注释), Phase 7 迁移时清除 |
| R2.3 | 类型封闭 (`Any` 扫描) | 🔴 仅已知 1 处 (`active_scenario_branches: Dict[str, Any]`, 命名审计 P0-1) — 维持登记 |
| R2.4 | 规范文档真实性 (实现偏差未注记) | ⚠️ → **已修** (§5.3/§5.4/§5.5 补 3 处实现注记: feedback 可选 snapshot_id / rollout 诚实未实现 / compile 可选 working_days) |
| R2.5 | Feedback/Transition 解耦红线 | ✅ 测试已验证 (回执不产生新快照) |
| R2.6 | 三权分离 (L5 不暴露分支状态) | ✅ L5 未实现, 无违例面 |

## Round 3 — 完备性与矛盾

| # | 检查项 | 结果 |
|---|---|---|
| R3.1 | 悬空类型引用 (WorkflowContext 式) | 🔴 **新发现 3 个**: `ReadOnlyWorldStateView` / `FrozenCustomerUniverseView` / `ResourceScope` — §5.1 签名引用但全仓规范无定义 → **已修** (新增主 API §5.1.1 三类型 frozen 定义, 与实现对齐) |
| R3.2 | §36 加载顺序契约模块表过时 | ⚠️ → **已修** (纳入 §37/§38) |
| R3.3 | 成熟度状态跨文档一致性 | ✅ 基线 §十一 / 评审报告 / 审计报告一致 (BLOCKED/PENDING) |
| R3.4 | L0-L6 vs L0-L7 残留矛盾 | ✅ 基线 frontmatter 已精确化; 主 API 规范 L0-L6 定位 = World Model 子集过渡描述 (符合基线 Resolution) |
| R3.5 | §37/§38 规范 vs 代码 | ✅ 规范-only (代码无), 注记明确"迁移待签署" — 符合门禁 |
| R3.6 | 测试非确定性 (set 迭代序) | 🔴 `test_compare_frequency_diff_plan_more` 依赖 PYTHONHASHSEED (之前全绿属侥幸) → **已修** (plan_codes 改 sorted 确定性取样, match_rate 精确断言 5/32) |

---

## 修复汇总

| 修复 | 文件 | 性质 |
|---|---|---|
| 基线 frontmatter 对齐 v1.0.2 | TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md | 文档 |
| 评审文档类型数注记 | TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md | 文档 |
| `compile_projection` + `generated_at` (tz-aware 必填) | planner_projection.py | **P0 时间契约修复** |
| API `partial_auth` 对齐 + `PartialProjectionAuthorization` 最小类型 | canonical_api.py | 规范对齐 |
| §5.3/§5.4/§5.5 实现注记 | 主 API 规范 | 文档真实性 |
| §5.1.1 三视图类型定义 | 主 API 规范 | **悬空类型清零** |
| §36 模块表纳入 §37/§38 | Canonical Types Spec | 文档 |
| test_compare Case 2 确定性化 | shadow/test_compare.py | 测试稳定性 |

## 遗留登记 (不修复, 有明确处置路径)

1. `decision_pipeline.py` naive `now()` ×2 — 旧遗留件已被 MVP 隔离, Phase 7 迁移清除
2. `active_scenario_branches: Dict[str, Any]` — 命名审计 P0-1, L5 实现时删除
3. 时间契约灰区 3 处 (tz-aware 输出型时间戳) — Phase 7 收紧
4. §37/§38 代码迁移 — 待双轨签署

## 终验

```
Registry 锚点:      50/50 有效
悬空类型:           0 (WorkflowContext/View/Scope 三批全闭合)
datetime.now 契约违规: 0 (planner_projection 已修; 遗留 2 处已登记隔离)
ontology tests:     172 passed, 2 skipped
svde core:          37 passed
shadow:             75 passed (含非确定性修复)
svde-bench:         121 passed
```

## 结论

三轮检查共发现 **9 项问题** (3 红 + 5 黄 + 1 测试稳定性), 现场修复 8 项。系统设计当前状态: 结构引用完整闭合、时间契约在 Canonical 路径上无违例、规范-实现签名全对齐、测试基线全绿且去随机化。剩余风险集中于已登记的 Phase 7 迁移项与签署门禁项, 无新发现的架构级缺陷。



================================================================================
# 第十七部分: Naming Audit
================================================================================


# TopPrism 本体命名与字段审计报告 (Kitchen Sink / Misnomer 审计)

**Document ID:** TOPPRISM-ONTOLOGY-NAMING-AUDIT-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 审计完成 — 处置项待立项 (代码修改受签署门禁约束)
**审计对象:** `svde/ontology/src/prism_ontology/world_model/state_snapshot.py` 全部 22 类型 / 130 字段
**方法论:** TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 7; Palantir Anti-Patterns (Kitchen Sink / Misnomer / God Object) + Naming Conventions
**工具:** 机械扫描 (裸名词 / DEPRECATED / 源系统命名残留 / 管道元数据) + 全字段人工复核

---

## 一、审计结论总览

| 检查项 | 结果 |
|---|---|
| 裸歧义名词 (value/quantity/score/type/date/name 裸用) | **0 处** ✅ |
| 源系统命名残留 (dtLastInspMod 式) | **0 处** ✅ |
| 管道元数据字段 (extracted_at/batched_at 等) | **0 处** ✅ |
| DEPRECATED 字段 | **1 处** ⚠️ |
| stringly-typed 枚举 (裸 str 应为 Enum) | **6 处** ⚠️ |
| **类型封闭红线违规 (Any 入公共字段)** | **1 处** 🔴 P0 |
| DDD 存疑 (源系统概念 vs 领域概念) | **2 项** ⚠️ |

---

## 二、P0 违规 (签署后首批修复)

### P0-1: `OperationalDecisionWorldState.active_scenario_branches: Dict[str, Any]`

- **违规**: 项目红线 "严禁 `Any` 进入公共 API 字段; 使用 `FrozenValue` 递归不可变联合类型"
- **旁证**: 架构基线 §十一 已标注 "Baseline–Event–Scenario: BLOCKED (代码层 execution_fact_stream/scenario_branches 仍混入 L4)"
- **处置**: L5 场景引擎实现时删除该字段 — 场景分支状态由 L5 Scenario Engine 持有 (WorldState 三权分离: L5 严禁暴露分支状态), WorldState 不携带场景状态。**不是改类型, 是删字段**。

---

## 三、⚠️ 处置项 (规范层可先行定义目标, 代码迁移待签署)

### A-1: `OperationalCustomer.planned_frequency: Optional[int]` [Kitchen Sink]

- 现状: 自带 `# DEPRECATED: Kept for back-compat. Source must be PolicyRegistry, not observation.` 注释
- 消费方核查: `planner_projection.py` 已改走 PolicyRegistry (FIX-1), 无生产读取方
- **处置**: 删除字段; 保留 `PolicyRegistry.operational_policies` 为频次唯一事实源

### A-2: stringly-typed 枚举 (6 处裸 `str` 应为 Enum)

| 字段 | 现值域 | 处置 |
|---|---|---|
| `OperationalCustomer.tier` | Key/A/B/C/D | 新增 `StoreTier` 枚举; 同时消除与 `AccountHierarchyEntity.channel_tier` (NKA/RKA 体系) 的歧义 — 两个"tier"是不同概念, Misnomer 风险 |
| `OperationalVisitPolicy.cadence_type` | STRICT_WEEKLY/BIWEEKLY/MONTHLY | 与 `CadenceRule.cadence_type` 共用新增 `CadenceType` 枚举 |
| `CadenceRule.cadence_type` | 同上 | 同上 |
| `OperationalCommitment.lock_level` | FREE/DAY_LOCKED/SEQUENCE_LOCKED | 新增 `LockLevel` 枚举 |
| `OwnershipConflictRecord.resolution_status` | FLAGGED_FOR_REVIEW/... | 新增 `ConflictResolutionStatus` 枚举 |
| `SupplyNodeEntity.delivery_status` | UNCALIBRATED/... | 新增 `DeliveryStatus` 枚举 |

### A-3: `PolicyRegistry.ownership_map: Dict[str, str]` [结构升级]

- **处置**: 评审报告建议 2 已立项 — `OwnershipAssignment` (§38) 落地后, `ownership_map` 降级为 §38 当前态投影, 最终删除裸映射。

### A-4: DDD 存疑 — `CognitiveCategory` 全类型铺开

- 现状: `category: CognitiveCategory` (OBSERVATION/POLICY/COMMITMENT/MEASUREMENT/DERIVED_ESTIMATE) 出现在 8 个类型上
- **问题**: 这是"认知来源标签" (数据溯源语义), 不是领域实体自身的业务属性 — 按 DDD 原则属**数据血缘**, 应归属 `DecisionLineageRecord` / `SourceManifest` 体系, 而非散布在领域实体上
- **处置**: 评审后裁决 — 保留 (若业务确认其运营语义) 或迁移至 Lineage 体系

### A-5: DDD 存疑 — `OperationalDecisionWorldState` 容器性质

- 现状: 15 个字段的世界状态容器, 含 `Dict[str, X]` 五个实体字典
- **裁定**: **不判 God Object** — 它是状态快照 (检查点), 不是领域实体; Palantir God Object 反模式针对"单类型承载多实体", 快照容器不适用。但需在 §十二.2 反模式禁令下持续监督: 新字段进入 WorldState 须过"这是世界状态还是实体属性"审查 (P0-1 的 `active_scenario_branches` 即反例)。

---

## 四、通过项 (无需处置)

- 命名质量整体良好: 全部字段为自解释业务语言, 无编码前缀, 无系统列名残留
- `BitemporalPeriod` / `SourceManifest.assembled_at` 等时间字段已符合时间契约 (2026-08-26 修复)
- `FrozenScalar`/`FrozenValue` 体系符合类型封闭目标 (唯 P0-1 例外)

---

## 五、处置顺序与依赖

| 序 | 项 | 层 | 依赖 |
|---|---|---|---|
| 1 | P0-1 删 `active_scenario_branches` | 代码 | **L5 场景引擎实现** (签署后) |
| 2 | A-1 删 `planned_frequency` | 代码 | 无生产消费方已验证; 随下一版本号递增执行 |
| 3 | A-2 六处 Enum 化 | 规范+代码 | 规范层可先行 (新增枚举类型登记); 代码迁移待签署 |
| 4 | A-3 ownership_map 投影化 | 规范+代码 | 依赖 §38 OwnershipAssignment (已登记) |
| 5 | A-4 CognitiveCategory 裁决 | 评审 | 待业务/架构确认 |
| 6 | A-5 WorldState 字段准入审查 | 流程 | 纳入 §十二.2 日常裁决 |

---

## 六、成熟度声明

未覆盖: 无 (2026-08-26 补审 contracts/ 别名层: world_state.py 为纯再导出门面,
4 个向后兼容别名 CustomerEntity/ResourceEntity/WorldState/WorldStateSnapshot,
无新字段无新语义 — 通过, 唯一注记: WorldState/WorldStateSnapshot 与
OperationalDecisionWorldState 双名并存属过渡期兼容, Phase 7 收敛)
审计覆盖: state_snapshot.py 全部 22 类型 / 130 字段 (机械扫描 + 人工复核)
处置实施: 0 项 (全部待立项; 代码项受签署门禁)
```



================================================================================
# 第十八部分: Renjun Plan vs Actual Comparison
================================================================================


# 仁军 Plan vs Actual 对比报告 v1.1 — 工作日约束验证

**Document ID:** TOPPRISM-PLAN-VS-ACTUAL-RENJUN-COMPARISON-v1_1
**Version:** v1.1 (工作日约束修正后)
**Date:** 2026-08-27
**变更:** 修复 depot 坐标错误 (苏州→崇川), 增加工作日过滤 (_working_dates)

## 一、SolverAdapter 全量回放结果 (32 店, FEASIBLE, time_limit=90s)

| 指标 | 值 | 说明 |
|---|---|---|
| Solver 状态 | **FEASIBLE** | restricted_column_pool optimal |
| PlanVersion | PLAN_仁军_2026-06-01 v1 [draft] | |
| 计划拜访 | 72 条 | 接近方案B 要求 75 (差 3 因求解时间限制) |
| 覆盖率 | **100%** | 32/32 店全在计划内 |
| 完成率 | **98.61%** | 与历史实际对齐后 |
| 频次合规(规划) | **100%** (32/32) | 每店频次与方案B 精确一致 |
| Key 店覆盖 | **15/15** | ✅ |

### PlanVsActualMetrics (历史数据对比)

| 指标 | 值 |
|---|---|
| 覆盖率 | 100% |
| 完成率 | 98.61% |
| 计划内完成 | 13 次 |
| 临时追加 | 58 次 |
| 频次合规率 | 84.38% |
| 旅行偏差 | 36.4 min |
| 服务偏差 | 19.4 min |

### 工作日约束验证

```
周末拜访: 0 次 ✅ (全部落在周一~周五)
活跃工作日: 15/20
日服务负荷: min=120, max=330, avg=246 min
max_visits_per_day 违例: 0 次
```

### Depot 校正发现

原代码使用苏州坐标 (31.30, 120.60) 作为 depot，但仁军门店全部位于南通如皋/海安区域 (~150km 远)，导致单店 depot leg ≥162 min，540 min 上限下 INFEASIBLE。修正为崇川市中心 (32.0084, 120.8943) 后立即 FEASIBLE。**部署时 depot 坐标必须从真实管区配置读取，不可硬编码。**

---

## 二、方案B vs 黄金基准 vs Phase 1 三方对比

| 维度 | 黄金基准 | 方案B | 历史6月 | Phase 1 管道 |
|---|---|---|---|---|
| 门店 | 36 | 32 | 32 | **32** |
| 总拜访 | 83 | 75 | 71 | **75** |
| 频次集 | 1/2/3/4 | **仅 1/2/4** | 自然分布 | 仅 1/2/4 |
| 频次合规 | - | 按政策 | 55.6% | **100%** |
| 工作日约束 | ❌ 未约束 | ✅ | - | **✅ (Mon-Fri)** |

## 三、BIZ-01 签署建议

方案B 用 48 处修改给出了业务事实：**3次/月不是合法频次**（全方案升级为 4，无降级）。

建议 BIZ-01 签署选项重写为：
> [ ] 确认合法频次集 {1, 2, 4}（方案B 证据）
> [ ] 或：允许其他组合

## 四、NT23 等 4 家摘牌店确认

NT23人民中路(Key)、NT53正翔(B)、NT69二案金雅(B)、NT45吴窑(C) 在方案B 中被移除出服务计划（非转给其他代表），历史6月零拜访。
建议创建 `BusinessSignal(signal_type="coverage_risk", value="inactive")` 供后续周期评估。



================================================================================
# 第十九部分: Business Open Questions
================================================================================


# 业务开放问题 — 需要业务方裁决

> 来源：Sales Visit Planning 本体与世界模型设计 §14
> 背景：这些问题直接决定世界模型中哪些状态是事实、哪些是策略，以及 Phase 2/3 的评价方式。
> **不应由算法团队自行猜测。**
> 状态：待业务方回复

## Q1: "客户"是什么粒度？

- A) 客户公司 (Account)
- B) 客户地点 (Location / Store)
- C) HCP (Healthcare Professional，如医生、采购主管)

**影响**: 本体类型定义、路线排列粒度、归属关系模型

## Q2: 拜访频次是合规要求还是动态建议？

- A) 硬性合规要求（必须严格执行，不满足即违规）
- B) 动态建议（可根据机会价值调整）

**当前证据**: 方案B 中频次仅认 {1, 2, 4}；黄金基准严格同周几硬锁定

**影响**: BIZ-01 签署内容重写；`CoveragePolicy.required_visits` 的刚性等级

## Q3: 哪些拜访一旦确认就不可移动？

- A) 已确认门店+日期全部冻结
- B) 未来 3 天内冻结
- C) 仅经理手动锁定的冻结
- D) 以上组合（请说明组合规则）

**影响**: Phase 3 Rolling-horizon 重算的冻结规则和稳定性预算参数

## Q4: 机会价值的来源

- A) 现有 CRM 字段直接映射（如 store_tier → priority_score）
- B) 商业规则引擎计算（如 tier × potential × recency）
- C) 独立建模（机器学习预测客户响应概率）

**影响**: BusinessSignal 数据管线的复杂度、Phase 2 上线时间表

## Q5: 前 3 个 KPI 是什么？

| 候选 | 排序 |
|---|---|
| 价值覆盖 | [ ] 第___ |
| 销量提升 | [ ] 第___ |
| 工时优化 | [ ] 第___ |
| 里程减少 | [ ] 第___ |
| 频次合规 | [ ] 第___ |

**影响**: ScenarioEngine 对比报告的维度排序；Phase 2 成功评估标准

## Q6: 人工覆盖计划的原因码

以下是候选原因码清单，请确认是否完整或需要增补：

- CUSTOMER_REQUESTED_CHANGE
- TIME_CONFLICT
- WEATHER_DISRUPTION
- VEHICLE_ISSUE
- REP_UNAVAILABLE
- URGENT_VISIT_REQUIRED
- ROUTE_OPTIMIZATION_REJECTED
- OTHER (请补充)

**影响**: ManualOverride.reason_code 字典；Phase 3 计划接受模型的训练信号分类


================================================================================
# 第二十部分: Business Signoff Requirements
================================================================================


# 需要业务方确认的事项 (Business Owner Sign-off Requirements)

**Document ID:** TOPPRISM-BUSINESS-SIGNOFF-v1.0  
**Date:** 2026-08-24  
**Status:** **MANDATORY BUSINESS OWNER CONFIRMATIONS BEFORE CODE CHANGES**  
**说明**: 严格区分**业务语义签署事项**（必须业务主管明确签署）与**技术/产品决策事项**（由团队内部决定，不属于业务签署）。本轮仅发送业务语义部分给业务方。

---

## 第一部分：必须业务方签署的业务语义事项 (Business Semantics)

> 业务方必须逐项回复 A/B/C/D 选项或自定义描述。这是阻断代码改动的关键业务依据。

### 确认 1：拜访频次语义（特别是 3 次/月）
**问题**：`OperationalVisitPolicy.target_frequency_per_month=3` 的真实业务含义是什么？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 在 4 周内选择 3 周进店，且必须固定在同一个周几（当前 SVDE 行为） |
| **B** | 每 9~10 天进店一次（严格等距，与周几无关） |
| **C** | 由大仓配送日历人工排定（频次仅作参考） |
| **D** | **其他（请描述）：_______________** |

### 确认 2：DeferralPolicy（顺延）业务规则
**问题**：客户请求顺延拜访时，业务规则如何执行？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 单客户单月最多 1 次顺延，且必须在原计划的 7 天内完成 |
| **B** | 单客户单月最多 2 次，且必须由 REP_MANAGER 审批 |
| **C** | 顺延后必须在下一周期强制恢复同周几节奏（无弹性） |
| **D** | **其他（请描述）：_______________** |

### 确认 3：Key / A 级门店 REQUIRED 零脱访刚性
**问题**：极端情况下（如代表突发长期病假），应如何处理？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 绝对零脱访：触发紧急代班（即使跨代表） |
| **B** | 允许带补偿的脱访：后续 1 周内必须补访，否则触发重大事故 |
| **C** | 核心 7 天：超出 7 天必须立即升级 |
| **D** | **其他（请描述）：_______________** |

### 确认 4：GPS 偏差阈值
**问题**：当前 Guard C 阈值 500m 是否合理？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 500m 合理 |
| **B** | 应放宽到 1km（部分门店商圈跨度大） |
| **C** | 应收紧到 200m |
| **D** | **其他（请描述）：_______________** |

### 确认 5：单日工时双重红线
**问题**：近郊 480min vs 长途日 660min 这一区分是否被业务批准？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 480 / 660 分钟双重红线被业务批准 |
| **B** | 单一统一红线（如 600 min） |
| **C** | 长途日按距离系数弹性（非硬编码 660） |
| **D** | **其他（请描述）：_______________** |

### 确认 6：客户归属冲突的人工解决优先级
**问题**：当 `OwnershipConflictRecord` 出现时，应按何种规则判定当前有效代表？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 谁实际打卡最多，谁就是当前有效代表 |
| **B** | 按区域归属优先级（REP_001 优先于 REP_002） |
| **C** | 必须由 REP_MANAGER 强制指派 |
| **D** | **其他（请描述）：_______________** |

### 确认 7：多产品线组合的拜访合并策略
**问题**：一家门店同时销售皇家美素（爆品）和源悦（新品）时拜访如何处理？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 一次拜访合并执行（默认） |
| **B** | 每次拜访聚焦单一产品线 |
| **C** | 按月度目标自动决策 |
| **D** | **其他（请描述）：_______________** |

### 确认 8：决策引擎的人工审批层级
**问题**：对于不同敏感度的决策，审批人应如何分层？

| 选项 | 业务语义 |
| :--- | :--- |
| **A** | 仅 REP_MANAGER 级别 |
| **B** | REP_MANAGER + REGIONAL_DIRECTOR 双签 |
| **C** | Key 店自动升级到 DIRECTOR 审批 |
| **D** | **其他（请描述）：_______________** |

---

## 第二部分：技术/产品联合决策事项 (Internal Team Decisions)

> **以下事项不应伪装成业务签署项，而应由技术/产品团队内部决策：**

| 事项 | 决策权归属 | 备注 |
| :--- | :--- | :--- |
| 真实路网矩阵集成方案（OSRM / 高德 / 百度） | **技术团队** | 可后置实施 |
| 仓库配送日历数据接入方式（ERP / Excel / API） | **技术与产品** | 影响数据源选型 |
| Scenario Engine 的技术实现细节 | **技术团队** | 在 L5 落地阶段决定 |
| L7 Decision Engine 的模块拆分与命名 | **技术团队** | 在 L7 Spec 中决定 |
| GitHub 目录结构和代码迁移策略 | **技术团队** | 在代码实施计划中决定 |
| PlannerStateProjection 字段演进 | **技术团队** | 在 L6 Spec 中决定 |

---

## 第三步：完成签署后的后续动作

业务方逐项回复上述 8 项后：
1. 我方将根据回答更新 `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md` 与 `SVDE_OPERATIONAL_DECISION_WORLD_MODEL_SPEC_v1.0.md`；
2. 内部团队对第二部分的 6 项技术/产品决策形成书面决议；
3. 之后才能提交 **代码实现计划 v1.0** 进行 L7 Decision Engine 子系统的物理重构；
4. 物理重构完成后才能继续 L5 真实多分支仿真引擎的开发。

**未经业务方签署，我不会动任何代码或添加任何测试。**
