# CP-SAT 开链精确 TSP（cpsat）

> 类别：精确（约束规划） | 实现：`VisitModel/src/visitmodel/tsp/open_chain.py`（`_exact_open_tsp_status` / `ExactTSPEngine`） | 矩阵身份：质量锚（n≤35 实测全 OPTIMAL）

## 它解决什么

顺序层的**质量锚**：给定当天店集合，求**开放路径**（无场站往返）的最短排列，并给出求解状态（OPTIMAL / FEASIBLE / …）。全系统"数学天花板"的证据来源——基线 A 与所有 km 主张的排序口径都由它定。

## 机制

- OR-Tools CP-SAT 的 **AddCircuit** 约束：节点间弧变量构成哈密顿圈；开放路径通过引入 dummy 场站（边权 0）转化为圈。
- 求解状态**随结果一起交付**（`status` 字段）——调用方据此决定是否称为"日内已证最优"；FEASIBLE 只能当限时参照。
- 8-worker 并行：平局次序可跨次抖动（证明最优时成本唯一，但路线可能不唯一）→ **确定性红线场景**（逐位复现）不要把求解器放进搜索期。

## 复杂度与预算

- 实测（矩阵口径 `cp_timeout=30s/日`）：n≤35 全部 OPTIMAL（22ms~1.06s）；n>35 未复测——**状态门控**：非 OPTIMAL 的日子按 FEASIBLE 口径报告，禁止外推"已达最优"。
- 确定性档：1 worker + 确定性时限（r2_alns 文档有实测记录）。

## 已知边界与陷阱

1. km 主张与排序耦合：同一日历换 TSP 档（nn2opt）会 +11~16%——报告必须带 TSP 因子。
2. 整数目标毫单位口径 vs 浮点重算：`sp_km_pool` 与 `sp_km_recomputed` 分开记录，禁止跨口径拼 gap。
3. LKH 在显式路网矩阵上曾劣于 CP-SAT（09 线 17.4 vs 14.03 km）——主精确引擎选 CP-SAT 有实测依据。

## 引用论文 / 资料

- Google OR-Tools CP-SAT：https://developers.google.com/optimization/cp/cp_solver（AddCircuit 约束文档）

## 相关文件与测试

- `VisitModel/src/visitmodel/tsp/open_chain.py`；`algos/tsp_engine.py`（shim）
- 使用点：矩阵 runner（`route_with_tsp`）、R2ALNS `final_reroute`、base 构造式
