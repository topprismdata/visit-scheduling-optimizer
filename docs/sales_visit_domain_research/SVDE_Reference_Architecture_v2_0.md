# SVDE Reference Architecture Specification v2.0
## 企业级受治理决策智能操作系统白皮书 · 理论大纲与工程全景证据

> **文档标识**：`SVDE-ARCH-SPEC-V2.0`  
> **冻结日期**：2026-08-22  
> **终极定位**：**Governed Decision Intelligence Infrastructure（企业级受治理决策智能基础设施）** / **Enterprise Decision Operating System（企业决策操作系统）**。  
> **核心命题**：**Agent is Interface, Protocol is Runtime**。从“提示词调工具（Agent Workflow）”彻底演进为“**以语义契约、类型安全、语义验证、异构编译、动态自适应与经验因果治理为核心的决策智能基础设施**”。  
> **非外推边界**：本架构已在约束优化型决策范式下完成微观调度、物理空间、战略资源与动态运行时的全闭环验证；不向无约束直觉决策或全自主 AGI 外推。

---

## 1. 终极架构拓扑：六层决策智能操作系统（The 6-Layer Decision OS）

```
                     ┌───────────────────────────────────────────────────────────┐
                     │          Decision Governance Layer (全局治理与红线层)       │
                     │  • Constraint Authority Hierarchy (L0 法律红线 > L1 战略...) │
                     │  • Memory Governance & Evolution Engine (因果提炼/生命周期)│
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │ 顶层治理约束
                                                   ▼
                     ┌───────────────────────────────────────────────────────────┐
                     │           Interface Layer (人类专家 / 领域 Agent / API)   │
                     │  • Protocol not Runtime (Agent 仅作为交互媒介，非系统内核) │
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │
                                                   ▼
                     ┌───────────────────────────────────────────────────────────┐
                     │            Semantic Layer (决策语义定义与安全层)          │
                     │  1. Semantic Contract       (业务契约与不可侵犯底线)        │
                     │  2. Constraint Type System  (强类型系统与生成期类型安全)   │
                     │  3. Decision Semantic Validation (Pre-Compile DSVL 闸门)  │
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │
                                                   ▼
                     ┌───────────────────────────────────────────────────────────┐
                     │           Decision Compiler Layer (数学建模与编译层)      │
                     │  1. Math Compiler           (MIP / CP / Flow 统一抽象模型) │
                     │  2. Solver Adapters         (MathOpt / HiGHS / CP-SAT 等) │
                     │  3. Independent Sequence Oracle (跨后端等价性仲裁基准)     │
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │
                                                   ▼
                     ┌───────────────────────────────────────────────────────────┐
                     │            Decision Runtime Layer (运行时状态与自适应层)  │
                     │  1. Runtime State Model     (物理状态机与历史事实不可逆)   │
                     │  2. Event Triage Engine     (Data vs. Semantic 变异分诊)  │
                     │  3. Incremental Recompile   (最小破坏重排与承诺保持)       │
                     │  4. Post-Event DSVL         (事件后动态可行性秒级复验)     │
                     └─────────────────────────────┬─────────────────────────────┘
                                                   │
                                                   ▼
                     ┌───────────────────────────────────────────────────────────┐
                     │             Decision Memory Layer (因果记忆与演化层)      │
                     │  • Episode Memory           • Constraint Evolution        │
                     │  • Outcome Memory           • Assumption Memory           │
                     │  • Counterfactual Memory    • Causal Dependency Memory    │
                     └───────────────────────────────────────────────────────────┘
```

---

## 2. 核心机制演进与架构规范升级

### 2.1 约束法定等级体系（Constraint Authority Hierarchy）
在多 Agent 协同与规则仲裁中，彻底消除单一加权打分的偶然性，确立**五级刚性层级（Strict Authority Levels）**：

$$
\text{Level 0: 法律与安全红线 (OSHA/劳动法/危化品/冷链)} \gg \text{Level 1: 企业战略红线 (Capex/Opex/品牌等级)} \gg \text{Level 2: 客户锁定承诺 (Locked Commitments)} \gg \text{Level 3: 经营目标 (Revenue/Coverage)} \gg \text{Level 4: 局部优化偏好}
$$

