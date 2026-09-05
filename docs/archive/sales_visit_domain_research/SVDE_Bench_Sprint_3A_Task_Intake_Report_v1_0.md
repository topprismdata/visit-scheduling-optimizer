# SVDE-Bench Sprint 3A — Semantic Evaluator Task 入册报告 v1.0
## 语义契约评估器任务书入册 · 评价智能第一阶段 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-3A-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 3A — Semantic Evaluator Implementation Task v1.0`  
> **核心命题**：**实现 SVDE-Bench 首个核心评价器：`SemanticEvaluator`（语义契约评估器），回答核心科学问题——“AI 生成的决策，是否真正理解并遵守了业务语义契约？”**。  
> **核心原则**：① 严格确定性结构化评估，杜绝 LLM Judge 替代规则 ✅ ② 输入严格限定为 `DecisionCase + DecisionArtifact`，零内部状态泄露 ✅ ③ 产生可审计 Evidence，区分 `HARD_COMMITMENT` 违背与 `SOFT_PREFERENCE` 妥协 ✅  
> **治理层与证据更新**：`EV-INTAKE-009` 证据入册，治理层记录 `KB-GOV-039`，路线图标记 Sprint 3A 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **评价器定位：Semantic Evaluator**<br>评价决策产物是否真正理解并遵守业务语义契约 | 对应 SVDE 架构核心：`Decision Feasibility` 与 `Constraint Semantic Preservation` | **确立为第一核心评价器** |
| **2** | **黑盒输入边界**<br>只允许 `DecisionCase + DecisionArtifact`，禁止访问 Agent 内部状态/Prompt/CoT/Solver 变量 | 严格执行 Benchmark 黑盒防作弊纪律 | **保持纯黑盒评价** |
| **3** | **输出数据模型：`SemanticEvaluationResult`**<br>`overall_pass`, `constraint_accuracy`, `constraint_results`, `violations`, `explanations` | Pydantic v2 强类型模式定义，每条约束输出结构化 `ConstraintResult` | **实现强类型结果模型** |
| **4** | **三条核心语义评估规则**：<br>- Rule 1: `HARD_COMMITMENT` 必须满足，违背则整体 `FAILED`<br>- Rule 2: 约束类型体系校验（Hard vs Soft vs Invariant 区分）<br>- Rule 3: 商业意图与决策动作语义对齐（Intent Alignment） | 100% 对应 `Constraint Type System` 与 `DSVL` 规则体系 | **确定性算法规则实现** |
| **5** | **Golden Case 001 A/B 对比判定**：<br>- Baseline A (Pure Solver): 判定 `overall_pass = False`<br>- Baseline B (Semantic Aware): 判定 `overall_pass = True` | 实证语义评价器具备准确区隔“裸优化假可行”与“语义真可行”的能力 | **Golden Case 严格对账** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. 仅评价不生成 / 2. 零 Solver 访问 / 3. 零内部状态读取 / 4. 输出可审计 Evidence | 100% 保持评价器独立性 | **自动化测试验证** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-009` 证据入册
- **来源**：`SVDE-Bench Sprint 3A — Semantic Evaluator Implementation Task v1.0`
- **评级**：`Level-A (官方 Sprint 3A 执行任务书)`
- **支持面**：支持 `SemanticEvaluator` 架构、`SemanticEvaluationResult` 结构、三条核心评估规则与 Golden Case 001 A/B 判定标准。

### 2.2 治理层记录 `KB-GOV-039`
- 正式登记 `SVDE-Bench Sprint 3A Semantic Evaluator Acceptance`。
- 确认进入 **Sprint 3A（Semantic Evaluator Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 2: First Golden Case End-to-End Pipeline ✅ (DoD 达成)
           │
           ▼
Sprint 3A: Semantic Evaluator Implementation ◀ 立即执行
  • 编写 svdebench/evaluator/semantic.py (实现 SemanticEvaluator 与 SemanticEvaluationResult)
  • 更新 svdebench/evaluator/__init__.py 导出评价器与结果模型
  • 编写 tests/test_semantic_evaluator.py (包含 5 组全覆盖测试用例)
  • 验证 Baseline A (FAIL) vs Baseline B (PASS) 的语义评价结论
  • 执行 pytest 全量自检与架构门禁复核
```
