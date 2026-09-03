# SVDE 跨行业世界模型研究与设计基线 v1.0

状态：研究基线（非冻结规范）  
日期：2026-08-24

## 1. 结论先行

当前 SVDE 更准确的定位是“带本体和规划原型的决策系统”，还不是完整的运营世界模型（Operational Decision World Model）。原因不是实体字段不够多，而是缺少以下闭环：

`现实系统 → 观测与状态估计 → 带时间的世界状态 → 状态转移/因果模型 → 情景推演 → 规划 → 执行反馈`

本体解决“世界中有什么、如何分类、如何关联”；世界模型还必须回答：

- 现在处于什么状态，状态在什么时间有效；
- 这个状态来自哪条证据，可信度如何；
- 执行一个动作后，哪些状态会改变；
- 如果采取另一个方案，未来可能怎样；
- 规划器消费的是哪个状态切片，计划会造成什么预期状态转移。

因此，下一阶段不应继续以“补几个字段、增加几个测试、调求解器”为主，而应先完成 Operational Decision World Model 的概念、状态、转移、推演和规划接口设计。

## 2. 术语边界

### 2.1 本体（Ontology）

本体是受约束的语义模型：类、关系、属性、约束、规则和术语定义。它保证不同模块对“客户、代表、承诺、观测、计划”等词有一致含义，但本体本身不等于运行中的世界。

### 2.2 数字孪生（Digital Twin）

数字孪生强调现实对象与数字表示之间的持续同步、状态演化、仿真和决策支持。ISO 23247 在制造场景中把参考架构分为领域/实体视图和功能视图；JPL 则将数字孪生描述为可交互、跨领域、跨尺度的状态与时间演化数字副本。

### 2.3 AI 世界模型（World Model）

在自动驾驶等领域，世界模型通常指能够从观测估计当前状态、预测未来状态并向规划器提供可滚动推演接口的模型。它不只生成内容，必须能支持约束推理、代价评估、不确定性处理和决策。

### 2.4 SVDE 应采用的术语

SVDE 不需要照搬自动驾驶的潜变量生成模型，也不能把静态知识图谱称为世界模型。更准确的名称是：

> **Operational Decision World Model（运营决策世界模型，ODWM）**：面向企业决策的、带时间和证据的状态模型，能够表达观测、政策、承诺、计划、执行和状态转移，并为规划器提供可审计的情景推演接口。

## 3. 跨行业研究发现

### 3.1 制造业数字孪生：实体视图之外必须有功能与演化视图

ISO 23247 的价值不在于增加制造对象名称，而在于同时规定领域/实体视图和功能视图。一个可用的孪生需要知道对象是什么，也需要知道数据如何采集、如何同步、如何分析、如何支持控制。

对 SVDE 的启示：`CustomerEntity`、`ResourceEntity` 等实体只能构成本体层；还必须有观测接入、状态估计、模型执行、规划和反馈功能层。

### 3.2 NASA/JPL 控制架构：现实状态、软件状态和意图必须分离

JPL Mission Data System 明确区分目标系统的物理状态与控制系统的软件状态。软件状态包含估计值和意图，并以时间线方式表达；目标是对时间区间的期望条件，控制器通过执行动作使状态满足约束，并持续重规划。

对 SVDE 的启示：

- 历史拜访记录是 `Observation`，不是当前事实的直接替代；
- 客户归属、拜访频次政策和锁定承诺不是同一种对象；
- 计划是 `Intent`，不是已经发生的事实；
- 执行反馈必须更新下一版世界状态；
- 状态必须有有效时间（valid time）和记录时间（transaction time）。

### 3.3 供应链控制塔：世界是多层网络、事件和依赖，而不是单条路线

供应链数字孪生通常围绕多级节点、库存/订单状态、运输事件、供需依赖和情景分析建立。其核心不是把订单表搬进图数据库，而是对网络状态变化进行可见性、预测和反事实分析。

对销售拜访的启示：客户、代表、区域、门店、供应节点、产品线和拜访承诺应形成关系网络；“线路变长”只是网络状态和政策共同作用后的表象。

### 3.4 医疗流程：流程状态和资源状态同等重要

医疗数字孪生将患者流程、临床资源、等待状态、服务能力和时间约束放进同一动态框架，并用仿真与优化支持排班和流转。

对 SVDE 的启示：拜访计划不能只表达“访问哪些客户”，还要表达客户处于什么业务阶段、代表有哪些工作日能力、拜访动作会改变什么业务状态，以及未履约会产生什么后果。

### 3.5 自动驾驶：规划器需要可消费的未来状态，而非静态语义图

