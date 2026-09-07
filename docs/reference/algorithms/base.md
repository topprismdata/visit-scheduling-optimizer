# base（构造式基准：原分配 + 精确日内排序）

> 类别：构造式 | 实现：`experiments/run_contract_matrix.py::base_schedule` | 研究矩阵角色：**对比基准**——其他引擎的公里数都以它为分母

## 它解决什么

**不搜索**。保持原计划日历不动，只按共同规则（CP-SAT 精确排序）重排每日顺序——回答"业务现状的天花板在哪"。它是矩阵里所有引擎的**参照系**：各引擎的公里数都以 base 为分母（`vs_base_pct`）。

## 输入 / 输出

- 输入：共同原始计划 `days_orig`、距离矩阵 `D`、TSP 档位（主口径 cpsat）。
- 输出：候选列 `[(date, route, km)]` 入池 → Contract-SP 终闸（协议见 [../concepts/set-partitioning-final-gate.md](../concepts/set-partitioning-final-gate.md)）。

## 口径要点
- 基线数值存 `output/cpsat_plan_baselines.json`（0.1km 精度；毫精度改进为已知待办，见 GitHub issue #5/#6 的可移植性与口径整改批次）。
- 各日 CP-SAT 均**证完（OPTIMAL）**时 = "基线 A"（已证最优排序口径）；未证完 = 限时参照，禁止称已证最优。
- 基线列在生产协议（v2）中是每格安全网；研究协议（v3）中 base 是独立参照格，不注入引擎格。

## 相关

- 概念：[集合划分与终闸](../concepts/set-partitioning-final-gate.md)
- 数值对照：`output/cpsat_plan_baselines.json`；验收字段 `beats_baseline`（见 README §全局事实）
