# SVDE-Bench v0.1 Implementation Charter 任务书解析与裁定报告 v1.0
## Coding Agent 工程实施任务书入册 · 评测仓库工程规范 · 治理层登记

> **文档标识**：`SVDE-BENCH-CHARTER-INTAKE-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`~/Downloads/SVDE-Bench_v0.1_Implementation_Charter.md`（406 行，Sprint 1–3 工程实施任务书）  
> **四项原则执行**：① 任务书作为工程实施指南与 Evidence 入库（`EV-INTAKE-003`）✅ ② 核心接口与数据模型 100% 对齐既有架构（0 新增 Domain）✅ ③ 绝不降低验证标准与指标体系 ✅ ④ 优先复用 Phase 0–5 已闭环的测试工件与 Oracle ✅  
> **工程里程碑跃迁**：SVDE-Bench 正式从《研究设计规范（Phase 7.4.0–7.4.14）》进入 **《工程实施任务阶段（Phase 7.4.15+）》**，确立了构建最小可运行评测仓库 `svde-bench/` 的完整工程准则。

---

## 1. 任务书核心工程要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE 既有体系对齐与实现方案 | 裁定结论 |
|---|---|---|---|
| **1** | **Sprint 1 范围冻结：10 个 Golden Cases**<br>（配送 4 / 仓储 2 / 渠道 2 / 拜访 2） | 100% 对应并复用 Phase 3.2/3.3（拜访 2）、Phase 4.1（仓储 2）、Phase 4.2（渠道 2）、Phase 4.3（配送 4）已生成的成熟工件与测试 Case | **采纳为 Sprint 1 最小基准集** |
| **2** | **Sprint 1 明确不做边界**<br>（无大规模 Dataset/无企业接入/无 UI/无 Leaderboard/无自研 Solver） | 彻底对齐 **Protocol not Runtime** 与专注评测内核的防发散纪律 | **严格执行** |
| **3** | **独立仓库结构 `svde-bench/`**<br>（`core/`, `evaluator/`, `oracle/`, `datasets/`, `agents/`, `runner/`, `reports/`, `tests/`） | 标准 Python 包架构（`pyproject.toml` 支持 `pip install -e .`），解耦评测 Harness 与算法内核 | **采纳为工程脚手架标准** |
| **4** | **Core Data Model**<br>`DecisionCase` (输入) $\longleftrightarrow$ `DecisionArtifact` (输出) | `DecisionCase`: id, domain, intent, world_state, contract, runtime, events<br>`DecisionArtifact`: decision, trace, explanation, memory_update | **复用**（完全对齐 Step 0.5 5 大工件与 Trace Schema） |
| **5** | **Agent 标准接口与隔离铁律**<br>`BaseDecisionAgent.solve(case) -> DecisionArtifact` | **严禁 Agent 访问 Oracle、Gold Label、Evaluator**，彻底杜绝 Benchmark 泄露 | **确立为安全基准铁律** |
| **6** | **四大 Evaluator 职责划分**：<br>1. Semantic / 2. Feasibility / 3. Runtime / 4. Memory | 分别对应 Type System 准确率、DSVL 决策可行性、状态机不可逆与 MDVL 晋升/拒绝检查 | **复用既有验证逻辑** |
| **7** | **独立 Oracle 规范**<br>（OR-Tools CP-SAT 独立实现，严禁求解器调用 Oracle） | 100% 继承 Phase 3.3/4.1/4.2/4.3 已验证的独立 Exact CP-SAT Oracle 隔离规范 | **复用** |
| **8** | **三大对比 Baselines**：<br>A. Pure Solver / B. LLM Mock Agent / C. SVDE Agent | 分别验证“纯优化 vs. 业务决策”、“提示词 LLM 脆弱性”与“完整 SVDE 决策编译器闭环能力” | **采纳为基线对照标准** |
| **9** | **自动化测试套件（pytest 支持）**<br>Schema / Oracle / Evaluator / Golden Case 四维测试 | 确保评测系统自身的工程健壮性与持续集成（CI）能力 | **采纳为工程交付门槛** |
| **10** | **三项开发禁令**：<br>禁改指标定义 / 禁降验证标准 / 禁简化 Memory 为普通 RAG | 守卫科学真实性，确保研究结论不被工程妥协稀释 | **固化为 Agent 行为红线** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-003` 证据入册
- **来源**：`SVDE-Bench v0.1 Implementation Charter`
- **评级**：`Level-A (工程实施规范与任务书)`
- **支持面**：支持独立仓库 `svde-bench/` 架构、`DecisionCase / DecisionArtifact` 核心数据模型、四大 Evaluator 与三基线对比。

### 2.2 治理层记录 `KB-GOV-033`
- 正式登记 `SVDE-Bench v0.1 Implementation Charter & Sprint 1 Scope`。
- 确认 Sprint 1 范围为 **10 个 Golden Cases**（4 配送 / 2 仓储 / 2 渠道 / 2 拜访），锁定 `svde-bench/` 八大目录工程拓扑与 7 项验收标准。

---

## 3. 结论与工程实施路线

```
Research Specification (Phase 7.4.0–7.4.14) ✅
           │
           ▼
Implementation Charter (Phase 7.4.15) ✅
           │
           ▼
Coding Agent Execution (svde-bench/ 工程脚手架搭建与 10 Golden Cases 自动化执行) ◀ 就绪
```

本任务书完成了从“评测规范”到“工程实施协议”的关键跨越。待指令启动 **`svde-bench/` 独立评测仓库工程搭建与 Sprint 1 验收套件执行**！
