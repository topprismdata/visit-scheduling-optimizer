# SVDE Domain Onboarding Specification v1.0
## 决策编译器跨领域接入标准规范（The Standard Onboarding Protocol）

> **文档标识**：`SVDE-ONBOARDING-SPEC-V1.0`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Step 0.5 —— Phase 4 通用化基准（Generalization Benchmark）的前提规范  
> **核心命题**：**SVDE 是通用决策编译器，不是单一拜访排班产品**。本规范定义类似 *Kubernetes Operator Interface* 或 *POSA 契约* 的标准协议，确保任何新业务领域接入 SVDE 时，遵循统一的 **Contract $\to$ Type $\to$ DSVL $\to$ Oracle $\to$ Trace** 接入标准，杜绝“换行业重新开发”。

---

## 1. 架构定位：领域接入的五大必需工件（The 5-Artifact Contract）

任何新领域（如仓储库位、渠道布局、干线配送）接入 SVDE 决策编译器，必须且仅需提供以下 **5 个标准不可变工件**，即可直接复用 SVDE 编译与验证内核：

```
                    ┌──────────────────────────────────────────────────────────┐
                    │               SVDE Compiler Kernel (通用内核)            │
                    │  - Constraint Pipeline Engine  - DSVL Core Scanner       │
                    │  - MathOpt Backend Adapters    - Trace Recorder          │
                    └──────────────────────────────────────────────────────────┘
                                                 ▲
                                                 │ 标准协议注入 (5-Artifacts)
                    ┌────────────────────────────┴─────────────────────────────┐
                    │            Domain-Specific Onboarding Package            │
                    │  1. Decision Semantic Contract (契约与不变量)            │
                    │  2. Constraint Type Registry (领域类型定义)              │
                    │  3. DSVL Domain Rules (决策可行性三族规则)                │
                    │  4. Independent Oracle Definition (仲裁与等价基准)        │
                    │  5. Decision Runtime Trace Schema (因果追踪模式)          │
                    └──────────────────────────────────────────────────────────┘
```

---

## 2. 五大标准工件规范（Artifact Specifications）

### 工件 1: Decision Semantic Contract（决策语义契约）
- **文件规范**：`<domain>_semantic_contract_v1_0.yaml`
- **必需定义**：
  1. **实体与输入模式（Entities & Intent）**：定义业务决策的一等对象（如货位/SKU、商圈/门店、车次/订单）。
  2. **业务约束清单（Semantic Constraints）**：声明 C1–Cn 条不可侵犯的业务边界，每条必须标注 `hardness`（HARD / SOFT_PREFERENCE / OBJECTIVE_PENALTY）与 `relaxable`。
  3. **决策级不变量（Decision Invariants）**：声明 $I_1–I_m$ 条核心业务底线（如危险品隔离不变量、核心客户必达不变量）。
  4. **规范目标函数（Canonical Objective）**：声明多层字典序或标量化目标结构，禁止下游 Solver 随意定义目标。

### 工件 2: Constraint Type Registry（约束类型注册表）
- **文件规范**：`<domain>_constraint_type_registry_v1_0.yaml`
- **必需定义**：
  1. **类型化元数据**：每条约束必须映射为强类型 `TypedConstraint`：
     - `semantic_class`：枚举（Equality, Cardinality, Temporal, Spatial, Capacity, MutualExclusion, Objective）。
     - `cardinality`：操作符与取值（如 `==`, `<=`, `range`, `pairwise_mutex`）。
     - `domain_provenance`：业务规则与法源依据（杜绝无来源的幻影约束）。
  2. **生成期静态检查规则（Type Check Rules）**：定义 Cardinality 匹配（如 ExactlyOne 要求 $k=1$）、HARD 自动软化阻断（TC-001）、目标与约束空间隔离（TC-003）。
  3. **后端多形态投影键（Solver Bindings）**：声明该类型在 MIP、CP-SAT 或规则引擎中的投影映射。

### 工件 3: DSVL Domain Rule Registry（决策语义验证规则集）
- **文件规范**：`<domain>_dsvl_rules_v1_0.yaml`
- **必需定义**：
  1. **Invariant Rules（Family I）**：验证业务不变量在编译后是否 100% 存在对应执法元素（缺一即判定 *Decision Infeasible*）。
  2. **Semantic Rules（Family S）**：
     - *S001 无静默丢弃*（覆盖矩阵零空洞）；
     - *S002 幻影零容忍*（100% 约束可溯源）；
     - *S003 软化白名单闭合*（非白名单约束严禁降级）；
     - *S005 实例基数律*（区分 Type Identity 与 Instance Identity）。
  3. **Trace Rules（Family T）**：验证 Intent $\leftrightarrow$ Type $\leftrightarrow$ Model 双射闭合。
  4. **双位检查机制**：支持 Pre-Compile（编译前静态扫描）与 Post-External-Data（外部数据扰动后复验）。

### 工件 4: Independent Oracle Definition（独立仲裁基准定义）
- **文件规范**：`<domain>_oracle_definition_v1_0.md`
- **必需定义**：
  1. **梯队定位（Ladder Level）**：声明属于 Enumeration Oracle、Exact Solver Oracle 还是 Independent Solver Oracle。
  2. **独立性隔离保障**：变量命名空间隔离（如 `o_x_*`）、参数与随机种子隔离、目标函数独立推导，禁止与编译生成器共享代码。
  3. **最优性断言标准**：声明 `status=OPTIMAL` 与 `gap=0` 判定线（或声明启发式上界基准）。
  4. **外部现实仲裁机制（World Model Arbitration）**：定义该领域的外部变异分类法（Data Variation vs. Semantic Variation）。