自动驾驶研究把世界模型视为预测性状态转移接口：规划器可以对候选动作进行 rollout，比较未来代价，处理交互和不确定性。只生成未来画面而不服务于规划，不足以称为决策世界模型。

对 SVDE 的启示：必须支持“如果延期客户 A”“如果将客户 B 转给代表 C”“如果固定周几拜访”等反事实场景，并返回覆盖、承诺、距离、稳定性和业务风险的预期结果。

### 3.6 企业知识图谱：语义和溯源是基础，但图谱本身不是世界模型

企业知识图谱适合统一术语、实体、关系、目标和架构。W3C PROV-O 进一步提供了可表达实体、活动、代理及其来源关系的标准语义。但知识图谱通常描述“已知关系”，不自动提供时间演化、动作效果和未来推演。

对 SVDE 的启示：图谱/本体是 ODWM 的语义底座；必须在其上增加时间状态、转移模型、场景和规划契约。

## 4. 跨行业共同结构

跨行业比较后，可以抽象出七个不可缺少的世界模型组件：

| 组件 | 必须回答的问题 | SVDE 对应要求 |
|---|---|---|
| 现实边界 | 哪些对象和外部过程被建模 | 客户、代表、组织、门店、供应节点、日历、路网 |
| 状态 | 现在是什么状态 | 带时间版本的客户、承诺、资源、覆盖和执行状态 |
| 观测与证据 | 为什么相信这个状态 | 来源、采集时间、质量、置信度、冲突 |
| 转移/动力学 | 动作会怎样改变状态 | 拜访完成、延期、改派、失约、政策变更的状态转移 |
| 目标与约束 | 什么是可接受的未来 | 频次、节奏、锁定、归属、覆盖、业务价值、距离 |
| 情景推演 | 换一种决策会怎样 | 可复现的 what-if / counterfactual rollout |
| 规划与反馈 | 如何选择并持续修正 | 规划器输入投影、计划输出、执行回写、重规划 |

缺少任一项时，系统最多是静态本体、数据集成层或一次性优化器。

## 5. 对当前 SVDE 的严格诊断

### 5.1 已经具备的部分

- 已开始区分客户、资源、产品线、供应节点和执行事实；
- 已有来源清单、哈希和计数等数据溯源雏形；
- 已有计划、求解、审计和人工审批流程；
- 已经意识到历史记录、业务政策和决策结果不能完全混为一谈。

### 5.2 仍然不是世界模型的关键原因

1. **历史观察与业务政策仍有混淆**：例如从第一条历史记录推导 `planned_frequency`，这把“曾经观察到的频次”冒充成“当前政策”。
2. **派生值与现实事实仍有混淆**：用客户坐标质心作为 `home_depot_coord`，质心是路由派生锚点，不是事实上的基地。
3. **默认语义被当成事实**：固定生成合同摘要、战略角色等字段，缺少证据等级和待确认状态。
4. **缺少时间模型**：没有完整表达政策、归属、承诺和实体关系何时生效、何时失效、何时被记录。
5. **缺少事件和状态转移**：有执行事实流，但没有明确的事件类型、前置状态、后置状态和转移规则。
6. **缺少计划意图与承诺分离**：计划、锁定承诺、历史执行、当前观测和推断应是不同对象。
7. **缺少情景推演接口**：规划器还不能对候选动作做标准化、可审计的未来状态 rollout。
8. **缺少不确定性传播**：数据质量问题被记录了，但尚未系统地传播到状态、候选计划、风险和审计结论。
9. **规划器输入仍偏静态**：真实路网、营业日历、客户政策、代表能力和业务价值没有作为一个带版本的状态投影进入规划。
10. **本体关系尚未形成可执行业务图**：实体存在不等于关系、事件和规则已能驱动决策。

因此，当前成果应称为“ontology-backed planning prototype”，不能宣称为完整数字孪生或世界模型。

## 6. 目标架构：SVDE Operational Decision World Model

```text
External Reality
  ├─ master data / transactions / GPS / visits / calendars / policies
  ↓
Observation & State Estimation
  ├─ source evidence
  ├─ quality/confidence
  └─ conflict set
  ↓
Canonical World State Store
  ├─ time-versioned snapshot
  ├─ event history
  ├─ ontology relations
  ├─ policies / commitments / goals
  └─ derived estimates
  ↓
Transition & Scenario Engine
  ├─ action preconditions
  ├─ expected effects
  ├─ uncertainty
  └─ reproducible rollout
  ↓
Planner Projection
  ├─ typed state slice
  ├─ hard constraints
  ├─ soft objectives
  └─ allowed actions
  ↓
Candidate Plan → Audit → Human Approval → Execution
                                      ↓
                              New observations / state revision
```

