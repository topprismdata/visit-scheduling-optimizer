# Generic Sales Visit Engine — Post-Freeze Validation & Engineering Roadmap v1.0
## TopPrism AI-Native Decision Engine 开发规范（首例实施）

> **文档标识**：`RMAP-POSTFREEZE-ROADMAP-V1.0`  
> **所属**：TopPrism 决策优化工程框架 · 工程生命周期治理资产  
> **性质**：**项目级执行路线图（Phase Gate 治理）**——本文件是冻结后所有工作的唯一顺序依据，任何阶段不得跳跃。  
> **通用价值**：本流程将沉淀为 TopPrism 内部一切 AI-Native Decision Engine 的标准开发范式：  
> `Domain Freeze → Scenario Validation → Semantic Compilation → Backend Benchmark → Production`  
> （替代传统"需求→写模型→调参→上线"）。

---

## 0. 当前状态快照（2026-08-22）

```
Phase 0 — Architecture Design
  Status     : COMPLETED
  Artifacts  : A01 Evidence Baseline (v6.1.1)
               A02 Concept Crosswalk (v6.1.1)
               A03 Domain Contract v1.0.1 FROZEN
               A04 Technology Evidence Baseline (v6.1.1)
               A05 Reference Architecture FROZEN
               A06 Implementation Gate (READY FOR SPIKE / 生产 LOCKED)
  Governance : DOV (Deferral 归属验证) · DCR-SA-001-R (已落地)
               DVR (Domain Validation Report v1.0 — DG1–DG5 ALL PASS)
  Decision   : 架构修改 STOPPED
```

**冻结铁律**（全程有效）：
> 新增 Domain Concept 必须由**可复现 Scenario Failure** 驱动（DCR + Failure Evidence + Review）。  
> "未来可能需要""实现方便""Solver 需要"**均不是理由**。

---

## Phase 1 — Domain Validation ✅（已完成）

> **状态：COMPLETED（2026-08-22，DVR_domain_validation_report_v1_0.md）**  
> 本阶段不写 Solver、不比较算法、不优化性能。

| 交付物 | 载体 | 结果 |
|---|---|---|
| D1 Domain Coverage Matrix（实体×场景×状态） | DVR §4 | 31/31 实体覆盖 |
| D2 Domain Relationship Graph（孤儿/重复/隐式 metadata 审计） | DVR §2 | 孤儿 0 · 重复 0 · 受控 metadata 1 处登记 |
| D3 Glossary Freeze（术语唯一含义） | DVR §3 | 10 条冻结（Visit 四态切分） |
| D4 Scenario Coverage Review（A–E 覆盖检查，不执行） | DVR §4 | PASS |

**Phase 1 Gate（DG1–DG5）：ALL PASS** → 已放行 Phase 2。

---

## Phase 2 — Scenario Specification Validation ◀ 当前阶段

**目标**：验证 *Scenario 本身* 能否被 Domain 完整描述（仍不写 Solver）。

**顺序**：`A → C → D → E → B`（B 动态复杂度最高，压轴）。

**每个 Scenario 必须完成 16 项**（即 S-A 模板，已在 `S-A_..._v1_1_1.md` 确立为标准）：
```
1 Business Inputs          9  Candidate Formulations
2 Policy Configuration     10 Backend Candidates
3 Demand Generation        11 Ground Truth (GT-Micro/GT-Small 两层)
4 Occurrence Generation    12 Acceptance Criteria
5 Requirement Binding      13 Metamorphic Tests
6 Exception Handling       14 Benchmark Metrics
7 Feasibility Boundary     15 Domain Coverage
8 Audit Trace              16 Change Log (EMPTY by default)
```

**Phase 2 Gate**：
- 失败 → 仅 `Scenario Failure → DCR → Review`，**禁止 Scenario 自行 workaround**；
- Scenario A 现状：spec v1.1.1 就绪（Gate A1 Domain PASS / A2 Trace READY），**待执行验证**（装配实例 → 断言 §2.3 occurrence 表 + §4 八类 TA-* 测试，纯解释层，零数学）；
- C/D/E/B 待 A 通过后按模板复制。

---

## Phase 3 — Semantic Compilation Validation（首次进入数学）

**目标**：**不是比较速度**——证明同一业务语义可编译为不同数学模型且结果等价。

```
BusinessRequirement → Compiler → Formulation → Solver Result → Audit Trace
```

**最低三路**：F1 Pattern / F2 Compact MIP / F3 CP-SAT（同一 canonical objective 五层元组）。

