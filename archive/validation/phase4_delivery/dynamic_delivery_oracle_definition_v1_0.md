# Dynamic Delivery Independent Oracle Definition v1.0 — Phase 4.3 Artifact 4（Immutable）

oracle_id: DD-ORACLE-DEF-V1.0
generated_at: "2026-08-22"
ladder_level: "Exact Solver Oracle（独立 CP-SAT 实现，Sequence Oracle 事件序列验证，模型空间完全隔离）"

## 1. 独立性隔离声明
- **变量命名**：`dd_o_x_{order}_{veh}` 与 `dd_o_arr_{order}`，与生成器 `f2_dd_x_*` 严格隔离。
- **目标推导**：独立构建四级字典序标量化模型（$L2 \times 10^6 - L3 \times 10^3 - L4 \times 1$）。
- **代码隔离**：不引用配送模型生成器的任何模型对象或约束函数。

## 2. Sequence Oracle 设计（针对事件流的多节点逐级仲裁）
针对动态事件序列进行分步仲裁，验证每个事件节点的 Decision Feasibility：
- **Node 0 ($t_0$)**：初始批次全局静态规划基准。
- **Node 1 ($t_1 = 120\text{min}$)**：Data Variation（轻微拥堵 ETA 微调）$\implies$ 验证零重编译，既有方案保持。
- **Node 2 ($t_2 = 180\text{min}$)**：Semantic Variation（`VEH_02` 机械故障）$\implies$ 验证增量重编译、历史已送不可逆、锁 100% 保持。

## 3. 最优性判定准则
- 每个事件节点必须求得 `status=OPTIMAL` 且 `best_bound` 相等（Gap=0）。
- 输出 `(L1_status, L2_fulfilled_count, L3_disruption, L4_total_time_min)` 供异构比对。
