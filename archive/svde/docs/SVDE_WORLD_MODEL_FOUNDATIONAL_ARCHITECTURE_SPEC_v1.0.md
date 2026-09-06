---
**Status:** HISTORICAL SNAPSHOT — NOT THE CURRENT CANONICAL STRUCTURE
**MIGRATED-TO:** `svde/docs/TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md`
**Date:** 2026-08-25
**Reason for migration:** 本文档采用 L0-L6（6 层）分层；当前提议中的 Canonical 分层已扩展为 L0-L7（7 层），将"Planning & Execution"拆分为 L6 Planner Projection（仅产出纯数学载荷）+ L7 Enterprise Decision Engine（独立子系统）。
**Action required:** 任何引用本文档的代码、测试、报告必须改用 Baseline v1.0 的 L0-L7 分层。

> 在旧文档完成迁移或废止前，`L0-L7` 与 `L0-L6` 两套编号并存；本状态为 **PROPOSED CANONICAL / PARTIALLY ALIGNED**，**未达到已冻结架构标准**。

---

# SVDE World Model Foundational Architecture Specification v1.0

状态：基础架构草案（独立于具体领域与数据实例）  
版本：1.0  
日期：2026-08-24  
适用范围：SVDE 及其物流、销售拜访、医疗排班、供应链等领域适配器

## 1. 文档定位

本文定义 SVDE 世界模型的基础架构，不定义销售拜访、物流或医疗领域的业务规则，也不定义任何具体客户、代表、路线或历史数据。

本文回答的是：

- 什么是 SVDE 世界模型；
- 世界模型与本体、数据实例、规划引擎如何分层；
- 世界状态如何表示和演化；
- 观测、事实、政策、承诺、计划和推断如何区分；
- 动作如何产生可审计的状态转移；
- 场景推演如何向规划器提供未来状态；
- 哪些条件满足后，领域模型才可以接入 SVDE。

## 2. 核心定义

### 2.1 世界模型

世界模型是对某一目标系统在时间中的可计算表示。它不仅包含实体和关系，还必须能够表示：

1. 当前状态；
2. 状态的来源和可信度；
3. 状态随事件和动作如何变化；
4. 目标、约束和承诺；
5. 候选动作可能导致的未来状态；
6. 执行结果如何反馈并修订模型。

### 2.2 SVDE Operational Decision World Model（ODWM）

SVDE 采用运营决策世界模型（ODWM）定义：

> 一个带时间、证据、状态转移和情景推演能力的决策世界表示，为规划器提供可追溯的状态投影，并在执行后通过新观测闭环更新。

### 2.3 世界模型不是以下任何单一对象

| 对象 | 能解决什么 | 不能单独解决什么 |
|---|---|---|
| 本体 | 定义概念、关系和语义边界 | 当前状态、状态变化和未来推演 |
| 数据仓库 | 保存事实和历史记录 | 动作效果和决策后果 |
| 知识图谱 | 连接实体和关系 | 时态演化与可执行转移 |
| 规划引擎 | 在给定状态和约束下搜索计划 | 判断现实状态是否可信 |
| 数字孪生 | 同步现实对象并支持仿真 | 不一定具备领域决策语义 |
| 机器学习模型 | 估计、预测或评分 | 不自动定义业务世界结构 |

ODWM 是这些能力之间的受约束组合，而不是某一个组件的替代名称。

## 3. 分层架构

```text
L0  Foundational Architecture
    定义世界模型的基本边界、生命周期和接口

L1  World Model Meta-Model
    Entity / State / Event / Action / Policy / Goal /
    Commitment / Observation / Transition / Scenario

L2  Domain Ontology
    将通用类型映射到物流、销售拜访、医疗等领域

L3  Domain Dynamics & Rules
    定义领域动作、前置条件、后置状态和业务约束

L4  World State Instance
    某一时间点、某一数据版本下的现实状态实例

L5  Scenario Instance
    从当前状态复制出的假设状态和候选动作序列

L6  Planning & Execution
    规划、审批、执行、观测回写和重规划
```

依赖方向必须单向：

```text
L0 → L1 → L2 → L3 → L4 → L5 → L6
```

领域实例不得反向改变 L0/L1 的基础语义。若基础语义需要变化，必须进行架构版本变更，而不是通过领域字段隐式覆盖。

## 4. L0 基础架构职责

L0 只规定以下不变量：