### 6.1 建议的最小核心对象

```python
WorldStateSnapshot
Observation
Policy
Commitment
VisitDemand
ResourceAvailability
PlanIntent
ExecutionEvent
DerivedEstimate
Scenario
StateTransition
EvidenceRecord
ConflictRecord
```

这些对象必须有明确的类型边界。尤其要禁止以下折叠：

`Observation ≠ Policy ≠ Commitment ≠ PlanIntent ≠ ExecutionEvent ≠ DerivedEstimate`

### 6.2 状态快照的最低契约

```python
WorldStateSnapshot(
    state_id,
    valid_time,
    transaction_time,
    model_version,
    entities,
    relations,
    observations,
    policies,
    commitments,
    resource_availability,
    derived_estimates,
    unresolved_conflicts,
    uncertainty_summary,
    source_manifest,
)
```

### 6.3 规划器必须消费的不是“所有数据”，而是状态投影

规划器输入应是可追溯的 `PlannerStateProjection`，包含：

- 当前有效客户/代表/区域关系；
- 当前生效的频次、节奏、时段和锁定承诺；
- 代表工作日和能力；
- 真实路网成本矩阵及版本；
- 必须满足的约束和可牺牲的偏好；
- 每个字段的证据、置信度和有效期；
- 允许的动作及其状态转移定义。

## 7. 对销售拜访问题的重新解释

“缩短在途距离”不是一个直接的路线问题，而是一个需要先进行状态诊断的情景问题：

1. 当前跨区分配是否是事实、政策还是历史惯例？
2. 当前频次和锁定承诺是否仍然生效？
3. 观测到的路线长是单日顺序问题，还是周期/辖区状态问题？
4. 改派、延期、改日或重排分别会触发哪些状态转移和业务代价？
5. 只有在固定不可牺牲的承诺后，才对候选动作进行路线级 rollout。

世界模型的输出不应只是“新路线”，而应是：

```text
候选动作
→ 预期客户覆盖变化
→ 频次/节奏/锁定承诺影响
→ 代表工作负荷变化
→ 在途时间/距离变化
→ 计划稳定性变化
→ 未履约和业务价值风险
→ 证据与不确定性
```

## 8. 下一阶段建议：先研究与建模，暂停表面优化

### Phase WM-0：世界模型研究与术语冻结

- 完成跨行业研究矩阵；
- 确认 SVDE 使用 ODWM，而非泛化的“AI 世界模型”说法；
- 冻结 Observation / Policy / Commitment / Plan / Execution / Estimate 的定义；
- 形成不可折叠清单。

### Phase WM-1：状态与时间模型

- 重构 `WorldStateSnapshot`；
- 增加 valid time、transaction time、版本和冲突；
- 把政策、承诺、历史事实和派生值分开；
- 为每项状态绑定证据与置信度。

### Phase WM-2：转移与情景接口

- 定义拜访完成、延期、改派、取消、失约、政策变更等状态转移；
- 建立可复现的 scenario/rollout 接口；
- 规定不确定性如何传播到候选计划和审计。

### Phase WM-3：规划器状态投影

- 规划器只接受版本化 `PlannerStateProjection`；
- 路由、周期、辖区规划分别声明消费哪些状态和产生哪些转移；
- 规划结果必须返回预期后状态，而不是只有路线和分配。

### Phase WM-4：再做真实数据验证

在 WM-0 至 WM-3 完成前，不应继续用更多通测来证明“世界模型已经完成”。测试应验证契约和转移语义，而不只是验证求解器返回了一个可行解。

## 9. 研究参考

