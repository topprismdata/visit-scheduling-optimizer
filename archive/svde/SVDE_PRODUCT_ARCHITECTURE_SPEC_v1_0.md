# SVDE Core Framework — 产品架构设计与技术全景规范 (v1.0)
**Document ID:** SVDE-PRODUCT-ARCHITECTURE-SPEC-V1.0  
**Date:** 2026-08-24  
**Classification:** Canonical Product Architecture & Engineering Blueprint  
**Status:** **APPROVED & GOVERNED (Enterprise Decision Intelligence OS Baseline)**  

---

## 1. 框架定位与设计哲学

**语义验证决策引擎（Semantic Validated Decision Engine, SVDE）** 是一个面向企业复杂运营调度的 **决策智能操作系统（Enterprise Decision Intelligence Operating System, Decision OS）**：

```
[SVDE 不是什么]                       [SVDE 是什么]
• 不是单体运筹优化求解器 (OR Solver)   • 声明式决策语义编译器 (Decision Compiler)
• 不是通用的 Chat 智能体工作流平台      • 可扩展的多步算力流水线路由器 (Capability Router)
• 不是某个特定领域的排班/分派小工具     • 物理/业务/语义正交独立的三维决策审计器 (Decision Auditor)
                                      • 带失效边界与抗负迁移的组织经验治理系统 (Governed Memory)
```

### 核心架构公理：
$$\text{DecisionRequest} \xrightarrow[\text{DomainAdapter}]{\text{Compile}} \text{DecisionSpec} \xrightarrow[\text{CapabilityRouting}]{\text{Plan}} \text{DecisionPlan} \xrightarrow[\text{PipelineExec}]{\text{Runtime}} \text{DecisionResult} \xrightarrow[\text{3D Audit}]{\text{Audit}} \text{DecisionArtifact}$$

---

## 2. 产品架构全景图 (Product Architecture Flowchart)