### 工件 5: Decision Runtime Trace Schema（运行时追踪模式）
- **文件规范**：`<domain>_trace_schema_v1_0.json`
- **必需定义**：
  1. **四段完整因果链**：`Decision Intent → Semantic Contract → Typed Constraints → DSVL State → MathOpt Model → Solver Output → Outcome`。
  2. **业务解释字段（Decision Explainability）**：结构化输出为什么选择 A、为什么延期 B、为什么拒绝 C。
  3. **Research Memory 钩子**：记录假设（Assumption）生命周期与失败分诊归因。

---

## 3. 接入合规检查清单（Onboarding Compliance Checklist）

新领域接入前必须通过以下 **8 项静态准入门限（Gates）**，方可进入 Benchmark 执行：

- [ ] **Gate O1 (Contract Freeze)**: 领域契约完整冻结，不存在未定业务规则。
- [ ] **Gate O2 (Type Safety)**: 约束类型注册表 100% 覆盖业务需求，生成期检查规则就绪。
- [ ] **Gate O3 (DSVL Coverage)**: 三族 12 条基础规则已特化为领域实现，支持前置/后置双检。
- [ ] **Gate O4 (Oracle Isolation)**: 独立 Oracle 代码完全隔离，不存在同源欺骗。
- [ ] **Gate O5 (Trace Integrity)**: 全链路因果数据结构已定义且机读。
- [ ] **Gate O6 (Negative Knowledge)**: 明确定义了该领域“不是什么”（如：$\text{Warehouse Slotting} \ne \text{TSP}$）。
- [ ] **Gate O7 (Variation Boundary)**: 明确了外部数据变异（如货位尺寸微调）与语义变异（如温区不可混放破坏）的界限。
- [ ] **Gate O8 (Assumption Registry)**: 初始化了该领域的冻结假设集（A001..An）。

---

## 4. 四大业务领域结构对比矩阵（Domain Comparison Matrix）

本矩阵确立了 Phase 4 通用化探索的领域梯度，验证 SVDE 跨越不同对象、时间与物理形态的编译能力：

| 维度 | Domain 1: 拜访调度（已闭环 ✅） | Domain 2: 仓储库位优化（Phase 4.1 ◀） | Domain 3: 渠道布局决策（Phase 4.2） | Domain 4: 配送调度（Phase 4.3） |
|---|---|---|---|---|
| **一等计算对象** | 销售代表 $\times$ 客户拜访需求 | 仓储货位 $\times$ SKU 批次存取 | 商圈网格 $\times$ 门店分销权 | 运力车辆 $\times$ 订单配送包 |
| **时间尺度** | 周期静态计划（2–4 周） | 准实时/波次动态（小时/班次） | 战略/战术规划（季度/年度） | 动态执行（日度/分钟级） |
| **核心物理约束** | 拜访频次、节奏、日容量、时窗 | 容积/承重、温区隔离、动线避让、周转率 | 辖区排他性、覆盖重叠度、渠道冲突 | 车辆配载、路网通行时段、装卸时窗 |
| **业务核心目标** | 覆盖率最大化、服务公平性、行程成本 | 拣货动线最短、出入库吞吐最大、空间利用率 | 市场渗透率最高、渠道收益最大、竞争压制 | 履约准时率、总里程最小、装载率均衡 |
| **数据变异源 (Data Var)** | 行程距离微调、平均停留时间微调 | 拣选行走耗时微调、货品重量微调 | 商圈人口统计微调、客流微调 | 动态路况慢行、实时车速微调 |
| **语义变异源 (Semantic Var)** | 锁定日冲突、业务员离职缺勤 | 危险品混放禁忌、冷链温区故障 | 区域排他协议违背、特许权争端 | 车辆故障、订单硬时窗违约 |
| **核心数学模式** | MP-01 (Assign), MP-02 (Cover), MP-04 (CP) | MP-01 (Assign), MP-03 (Flow), 2D/3D Packing | MP-06 (MIP), Location-Allocation | MP-05 (VRP), Time-Dependent Routing |

---

## 5. Phase 4.1 仓储库位优化（Agentic Warehouse Engine）接入指引

作为通用化第一战，Phase 4.1 将严格按照本规范提供 **5 大仓储工件**：
1. `warehouse_slotting_semantic_contract_v1_0.yaml`（定义货位、SKU、温区隔离不变量、出入库动线目标）。
2. `warehouse_constraint_type_registry_v1_0.yaml`（定义 `VolumeFit`, `WeightCapacity`, `ZoneIsolation`, `AffinityProximity` 等类型）。
3. `warehouse_dsvl_rules_v1_0.yaml`（验证危化品隔离不变量、出入库瓶颈可行性）。
4. `warehouse_oracle_definition_v1_0.md`（以独立 Exact Packing/Assignment Solver 为基准）。
5. `warehouse_trace_schema_v1_0.json`（记录 SKU $\to$ 货位指派的完整因果理由）。
