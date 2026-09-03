# TopPrism Enterprise World Model — Architecture Audit Round 1

**Document ID:** TOPPRISM-ARCHITECTURE-AUDIT-ROUND1-v1.0  
**Status:** REVIEW DRAFT — NOT A FREEZE DECISION  
**Date:** 2026-08-25  
**Scope:** World Model、Decision Engine、Ontology、State Transition、Scenario、Planner Projection、Execution Feedback 的整体架构审查  
**代码变更:** 无  
**测试结论:** 本轮不以测试数量作为架构通过条件

---

## 1. 审查结论

当前系统已经形成了大量规范、类型和局部 runtime，但整体架构尚未达到冻结条件。最主要的问题不是某个字段或算法，而是系统存在多套不完全一致的架构解释：

1. 基础架构文档采用 L0–L6，TopPrism 责任矩阵采用 L0–L7；
2. L3 与 L5 对反事实推演和动力学责任存在重叠；
3. L4 WorldState 的唯一所有权与 L7 只读视图访问规则尚未统一；
4. 计划批准、承诺锁定、执行事实在不同文档中混用；
5. 现有代码仍存在绕过 Canonical World Model API 的决策路径；
6. 销售拜访真实数据链路尚未证明“事实 → 状态 → 情景 → 规划 → 决策 → 执行反馈”的完整闭环。

因此，当前正确状态是：

```text
Architecture Alignment:  PARTIAL
World Model Boundary:    RECONCILIATION REQUIRED
Decision Engine Boundary: RECONCILIATION REQUIRED
Scenario Runtime:        NOT PROVEN
Execution Feedback Loop: NOT PROVEN
Canonical API Freeze:    BLOCKED
```

---

## 2. 当前存在的两套分层模型

### 2.1 基础架构文档的分层

`SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` 定义：

```text
L0 基础架构
L1 通用元模型
L2 领域本体
L3 领域动力学与规则
L4 世界状态实例
L5 情景实例
L6 规划与执行
```

### 2.2 TopPrism 责任矩阵的分层

`L0_L7_RESPONSIBILITY_MATRIX.md` 定义：

```text
L0 基础架构
L1 通用元模型
L2 领域本体
L3 动力学引擎
L4 运行时状态实例
L5 情景仿真
L6 Planner Projection
L7 Enterprise Decision Engine
```

### 2.3 影响

这不是编号差异，而是责任模型差异：

- 第一套模型把规划与执行合并在 L6；
- 第二套模型把规划投影放在 L6，把决策、审批和执行放在 L7；
- 领域适配器、求解器、审计器和反馈订阅器在两套模型中的归属因此不同。

### 2.4 必须采取的架构决策

必须选择一套唯一的 Canonical Layer Taxonomy。建议采用 TopPrism L0–L7，因为它能够显式区分：

```text
L6 = World Model 向 Decision Engine 暴露的数学投影
L7 = Decision Engine 对候选方案进行选择、审计、审批和执行编排
```

基础架构文档中的 L6 应改写为“Planner Projection”，并将 Planning、Approval、Execution 放入 L7。

在该决策完成前，不能冻结任何依赖层级编号的 API 或 Registry。

---

## 3. 架构级缺口清单

### A-01：L3 与 L5 的职责没有完全分离（P0）

当前文档同时把以下职责放入 L3 和 L5：

- 状态转移；
- 反事实推演；
- 分支状态；
- 约束求解空间。

建议唯一化为：

```text
L3 State Transition / Dynamics
    定义合法转移函数 δ、守卫、前置条件、后置效果和失败条件

L5 Scenario Engine
    在基线快照上运行一个或多个假设动作序列，调用 L3 产生分支结果
```

L3 是“规则和转移函数”，L5 是“情景执行器和比较器”。L3 不负责选择方案，L5 不重新定义业务规则。

### A-02：L4 基线状态被情景和执行状态污染（P0）

`OperationalDecisionWorldState` 当前同时包含：

- `execution_fact_stream`；
- `active_scenario_branches`；
- 现实客户、资源和政策；
- 访问生命周期记录。

这与“L4 是唯一现实快照、L5 分支不得污染基线、执行反馈应生成新快照”的架构原则不完全一致。

