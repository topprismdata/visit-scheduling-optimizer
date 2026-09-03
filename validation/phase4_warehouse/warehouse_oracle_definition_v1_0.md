# Warehouse Independent Oracle Definition v1.0 — Phase 4.1 Artifact 4（Immutable）

oracle_id: WH-ORACLE-DEF-V1.0
generated_at: "2026-08-22"
ladder_level: "Exact Solver Oracle（独立 CP-SAT 实现，OPTIMAL+bound 验证，空间完全隔离）"

## 1. 独立性隔离声明（防同源欺骗）
- **变量命名**：`wh_o_x_{sku}_{loc}`，与生成器 `f2_wh_x_*` 严格隔离。
- **目标推导**：独立构建 Lexicographic 标量化权重（$L2 \times 10^6 - L3 \times 1$）。
- **代码隔离**：不引用仓储模型生成器的任何模型对象或约束函数。

## 2. 最优性判定准则
- 必须求得 `status=OPTIMAL` 且 `best_bound` 相等（Gap=0）。
- 输出 `(L1_status, L2_allocated_count, L3_total_pick_cost)` 供四方严格比对。

## 3. 外部现实扰动仲裁界限（World Model Arbitration）
- **Data Variation**：货位距离微调 $\pm 10\%$、货重微调 $\pm 5\%$ $\implies$ 判定为正常数据波动，$L1/L2$ 结构保持。
- **Semantic Variation**：温区故障（ColdZone 库位清零）$\implies$ 触发容量短缺与冷链不变量阻断，必须走异常链。
