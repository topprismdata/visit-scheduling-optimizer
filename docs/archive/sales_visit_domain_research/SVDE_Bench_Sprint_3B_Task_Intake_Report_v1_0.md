# SVDE-Bench Sprint 3B — Feasibility Evaluator Task 入册报告 v1.0
## 可行性评估器任务书入册 · 评价智能第二维度 · 统一结果基类模型 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-3B-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 3B — Feasibility Evaluator Implementation Task v1.0`  
> **核心命题**：**实现 SVDE-Bench 第二类核心评价器：`FeasibilityEvaluator`（物理与数学可行性评估器），冻结统一结果基类 `BaseEvaluationResult`，回答核心科学问题——“一个决策是否不仅语义正确，而且在数学、资源、物理约束上真正可执行？”**。  
> **核心架构原则**：① `SemanticEvaluator` (语义正确) 与 `FeasibilityEvaluator` (物理/数学可行) 完全解耦并行 ✅ ② 独立 `Oracle Comparison Interface`（比较 feasibility/objective gap，严禁 Oracle 生成答案）✅ ③ 强化实证：**数学可行（Solution Feasible）不等于业务正确（Decision Feasible）**（Golden Case 001 Baseline A: Semantic FAIL + Feasibility PASS）✅  
> **治理层与证据更新**：`EV-INTAKE-010` 证据入册，治理层记录 `KB-GOV-040`，路线图标记 Sprint 3B 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **统一结果基类模型：`BaseEvaluationResult`**<br>`evaluator_name`, `overall_pass`, `score`, `findings`, `evidence` | 位于 `svdebench.evaluator.models`，派生 `SemanticEvaluationResult` 与 `FeasibilityEvaluationResult` | **架构标准化** |
| **2** | **评价器定位：Feasibility Evaluator**<br>评价容量、承重、时窗物理可行性与硬约束满足性 | 对应 SVDE 架构核心：`Solution Feasibility` 与 `Physical Rack/Vehicle Limits` 独立验证 | **确立为第二核心评价器** |
| **3** | **Oracle 对比接口（Oracle Comparison Interface）**<br>接收可选 `OracleReference`，比较 `feasibility_status` 与 `objective_gap` | 纯黑盒比对，严禁求解器调用 Oracle 或 Oracle 生成候选解 | **建立独立比对接口** |
| **4** | **三大核心可行性评估规则**：<br>- Rule 1: Hard Constraint Validation（容量、时窗、资源）<br>- Rule 2: Physical Feasibility（车辆配载 $\le$ 容量、库位体积 $\le$ 容积）<br>- Rule 3: Oracle Comparison（客观目标差距量化） | 纯确定性物理校验逻辑，与 Semantic 评估器零互相调用 | **确定性算法规则实现** |
| **5** | **Golden Case 001 A/B 核心对账结论**：<br>- Baseline A: `Semantic FAIL` + `Feasibility PASS`<br>- Baseline B: `Semantic PASS` + `Feasibility PASS` | 实证 **Solution Feasibility $\ne$ Decision Feasibility** 核心科学命题 | **Golden Case 严格对账** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. 仅评价不生成 / 2. 零 Solver 调用 / 3. 独立于 Semantic / 4. Oracle 完全隔离 | 100% 保持独立性与解耦 | **自动化测试验证** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-010` 证据入册
- **来源**：`SVDE-Bench Sprint 3B — Feasibility Evaluator Implementation Task v1.0`
- **评级**：`Level-A (官方 Sprint 3B 执行任务书)`
- **支持面**：支持 `BaseEvaluationResult` 统一基类、`FeasibilityEvaluator` 架构、Oracle 对比接口与双维度对比实证。

### 2.2 治理层记录 `KB-GOV-040`
- 正式登记 `SVDE-Bench Sprint 3B Feasibility Evaluator Acceptance`。
- 确认进入 **Sprint 3B（Feasibility Evaluator Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 3A: Semantic Evaluator Implementation ✅ (DoD 达成)
           │
           ▼
Sprint 3B: Feasibility Evaluator Implementation ◀ 立即执行
  • 编写 svdebench/evaluator/models.py (BaseEvaluationResult, FeasibilityEvaluationResult)
  • 重构 svdebench/evaluator/semantic.py 继承 BaseEvaluationResult
  • 编写 svdebench/evaluator/feasibility.py (实现 FeasibilityEvaluator 与 Oracle Comparison)
  • 更新 svdebench/evaluator/__init__.py 导出完整评估器套件
  • 编写 tests/test_feasibility_evaluator.py (包含 5 组全覆盖测试用例)
  • 执行 pytest 全量自检与架构门禁复核
```