应拆分为：

```text
L4 BaselineWorldState
    现实事实、有效政策、承诺、已确认执行事实

L5 ScenarioState
    base_snapshot_id + assumptions + hypothetical transitions + delta

ExecutionEventStream
    外部事实事件流，不直接作为 L4 的可变字段写入
```

执行事实只有经过反馈验证和状态转移后，才生成新的 L4 快照。

### A-03：批准、承诺、执行事实的生命周期混用（P0）

当前状态机存在：

```text
PLANNED → COMMITTED → IN_PROGRESS → COMPLETED
```

但不同文档对 `COMMITTED` 的含义不一致：有时表示“计划已批准”，有时表示“承诺已锁定”，有时接近“已下发执行”。

建议明确拆分：

```text
CandidatePlan
    → ApprovedDecision
    → CommitmentReserved
    → CommitmentCommitted
    → Dispatched
    → InProgress
    → Completed / Missed
```

其中：

- 审批是治理事件；
- 承诺锁定是 World Model 状态转移；
- 下发是 Decision Engine 的执行编排事件；
- 完成必须由真实 ExecutionEvent 证实。

审批不能直接制造完成事实，计划也不能自动变成执行事实。

### A-04：L4 只读视图和 L6 投影的所有权边界不一致（P1）

责任矩阵允许 L7 使用 L4 局部只读视图进行权衡；World Model Boundary 又要求 L7 不持有、缓存或传递 WorldState。

需要定义唯一访问模型：

```text
World Model owns Snapshot
    ↓
Projection Compiler reads Snapshot
    ↓
Decision Engine receives immutable Projection
```

如果 L7 仍需要业务解释信息，应由 World Model 输出带证据引用的只读 DecisionContextView，而不是让 L7 直接查询任意 L4 字段。

必须明确：

- 视图是否可跨步骤使用；
- 视图是否绑定 snapshot_id；
- 视图是否可进入 DecisionArtifact；
- 视图是否允许被缓存；
- 审计如何证明投影和视图来自同一个快照。

### A-05：Scenario API 的“不可暴露”表述存在歧义（P1）

当前文档一方面说 L5 不暴露给 L7，另一方面又允许 L7 调用 `request_scenario_rollout`。

正确边界应表述为：

```text
L7 可以调用受控 Scenario API；
L7 不可以接收、保存或传播 BranchedWorldState；
L7 只能接收 ScenarioResult / StateDelta / ImpactSummary。
```

这是“暴露接口”与“暴露内部状态实例”的区别，必须在所有边界文档中统一。

### A-06：现有 DecisionPipeline 存在边界旁路（P1）

现有 `prism_ontology/engine/decision_pipeline.py` 直接组合：

```text
Adapter → Solver → PlanAuditor → DecisionArtifact
```

并在 `human_approve_and_publish()` 中直接创建发布产物。该路径没有明确经过：

- Canonical World Model transition API；
- Commitment reservation / commit；
- World Model snapshot 版本校验；
- ExecutionEvent 反馈闭环。

因此当前代码更接近“领域求解流水线”，还不是完整的 L7 Enterprise Decision Engine。

必须将该路径标记为 Domain Solver Pipeline 或迁移到 L7 runtime，并禁止其直接制造 World Model 状态事实。

### A-07：领域桥接仍然从过时的观测字段读取业务政策（P1）

现有 `bridge.py` 的规划意图分发仍读取 `OperationalCustomer.planned_frequency`，而 Canonical World Model 已声明频次应来自 `PolicyRegistry`，该字段只是兼容字段。

这会破坏“政策是 World Model 的事实来源”原则，造成：

```text
同一客户
观测字段频次 ≠ 政策注册表频次
```

必须让领域桥接只消费经过版本化、带有效时间和证据的政策解析结果。

### A-08：真实业务垂直切片尚未证明架构闭环（P1）

现有真实数据与排班测试证明了数据摄入、频次审计和求解能力，但尚未证明以下闭环作为一个统一系统存在：

