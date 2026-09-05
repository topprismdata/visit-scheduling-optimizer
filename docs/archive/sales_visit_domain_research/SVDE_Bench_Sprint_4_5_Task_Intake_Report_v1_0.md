# SVDE-Bench Sprint 4.5 — Benchmark Calibration Task 入册报告 v1.0
## 基准可信度校准与完整性审计任务书入册 · 审计层架构建立 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-4.5-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 4.5 — Benchmark Calibration & Integrity Audit Task v1.0`  
> **核心命题**：**在横向扩展 10 个 Golden Cases 之前，建立 Benchmark Calibration Layer，从 Oracle 稳定性、Evaluator 公平独立性、代码级防作弊泄露扫描（Leakage Scan）与用例区分度（Case Quality）四大维度完成基准体系自洽性审计，确保评测体系客观可信**。  
> **四大核心问题回答（Q1–Q4）**：① Oracle 独立可信（支持无解识别、多重最优与目标权衡）✅ ② Evaluator 绝不退化为 Oracle Checker ✅ ③ 静态 AST 代码扫描杜绝跨模块非法导入泄露 ✅ ④ Golden Case 具备显著能力区分度（Decision Separation）✅  
> **治理层与证据更新**：`EV-INTAKE-015` 证据入册，治理层记录 `KB-GOV-045`，路线图标记 Sprint 4.5 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **校准层架构：`svdebench.calibration`**<br>`oracle_audit.py`, `evaluator_audit.py`, `leakage_scan.py`, `case_quality.py` | 独立于评测流水线的自省审计子包，负责评测工具链自检 | **确立为基准审计层** |
| **2** | **Oracle 健全性三大校准用例 (Sanity Cases)**：<br>- Case A: Infeasible Case (载重不足无解识别)<br>- Case B: Multiple Optimum (多重对称最优目标一致性)<br>- Case C: Objective Trade-off (多目标权衡稳定求解) | 验证 Oracle 求解器面对极端边界与冲突时的鲁棒性 | **装配为校准测试集** |
| **3** | **Evaluator 公平性审计 (`evaluator_audit.py`)**<br>验证 Evaluator 独立于 Oracle（Oracle 最优不代表 Agent 必须复制，允许存在业务鲁棒性溢价） | 彻底解耦数学最优与业务决策质量 | **固化为公平性原则** |
| **4** | **代码级防泄露扫描 (`leakage_scan.py`)**<br>四条规则：Agent 禁导 Oracle / Evaluator 禁导 Agent / Oracle 禁导 Evaluator / 私有数据集隔离 | 采用 Python `ast` 抽象语法树自动化扫描全部源码 | **确立为 CI 阻断防线** |
| **5** | **用例区分度评估 (`case_quality.py`)**<br>评估 Decision Separation（区分度）、Constraint Coverage（覆盖度）、Failure Interpretability（失败可解释度） | 确保每个入库 Case 均能有效区分优秀 Agent 与劣质 Agent | **建立用例质检标准** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. 基准自洽 / 2. 零答案泄露 / 3. 评测不退化 / 4. 用例有效区分 | 100% 满足审计标准 | **自动化审计验证** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-015` 证据入册
- **来源**：`SVDE-Bench Sprint 4.5 — Benchmark Calibration & Integrity Audit Task v1.0`
- **评级**：`Level-A (官方 Sprint 4.5 基准校准与审计规范)`
- **支持面**：支持 `svdebench.calibration` 模块、Oracle 稳定性测试套件、AST 防泄露扫描器与用例质量评估器。

### 2.2 治理层记录 `KB-GOV-045`
- 正式登记 `SVDE-Bench Sprint 4.5 Benchmark Calibration & Integrity Audit Acceptance`。
- 确认进入 **Sprint 4.5（Benchmark Calibration & Integrity Audit Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 4: Independent Oracle Implementation ✅ (DoD 达成)
           │
           ▼
Sprint 4.5: Benchmark Calibration & Integrity Audit ◀ 立即执行
  • 装配 svdebench/datasets/public/calibration/ 下 3 个 Sanity Cases (CALIB-A, B, C)
  • 实现 svdebench/calibration/ 下 4 个审计模块 (oracle_audit, evaluator_audit, leakage_scan, case_quality)
  • 编写 tests/test_oracle_calibration.py 与 tests/test_leakage_audit.py
  • 生成 reports/calibration/CASE-001-calibration-report.json
  • 执行 pytest 全量自检与架构门禁复核
```