```mermaid
flowchart TB
    %% 样式定义
    classDef clientLayer fill:#F8FAFC,stroke:#64748B,stroke-width:1.5px,color:#0F172A
    classDef adapterLayer fill:#EFF6FF,stroke:#3B82F6,stroke-width:1.5px,color:#1E3A8A
    classDef coreEngine fill:#EEF2FF,stroke:#6366F1,stroke-width:2px,color:#312E81
    classDef capabilityLayer fill:#F0FDF4,stroke:#22C55E,stroke-width:1.5px,color:#14532D
    classDef auditLayer fill:#FEF3C7,stroke:#F59E0B,stroke-width:2px,color:#78350F
    classDef memoryLayer fill:#FAF5FF,stroke:#A855F7,stroke-width:1.5px,color:#581C87
    classDef benchLayer fill:#F1F5F9,stroke:#94A3B8,stroke-width:1.5px,stroke-dasharray: 4 4,color:#334155

    %% 1. 业务接入层
    subgraph L1 ["1. 业务应用与接入层 (Client & Business Ingestion)"]
        direction LR
        B1["城配物流调度系统<br/>(Urban Delivery Dispatch)"]
        B2["太古/快消销售拜访系统<br/>(Sales Visit & CRM)"]
        B3["医院/床位排班与新业务<br/>(Hospital Bed / Extended)"]
    end
    class L1,B1,B2,B3 clientLayer

    %% 2. 领域适配层
    subgraph L2 ["2. 显式领域适配层 (Domain Adapter Registry)"]
        direction LR
        A1["DeliveryDomainAdapter<br/>• 车辆载重/温区<br/>• 订单时窗/货载"]
        A2["VisitDomainAdapter<br/>• 代表技能/工时<br/>• 拜访周期/频次"]
        A3["ThirdPartyAdapter<br/>• 动态注册机制<br/>• 零修改 Core 接入"]
        PRE["DataPrecheckValidator<br/>• 真实数据入库预检<br/>• ID唯一/边矩阵/时窗"]
    end
    class L2,A1,A2,A3,PRE adapterLayer

    %% 3. SVDE 决策操作系统内核
    subgraph L3 ["3. SVDE Core 决策智能操作系统 (Decision OS Kernel)"]
        direction TB
        REQ["DecisionRequest<br/>(标准化业务请求)"] --> COMP["DecisionCompiler<br/>(语义标准化编译器)"]
        COMP --> SPEC["DecisionSpec<br/>• DecisionClass (结构分类)<br/>• DecisionStructure (一等公民结构)<br/>• Hard / Soft Invariants (约束清单)"]
        
        SPEC --> PLAN["DecisionPlanner<br/>(结构化算力规划器)"]
        PLAN --> DPLAN["DecisionPlan<br/>(有序算力流水线 CapabilitySteps)"]
        
        DPLAN --> RUN["RuntimeOrchestrator<br/>(运行时流水线执行器)"]
        
        subgraph STRUCT ["一等公民决策结构 (Decision Structures)"]
            direction LR
            S1["AssignmentDecisionStructure<br/>(资源-任务离散分配)"]
            S2["RoutingDecisionStructure<br/>(路网节点/边矩阵/时窗)"]
            S3["Allocation / Scheduling...<br/>(多范式结构扩展)"]
        end
    end
    class L3,REQ,COMP,SPEC,PLAN,DPLAN,RUN,STRUCT,S1,S2,S3 coreEngine

    %% 4. 可插拔算力网关
    subgraph L4 ["4. 可插拔算力网关 (Capability Registry & Adapters)"]
        direction LR
        C1["DiscreteAssignmentSolver<br/>(运力装箱/离散分配能力)"]
        C2["SequentialRoutingCapability<br/>(PyVRP / TSP 路网时序能力)"]
        C3["LLMReasoningAgent<br/>(大模型前沿提示推理能力)"]
        C4["CP-SAT / MIP ExactSolver<br/>(精确数学运筹求解引擎)"]
    end
    class L4,C1,C2,C3,C4 capabilityLayer

    %% 5. 独立三维决策审计器
    subgraph L5 ["5. 独立三维决策审计与验证层 (Decision Auditor & Verifier)"]
        direction TB
        AUD["DecisionAuditor<br/>(三维正交独立验证)"]
        
        subgraph EV_SPACE ["正交证据空间 (Segregated Evidence)"]
            direction LR
            E1["PhysicalFeasibilityEvidence<br/>(容量/工作时长/边连通性)"]
            E2["BusinessFeasibilityEvidence<br/>(SLA锁定承诺/无静默丢单)"]
            E3["SemanticComplianceEvidence<br/>(特种资质/温区/语义合规)"]
        end
        
        ART["DecisionArtifact (终局交付物)<br/>• decision (决策方案)<br/>• solution_feasible (物理可行)<br/>• decision_feasible (业务可行)<br/>• semantic_compliance (语义合规)<br/>• PipelineExecutionAudit (确定性 MD5 指纹)"]
    end
    class L5,AUD,EV_SPACE,E1,E2,E3,ART auditLayer

    %% 6. 决策知识与记忆治理层
    subgraph L6 ["6. 决策知识与记忆治理层 (Governed Decision Memory)"]
        direction LR
        MEM_STORE["PrincipleStore<br/>• DISC-PRIN-001 (承诺优先)<br/>• DISC-PRIN-002 (资质刚性)<br/>• DISC-PRIN-003 (局部接管)"]
        MEM_MATCH["PrincipleMatcher<br/>• 特征感知匹配<br/>• 失效边界过滤 (MP-G2)<br/>• 优先级分层仲裁 (Tier 1-3)"]
        MEM_GOV["PrincipleGovernance (MP-G1..G6)<br/>• 反事实检验 (Counterfactual)<br/>• 抗负迁移防线 (Negative Transfer Def)"]
    end
    class L6,MEM_STORE,MEM_MATCH,MEM_GOV memoryLayer

    %% 7. 独立外围评测基准套件
    subgraph L7 ["7. 独立外围评测与压力套件 (SVDE-Bench / 外部消费者)"]
        direction LR
        BENCH_CASE["Multi-Domain Cases<br/>(D01-D10, V01-V10)"]
        BENCH_STRESS["Scale Stress Generator<br/>(N=10, 50, 100 阶梯算例)"]
        BENCH_DIFF["Oracle Differential Bridge<br/>(CPSATExactOracle 差异对齐)"]
    end
    class L7,BENCH_CASE,BENCH_STRESS,BENCH_DIFF benchLayer

    %% 数据与控制流连线
    B1 --> A1
    B2 --> A2
    B3 --> A3
    A1 --> PRE
    A2 --> PRE
    A3 --> PRE
    PRE --> REQ

    RUN <--> MEM_MATCH
    MEM_STORE <--> MEM_MATCH
    MEM_MATCH <--> MEM_GOV
    
    RUN --> C1
    RUN --> C2
    RUN --> C3
    RUN --> C4
    
    C1 --> AUD
    C2 --> AUD
    C3 --> AUD
    C4 --> AUD
    
    AUD --> EV_SPACE
    EV_SPACE --> ART

    %% Bench 作为独立消费者测试 Core
    BENCH_CASE -.->|验证调用| REQ
    BENCH_STRESS -.->|压力负载| REQ
    BENCH_DIFF -.->|差异核验| ART
```