```text
历史业务数据
→ Evidence / Observation
→ L4 WorldState Snapshot
→ L5 Scenario Rollout
→ L6 Planner Projection
→ L7 Candidate Decision
→ Audit / Approval
→ Commitment Transition
→ Execution Feedback
→ New WorldState Snapshot
```

在销售拜访领域，至少需要一个完整的“代表请假导致周期计划重排”垂直切片证明这一链路。

---

## 4. 当前架构成熟度矩阵

| 能力 | 设计状态 | Runtime 状态 | 架构判断 |
|---|---|---|---|
| L0/L1 元模型 | 文档较完整 | 部分类型存在 | 尚未完成唯一事实源收敛 |
| L2 销售拜访本体 | 有领域规范和映射 | 有部分实体 | 业务签署和来源治理仍需确认 |
| L3 状态转移 | 有 Guard 和哈希设计 | 有部分实现 | 需与 L5、审批生命周期重新分界 |
| L4 WorldState | 有快照类型和装载器 | 可装载真实数据 | 基线、事件流、情景字段尚未完全分离 |
| L5 Scenario | 有详细规范 | `scenario_engine.py` 尚未形成 | 未证明 |
| L6 Planner Projection | 有契约和编译器 | 有部分实现 | 仍使用估算路网和旧字段路径 |
| L7 Decision Engine | 有详细规范 | 现有 pipeline 更像领域流水线 | 未形成完整 runtime |
| Execution Feedback | 有类型和边界描述 | 闭环未证明 | 未形成可重放闭环 |

---

## 5. 第一轮架构审查后的冻结门禁

在继续 API Freeze 或 Runtime 扩展之前，必须完成：

1. 统一 L0–L7 唯一分层模型；
2. 明确 L3 转移函数与 L5 情景执行器的边界；
3. 从 L4 拆出 ScenarioState 和 ExecutionEventStream；
4. 重新形式化批准、承诺、下发、执行、完成五类状态；
5. 统一 L4 View、L6 Projection、DecisionContext 的访问权；
6. 将现有 DecisionPipeline 明确降级为 Domain Solver Pipeline 或迁移到 L7；
7. 让政策解析成为规划的唯一频次和承诺来源；
8. 完成一个真实销售拜访垂直切片。

---

## 6. 下一轮审查计划

### Round 2：状态与因果生命周期

重点审查：

- Observation / Fact / Policy / Commitment / Plan / ExecutionEvent 的转换边界；
- 状态转移是否可重放、可逆向解释和可补偿；
- ScenarioResult 如何与真实状态隔离；
- 执行反馈如何创建新快照。

### Round 3：销售拜访端到端垂直切片

重点审查：

- 辖区分配、周期覆盖、单日路线三层决策是否真正分离；
- 真实客户、频次、归属、承诺、时段、历史耗时如何进入 WorldState；
- 规划结果如何形成 DecisionArtifact；
- 计划变更如何影响承诺和后续周期。

Round 3 完成后，才形成架构级最终整改清单和 runtime 路线图。

---

## 7. Round 2：状态与因果生命周期复核结果

Round 2 对 `StateTransitionEngine`、L5 Scenario 规范、L7 Decision Engine 事务规范以及现有 WorldState 实例进行了交叉复核。发现以下新增架构问题。

### A-09：L3 文档仍内嵌 L5 分支实现（P0）

`SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md` 在 L3 文档中直接定义了 `fork_scenario_branch()`，并以 `WorldStateSnapshot` 作为返回值；同时，L5 规范又规定分支状态只能在 L5 内部存在，对外只能返回 `ScenarioResult`。

这形成了两个相互竞争的 Scenario 入口：

```text
L3 fork_scenario_branch(...) -> WorldStateSnapshot
L5 request_scenario_rollout(...) -> ScenarioResult
```

必须保留一个对外入口：

```text
L3：只提供 transition(state, event, action) -> state/delta 的规则能力
L5：负责 fork、rollout、compare，并只返回 ScenarioResult
```

`WorldStateSnapshot` 不得作为 L5 分支 API 的返回类型。

### A-10：状态转移模型没有区分“事实事件”和“控制动作”（P1）

L3 数学模型使用：

```text
WorldState(t+1) = δ(WorldState(t), Event(t), Action(t))
```

