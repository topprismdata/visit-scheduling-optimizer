# TopPrism 企业世界模型定位与优势传播规范 v1.0

状态：产品定位与对外传播基线  
日期：2026-08-24  
适用范围：TopPrism 官网、GitHub、产品介绍、销售材料、内部培训

## 1. 一句话定位

> **TopPrism 让企业拥有一个可计算、可推演、可审计的业务世界，在这个世界中理解状态、评估行动并执行关键决策。**

英文：

> **TopPrism gives enterprises a computable, simulatable, and auditable model of their business world—so they can understand state, evaluate actions, and execute critical decisions.**

## 2. 为什么棱镜要做企业世界模型

企业的核心问题不是缺少更多报表或更多局部算法，而是决策所需的语义、状态、规则和后果分散在不同系统中：

```text
ERP / CRM / SCM / HR
SOP / 合同 / 政策
Excel / 人工经验
预测模型 / 优化器
执行记录 / 异常反馈
```

传统系统通常分别回答：

- 发生了什么；
- 有哪些数据；
- 某个模型预测什么；
- 某个局部优化器给出什么方案。

但企业真正需要回答：

```text
当前企业世界是什么状态？
哪些状态是事实、政策、承诺或推断？
采取某个动作后会发生什么？
哪些约束和风险不能被牺牲？
哪个方案值得执行？
执行结果是否改变了下一次决策？
```

这正是企业世界模型的价值。

## 3. 棱镜的产品边界

```text
TopPrism
└── Prism Enterprise Decision Intelligence
    ├── Enterprise World Model
    │   ├── Semantic State
    │   ├── Evidence & Provenance
    │   ├── Policies & Commitments
    │   ├── Business Dynamics
    │   └── Scenario / Simulation
    ├── Decision Engine
    │   ├── Intent Diagnosis
    │   ├── Capability Orchestration
    │   ├── Candidate Generation
    │   ├── Optimization
    │   ├── Audit & Approval
    │   └── Execution Feedback
    └── Domain Decision Engines
        └── SVDE Sales Visit Decision Engine
```

SVDE 是第一个领域决策引擎，不是总平台名称。

## 4. 棱镜的核心优势

### 优势一：从企业语义出发，而不是从算法出发

许多系统从预测模型、求解器或数据表开始。棱镜从企业决策中的核心语义开始：

```text
Entity
Relation
Observation
Policy
Commitment
Demand
Goal
Action
Event
State Transition
Scenario
Plan
Execution
```

这让系统能够区分：

```text
历史上发生过什么
企业规定应该怎样
企业已经承诺什么
系统计划怎样做
实际执行了什么
系统推断出了什么
```

产品价值：减少“把历史数据误当业务规则”“把推断值误当事实”“把计划误当执行”的决策错误。

### 优势二：世界模型内置决策后果，而不是只提供当前状态

棱镜不止保存当前状态，还提供状态转移和情景推演：

```text
基线状态
→ 假设采取动作 A
→ 推演后续状态
→ 计算约束、风险和目标变化
→ 与动作 B、C 比较
```

