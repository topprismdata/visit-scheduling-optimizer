# SVDE Architecture Specification v1.0
## Decision Compiler Infrastructure 架构白皮书与技术规范

> **文档标识**：`SVDE-ARCH-SPEC-V1.0`  
> **冻结日期**：2026-08-22  
> **架构分水岭判定**：基于 Phase 3.3（GT-Small + MathOpt + KBC-05 仲裁）完整证据闭环，SVDE 正式从 v0.1 概念设计升级为 **SVDE Architecture v1.0（编译器式企业决策系统架构）**。  
> **核心命题**：**Agent is Interface, not Runtime (Protocol not Runtime)**。核心不是构建 Agent 调 Tools 的工作流，而是构建具备类型检查与语义验证能力的 Decision Compiler 基础设施。

---

## 1. 总体架构拓扑（The Seven-Layer Decision Topology）

```
                    Human / Agent Interface
                              ↓
                  Decision Experience Layer
                              ↓
                     Decision Compiler
        ┌──────────────────────────────────────────┐
        │  1. Semantic Contract (冻结契约)          │
        │          ↓                               │
        │  2. Constraint Type System (类型安全)    │
        │          ↓                               │
        │  3. Decision Semantic Validation (DSVL)  │
        └──────────────────────────────────────────┘
                              ↓
                   Decision Engine Layer
        ┌──────────────────────────────────────────┐
        │  Optimization  │  Simulation             │
        │  Prediction    │  Business Rules         │
        └──────────────────────────────────────────┘
                              ↓
                     Decision Runtime
                              ↓
                     Decision Memory
```

---

## 2. 核心组件规范与职责边界

### 2.1 Layer 1: Decision Compiler（决策编译器核心）
决策编译器将高层业务意图（Business Intent）确定性地编译为数学执行指令，下设三个流水线阶段：

1. **Semantic Contract Layer（语义契约层）**
   - **职责**：定义不可侵犯的业务边界，形成机器可读的 C1–C10 语义约束规范与 $I_1–I_5$ 业务不变量。
   - **核心断言**：Contract 冻结先于任何模型生成；禁止下游绕过 Contract 直接向 Solver 注入规则。
2. **Constraint Type System（约束类型系统）**
   - **职责**：将业务约束从无类型的字符串提升为强类型的 `TypedConstraint`（定义 `semantic_class`, `cardinality`, `hardness`, `relaxable`, `domain_provenance`）。
   - **核心断言**：类型在生成期实施静态检查（Shift Left），确定性拦截 `AddExactlyOne@k=2`、`HARD_AUTO_SOFTENING` 等 6 类语义错误。
3. **Decision Semantic Validation Layer — DSVL（决策语义验证层）**
   - **职责**：验证约束集合是否仍然保持原业务意图（Decision Feasibility）。
   - **执行时机**：**前置（Pre-Compile，模型生成前）+ 后置（Post-External-Data，外部现实数据接入后）双重验证**。
   - **三大法宝**：
     - *Invariant Checking*（业务不变量绝对保持，如锁定日、不可拆分资源）；
     - *Constraint Semantic Checking*（约束含义不被错误降级或软化，幻影约束零容忍）；
     - *Trace Consistency Checking*（Intent $\to$ Contract $\to$ Type $\to$ Model $\to$ Solution 全链路可追溯）。

### 2.2 Layer 2: Decision Engine Layer（多模态决策引擎层）
- **定位**：无状态的多引擎执行池（Optimization / Simulation / Prediction / Rules）。
- **解耦原则**：底层 Solver（MathOpt / HiGHS / CP-SAT / VRPSolverEasy）全部为 Reference 态，**Solver 的更替或升级绝不触发上游业务知识库与契约的变更**。

### 2.3 Layer 3: Decision Runtime & Decision Memory（运行时与决策记忆）
- **Decision Feasibility vs. Solution Feasibility**：
  - Solver 仅验证 *Solution Feasibility*（“解是否满足数学公式”）；
  - DSVL 与 Runtime 验证 *Decision Feasibility*（“数学解是否依然忠实于原业务决策”）。
- **Decision Memory**：将完整的因果链路（Decision IR $\to$ Typed Constraints $\to$ Solver Outputs $\to$ Outcomes）沉淀为企业的决策知识资产，支撑持续回溯与学习。

---

## 3. 核心术语冻结表（Terminology Freeze）

