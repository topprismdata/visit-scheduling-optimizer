# TopPrism Canonical Enterprise Architecture Decision Baseline v1.0

**Document ID:** TOPPRISM-CANONICAL-ENTERPRISE-ARCHITECTURE-DECISION-BASELINE-v1.0  
**Status:** ARCHITECTURE DECISION DRAFT — NOT FROZEN  
**Date:** 2026-08-25  
**Scope:** Prism Enterprise World Model、Prism Decision Engine、SVDE Sales Visit Decision Engine  
**Code status:** No runtime changes authorized by this document

---

## 1. Decision Summary

本文件将 TopPrism 的整体架构收敛为唯一的 L0–L7 模型，并明确三条相互独立的生命周期：

```text
Decision Publication Lifecycle
Commitment Lifecycle
Execution Lifecycle
```

核心架构决策：

1. 采用 TopPrism L0–L7 分层，废止“L6 = 规划与执行”的旧解释；
2. L4 只代表现实基线状态，不承载情景分支；
3. L5 负责反事实情景执行，但不向 L7 暴露分支 WorldState；
4. L6 只负责把 World Model 状态编译为版本化数学投影；
5. L7 负责意图、候选方案、权衡、审计、审批、决策发布和执行编排；
6. 审批、承诺锁定和实际执行不再共享同一个状态；
7. 只有经验证的执行事件才能生成新的现实基线快照。

本文件是架构基线草案，不代表业务签署、技术签署或 API Freeze 已完成。

---

## 2. Canonical Product and System Topology

```text
TopPrism
└── Prism Enterprise Decision Intelligence
    ├── Prism Enterprise World Model
    │   ├── L0 Foundational Architecture
    │   ├── L1 General Metamodel
    │   ├── L2 Domain Ontology
    │   ├── L3 Dynamics & State Transition
    │   ├── L4 Baseline World State
    │   ├── L5 Scenario & Counterfactual Engine
    │   └── L6 Planner Projection
    │
    └── Prism Decision Engine
        └── L7 Intent → Candidate → Audit → Approval → Dispatch
            └── Domain Decision Solver
                └── SVDE Sales Visit Decision Engine
```

### 2.1 Product identity

- **Prism Enterprise World Model**：保存和演化企业现实的可计算表示；
- **Prism Decision Engine**：在世界模型之上选择和治理行动；
- **SVDE**：销售拜访领域决策求解器与适配器，不是整个 Enterprise World Model，也不是整个 Decision Engine。

### 2.2 Canonical dependency direction

```text
Ontology → World State → Transition / Scenario → Projection → Decision
```

禁止以下反向依赖：

- Solver 重新解释领域术语；
- Decision Engine 持有或修改 WorldState；
- Scenario 结果覆盖现实快照；
- 领域适配器修改 L0/L1 基础语义；
- 执行结果直接覆盖历史状态。

---

## 3. Canonical L0–L7 Responsibility Model

| 层级 | Canonical 名称 | 所属系统 | 负责什么 | 不负责什么 |
|---|---|---|---|---|
| L0 | Foundational Architecture | World Model | 系统边界、时间、证据、状态、转移和回放公理 | 领域规则、算法、客户字段 |
| L1 | General Metamodel | World Model | Entity、State、Observation、Policy、Commitment、Action、Event、Scenario 等元类型 | 具体行业语义 |
| L2 | Domain Ontology | World Model | Customer、Cadence、Ownership、VisitDemand 等领域概念与关系 | 求解器参数、审批逻辑 |
| L3 | Dynamics & Transition | World Model | 合法状态转移、Guard、前置条件、后置效果、失败和补偿 | 候选方案选择 |
| L4 | Baseline World State | World Model | 某一 snapshot 下已确认的现实事实、政策、承诺和历史执行结果 | 假设分支、候选计划、审批状态 |
| L5 | Scenario & Counterfactual | World Model | 在基线之上执行假设动作序列并产生 ScenarioResult | 修改基线、选择最终方案 |
| L6 | Planner Projection | World Model → Decision Engine | 生成绑定 snapshot/scenario/cost model 的数学投影 | 求解、权衡、审批、执行 |
| L7 | Enterprise Decision Engine | Decision Engine | 意图、能力编排、候选方案、审计、权衡、审批、发布、派发 | 持有或直接修改 WorldState |

### 3.1 L6 projection contract invariant

每个 `PlannerStateProjection` 必须至少绑定：

```text
source_snapshot_id
scenario_id (nullable for baseline planning)
intent_id
policy_version_set
cost_model_id
projection_version
evidence_refs
quality_status
```

投影不是 WorldState，也不是 CandidatePlan。它是可重放、可审计的求解输入切片。

---

## 4. State Ownership and Storage Boundaries

### 4.1 L4 BaselineWorldState

L4 只保存已经确认属于现实基线的内容：

- 经过证据绑定的实体和关系；
- 当前有效的版本化政策；
- 已确认的业务承诺；
- 已验证并归并的执行事实；
- 未解决冲突和数据质量状态；
- snapshot 的时间、版本和来源清单。

L4 不保存：

- `BranchedWorldState`；
- 未批准的 CandidatePlan；
- 尚未执行的假设结果；
- 仅由求解器产生的临时路线；
- 未经证据升级的政策事实。

