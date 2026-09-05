# SVDE-Bench Sprint 4 — Independent Oracle Task 入册报告 v1.0
## 独立数学参考预言机任务书入册 · 评价可信根建设 · 三方边界严格隔离 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-4-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 4 — Independent Oracle Implementation Task v1.0`  
> **核心命题**：**实现 SVDE-Bench 独立 Gold Reference Oracle（`ExactOracle` 与 `CPSATExactOracle`），回答核心科学问题——“对于一个决策用例，在不依赖任何 Agent 实现的前提下，什么是数学/约束空间中的可验证客观参考基准？”**。  
> **四项不可妥协隔离原则**：① **Oracle 独立性 (Gate 1)**：Oracle 严禁导入 `agents/` 包，零同源代码共享 ✅ ② **零答案泄露 (Gate 2)**：Oracle 仅输出客观数值与可行性状态（`OracleReference`），严禁输出 Agent 式决策动作建议 ✅ ③ **评估器解耦 (Gate 3)**：Evaluator 被动读取 OracleReference 进行 Gap 计算，Oracle 严禁调用 Evaluator ✅ ④ **语义隔离 (Gate 4)**：Oracle 不理解商业优先级/VIP/Prompt，只对纯数学约束求解 ✅  
> **治理层与证据更新**：`EV-INTAKE-014` 证据入册，治理层记录 `KB-GOV-044`，路线图标记 Sprint 4 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **Oracle 核心定位：可信参考基准**<br>独立生成 Gold Reference 的数学验证组件，非 Agent/非插件/非决策生成器 | 对应 SVDE 架构核心：`Independent Sequence Oracle` 与基准公正性基础 | **确立为可信客观根** |
| **2** | **三方边界隔离 (Three-Way Isolation)**<br>$\text{DecisionCase} \implies (\text{Agent} \to \text{Candidate}) \parallel (\text{Oracle} \to \text{Reference}) \implies (\text{Evaluator} \to \text{Compare})$ | 物理与代码级双重阻断，杜绝 Agent 读取 Oracle 作弊 | **建立三方物理隔离** |
| **3** | **输出数据模型：`OracleReference`**<br>`case_id`, `feasibility_status`, `objective_value`, `constraint_summary`, `solution_metadata`, `solver_status` | 位于 `svdebench.oracle.models`，严禁包含业务决策建议字段 | **冻结参考结果模型** |
| **4** | **独立 CP-SAT Oracle 实现 (`svdebench.oracle.cpsat`)**<br>基于 Google OR-Tools 原生 CP-SAT 独立建模（容量/时窗/硬约束），独立目标推导 | 零复用 Agent 端的模型生成器或约束解析器 | **独立原生数学实现** |
| **5** | **基准完整性测试套件 (`test_oracle_integrity.py`)**<br>独立运行、零 Agent 依赖、非 DecisionArtifact 输出、幂等性、Golden Case 参考值正确性 | 确保 Oracle 作为 Benchmark 可信根的绝对科学性 | **自动化完整性验证** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. 独立性 / 2. 零泄露 / 3. 评估器分离 / 4. 语义隔离 | 100% 保持纯数学参考本质 | **代码静态与动态双审** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-014` 证据入册
- **来源**：`SVDE-Bench Sprint 4 — Independent Oracle Implementation Task v1.0`
- **评级**：`Level-A (官方 Sprint 4 独立 Oracle 实施任务书)`
- **支持面**：支持 `OracleReference` 结构、`CPSATExactOracle` 架构、三方物理隔离边界与基准完整性测试。

### 2.2 治理层记录 `KB-GOV-044`
- 正式登记 `SVDE-Bench Sprint 4 Independent Oracle Implementation Acceptance`。
- 确认进入 **Sprint 4（Independent Oracle Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 3.5: Evaluation Framework & Profile Freeze ✅ (DoD 达成)
           │
           ▼
Sprint 4: Independent Oracle Implementation ◀ 立即执行
  • 编写 svdebench/oracle/models.py (定义 OracleReference 强类型模型)
  • 更新 svdebench/oracle/base.py (完善 BaseOracle 与 ExactOracle 接口)
  • 编写 svdebench/oracle/cpsat/{__init__.py, model.py, solver.py} (实现独立 CP-SAT 求解器)
  • 更新 svdebench/oracle/__init__.py 导出 Oracle 模型与求解引擎
  • 编写 tests/test_oracle_integrity.py (包含 5 组基准完整性与隔离性测试)
  • 执行 pytest 全量自检与架构门禁复核
```