| 术语名称 | 规范英文 | 权威定义与边界 |
|---|---|---|
| **决策编译器** | Decision Compiler | 将企业业务决策意图规范化、类型化、验证并无损编译为可执行计算模型的软件基础设施。 |
| **决策可行性** | Decision Feasibility | 解与计算过程是否忠实满足业务意图与底线不变量。与单纯满足数学方程的 *Solution Feasibility* 严格区分。 |
| **决策语义验证层** | DSVL | Decision Compiler 的语义安全闸门，通过 Invariant / Semantic / Trace 三族规则守卫 Decision Feasibility。 |
| **约束语义流水线** | Constraint Semantic Pipeline | 约束演进的五级确定性链路：$\text{Business Rule} \to \text{Semantic Contract} \to \text{Typed Constraint} \to \text{Math Constraint} \to \text{Solver Constraint}$。 |
| **数据变异 vs. 语义变异** | Data vs. Semantic Variation | 外部现实（如路网、耗时）变化仅导致目标数值微调而不改变决策结构者为 **Data Variation**；迫使约束失效或决策重组者为 **Semantic Variation**。 |
| **负向知识** | Negative Knowledge | 明确界定系统“不是什么”与“禁止调用什么”（例如：$\text{Territory Alignment} \ne \text{VRP / Clustering}$），有效消除 Agent 幻觉。 |

---

## 4. 失败分类学标准（The SVDE Failure Taxonomy）

本规范正式冻结源自 Phase 3.2 与 Phase 3.3 实战的 **SVDE 失败三级分诊法（Failure Triage Method）**：

```
                              System Failure Occurs
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        Assumption Failure?                      Implementation Failure?
  (查阅 Frozen Assumption Registry)            (按 Class A/B/C 三级分诊)
        │                                                 │
        ├─ A001..A005 失效 → 修订假设并重申范围           ├─ Class A: Domain 缺失 → 严谨 DCR
        └─ 否则进入 Implementation 分诊                   ├─ Class B: 编译规则缺失 → 登记 CRR
                                                          └─ Class C: 生成/校验实现缺陷 → 就地修复
```

- **Class C 典型缺陷库**（已沉淀入 Compiler 守卫）：
  1. *Checker Scope Error*（如 `tc006` 将容量误当频次）：验证器本身必须具有类型边界。
  2. *Identity Granularity Error*（如 `C03` 实例唯一误判）：必须区分 Type Identity 与 Instance Identity。
  3. *Vocabulary Mapping Error*（如 `T002` 大小写敏感断链）：语义校验必须基于大小写免疫的稳定 Ontology 词表。

---

## 5. Phase 4 演进方向：从单一排班到决策编译器通用化

Phase 4 的核心战略任务由“单纯追求大规模算力跑分”正式调整为 **Decision Compiler Generalization（决策编译器通用化验证）**，探索本架构跨领域的迁移能力：

```
                                 SVDE Decision Compiler v1.0
                                                │
         ┌──────────────────────┬───────────────┴──────────────┬──────────────────────┐
         ▼                      ▼                              ▼                      ▼
  Domain 1 (已闭环)      Domain 2 (仓储)                Domain 3 (渠道)        Domain 4 (配送)
Sales Visit Scheduling  Agentic Warehouse Engine     Retail Channel Layout   Fleet Route Logistics
```

---

## 6. 《Beyond Agents》核心章节映射大纲

| 章节 | 标题 | 核心理论命题 | 对应的 SVDE 工程实证底座 |
|---|---|---|---|
| **Chapter 1** | Beyond Agents | 为什么 Agent Workflow 不是企业计算的终点（Protocol not Runtime） | Phase 0–1：三层纪律与领域本体冻结 |
| **Chapter 2** | Decision as Computational Object | 决策作为一等计算对象的语义表征方法 | Phase 2：五场景闭环与不新增 Domain 证明 |
| **Chapter 3** | From Agent Workflow to Decision Compiler | 编译器式架构如何替代脆弱的提示词调工具流 | Phase 3.0–3.1：编译契约与符号映射表 |
| **Chapter 4** | Constraint Type System | 教 AI 理解“什么是绝对不能打破的业务底线” | Phase 3.3-②：C01–C10 类型注册与 6/6 生成期拦截 |
| **Chapter 5** | Decision Semantic Validation | 如何确保数学模型忠实于人类商业意图（DSVL） | Phase 3.3-③ & ⑤：三族规则与前置/后置双重守卫 |
| **Chapter 6** | From Solver to Decision Engine | 异构计算引擎与外部现实数据接入的解耦之道 | Phase 3.3-④ & ⑤：MathOpt 异构等价与 KBC-05 仲裁 |
| **Chapter 7** | Decision Memory | 企业如何从每一次决策因果回溯中持续演进 | Phase 3.3-⑥：全链路 Trace 与 Assumption 状态机 |
