# SVDE 企业世界模型专项研究基线 v1.0

状态：研究基线（非冻结架构）  
日期：2026-08-24  
研究对象：企业世界模型、企业数字孪生、业务流程数字孪生、企业本体、决策智能平台

## 1. 研究结论

企业世界模型并没有统一的行业标准定义。当前公开资料中至少存在两种用法：

1. **模型狭义**：表示企业状态和状态变化规律的模型；
2. **系统广义**：包含企业状态、语义层、动态/仿真引擎、情景推演、优化、决策和执行反馈的完整运行系统。

对于 SVDE，不能简单选择“世界模型不包含引擎”的说法。更准确的定义是：

> **企业世界模型是一个可执行的企业内部模拟系统，包含企业状态表示、业务语义、状态动力学、约束、目标、可行行动空间和情景推演；决策引擎是使用该世界模型进行候选生成、优化、权衡、审计和执行编排的行动层。**

世界模型可以包含“状态转移/仿真引擎”，但应与“选择哪一个行动”的决策引擎保持可审计的职责边界。

## 2. 学术研究证据

### 2.1 Business World Model

《Business World Model》直接将 world model 特化到企业和组织环境，提出企业世界模型应编码：

- business states；
- business dynamics；
- constraints；
- objectives；
- feasible action space。