---

## 3. 架构分层与核心职责矩阵

| 架构层级 | 核心组件 | 关键职责与设计原则 |
| :--- | :--- | :--- |
| **1. 业务接入层 (Client Layer)** | 城配物流 / 太古快消 / 医疗排班 | 负责接收业务侧真实诉求，通过标准 API 发送 `DecisionRequest`，不感知底层数学模型与求解算力。 |
| **2. 显式领域适配层 (Domain Adapters)** | `DomainAdapters` + `DataPrecheckValidator` | **领域翻译与数据防线**：负责将异构业务对象翻译为通用 `NormalizedEntity`。在数据进入决策链前强制执行 6 项预检（ID 唯一、非负数值、时窗合法、边矩阵完整、Depot 明确、禁隐式时间），杜绝脏数据入库。 |
| **3. 决策操作系统内核 (Decision OS Core)** | `Compiler` $\rightarrow$ `Planner` $\rightarrow$ `Runtime` | **SVDE Core 调度中枢**：根据一等公民结构契约（分配/路由）构建有序算力流水线（`CapabilitySteps`），执行与具体领域词汇彻底解耦的纯净调度。 |
| **4. 可插拔算力网关 (Capability Registry)** | `CapabilityRegistry` (CP-SAT/LLM/VRP) | **计算算力插件池**：通过统一 `CapabilityContract` 接口即插即用，承接实际的数学规划、启发式求解、大模型推理或仿真计算。 |
| **5. 独立三维决策审计层 (Decision Auditor)** | `DecisionAuditor` $\rightarrow$ `DecisionArtifact` | **决策合规把关人**：独立复核并输出正交的 **物理可行（`solution_feasible`）**、**业务可行（`decision_feasible`）** 与 **语义合规（`semantic_compliance`）** 证据，杜绝任何静默丢单。 |
| **6. 决策知识与记忆治理层 (Governed Memory)** | `PrincipleStore` + `PrincipleMatcher` | **组织经验复利层**：维护带失效边界的高阶决策原则，通过 MP-G1..G6 六重治理门禁与抗负迁移机制，在运行时为算力提供安全经验指导。 |
| **7. 独立外围评测套件 (SVDE-Bench)** | `SVDE-Bench` (Cases / Stress / Oracle) | **外部测量与验证仪器**：仅作为 Core 的独立消费者与压力负载套件，验证系统的极限性能与对抗鲁棒性，严禁反向入侵 Core。 |

---

## 4. 真实数据接入前置规范 (Pre-flight Gate)

在进入真实生产数据测试前，必须严格遵循以下使用范围与预检准则：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SVDE 真实数据运行模式准入表                           │
├────────────────────────┬──────────┬─────────────────────────────────────────┤
│ 运行模式               │ 准入状态 │ 准入前置条件                            │
├────────────────────────┼──────────┼─────────────────────────────────────────┤
│ 真实历史数据离线回放   │ ✅ 准入   │ 必须通过 DataPrecheckValidator 预检     │
│ 影子模式（与现有排班对比）│ ✅ 准入   │ 必须具备完整真实边矩阵，不依赖默认时间  │
│ 自动写回生产排班/决策  │ ⛔ 暂缓   │ 需完成影子模式差异分析与人工审批闭环    │
│ 未提供边矩阵的路由数据 │ ⛔ 暂缓   │ 必须补齐实际路网通行矩阵后方可准入      │
└────────────────────────┴──────────┴─────────────────────────────────────────┘
```