- **核心铁律**：低层级目标的置信度再高，**绝对严禁突破或软化高层级红线**。

### 2.2 记忆演化引擎（Memory Evolution Engine）
作为治理层的下属核心引擎，负责驱动记忆资产的长期演化：
1. **Memory Compression with Fidelity**：在压缩归纳（如 1000 Episodes $\to$ 24 策略模板）的同时，维持决策性能保留度 $\ge 98\%$。
2. **Bidirectional Lifecycle Management**：严密维护 `VALIDATED $\leftrightarrow$ DEPRECATED` 的双向可逆流转，支持商业环境漂移下的记忆自动失效与重新激活。
3. **Human Override Causal Assimilation**：建立人工干预的捕获、因果提炼与 Outcome 验证管道，实现人类专家智慧向因果依赖记忆（`DMEM-CAUSAL`）的安全转化。

---

## 3. 《Beyond Agents》七章技术专著大纲与工程全景证据

本规范正式冻结面向专著《Beyond Agents》的 **7 章核心理论命题与全生命周期工程实证映射表**：

| 专著章节 | 核心章节标题 | 核心理论与架构命题 | 对应的 SVDE 工程实证底座 |
|---|---|---|---|
| **Chapter 1** | **Beyond Agents: Protocol not Runtime** | 为什么 Agent 不是企业决策的核心，解构“提示词调工具流”的脆弱性，提出决策协议优先论 | Phase 0 & Phase 1：领域本体冻结、三层解耦纪律、0 DCR 治理底座 |
| **Chapter 2** | **Decision as the New Computational Object** | 决策作为一等计算对象的语义表征方法，如何形式化商业意图 | Phase 2：五大核心场景闭环（S-A 至 S-B），证明“不新增 Domain 是一种能力” |
| **Chapter 3** | **From Agent Workflow to Decision Compiler** | 从 Agent 脆弱工作流向编译器式决策架构的演进范式与符号字典映射 | Phase 3.0–3.1：编译契约、规范目标、数学符号与领域对象 100% 溯源 |
| **Chapter 4** | **Constraint Type System: Teaching AI What Cannot Be Broken** | 约束不是字符串：构建生成期类型安全体系（Shift Left 防御 6 类错误） | Phase 3.3-②：C01–C10 强类型注册表与 6/6 编译期阻断实证 |
| **Chapter 5** | **Decision Semantic Validation: Solution vs. Decision Feasibility** | 区分解可行性与决策可行性：构建前置与后置双重 DSVL 语义安全闸门 | Phase 3.3-③ & ⑤：三族 12 规则与外部路网数据接入下的决策保持 |
| **Chapter 6** | **Decision Runtime System: Adapting in a Changing World** | 运行时现实接入：状态机、历史不可逆性、Data vs. Semantic 变异分诊与增量编译 | Phase 4.3 & 5.0：Sequence Oracle 三节点时序验证与动态配送自适应 |
| **Chapter 7** | **Decision Intelligence OS: How Enterprises Learn From Decisions** | 决策记忆本体与治理：六类记忆资产、MDVL 晋升门限、因果图谱与防退化闭环 | Phase 5.1–5.3：A/B 对照实证、反事实/因果记忆引入、五大压力测试全通 |

---

## 4. 全生命周期验证全景档案（Phase 0–5 Milestone Dossier）

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ Phase 0–2: 决策对象形式化与领域契约冻结 (Domain Contract v1.0.1, 47 Frozen Concepts)     │
 │ Phase 3.0–3.3: 语义编译器基础与多后端等价 (GT-Micro/Small, MathOpt == CP-SAT Oracle)    │
 │ Phase 4.1–4.3: 跨决策范式通用化全闭环 (拜访-时间 / 仓储-空间 / 渠道-战略 / 配送-动态)    │
 │ Phase 5.0–5.3: 决策运行时与长期决策智能演进 (v1.5/v2.0 架构, 六大记忆资产, 压力测试全通) │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```