1. 世界模型必须有明确的目标系统边界；
2. 所有可计算状态必须带有效时间和模型版本；
3. 观测、政策、承诺、计划、执行和推断必须类型分离；
4. 任何状态必须可追溯到证据或明确标记为假设；
5. 所有状态变化必须由事件或动作转移产生；
6. 场景推演不得修改基线现实状态；
7. 规划器只能消费明确版本的状态投影；
8. 执行反馈必须产生新的观测或事件，而不是静默覆盖旧值。

L0 不规定：

- 具体领域实体名称；
- 具体优化算法；
- 具体数据库或图数据库；
- 具体求解器；
- 任何业务指标权重；
- 任何行业硬约束。

## 5. L1 通用元模型

### 5.1 Entity

现实世界中具有身份、边界和生命周期的对象。

```text
Entity = identity + type + attributes + relations + lifecycle
```

实体实例必须有稳定标识，不得使用名称或数组位置作为唯一身份。

### 5.2 State

实体、关系或系统在特定时间点的可断言状态。

```text
State = subject + predicate + value + valid_time + evidence
```

状态不是永久属性；同一状态可以在未来失效或被新证据修订。

### 5.3 Observation

从外部系统、传感器、人工输入或历史记录中获得的观测。

观测必须保留原始来源，不得直接升级为政策或硬约束。

### 5.4 Policy

规定系统应该如何运行的规则或制度。政策可有版本、适用范围、生效时间和失效时间。

### 5.5 Commitment

系统或参与方已经承诺的结果、时限或服务义务。承诺通常具有业务责任人和违反代价。

### 5.6 Goal

期望达到的状态或状态区间。目标可以是硬目标、软目标或优化目标，但不能未经领域确认自动升级为约束。

### 5.7 PlanIntent

计划系统打算执行的动作序列。计划意图不等于执行事实。

### 5.8 ExecutionEvent

现实中已经发生的动作或结果，必须记录执行时间、执行主体和结果。

### 5.9 DerivedEstimate

由规则、统计模型或机器学习模型推导出的估计值。派生估计必须保存计算方法、输入版本和不确定性。

### 5.10 StateTransition

描述动作或事件如何把一个状态变为另一个状态的规则。

```text
Transition =
    preconditions
    + action/event
    + effects
    + invariants
    + failure_conditions
    + uncertainty
```

## 6. 时间模型

所有可演化对象至少使用两种时间：

| 时间 | 含义 |
|---|---|
| valid_time | 该事实在现实世界中有效的时间区间 |
| transaction_time | 系统记录、接收或确认该事实的时间 |

预测和场景还需要：

| 时间 | 含义 |
|---|---|
| forecast_time | 生成预测的时间 |
| scenario_time | 情景中的假设未来时间 |
| execution_time | 动作实际执行的时间 |

禁止用单一 `timestamp` 同时表达这些语义。

## 7. 证据与不确定性

### 7.1 EvidenceRecord

```python
EvidenceRecord(
    evidence_id,
    source_type,
    source_ref,
    collected_at,
    valid_time,
    extraction_method,
    quality_score,
    confidence,
    reviewer,
)
```

### 7.2 主张类型

```text
FACT          已被来源直接支持的事实
OBSERVATION   某次观测记录
POLICY        规则或制度
COMMITMENT    已确认的业务承诺
INFERENCE     基于证据的推断
DERIVED       算法计算结果
HYPOTHESIS    尚未确认的假设
```

只有 `FACT`、已批准的 `POLICY` 和已确认的 `COMMITMENT` 才可能进入硬约束候选；`INFERENCE`、`DERIVED` 和 `HYPOTHESIS` 默认不得静默升级。

## 8. 事件与动作模型

事件表示已经发生的变化，动作表示计划要执行的变化。

```python
Action(
    action_id,
    action_type,
    actor,
    parameters,
    preconditions,
    expected_effects,
)

ExecutionEvent(
    event_id,
    event_type,
    actor,
    occurred_at,
    input_state_id,
    outcome,
    evidence,
)
```

每个领域动作必须说明：

- 允许在哪些前置状态下执行；
- 预期改变哪些状态；
- 哪些不变量必须保持；
- 失败时产生什么事件；
- 如何处理部分成功和不确定结果。

## 9. 世界状态快照

```python
WorldStateSnapshot(
    state_id,
    world_id,
    valid_time,
    transaction_time,
    model_version,
    entities,
    relations,
    observations,
    policies,
    commitments,
    goals,
    resource_states,
    derived_estimates,
    unresolved_conflicts,
    uncertainty_summary,
    source_manifest,
)
```

快照必须不可变。状态更新通过生成新快照完成，不得原地覆盖历史快照。

## 10. 场景与反事实推演