但目前生命周期图中的 `Event.PlanGenerated`、`Event.HumanSignedOff`、`Event.CheckInRecorded` 同时混合了：

- 决策系统产生的计划产物；
- 人工治理动作；
- 外部现实世界事实。

必须建立事件分类：

```text
DecisionEvent       计划生成、审批、撤回
CommitmentEvent     承诺预留、锁定、释放
ExecutionEvent      下发、签到、签退、未履约
ObservationEvent    GPS、门店状态、缺货、人工补录
```

只有 `ExecutionEvent` 和经验证的 `ObservationEvent` 才能证明现实状态已经发生变化；DecisionEvent 只能改变决策/治理状态。

### A-11：L7 事务协议与世界状态生命周期没有形成统一状态机（P0）

L7 规范使用：

```text
reserve_plan_commitment
→ write DecisionArtifact
→ commit_plan_transition
→ abort / compensate
```

而 L3 生命周期使用：

```text
PLANNED → COMMITTED → IN_PROGRESS → COMPLETED
```

两个模型缺少统一映射，尤其没有明确：

- `RESERVED` 是承诺状态还是事务锁状态；
- `COMMITTED` 是审批结果还是现实业务承诺；
- `ROLLED_BACK` 应落在 DecisionArtifact、Commitment 还是 VisitLifecycle；
- Artifact 写入失败时，World Model 是否已经产生新的现实快照。

建议把事务状态与业务状态分离：

```text
DecisionPublicationState:
    DRAFT → APPROVED → PUBLISHED → REVOKED

CommitmentState:
    AVAILABLE → RESERVED → COMMITTED → RELEASED / EXPIRED

VisitExecutionState:
    PLANNED → DISPATCHED → IN_PROGRESS → COMPLETED / MISSED
```

三条状态机通过带引用的事件关联，而不是共享一个 `COMMITTED` 状态。

### A-12：场景推演缺少“假设动作 → 预期后状态”的完整因果链（P1）

L5 已定义 `base_snapshot_id`、`perturbation_events` 和 `ScenarioResult`，但架构上仍需保证每个结果都能回答：

```text
假设动作是什么？
使用了哪一个 L3 transition model？
应用了哪些 guard？
产生了哪些 StateDelta？
哪些指标是由 Delta 推导出来的？
哪些结果仍然是不确定估计？
```

只有“容量影响摘要”或目标函数变化，不足以构成企业世界模型的反事实解释。

### A-13：WorldState 实例仍将“现实历史”和“未来假设”放在同一对象中（P1）

当前状态对象同时包含 `execution_fact_stream` 与 `active_scenario_branches`。即使这些字段声明为不可变，它们仍然属于不同语义层：

- execution facts 是已经发生的事实；
- scenario branches 是尚未发生的假设；
- snapshot 是某一现实时间点的基线。

不可变不等于语义隔离。下一版架构必须在类型和存储边界上区分三者。

---

## 8. Round 2 对生命周期模型的推荐基线

```text
Observation / External Event
        ↓ validation + evidence binding
World Model Transition
        ↓
New Baseline Snapshot (L4)

Decision Intent
        ↓
Scenario Rollout (L5, optional)
        ↓
Planner Projection (L6)
        ↓
Candidate Plan / Decision Artifact (L7)
        ↓ approval + commitment event
Commitment State Update (World Model)
        ↓ dispatch
Execution Event
        ↓ evidence validation
New Baseline Snapshot (L4)
```

核心原则：

1. 计划不是事实；
2. 审批不是执行；
3. 情景不是基线；
4. 承诺不是执行结果；
5. 只有验证后的执行事件才能形成新的现实状态。

---

## 9. Round 3：销售拜访真实业务垂直切片复核结果

Round 3 以“代表出勤中断导致周期计划重排”为目标用例，沿真实数据装载器、WorldState、Planner Projection、领域桥接和 Decision Pipeline 追踪数据流。

### A-14：真实数据装载到 Planner Projection 存在主链断点（P0）

`WorldStateAssembler` 从历史表读取了 `planned_frequency` 并写入 `OperationalCustomer` 的兼容字段，同时只创建了通用 `CadenceRule` 集合；它没有为每个客户创建带版本、有效时间和审批来源的 `OperationalVisitPolicy`。