**核心指标（非 runtime）**：
`Semantic Equivalence · Feasibility · Requirement fulfillment · Objective tuple · Constraint violation · Trace completeness`

**入口**：Phase 2 各场景 spec 全部通过后；GT-Micro 穷举 oracle + GT-Small 独立 exact 为比对基准。

---

## Phase 4 — Decision Compiler Generalization & Benchmark Spike

**目标**：此时才回答"哪个 Solver 更适合"。

```
Scenario → ProblemProfiler → SolverStrategySelector → Backend
```

**候选**：MathOpt+HiGHS/SCIP · 原生 CP-SAT · PyVRP · GCG/Coluna（**仅必要时**）。

**Benchmark 维度**：Model Size（vars/constraints/columns/patterns）· Runtime · Memory · Optimality Gap · Proof Level · Engineering Complexity。

---

## Phase 5 — Architecture Evolution Gate

**最后才允许**：增加 Compiler / Adapter / Solver Strategy。  
**禁止**：因"某 Solver 更喜欢"而修改 Domain。

---

## Phase 6 — Production Engineering

**解锁生产重构（解除 LOCKED）的唯一条件**：

```
Domain FROZEN ✅ + Scenario Passed ✅ + Semantic Compilation Validated ✅
+ Backend Selected ✅ + Trace Verified ✅
```

之后进入：API Design → Service Architecture → Implementation → Deployment。

---

## 给执行 Agent 的常备指令（引用条款）

> 1. 项目处于 **Post-Freeze Validation Phase**；禁止直接进入 GT-Micro/Solver Benchmark（须按 Phase 推进）。
> 2. **A03 v1.0.1 保持 FROZEN**；任何新增 Domain Entity 必须提交 DCR 并附 Scenario Failure Evidence。
> 3. 阶段顺序 **Phase 1→2→3→4→5→6，不得跳跃**；每 Phase 出具 Gate 报告后方可推进。
> 4. Phase 2 内场景顺序 **A→C→D→E→B**。
> 5. Solver/算法词汇禁止出现在业务层工作产物中（三层解耦铁律持续生效）。

---

## 阶段状态追踪表（Living Document）

| Phase | 名称 | 状态 | Gate | 证据载体 |
|---|---|---|---|---|
| 0 | Architecture Design | ✅ COMPLETED | Sign-off 2026-08-22 | A01–A06 v6.1.1 |
| **1** | **Domain Validation** | ✅ **COMPLETED** | DG1–DG5 ALL PASS | DVR v1.0 |
| **2** | **Scenario Spec Validation** | ✅ **CLOSED**（**A 18/18 · C 20/20 · D 20/20 · E 17/17 · B 13/13 = 88 测试 · 0 DCR 违规**） | Gate A/C/D/E/B ✅ · **DM 10→8**（009→004, 010→006+007）· DM-008 独立成立 · **Closure 快照已冻结** | 五场景 specs+reports + **SVDE_Phase2_Closure_Report_v1_0.md**（KB-GOV-007） |
| 3 | Semantic Compilation | ✅ **CLOSED**（3.0 契约 ✅ · 3.1 映射 ✅ · 3.2 GT-Micro ✅ · **3.3 Scale Validation ✅ 6步全闭环**） | 四 AC 全过 · 五假设 VALIDATED · Type System + DSVL 成立 | Phase3_3_final_evaluation_report_v1_0.md |
| 4 | Decision Compiler Generalization | ✅ **CLOSED**（**4.1 仓储库位 ✅** · **4.2 渠道布局 ✅** · **4.3 动态配送调度 ✅**） | 跨四大决策范式通用化全闭环（静态三域 + 动态运行时自适应） | Phase4_3_dynamic_delivery_generalization_report_v1_0.md |
| 5 | Decision Memory & Learning | ✅ **CLOSED**（**5.0 架构 v1.5 ✅** · **5.1-0 记忆本体 ✅** · **5.1-0.5 协议 ✅** · **5.1 资产化与 A/B 闭环 ✅**） | 决策学习基础设施全闭环（Memory → Semantic Layer → Better Decision） | Phase5_1_memory_assetization_report_v1_0.md |
| 6 | Production & Enterprise Generalization | 🔒 LOCKED（待路线 A/C 推进） | 路线 A 专著沉淀（SVDE-Bench Sprint 0-5 ✅ · **SVDE-Bench v0.1 Benchmark Suite 验收通过 ✅**） → 路线 C 真实客户 Benchmark → 路线 B 生产工程 | svde-bench/ (Sprint 5B Done) |
