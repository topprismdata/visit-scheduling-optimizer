# TopPrism 企业世界模型架构上位约束 (Overarching Architectural Constraint)

**Document ID:** TOPPRISM-ENTERPRISE-WORLD-MODEL-PRODUCT-COMMUNICATION-SPEC-v1.0  
**Date:** 2026-08-24  
**Status:** **MANDATORY ARCHITECTURAL CONSTRAINT (强制架构上位约束)**  
**Authority:** **产品最高层级架构约束。所有后续设计、代码、报告必须遵守，不得继续沿用 "SVDE = 整个系统" 的旧定义。**

---

## 一、产品层级 (Product Hierarchy)

```
TopPrism
└── Prism Enterprise Decision Intelligence (产品家族)
    ├── Prism Enterprise World Model (企业世界模型系统)
    ├── Prism Dynamics & Scenario Engine (动力学与情景仿真引擎)
    ├── Prism Decision Engine (企业决策引擎)
    └── Domain Decision Engines (领域决策引擎)
        └── SVDE Sales Visit Decision Engine (销售拜访领域决策引擎)
```

**关键澄清**：
- **SVDE 是领域决策引擎，不是企业世界模型平台的总名称**。
- SVDE 是建立在 Prism Enterprise World Model 之**上**的领域应用。
- 世界模型系统、动力学仿真引擎、决策引擎是 SVDE **消费**的底层底座，不是 SVDE 本身。

---

## 二、企业世界模型定义 (Enterprise World Model Definition)

企业世界模型**不是静态数据库、本体、知识图谱或路线优化器**，而是一个**可执行的企业内部模拟系统**，至少包含：

```
Semantic State                  — 当前企业状态
Evidence and Provenance        — 状态可追溯性
Business Policies and Commitments — 业务规则与承诺
Business Dynamics              — 业务动力学
State Transition Engine        — 状态转移引擎
Scenario / Simulation Engine   — 反事实情景推演与仿真
Constraints and Objectives     — 约束与目标
Feasible Action Space           — 可行动作空间
Planner Projection Interface   — 规划器投影接口
Execution Feedback             — 执行反馈闭环
```

它必须能回答 **5 个问题**：
1. 企业当前处于什么状态？
2. 这个状态为什么可信？
3. 如果采取某个动作，状态会如何变化？
4. 哪些未来状态是可行的？
5. 哪个候选方案更符合目标、约束和风险要求？

---

## 三、决策引擎定义 (Decision Engine Definition)

决策引擎是世界模型系统之上的**行动层**，负责：

```
Business Intent Diagnosis   — 业务意图诊断
Capability Orchestration     — 能力编排
Candidate Generation        — 候选方案生成
Planning / Optimization     — 规划与优化
Trade-off Evaluation        — 多目标权衡评估
Physical / Business / Semantic Audit — 三维独立审计
Human Approval              — 人工审批
Execution Orchestration     — 执行编排
Execution Feedback          — 执行反馈
```

**关键边界**：
- 状态转移和情景推演属于世界模型系统；
- 规划器是世界模型向决策引擎提供的接口能力；
- 候选方案选择、审计、审批和执行编排属于决策引擎；
- 两者可以部署在同一产品内，但**不能混淆契约和责任**。

---

## 四、必须读取的资料 (Agent 必须先学习)

1. `SVDE_ENTERPRISE_WORLD_MODEL_RESEARCH_BASELINE_v1_0.md`
2. `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md` (本文档)
3. `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md`
4. `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md`
5. `SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md`
6. `SVDE_PLANNER_PROJECTION_CONTRACT_v1.0.md`
7. `SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC_v2.0.md`
8. 当前 WM-FIX v3.0 报告及其对应代码

---

## 五、必须重新审查的内容 (Re-Audit Checklist)

| 审查维度 | 当前状态 | 必须判定 |
| :--- | :--- | :--- |
| L0-L7 分层是否存在 | 文档存在但易混淆 | 应严格界定 |
| L0/L1 是否仍被销售拜访语义污染 | 易发生 | **必须纯净**（World Model 不能被 SVDE 反向污染） |
| L3 是否真正属于世界模型动力学层 | `transition_engine.py` 已被归入 world_model/ | **OK 但需语义确认** |
| L4 是否是唯一 Canonical Enterprise WorldState | `OperationalDecisionWorldState` | **OK 但当前被 SVDE 测试深度耦合** |
| L5 是否是真正的 Scenario / Simulation Engine | `rollout_reallocation_scenario` 是简单实现 | **严重不足**（应支持多分支并行、反事实链） |
| L6 是否只是 Planner Projection Interface | `PlannerStateProjection` | **OK** |
| L7 是否单独定义了 Enterprise Decision Engine | **未定义** | **必须新增** |
| SVDE 是否被正确降为领域决策引擎 | **当前 SVDE = 系统** | **必须降级为"消费世界模型与决策引擎的应用"** |
| 规划器、审计器、审批、执行反馈分别属于哪一层 | 全部混在 SVDE | **必须按层重新归位** |

---

## 六、交付顺序 (MUST FOLLOW BEFORE ANY CODE CHANGES)

本轮 **不得先增加测试或扩展销售拜访字段**，必须先交付 8 项：

1. L0-L7 架构责任矩阵；
2. World Model System Boundary（边界定义）；
3. Decision Engine Boundary（边界定义）；
4. World Model ↔ Decision Engine Interface Contract（接口契约）；
5. 当前代码和文档影响分析；
6. 需要修改的规范清单；
7. 需要业务方确认的事项；
8. **经确认后再提交代码实现计划**。

---

## 七、禁止过度声明 (Reporting Discipline)

**所有报告必须区分五级成熟度**：

| 级别 | 状态 |
| :--- | :--- |
| 1 | 设计已定义 (Specification Defined) |
| 2 | 代码已实现 (Code Implemented) |
| 3 | 测试已验证 (Tests Verified) |
| 4 | 真实业务已验证 (Real Business Validated) |
| 5 | 生产能力已具备 (Production-Ready) |

**严禁出现**以下过度宣称：
- ❌ "企业世界模型已经完成"
- ❌ "决策引擎已经完成"
- ❌ "所有领域都具备生产能力"
- ❌ "已实现真实路网级优化"
- ❌ "已实现完全自主决策"

**任何宣称都必须明确标注所处的成熟度级别（1~5）**，让评审者一眼看清当前真实的工程进度。