而 `PlannerStateProjectionCompiler` 明确拒绝从客户观测字段读取频次，并要求在 `PolicyRegistry.operational_policies` 中解析活动政策。

当前两条路径形成冲突：

```text
Assembler：frequency → OperationalCustomer.planned_frequency
Projection：frequency ← PolicyRegistry.operational_policies
```

结果是：真实数据可以装载为 WorldState，但不能保证进入 Planner Projection。必须补齐：

```text
历史频次观测
    ↓ Evidence / Policy Derivation
业务确认或明确标记为待确认
    ↓
Versioned OperationalVisitPolicy
    ↓
Planner Projection
```

未经业务确认的历史频次只能作为 `Observation` 或 `DerivedEstimate`，不能静默升级为硬约束政策。

### A-15：领域桥接存在第二条绕过 Projection 的规划路径（P1）

`SVDEOntologyAdapter.dispatch_planning_intent()` 直接读取 `world_state.get_rep_universe()`，使用 `OperationalCustomer.planned_frequency` 生成模式空间，并把客户对象直接放进 Solver-ready payload。

这与 L6 Planner Projection 的架构职责冲突：

```text
规范路径：WorldState → L6 Projection → L7 / Domain Solver
实际路径：WorldState → Bridge → Solver payload → Solver
```

必须保留一个唯一规划入口。领域桥接只能负责意图和领域对象映射，不能重新实现频次解释、模式空间生成或 Planner Projection。

### A-16：真实数据中的默认值没有按证据等级隔离（P1）

当前装载器对缺失数据使用了若干默认值或推断值，例如：

- 缺失频次时默认为 1；
- 缺失服务时长时默认为 50 分钟；
- 缺失大仓时写入“默认大仓”；
- 缺失区域时写入默认区域；
- 无坐标时使用几何中心或固定坐标兜底；
- 缺失交易时间时使用当前时间。

这些值在技术上可能让测试继续运行，但在世界模型语义上必须区分：

```text
Observed Fact
Derived Estimate
Assumption / Placeholder
Unresolved Data Quality Issue
```

默认值不能以客户事实、政策事实或真实路网事实的形式进入规划器。缺失关键输入时，应进入数据质量门禁或显式的部分投影模式。

### A-17：当前领域本体不足以支撑真实销售拜访的三层决策（P1）

真实销售拜访不是单一路线问题，而是：

```text
Territory Alignment
    → Periodic Coverage / Cadence
        → Daily Route Sequencing
```

当前领域对象已经描述了 Customer、OwnershipPolicy、CadenceSpec、Commitment、ActualVisit 和 TravelCostMatrix，但真实装载和规划主链仍主要围绕“代表已有门店集合 + 频次模式 + 日路线”运行，尚未把以下因素作为可执行状态与决策输入完整串起来：

- 代表—客户归属变更的业务原因与审批；
- 客户固定日、锁定件和顺延政策；
- 多周期承诺之间的冲突；
- 产品线和现场动作对服务时长的影响；
- 大仓到货节奏与拜访时序；
- 未履约后的业务代价和后续周期影响。

因此，当前系统可以证明“某种周期排班可以被求解”，但还不能证明“销售拜访业务世界可以被完整推演和决策”。

### A-18：代表出勤中断垂直切片尚未形成（P1）

目标情景应当是：

```text
RepAbsenceEvent
    → 识别受影响的 Commitment / VisitDemand
    → L3 校验可延期、改派和保留规则
    → L5 比较多个重排情景
    → L6 生成各情景的数学投影
    → L7 选择并审批方案
    → 写入新的 Commitment 状态
    → 执行反馈回写新的 L4 Snapshot
```

当前已有数据摄入、频次审计和周期求解测试，但尚未形成这条跨模块、跨状态、跨时间的可回放业务闭环。

### A-19：规划投影仍包含“估算路网”语义，不能等同真实路线世界（P1）

当前投影编译器可以基于 Haversine 距离和固定速度估算通行时间。它适合测试或缺失数据的诊断，但不能被标记为真实路网规划能力。