### 4.2 ExecutionEventStream

执行事件流是追加式输入，不是 L4 的可变列表字段：

```text
External Execution Event
    → Evidence Validation
    → L3 Transition
    → New L4 Baseline Snapshot
```

同一事件必须具备事件身份、发生时间、接收时间、来源、主体、目标实体和证据引用。

### 4.3 L5 ScenarioState

L5 内部可以创建分支状态，但分支必须绑定：

```text
base_snapshot_id
assumption_set
perturbation_events
transition_model_version
simulation_time
```

L5 对外只返回：

```text
ScenarioResult = StateDelta + ImpactSummary + Uncertainty + branch_hash
```

不返回、不过渡、也不允许 L7 保存完整 `BranchedWorldState`。

---

## 5. Three Independent Lifecycles

### 5.1 Decision Publication Lifecycle

```text
DRAFT
  → EVALUATED
  → APPROVED
  → PUBLISHED
  → REVOKED / EXPIRED
```

含义：决策产物是否已经通过审计、审批和发布治理。

它不表示现实世界已经执行。

### 5.2 Commitment Lifecycle

```text
AVAILABLE
  → RESERVED
  → COMMITTED
  → RELEASED / EXPIRED / CANCELLED
```

含义：业务承诺或资源锁定是否已经占用和生效。

`RESERVED` 是事务临时状态，`COMMITTED` 是 World Model 中的业务承诺状态。回滚事务不得伪装成历史上从未发生，必须保留审计事件。

### 5.3 Execution Lifecycle

```text
PLANNED
  → DISPATCHED
  → IN_PROGRESS
  → COMPLETED / MISSED / ABORTED
```

含义：现实执行是否已经被下发、开始和证实。

`COMPLETED` 只能由经过验证的 `ExecutionEvent` 产生，不能由审批或发布动作直接产生。

### 5.4 Cross-lifecycle event mapping

```text
Decision APPROVED
    → Commitment RESERVED / COMMITTED
    → Decision PUBLISHED
    → Execution DISPATCHED
    → External ExecutionEvent
    → Execution COMPLETED / MISSED
    → L3 Transition
    → New L4 Snapshot
```

三条生命周期必须通过显式事件关联，禁止共享一个含义不清的 `COMMITTED` 状态。

---

## 6. Canonical Request and Feedback Flow

```text
1. Business Intent
       ↓
2. World Model reads versioned baseline snapshot
       ↓
3. Optional L5 Scenario Rollout
       ↓
4. L6 Planner Projection
       ↓
5. L7 Domain Solver generates CandidatePlan
       ↓
6. L7 performs trade-off evaluation and independent audit
       ↓
7. Human / Policy approval
       ↓
8. World Model Commitment transition
       ↓
9. L7 dispatches execution
       ↓
10. External system emits ExecutionEvent
       ↓
11. World Model validates event and creates new baseline snapshot
```

### 6.1 Prohibited shortcuts

- `WorldState → Solver → DecisionArtifact` without L6 projection;
- `CandidatePlan → COMPLETED` without an execution event;
- `Observation → Policy` without evidence and governance;
- `ScenarioResult → BaselineWorldState` without real execution confirmation;
- `DecisionEngine → mutate WorldState` without L3 transition API。

---

## 7. Business Vertical Slice Required for Architecture Acceptance

首个架构验收场景固定为：

```text
代表请假 3 天
→ 识别受影响客户、频次和承诺
→ 生成延期、改派、保持原计划等情景
→ 比较覆盖、承诺风险、工时和在途成本
→ 生成周期计划投影
→ 形成候选决策
→ 审计和人工审批
→ 更新承诺状态并下发
→ 接收执行反馈
→ 生成新的现实快照
```

必须能够回答：

- 哪些是现实事实；
- 哪些是政策；
- 哪些是已锁定承诺；
- 哪些是情景假设；
- 哪些是求解器输出；
- 哪些状态已经真正执行；
- 每个变化由什么事件和证据支持。

---

## 8. Freeze Gates After This Baseline

在以下事项完成前，本文件和 Canonical API 均保持 Draft：

1. 基础架构规范、L0–L7 矩阵和边界文档全部采用本分层；
2. L4/L5/ExecutionEventStream 语义和存储边界完成统一；
3. 三条生命周期通过业务和技术评审；
4. 频次、归属、承诺和延期政策的来源与责任人完成业务确认；
5. 代表请假垂直切片完成真实数据回放；
6. ScenarioResult、PlannerProjection、DecisionArtifact 能被同一 snapshot 链接；
7. 执行反馈能够形成下一版 L4 snapshot；
8. 只有在架构门禁通过后，才进入 runtime 重构和 Canonical API Freeze。

---

## 9. Decision Log

| 决策项 | 当前决定 | 状态 |
|---|---|---|
| Canonical layer taxonomy | 采用 L0–L7 | 待文档同步 |
| Baseline vs Scenario | L4 与 L5 分离 | 待类型/API 设计 |
| Execution events | 追加事件流，经 L3 生成新快照 | 待业务确认来源 |
| Approval vs Commitment | 三条生命周期独立 | 待技术评审 |
| Solver entry | 只能消费 L6 Projection | 待桥接重构 |
| First vertical slice | 代表请假 3 天重排 | 待真实数据验证 |