场景是从某个基线快照复制出来的假设世界，不是现实世界的新事实。

```python
Scenario(
    scenario_id,
    base_state_id,
    assumptions,
    candidate_actions,
    transition_model_version,
    rollout_states,
    uncertainty,
)
```

场景引擎必须满足：

1. 不修改基线快照；
2. 记录全部假设；
3. 使用固定的转移模型版本；
4. 输出状态差异，而不是只输出目标函数；
5. 支持重复运行并得到一致结果；
6. 区分预测结果和实际执行结果。

## 11. 规划器接口

规划器不应直接读取整个世界库，而应接收版本化的状态投影：

```python
PlannerStateProjection(
    projection_id,
    source_state_id,
    decision_scope,
    effective_time,
    entities,
    hard_constraints,
    soft_preferences,
    goals,
    allowed_actions,
    cost_models,
    evidence_refs,
)
```

规划结果必须包含预期后状态：

```python
PlanResult(
    plan_id,
    source_projection_id,
    selected_actions,
    expected_state_delta,
    feasibility,
    objective_breakdown,
    unresolved_issues,
    audit_refs,
)
```

规划器的职责是搜索方案，不是重新解释业务术语、猜测缺失政策或修复世界状态。

## 12. 闭环生命周期

```text
Observe
  → Estimate
  → Snapshot
  → Project
  → Plan
  → Audit
  → Approve
  → Execute
  → Observe outcome
  → Reconcile new snapshot
```

人工审批属于治理动作，不应被视为状态已经执行。只有执行事件被观测并确认后，计划意图才可以转化为执行事实。

## 13. 一致性与安全不变量

### 13.1 语义不变量

- 观察不能自动变成政策；
- 推断不能自动变成事实；
- 计划不能自动变成执行；
- 场景不能污染基线；
- 派生值不能伪装成现实实体；
- 不同有效时间的状态不能无条件合并。

### 13.2 规划不变量

- 每个硬约束必须有来源；
- 每个候选动作必须有前置条件和预期效果；
- 每个计划必须引用一个明确的状态投影；
- 规划结果必须能解释状态差异；
- 不确定性必须进入风险或审计输出。

## 14. 与领域适配器的契约

领域适配器必须提供：

1. 领域实体映射；
2. 领域事件类型；
3. 领域动作及转移规则；
4. 领域政策和承诺模型；
5. 领域 competency questions；
6. 数据源和证据映射；
7. 领域状态投影；
8. 领域反例和冲突处理规则。

领域适配器不得：

- 修改 L0/L1 的基本语义；
- 把领域默认值写成基础架构硬规则；
- 省略来源、时间和不确定性；
- 直接把原始数据交给规划器；
- 以测试通过替代业务语义确认。

## 15. 合规门禁

任何领域模型进入生产前，必须证明：

- L0/L1 对象边界未被折叠；
- 每个核心 competency question 有可执行回答；
- 状态、事件、动作和转移可回放；
- 每个硬约束可追溯到证据和责任人；
- 场景推演不会修改基线状态；
- 规划输出包含预期后状态和不确定性；
- 执行反馈可生成新的世界状态版本。

## 16. 参考标准与研究资料

- [ISO 23247-2:2021 — Digital twin framework for manufacturing](https://www.iso.org/standard/78743.html)
- [ISO/IEC 30188 — Digital twin reference architecture](https://www.iso.org/standard/53308.html)
- [ETSI TS 103 846 — Digital Twins: Functionalities and communication reference architecture](https://www.etsi.org/deliver/etsi_ts/103800_103899/103846/01.01.01_60/ts_103846v010101p.pdf)
- [NASA/JPL Mission Data System Architecture](https://mds.jpl.nasa.gov/public/arch/architecture_body.shtml)
- [W3C Ontology Engineering and Patterns](https://www.w3.org/2001/sw/BestPractices/OEP/)
- [W3C PROV-O](https://www.w3.org/TR/prov-o/)
- [World Models for Autonomous Driving: An Initial Survey](https://arxiv.org/abs/2403.02622)

## 17. 版本边界

本文是 L0 基础架构规范。以下内容必须在后续文档定义：

- `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md`：L1 元模型；
- `SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC_v1.0.md`：L2 销售拜访本体；
- `SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md`：状态转移和情景引擎；
- `SVDE_PLANNER_PROJECTION_CONTRACT_v1.0.md`：规划器投影契约。

在这些文档完成之前，不应将任何销售拜访字段标记为 L0/L1 基础语义，也不应声称具体领域已经完成世界模型建设。
