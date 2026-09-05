# SVDE-Bench v0.1 执行控制与 Sprint 规划入册报告 v1.0
## Coding Agent 执行指令 · 六阶段 Sprint 路径 · 治理层登记

> **文档标识**：`SVDE-BENCH-EXECUTION-INTAKE-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`~/Downloads/SVDE-Bench_v0.1_Agent_Execution_Prompt_and_Sprint_Plan.md`（390 行，执行控制与 Sprint 规划规范）  
> **四大原则与执行纪律**：① 任务书作为执行控制指令入库（`EV-INTAKE-004`）✅ ② 角色严格定位为 **SVDE-Bench Core Engineer Agent**（只实现不重新定义）✅ ③ 四大不可妥协原则（Decision Artifact优先 / 语义层优先 / Oracle独立 / 零数据泄露）严格固化 ✅ ④ 开发策略遵循 `TDD + Milestone Delivery + Human Review Gate` 串行演进 ✅  
> **里程碑跃迁**：SVDE-Bench 正式确立了从 **Sprint 0（仓库脚手架） $\to$ Sprint 1（核心模型） $\to$ Sprint 2（首个闭环用例） $\to$ Sprint 3（四大评估器） $\to$ Sprint 4（独立 Oracle） $\to$ Sprint 5（10 个 Golden Cases）** 的精细化工程执行路线。

---

## 1. 执行控制规范核心要素逐项裁定与映射表

| # | 执行控制核心要求 | SVDE 既有工程体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **Agent 角色与事实源层级**<br>`Research Spec > Implementation Charter > Sprint Task > Code` | 确立 Agent 只负责工程实现、架构一致性与测试，禁止擅自修改 Benchmark 定义 | **确立为核心工作纪律** |
| **2** | **四大不可妥协原则 (Non-Negotiable Principles)**：<br>1. Decision Artifact > Solver Solution<br>2. Semantic Layer > Solver Layer<br>3. Oracle Independence<br>4. No Benchmark Leakage | 100% 对应 Phase 3–5 核心原则（Protocol not Runtime、Memory 不直赋求解器变量、Oracle 完全隔离、杜绝通过 Gold Label 作弊） | **固化为四项工程铁律** |
| **3** | **开发策略：禁止一次性大规模实现**<br>`TDD + Milestone Delivery + Human Review Gate` | 拒绝黑盒大包交付，每 Sprint 必须产出可运行代码、测试与结构化报告，经评审后推进 | **确立为标准迭代模式** |
| **4** | **Sprint 0–5 六阶段精细化演进路径**：<br>- Sprint 0: Repository Bootstrap (pyproject, 目录, pytest)<br>- Sprint 1: Core Schema (Case, Artifact, Trace, Memory)<br>- Sprint 2: First Golden Case (首个端到端闭环用例)<br>- Sprint 3: Evaluator (Semantic, Feasibility, Runtime, Memory)<br>- Sprint 4: Oracle (独立 CP-SAT 实现)<br>- Sprint 5: Ten Golden Cases (4/2/2/2 全量交付) | 极度清晰的增量交付阶梯，完美契合工程可控性与持续集成（CI）标准 | **采纳为 Sprint 执行路线图** |
| **5** | **Agent 三轮自检机制 (Three-Round Self-Check)**：<br>R1 代码正确性 / R2 架构一致性 / R3 基准完整性 | 每次提交前自动化执行三轮审计，确保无代码崩溃、无规范违背、无数据泄露 | **内嵌为交付检查模板** |
| **6** | **四项严禁行为 (Forbidden Actions)**：<br>禁自定义新指标 / 禁简化 Memory 为普通 RAG / 禁 LLM 替代 Oracle / 禁自动生成 Label 后直接采用 | 彻底杜绝常见企业 AI Benchmark 的自欺欺人缺陷 | **固化为安全红线** |
| **7** | **固定响应格式 (Agent Response Template)**：<br>Completed / Changes / Files / Tests / Architecture Check / Questions / Next Step | 标准化交互结构，确保人机协同评审的高效与透明 | **确立为输出模板** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-004` 证据入册
- **来源**：`SVDE-Bench v0.1 Agent Execution Prompt & Sprint Plan`
- **评级**：`Level-A (官方执行控制指令与 Sprint 计划)`
- **支持面**：支持 Coding Agent 身份定位、四大不可妥协原则、六阶段 Sprint 演化路径、三轮自检机制与固定汇报格式。

### 2.2 治理层记录 `KB-GOV-034`
- 正式登记 `SVDE-Bench v0.1 Execution Control & Sprint Roadmap`。
- 确认进入 **Sprint 0（Repository Bootstrap）** 执行阶段。

---

## 3. 结论与工程启动准备

```
Research Specification (Phase 7.4.0–7.4.14) ✅
           │
           ▼
Implementation Charter (Phase 7.4.15) ✅
           │
           ▼
Execution Prompt & Sprint Plan (执行控制冻结) ✅
           │
           ▼
Sprint 0: svde-bench/ 工程脚手架初始化 (pyproject.toml / 目录结构 / pytest 环境) ◀ 下一步启动
```

待指令正式启动 **Sprint 0：`svde-bench/` 独立仓库脚手架初始化与基础测试环境搭建**！