该研究进一步提出，企业世界模型应允许系统模拟替代行动序列、估计未来业务结果、评估不确定性下的权衡，并整合语义数据、概率模型、确定性业务规则和显式行动空间，形成可执行的内部模拟器。([Business World Model](https://arxiv.org/abs/2606.10044))

这与 SVDE 的目标高度一致，也说明“企业世界模型含动态/推演引擎”不是扩大解释，而是企业场景中的合理定义。

### 2.2 CIMOSA Enterprise Modelling Ontology

CIMOSA 企业建模本体同时覆盖功能、信息、资源、组织和时间，并定义活动、流程、事件、资源能力、企业对象、对象状态和组织单元。([The CIMOSA Enterprise Modelling Ontology](https://doi.org/10.1016/S1474-6670(17)44645-3))

启示是：企业世界模型不能只有实体本体，还必须表达流程、事件、资源、能力、对象状态和时间。

### 2.3 Enterprise Ontology

Enterprise Ontology 研究将本体定位为企业建模框架的语义基础，而不是企业运行系统本身。([The Enterprise Ontology](https://doi.org/10.1017/S0269888998001088))

启示是：本体提供语义基础；企业世界模型还需要状态实例、动态规则和运行反馈。

### 2.4 企业数字孪生研究

业务流程数字孪生研究通常将仿真模块和优化模块放在同一框架中，用于测试策略、预测延迟、识别瓶颈和优化履约。([Digital Twin Framework for Business Transactional Processes](https://doi.org/10.1016/B978-0-323-88506-5.50272-2))

近期企业数字孪生研究还将实时数据、状态估计、不确定性传播、预测控制和决策支持组合为一个闭环。([Digital Twin Framework for Proactive Enterprise Management](https://www.jove.com/t/71231/a-digital-twin-framework-for-proactive-enterprise-management-research))

## 3. 企业平台和知名公司的公开定义

### 3.1 Palantir：Ontology + Actions + Scenarios + Closed Loop

Palantir Foundry 的公开说明非常接近企业世界模型的广义实践：

- Ontology 提供决策所需的当前世界状态；
- Scenario 可以从真实状态分叉并应用动作；
- 模型可以预测复杂的下游影响；
- 用户比较方案后提交动作；
- 动作写回 Ontology，触发外部系统和后续流程；
- 决策及其理由进入可审计的 action log。

这实际上是：

```text
语义状态层
+ 情景/仿真层
+ 决策动作层
+ 执行回写层
```

而不只是知识图谱。([Palantir Operational Applications](https://www.palantir.com/docs/foundry/app-building/operational-apps))

### 3.2 IBM：数字孪生包含数据、分析、仿真和反馈

IBM 对数字孪生的企业定义包含：现实对象或系统的数字表示、实时数据集成、持续监测、仿真、分析和反馈控制。其公开说明还提到，企业可以连接多个数字孪生，整合 CRM、ERP 和业务流程，以支持未来场景和决策。([IBM What Is a Digital Twin](https://www.ibm.com/think/topics/digital-twin))

### 3.3 Microsoft：Process Digital Twin

Microsoft 的 Process Digital Twin 资料将数字孪生从物理设备扩展到业务流程，重点是流程状态、过程数据和运营改进，而不仅是三维资产模型。([Microsoft Process Digital Twin](https://info.microsoft.com/rs/157-GQE-382/images/Digital%20Twin%20Vision.pdf))

### 3.4 McKinsey：企业级数字孪生是跨系统的决策模型

McKinsey 将供应链数字孪生描述为跨资产、人员、流程和供应链节点的统一模型，并强调它可以进行端到端场景推演、比较权衡并支持日常决策，而不是只做一次性预测。([McKinsey Supply Chain Digital Twins](https://www.mckinsey.com/capabilities/quantumblack/our-insights/digital-twins-the-key-to-unlocking-end-to-end-supply-chain-growth))

McKinsey 还将企业数字孪生描述为多个互联数字孪生的系统，覆盖资产、人员和核心业务流程，并连接实时数据与决策。([McKinsey Digital Twins and Enterprise](https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/digital-twins-the-foundation-of-the-enterprise-metaverse))

### 3.5 Deloitte：企业数字孪生需要流程、仿真、数据和治理重构

Deloitte 强调，企业数字孪生不是单纯部署一套技术，需要跨部门数据、仿真平台、工作流、决策反馈循环、安全和治理共同配合。([Deloitte Understanding Digital Twin Technology](https://www.deloitte.com/us/en/insights/topics/emerging-technologies/understanding-digital-twin-technology.html))

### 3.6 BCG：决策智能可以把供应链数字孪生化

BCG 将 decision agent 描述为供应链的数字孪生：整合需求预测、供应能力、成本结构，指出信息缺口，模拟候选响应并评估成本和可行性。BCG 同时强调，需要结构化的跨职能数据层和编码化业务逻辑。([BCG AI Decision Agents](https://www.bcg.com/publications/2026/how-ai-decision-agents-transform-strategy))

BCG 对供应链数字孪生的描述也包含资产、仓库、物流、库存和物料流的模拟、风险识别以及多规划周期的决策支持。([BCG Supply Chain Digital Twins](https://www.bcg.com/capabilities/operations/conquering-complexity-supply-chains-digital-twins))

## 4. 各来源对企业世界模型的共同结构

| 能力 | 学术企业世界模型 | 企业数字孪生 | Palantir 类运营平台 | SVDE 应实现 |
|---|---|---|---|---|
| 当前状态 | 必须 | 必须 | Ontology 当前世界 | Canonical WorldState |
| 企业语义 | 实体与业务语义 | 数据/流程模型 | Ontology | L1/L2 语义层 |
| 时间与事件 | 状态动力学 | 实时同步/事件 | Action log | Event + bitemporal state |
| 约束与目标 | 明确要求 | 场景约束 | 规则和提交标准 | Policy / Commitment / Goal |
| 动态模型 | business dynamics | 仿真/预测 | 模型驱动 scenario | Transition Engine |
| 行动空间 | feasible action space | 控制/操作 | Actions | Capability / Action Catalog |
| 情景推演 | 核心能力 | 核心能力 | Scenario fork | Scenario Rollout |
| 优化与规划 | 可调用 | 常见模块 | 应用层能力 | Decision Engine / Planner |
| 执行反馈 | 目标 | 双向反馈 | 写回 Ontology | Execution Event |
| 审计与治理 | 不确定性/约束 | 数据治理 | Action log | Evidence / Audit |

## 5. SVDE 的正确定位

SVDE 不应采用以下过窄定义：

```text
World Model = 静态实体 + 关系 + 数据快照
Decision Engine = 完全独立、只读取数据的求解器
```

建议采用以下广义企业架构：

```text
SVDE Enterprise World Model System
├── Semantic State Layer
│   ├── Enterprise Ontology
│   ├── Canonical State
│   ├── Evidence / Provenance
│   └── Policy / Commitment / Goal
├── World Dynamics Layer
│   ├── Observation Assimilation
│   ├── State Transition Engine
│   ├── Rule Evaluation
│   └── Derived Estimates
├── Scenario & Simulation Layer
│   ├── State Forking
│   ├── Counterfactual Rollout
│   ├── Forecast Models
│   └── Uncertainty Propagation
└── Decision Interface Layer
    ├── Planner Projection
    ├── Candidate Evaluation
    └── Execution Feedback Contract

SVDE Decision Engine
├── Business Intent Diagnosis
├── Capability Orchestration
├── Candidate Generation
├── Optimization / Planning
├── Multi-dimensional Audit
├── Human Approval
└── Action Submission / Execution
```

结论：

- **状态转移引擎和情景仿真引擎属于世界模型系统内部**；
- **规划器可以是世界模型的使用者，也可以作为世界模型系统的决策接口组成部分**；
- **最终候选选择、审计、审批和执行编排属于决策引擎**；
- 两者可以部署在同一个产品中，但必须在契约上区分输入、输出和责任。

## 6. 对当前 SVDE 文档的影响

现有 L0~L6 分层可以保留，但需要改写命名和边界：

```text
L0 Foundational Architecture       世界模型系统基础架构
L1 World Model Meta-Model          世界模型元模型
L2 Domain Ontology                 企业领域语义
L3 Dynamics & Transition           世界动力学/状态转移
L4 Canonical State                 企业当前状态实例
L5 Scenario & Simulation            企业情景与推演引擎
L6 Decision Interface               规划器投影与决策接口
L7 Decision Engine                 规划、审计、审批、执行编排
```

当前套件只有 L0~L6，却把规划与决策产物全部压在 L6，缺少清晰的 L7 决策引擎层。建议新增：

`SVDE_ENTERPRISE_DECISION_ENGINE_ARCHITECTURE_SPEC_v1.0.md`

该文档应定义：

- 世界模型如何向决策引擎提供状态；
- 决策引擎如何请求情景推演；
- 规划器如何生成候选动作；
- 审计如何验证预期后状态；
- 人工批准如何写回行动；
- 执行结果如何更新世界模型。

## 7. 研究结论对销售拜访的直接启示

“缩短在途距离”不应被建模成单纯的路线优化问题，而应作为企业世界模型上的一个决策场景：

```text
当前销售运营状态
→ 假设改变辖区/客户归属/拜访周期/单日顺序
→ 世界模型推演状态变化
→ 决策引擎比较距离、覆盖、承诺、工作量和业务价值
→ 形成候选决策
→ 审批与执行
→ 实际结果回写
```

这与企业供应链数字孪生和 Palantir operational application 的共同模式一致：不是先展示一个优化结果，而是先围绕决策建立当前世界、候选动作、情景后果和可审计写回。

## 8. 最终研究判断

关于“企业世界模型是否含引擎”，不能回答简单的“含”或“不含”。应区分：

```text
世界模型核心：状态 + 语义 + 动力学 + 约束 + 目标 + 行动空间
世界模型运行引擎：状态估计 + 状态转移 + 情景仿真 + 预测
决策引擎：候选生成 + 优化 + 权衡 + 审计 + 审批 + 执行编排
```

在产品层，这三者可以组成一个统一的企业决策系统；在架构层，必须保持边界，否则无法判断一个错误来自状态错误、转移错误、预测错误，还是决策选择错误。

SVDE 的最终目标应定义为：

> **Enterprise World Model + Decision Engine：一个以企业语义和动态状态为基础，能够对经营动作进行情景推演、约束评估、优化选择和闭环执行的企业决策操作系统。**