必须在 Projection 元数据中明确：

```text
cost_model_type = REAL_NETWORK / ESTIMATED_GEOMETRIC / FALLBACK
source_ref       = 路网数据集或估算规则版本
quality_status   = VERIFIED / APPROXIMATE / BLOCKED
```

在真实数据影子模式中，若业务问题要求缩短在途距离，`ESTIMATED_GEOMETRIC` 只能产生诊断结果，不能产生生产决策。

---

## 10. Round 3 垂直切片验收条件

“代表出勤中断导致周期计划重排”要成为架构通过样例，至少必须证明：

1. 真实历史数据被分为 Observation、Policy、Commitment、ExecutionEvent，而非全部进入 Customer 属性；
2. 频次来源来自版本化 PolicyRegistry，并带有效时间与证据引用；
3. 出勤中断是一个明确的外部事件，不是直接修改代表容量字段；
4. L3 对每个候选动作执行合法性守卫；
5. L5 输出多个 ScenarioResult，不暴露分支 WorldState；
6. L6 Projection 引用统一的 `snapshot_id`、`scenario_id` 和成本模型版本；
7. L7 产出 DecisionArtifact，并区分批准、承诺锁定和执行下发；
8. 执行反馈能够生成新的基线快照；
9. 整个链路可以用同一输入和显式时间重新运行并得到同一审计结果。

---

## 11. 架构整改优先级与实施路线

### Phase A：架构决策冻结前置（不改 runtime）

1. 选择唯一 L0–L7 分层并回写基础架构规范；
2. 形成 L3/L4/L5/L6/L7 责任矩阵的单一事实源；
3. 决定三条独立状态机：DecisionPublication、Commitment、VisitExecution；
4. 决定 BaselineWorldState、ScenarioState、ExecutionEventStream 的存储和 API 边界；
5. 决定 L4 View、L6 Projection、DecisionContextView 的权限与生命周期；
6. 通过“代表出勤中断重排”用例完成业务方语义签署。

### Phase B：语义闭环契约

1. 为真实数据定义 Observation → Policy / Commitment / ExecutionEvent 的升级规则；
2. 为每条硬约束记录 evidence、policy_version、valid_time 和责任人；
3. 定义 ScenarioResult 的因果字段：assumptions、applied_transitions、state_delta、impact、uncertainty；
4. 定义 Projection 的 source_snapshot、scenario、cost_model 和 quality 状态；
5. 将领域桥接改为只产生 Intent / Domain Mapping，不再直接生成 Solver payload。

### Phase C：runtime 实施顺序

```text
Policy / Evidence Resolver
    ↓
Baseline WorldState + Event Stream
    ↓
L3 Transition Engine
    ↓
L5 Scenario Engine
    ↓
L6 Planner Projection
    ↓
L7 Decision Orchestrator
    ↓
Commitment / Dispatch / Execution Feedback
```

不得先实现“直接调用 Solver 的快捷链路”，再事后补 World Model；否则会再次形成领域求解器冒充企业决策引擎的问题。

### Phase D：唯一垂直切片验收

首个架构验收样例固定为：

```text
代表请假 3 天 → 影响识别 → 候选延期/改派情景 → 周期计划重排
→ 审计 → 人工审批 → 承诺锁定 → 执行反馈 → 新快照
```

只有该垂直切片完成并能重放，才允许宣称 World Model 与 Decision Engine 已形成真实业务闭环。

---

## 12. Round 1–3 总体结论

当前系统不是“代码不够多”，而是架构语义还没有收敛到一个唯一的运行模型。现阶段应停止以测试数量或局部类型数量作为成熟度主要指标，改用以下架构验收问题：

```text
事实从哪里来？
谁拥有基线状态？
什么事件可以改变现实？
什么动作只能存在于情景？
规划器消费哪一个版本化投影？
谁可以批准、锁定、下发和确认执行？
执行反馈如何生成下一版世界状态？
```

在这些问题形成唯一答案前：

```text
不冻结 Canonical API
不启动大规模 runtime 重构
不把 SVDE 领域求解流水线宣传为 Enterprise Decision Engine
不对真实业务收益作未经对照实验的承诺
```
