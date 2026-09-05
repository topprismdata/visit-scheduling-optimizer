# SVDE-Bench Sprint 3.5 — Evaluation Framework Freeze Task 入册报告 v1.0
## 四维决策智能画像模型冻结 · 报告模式标准化 · 评价方法论冻结 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-3.5-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 3.5 — Evaluation Framework Freeze Task v1.0`  
> **核心命题**：**冻结 SVDE-Bench v0.1 四维决策智能画像（Four-Dimensional Decision Intelligence Profile），确立“严禁使用单一加权总分压缩评价”的核心评分纪律，完成评测结果聚合契约、报告 JSON Schema 与五大基准完整性规则的终态冻结**。  
> **核心架构原则**：① 四维正交评价模型（Semantic / Feasibility / Runtime / Memory）✅ ② 统一聚合契约 `DecisionIntelligenceProfile` ✅ ③ 报告模式标准化（`case_id` + `agent_name` + `decision_artifact` + `evaluation_profile`）✅ ④ 五大基准完整性铁律全局冻结 ✅  
> **治理层与证据更新**：`EV-INTAKE-013` 证据入册，治理层记录 `KB-GOV-043`，路线图标记 Sprint 3.5 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **四维决策智能画像模型 (Decision Intelligence Profile)**<br>Semantic Correctness $\times$ Execution Feasibility $\times$ Runtime Adaptability $\times$ Memory Governance | 对应企业决策的四维正交能力，彻底杜绝片面以数学解或提示词能力作为评价基准 | **确立为标准评价模型** |
| **2** | **评分策略冻结 (Score Policy Freeze)**<br>严禁压缩为单一总分（如 92.5分），必须以 Profile 形式并列呈现各维度的独立表现 | 保护不同 Agent（数学优秀型 vs. 语义感知型）的特质与可解释差异 | **固化为核心评分纪律** |
| **3** | **统一画像聚合模型：`DecisionIntelligenceProfile`**<br>`case_id`, `agent_name`, `semantic_result`, `feasibility_result`, `runtime_result`, `memory_result`, `overall_summary` | 位于 `svdebench.evaluator.profile`，纯聚合不重算，支持部分缺失兼容 | **实现强类型画像契约** |
| **4** | **标准报告模式冻结 (Benchmark Report Schema)**<br>`case_id` + `agent_name` + `decision_artifact` + `evaluation_profile (四维)` | 统一 `reports/` 目录下所有 Benchmark Case 的产出结构 | **标准化报告格式** |
| **5** | **五大基准完整性规则 (Integrity Rules 1–5)**：<br>1. 仅评价不生成 / 2. 零 Solver 调用 / 3. 零内部状态读取 / 4. Oracle 仅参考 / 5. Promotion 仅为评价结论 | 全局冻结为不可妥协的防作弊铁律 | **固化为工程基准红线** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-013` 证据入册
- **来源**：`SVDE-Bench Sprint 3.5 — Evaluation Framework Freeze Task v1.0`
- **评级**：`Level-A (官方 Sprint 3.5 评价方法论冻结任务书)`
- **支持面**：支持 `DecisionIntelligenceProfile` 结构、四维正交画像模型、Score Policy 禁单一总分纪律与报告 JSON Schema。

### 2.2 治理层记录 `KB-GOV-043`
- 正式登记 `SVDE-Bench Sprint 3.5 Evaluation Framework & Profile Schema Freeze`。
- 确认进入 **Sprint 3.5（Evaluation Framework Freeze Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 3D: Memory Evaluator Implementation ✅ (DoD 达成)
           │
           ▼
Sprint 3.5: Evaluation Framework Freeze ◀ 立即执行
  • 编写 svdebench/evaluator/profile.py (实现 DecisionIntelligenceProfile 与聚合生成器)
  • 更新 svdebench/runner/pipeline.py (支持生成包含完整 evaluation_profile 的标准报告)
  • 更新 svdebench/evaluator/__init__.py 导出 Profile 相关模型
  • 迁移 reports/golden_case_001_report.json 符合标准模式
  • 编写 tests/test_evaluation_profile.py (包含 5 组全覆盖单元测试)
  • 执行 pytest 全量自检与架构复核
```
