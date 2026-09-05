# SVDE-Bench Sprint 2 First Golden Case Task 入册报告 v1.0
## 首个端到端黄金用例任务书入册 · 双 Baseline 对照 · 决策产物闭环 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-2-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`~/Downloads/SVDE-Bench_Sprint_2_First_Golden_Case_End_to_End_Pipeline_Task_v1_0.md`（449 行，Sprint 2 规范）  
> **核心命题**：**验证首个端到端完整评测流水线（$\text{Case} \to \text{Agent} \to \text{Artifact} \to \text{Validator} \to \text{Trace} \to \text{Memory} \to \text{Report}$），通过纯优化 Agent（Baseline A）与语义感知 Agent（Baseline B）的 A/B 行为对比，实证决策产物（Decision Artifact）的完备性与可审计性**。  
> **治理层与证据更新**：`EV-INTAKE-008` 证据入册，治理层记录 `KB-GOV-038`，路线图标记 Sprint 2 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | 既有体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **Golden Case 001 场景装配**<br>`Dynamic Delivery Failure Recovery v0.1` | 车辆故障下保护 VIP 客户（`ORD-03`）锁定交付窗口，商业意图设定为“承诺保护高于局部运输成本” | **装配为标准公共用例** |
| **2** | **候选方案 A/B 设计**：<br>- Candidate A: 成本最低但破坏承诺<br>- Candidate B: 成本微增但承诺 100% 保持 | 对应 Phase 5.1 A/B 闭环测试的核心对照逻辑 | **固化为评测标准解空间** |
| **3** | **双 Baseline Agents 实现**：<br>- Baseline A: `PureSolverMockAgent`（选 A）<br>- Baseline B: `SemanticAwareAgent`（选 B） | 检验无约束优化与决策编译器的本质差异（Solution Feasibility vs. Decision Feasibility） | **实装于 `svdebench.agents.baseline`** |
| **4** | **决策产物（DecisionArtifact）完备性**<br>包含 decision, trace, explanation, validation_result, memory_patch | 彻底践行 `Decision Artifact > Solver Solution` 核心原则 | **Pydantic 强类型输出** |
| **5** | **Memory Artifact 生成**<br>生成 `DMEM-EPISODE` 纯语义经验补丁（严禁求解器变量） | 遵循 Sprint 1B `MemoryObject` 与 `The Semantic Impact Law` 约束 | **生成标准 Memory 补丁** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. Artifact 优先 / 2. Memory 不改 Solver / 3. Oracle 隔离 / 4. 评测不读内部状态 | 100% 遵守既有治理铁律 | **全程自动化自检** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-008` 证据入册
- **来源**：`SVDE-Bench Sprint 2 First Golden Case End-to-End Pipeline Task v1.0`
- **评级**：`Level-A (官方 Sprint 2 执行任务书)`
- **支持面**：支持 Golden Case 001 场景规范、双 Baseline 行为模式、端到端评测流水线与报告 Schema。

### 2.2 治理层记录 `KB-GOV-038`
- 正式登记 `SVDE-Bench Sprint 2 First Golden Case Acceptance`。
- 确认进入 **Sprint 2（First Golden Case Pipeline Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 1B: Decision Memory Schema Implementation ✅ (DoD 达成)
           │
           ▼
Sprint 2: First Golden Case End-to-End Pipeline ◀ 立即执行
  • 装配 svdebench/datasets/public/cases/CASE-001-DELIVERY-RECOVERY.yaml
  • 实现 svdebench/agents/baseline/pure_solver_agent.py (Baseline A)
  • 实现 svdebench/agents/baseline/semantic_aware_agent.py (Baseline B)
  • 实现 svdebench/runner/pipeline.py (端到端运行、校验与报告生成)
  • 编写 tests/test_golden_case_001.py (覆盖 Case 加载、双 Agent 执行、校验、Trace 与 Memory 补丁)
  • 生成 reports/golden_case_001_report.json 并通过 pytest 全量验证
```
