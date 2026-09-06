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