- [ISO 23247-2:2021 — Digital twin framework for manufacturing](https://www.iso.org/standard/78743.html)
- [NASA/JPL Mission Data System Architecture](https://mds.jpl.nasa.gov/public/arch/architecture_body.shtml)
- [NASA JPL IDEAS Digital Twin](https://ideas-digitaltwin.jpl.nasa.gov/)
- [W3C PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/)
- [World Models for Autonomous Driving: An Initial Survey](https://arxiv.org/abs/2403.02622)
- [World Models for Autonomous Driving: From Future Generation to Decision Making](https://huanghuan945-ops.github.io/ADWM-survey/)
- [A hybrid simulation/optimization architecture for developing a digital twin](https://doi.org/10.1016/j.ifacol.2022.09.448)
- [An intelligent digital twin framework with AI-driven optimization for patient flow and clinical scheduling](https://pubmed.ncbi.nlm.nih.gov/42528795/)
- [OMG Enterprise Knowledge Graph Task Force](https://www.omg.org/ekg/)

## 10. 最终判断

SVDE 目前已经有构建世界模型的若干砖块，但还没有完成世界模型本身。最重要的缺口不是“缺少更多销售字段”，而是没有把现实观测、业务政策、承诺、计划意图、执行事件、派生估计和未来状态转移组织成一个带时间、证据和闭环反馈的系统。

下一步应以本研究基线为输入，编写并评审 `SVDE_OPERATIONAL_DECISION_WORLD_MODEL_SPEC_v1.0.md`，之后再重构本体和规划器接口。

## 11. 资料与证据补充方案

这项工作不能只靠编码。代码只能把已经明确的概念、规则和状态转移实现出来；它不能替业务方决定“什么是事实”“什么是政策”“什么承诺不可牺牲”，也不能凭空产生真实的状态转移规律。

### 11.1 四类必须补充的外部资料

| 资料类别 | 作用 | 典型来源 | 产出 |
|---|---|---|---|
| 世界模型/数字孪生标准 | 约束架构边界和状态同步概念 | ISO 23247、ISO/IEC 30188、ETSI Digital Twin、NASA/JPL | 架构原则、状态/事件/动作边界 |
| 本体工程方法 | 约束如何提出概念、定义范围和验证 | W3C OEP、METHONTOLOGY、NeOn、 competency questions | 本体范围、术语表、能力问题集 |
| 领域业务资料 | 说明销售拜访现实中有哪些规则和例外 | SOP、制度、合同、排班规则、访谈、历史计划 | 业务事实、政策、承诺、例外库 |
| 真实运行数据 | 验证状态和转移是否符合现实 | 客户主数据、代表日历、GPS、拜访记录、改派/失约记录 | 观测、证据、质量、参数校准 |

标准不是业务真相，论文也不是业务规则。它们只能提供方法和可迁移结构；任何销售拜访硬约束仍必须由业务资料和业务方确认。

### 11.2 推荐的研究顺序

1. **先做范围问题（Competency Questions）**：例如“哪些客户在某日处于可拜访状态？”“该频次来自政策还是历史观察？”“如果延期一次，下一次最晚何时必须拜访？”本体必须能回答问题，而不是先罗列类名。W3C 的本体工程实践也强调可复用模式和明确的语义边界。([W3C Ontology Engineering and Patterns](https://www.w3.org/2001/sw/BestPractices/OEP/))
2. **再做现实词汇和事件访谈**：让业务方逐项区分事实、政策、承诺、计划和执行，并收集反例、例外和冲突。
3. **再做时间与证据建模**：每条状态标记有效时间、记录时间、来源、置信度和是否为派生值。PROV-O 可用于表达实体、活动、代理和来源关系。([PROV-O](https://www.w3.org/TR/prov-o/))
4. **再做状态转移建模**：从真实案例中抽取“前置状态—动作—后置状态—副作用—失败条件”，而不是先写求解器约束。
5. **最后才编码**：编码实现本体、状态存储、转移引擎、场景推演和规划器投影，并用真实案例回放验证。

### 11.3 每条关键主张必须有证据等级

建议为每个字段、关系和规则建立主张登记表：

```text
claim_id
statement
claim_type: FACT | POLICY | COMMITMENT | INFERENCE | DERIVED
source_type: STANDARD | PAPER | SOP | INTERVIEW | DATA
source_ref
owner
valid_time
confidence
business_approval
counter_examples
```

没有来源或业务确认的内容只能标记为 `PROPOSED` / `UNMAPPED`，不能进入硬约束，更不能被规划器默认为事实。

### 11.4 需要建立的研究资产

- `WORLD_MODEL_GLOSSARY.md`：跨行业和销售拜访术语定义；
- `COMPETENCY_QUESTIONS.md`：本体与世界模型必须回答的问题；
- `DOMAIN_EVIDENCE_REGISTER.xlsx`：每条业务主张的来源和审批状态；
- `STATE_TRANSITION_CATALOG.md`：事件、前置条件、后置状态和副作用；
- `COUNTEREXAMPLE_CATALOG.md`：跨区、延期、失约、重复拜访、数据冲突等反例；
- `WORLD_MODEL_COVERAGE_MATRIX.md`：问题—状态—证据—转移—规划器能力映射。

### 11.5 对工程团队的硬性门禁

在以下条件满足前，禁止把新字段标记为冻结业务语义：

- 有明确 competency question；
- 有至少一个业务来源和一个真实案例；
- 已区分事实、政策、承诺、推断和派生值；
- 已定义有效时间和证据；
- 已给出至少一个反例；
- 已由业务责任人确认是否为硬约束。

这套门禁的目的，是防止再次出现“代码结构看起来完整，但业务语义没有被证明”的情况。