这与企业数字孪生和企业世界模型的主流实践一致：企业世界模型需要表达状态、动态、约束、目标和可行行动空间；企业运营系统还应能够分叉情景、应用动作并将决策写回。([Business World Model](https://arxiv.org/abs/2606.10044)，[Palantir Operational Applications](https://www.palantir.com/docs/foundry/app-building/operational-apps))

### 优势三：把“决策依据”作为一等公民

每个关键状态和决策都应该能够回答：

```text
来源是什么？
什么时间有效？
哪个版本的政策？
谁批准的？
使用了什么模型？
哪些数据存在不确定性？
```

棱镜的证据和溯源设计使决策不仅有结果，还有依据、版本和审计链。

### 优势四：将业务规则和优化器连接起来

传统做法通常是：

```text
业务系统有规则
优化器有数学输入
两边靠人工或脚本连接
```

棱镜的目标是：

```text
企业语义与政策
→ 版本化状态投影
→ 规划器/求解器
→ 预期后状态
→ 业务与语义审计
```

规划器不需要理解全部业务语义，但不能绕过业务语义和约束。

### 优势五：规划器可替换，世界模型不被单一算法锁定

棱镜的世界模型不依赖某个特定求解器：

```text
同一个 World Model
→ CP-SAT
→ VRP / PVRP
→ 启发式算法
→ 规则引擎
→ 仿真模型
→ 人工决策
```

这使得“业务语义和世界状态”与“某一种优化算法”解耦。

### 优势六：支持从一个领域扩展到多个企业决策领域

L0/L1 提供通用世界模型语义，L2/L3 由领域适配器扩展：

```text
销售拜访：辖区、客户、频次、代表、路线
供应链：库存、订单、供应商、产能、运输
医疗排班：患者、医护、资源、时段、服务流程
现场服务：工单、工程师、技能、备件、SLA
```

SVDE 是参考实现，而不是架构边界。

### 优势七：决策治理和人工责任内置在系统中

棱镜不把“全自动”作为默认目标，而是明确：

```text
机器生成候选
→ 机器审计
→ 人工审批
→ 受控执行
→ 结果反馈
```

这适合高代价、强约束和跨部门的企业决策。Deloitte 和 BCG 的企业数字孪生/决策智能实践也强调数据治理、业务责任和人工决策权的重要性。([Deloitte](https://www.deloitte.com/us/en/insights/topics/emerging-technologies/understanding-digital-twin-technology.html)，[BCG Decision Agents](https://www.bcg.com/publications/2026/how-ai-decision-agents-transform-strategy))

## 5. 与其他产品的差异化表达

| 类别 | 典型能力 | 棱镜补充的能力 |
|---|---|---|
| BI / Dashboard | 展示现状 | 推演动作后果并形成行动 |
| Data Platform | 汇聚数据 | 加入企业语义、状态和规则 |
| Knowledge Graph | 表达关系 | 加入时间、事件、转移和情景 |
| Digital Twin | 仿真对象或流程 | 面向企业决策和审计闭环 |
| Forecasting | 预测未来 | 比较多个动作造成的未来 |
| Optimizer | 求解局部方案 | 消费富语义状态并返回后状态 |
| AI Agent | 执行任务 | 在受约束世界中行动并留下审计链 |

不要宣传“我们比所有系统都强”，而应说：

> 棱镜将这些能力放进同一个企业决策闭环中，使预测、仿真、优化和执行共享同一份可追溯的业务世界。

## 6. 官网宣传结构

### 6.1 Hero

标题：

> **Model the business world. Simulate the options. Execute the decision.**

中文：

> **建模企业世界，推演行动后果，执行关键决策。**

副标题：

> TopPrism is an enterprise decision intelligence platform powered by an operational world model. It connects business semantics, live state, dynamics, constraints, and actions into an auditable decision loop.

### 6.2 官网三段能力

#### 1. Represent the world

将企业对象、关系、政策、承诺、事件和资源组织成带时间与证据的当前状态。

#### 2. Simulate the options

在不影响真实系统的情况下，模拟改派、延期、调度、资源调整和经营策略变化。

#### 3. Execute with confidence

比较目标、约束、风险和代价，生成经过审计、审批和反馈闭环的行动方案。

### 6.3 官网产品模块

```text
Enterprise World Model
Scenario & Dynamics Engine
Decision Engine
Audit & Governance
Domain Decision Engines
```

### 6.4 销售拜访案例

> 对“缩短销售拜访在途距离”的问题，SVDE 不会直接重排客户顺序。它会先识别问题属于辖区、周期还是单日路线层，再检查客户归属、拜访频次、锁定承诺、代表能力和历史履约，最后模拟多个候选动作并比较距离、覆盖、业务价值、工作量和风险。

## 7. GitHub 规划

### 7.1 仓库名称

推荐：

```text
prism-enterprise-world-model
```

备选：

```text
topprism-decision-intelligence
```

SVDE 作为领域目录：

```text
domains/sales_visit/
```

### 7.2 README 首屏

```markdown
# Prism Enterprise World Model

Prism is an enterprise decision intelligence framework powered by an
operational enterprise world model.

It models business state, semantics, policies, commitments, events,
dynamics, constraints, and feasible actions. It supports scenario
rollouts, planner projections, auditable decision artifacts, and
execution feedback.

SVDE (Sales Visit Decision Engine) is the first domain implementation
for field sales and visit operations.
```

### 7.3 GitHub 重点展示内容

GitHub 不应只展示测试数量，而应展示：

1. 世界模型层级图；
2. Entity / Policy / Commitment / Event / Action 示例；
3. 一个场景分叉和状态变化示例；
4. World Model → Planner Projection 流程；
5. Plan → Audit → Approval → Execution Feedback 流程；
6. 当前限制和未实现能力；
7. 可运行的最小示例；
8. 贡献和领域扩展方式。

### 7.4 GitHub 架构目录

```text
prism-enterprise-world-model/
├── world_model/
│   ├── ontology/
│   ├── state/
│   ├── dynamics/
│   ├── scenarios/
│   └── provenance/
├── decision_engine/
│   ├── intent/
│   ├── planning/
│   ├── audit/
│   ├── approval/
│   └── execution/
├── domains/
│   └── sales_visit/
├── examples/
├── docs/
└── tests/
```

### 7.5 GitHub 当前状态表达

```markdown
## Current Status

Prism is an actively evolving research and engineering framework.
The current implementation includes a canonical operational world-state
prototype, versioned policy structures, guarded transitions, scenario
branching, planner projections, and multi-dimensional audit prototypes.

SVDE is the first reference domain. Real road-network integration,
broader enterprise dynamics, and production decision-engine orchestration
remain active roadmap items.
```

## 8. 当前可宣传与不可宣传边界

### 可以宣传

- 企业决策世界模型架构；
- 业务语义与决策状态分离；
- 政策、承诺、事件和证据建模；
- 情景推演和状态转移原型；
- 规划器投影和多维审计；
- SVDE 销售拜访领域参考实现。

### 必须限定

- 真实数据回放；
- 历史服务时长估计；
- 约束下路线或周期优化；
- 场景容量影响；
- 业务收益和距离变化。

### 暂时不能宣传

- 通用企业世界模型已经生产就绪；
- 完全自主企业决策；
- 所有行业统一可用；
- 已经接入真实路网并保证最优；
- 未经同数据、同约束、同目标对照实验的收益百分比；
- 测试通过等于业务语义和生产能力已验证。

## 9. 内部统一讲解

### 30 秒版本

> 棱镜不是一个单点优化器，而是先建立企业的数字业务世界，记录企业当前状态、业务规则、承诺和资源，再模拟不同动作的后果，最后在这个世界中选择、审计和执行决策。

### 3 分钟版本

```text
数据库告诉我们有什么；
本体告诉我们这些东西是什么；
世界模型告诉我们现在是什么状态、为什么如此、动作后会怎样；
决策引擎在这些可能未来中选择下一步行动。
```

### 典型问题

问：你们是路线优化器吗？

答：路线优化只是一个领域能力。我们首先判断问题来自辖区、周期还是单日路线，再在企业世界模型中推演不同方案的业务后果。

问：你们是知识图谱吗？

答：知识图谱是语义底座的一部分。棱镜还需要状态、时间、事件、动作、状态转移、情景和执行反馈。

问：世界模型包括引擎吗？

答：企业世界模型系统包括状态转移和情景推演引擎；决策引擎负责候选方案生成、比较、审计、审批和执行编排。

## 10. 产品路线图

### Phase 1：Enterprise World Model Foundation

- Canonical enterprise state；
- ontology and evidence；
- policy and commitment model；
- bitemporal state and provenance。

### Phase 2：Dynamics and Scenario

- event-sourced transitions；
- deterministic scenario branches；
- causal effects and uncertainty；
- model calibration against execution outcomes。

### Phase 3：Decision Engine

- intent diagnosis；
- capability orchestration；
- candidate generation；
- planner projection；
- audit and approval；
- execution feedback。

### Phase 4：Domain Expansion

- sales visit and field operations；
- logistics and supply chain；
- workforce and healthcare scheduling；
- broader enterprise decision domains。

## 11. 最终官方表述

### 中文

> **TopPrism 构建企业决策世界模型，将企业语义、当前状态、业务动态、约束和行动空间连接成一个可推演、可审计、可执行的数字业务世界。企业可以在这个世界中比较经营动作的后果，并将经过治理的决策反馈回真实运营。SVDE 是 TopPrism 面向销售拜访与现场运营的首个领域决策引擎。**

### English

> **TopPrism builds enterprise decision world models that connect business semantics, operational state, dynamics, constraints, and feasible actions into a simulatable, auditable, and executable business world. Enterprises can compare the consequences of operational decisions before committing them, then feed governed outcomes back into real operations. SVDE is TopPrism’s first domain decision engine for sales visit and field operations.**

## 12. 参考资料

- [Business World Model](https://arxiv.org/abs/2606.10044)
- [Palantir Operational Applications](https://www.palantir.com/docs/foundry/app-building/operational-apps)
- [IBM What Is a Digital Twin](https://www.ibm.com/think/topics/digital-twin)
- [McKinsey Digital Twins for Supply Chain](https://www.mckinsey.com/capabilities/quantumblack/our-insights/digital-twins-the-key-to-unlocking-end-to-end-supply-chain-growth)
- [Deloitte Understanding Digital Twin Technology](https://www.deloitte.com/us/en/insights/topics/emerging-technologies/understanding-digital-twin-technology.html)
- [BCG AI Decision Agents](https://www.bcg.com/publications/2026/how-ai-decision-agents-transform-strategy)
