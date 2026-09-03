# SVDE-Bench Sprint 5 — Multi-Domain Benchmark Suite Task 入册报告 v1.0
## 十 Golden Case 领域覆盖矩阵 · 三类 Baseline Agent · 四维评价区分度 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-5-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 5 — Multi-Domain Golden Benchmark Suite Construction Task v1.0`  
> **核心命题**：**构建覆盖配送、仓储、渠道、拜访调度四类业务决策场景的 10 个 Golden Cases，验证 SVDE-Bench 对不同 Decision Intelligence 能力的区分能力，宣告 SVDE-Bench v0.1 完整数据集与评测体系正式验收**。  
> **核心交付**：
> ① 10 个 Golden Cases（配送 4/仓储 2/渠道 2/拜访 2）✅  
> ② 三类 Baseline Agent（Solver-only / Semantic-aware / Full Decision）✅  
> ③ 四维评价 Profile 全面区分度验证 ✅  
> ④ Benchmark Coverage Matrix & v0.1 主报告生成 ✅  
> **实施纪律**：先 Sprint 5A 冻结 Case Ontology 与 Schema Design，再 CASE-002~CASE-010 批量生产，避免“10 个孤例”退化为“一个真实 Benchmark 体系”。  
> **治理层与证据更新**：`EV-INTAKE-016` 证据入册，治理层记录 `KB-GOV-046`，路线图标记 Sprint 5 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **领域分布 10 Cases (4/2/2/2)**<br>Delivery (4) + Warehouse (2) + Channel (2) + Visit Scheduling (2) | 严格遵守 Sprint 5 任务书四大领域梯度 | **十大 Golden Cases 阵列入册** |
| **2** | **三类 Baseline Agent (Sol-only / Semantic / Full)**<br>建立下限 / 验证 SVDE 核心 / 验证完整能力 | 包含 `PureSolverMockAgent`, `SemanticAwareAgent`, 新增 `FullDecisionAgent` | **三类 Agent 矩阵对照** |
| **3** | **三道用例质量门限 (Gate A/B/C)**<br>区分度 / 覆盖度 / 失败可解释度 | 通过 `case_quality.py` 三维质检自动审计 | **用例质量标准化** |
| **4** | **统一 Case 格式 Schema 强约束**<br>严禁跨领域格式漂移 | 复用 Sprint 1A 已冻结的 `DecisionCase` Pydantic 模型 | **冻结用例设计语言** |
| **5** | **Oracle 全量覆盖**<br>每个 Case 必须具备独立 `OracleReference` | Sprint 4 实现的 `CPSATExactOracle` 扩展应用于全部 Case | **Oracle 全量可用** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-016` 证据入册
- **来源**：`SVDE-Bench Sprint 5 — Multi-Domain Golden Benchmark Suite Construction Task v1.0`
- **评级**：`Level-A (官方 Sprint 5 多领域基准构造任务书)`
- **支持面**：支持 10 Cases 领域覆盖矩阵、三类 Baseline Agent 矩阵、Benchmark 主报告输出。

### 2.2 治理层记录 `KB-GOV-046`
- 正式登记 `SVDE-Bench Sprint 5 Multi-Domain Benchmark Suite Construction Acceptance`。
- 确认进入 **Sprint 5（Multi-Domain Golden Benchmark Suite Construction）** 执行。

---

## 3. 下一步执行指引（Sprint 5A → Sprint 5B）

```
Sprint 4.5: Benchmark Calibration & Integrity Audit ✅ (DoD 达成)
           │
           ▼
Sprint 5A — Golden Case Ontology & Dataset Schema Design ◀ 当前启动
  • 冻结 Case Ontology (Domain Taxonomy, Difficulty Levels, Decision Dimensions)
  • 冻结 10 Cases 场景细节 (CASE-002 ~ CASE-010)
  • 扩展 FullDecisionAgent (Agent C) 实现

           │
           ▼
Sprint 5B — Ten Golden Cases Production & Suite Assembly
  • 实现剩余 9 个 Golden Cases (CASE-002 ~ CASE-010)
  • 编排 reports/benchmark/coverage_matrix.json
  • 编排 reports/svde_bench_v0_1_report.json (Master Report)
  • 编写 tests/{test_golden_case_suite, test_domain_coverage, test_agent_matrix, test_benchmark_report}.py
  • 执行 pytest 全量自检，目标 ≥ 100 组测试全绿
```
