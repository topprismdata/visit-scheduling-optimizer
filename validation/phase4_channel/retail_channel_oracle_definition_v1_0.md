# Retail Channel Independent Oracle Definition v1.0 — Phase 4.2 Artifact 4（Immutable）

oracle_id: CH-ORACLE-DEF-V1.0
generated_at: "2026-08-22"
ladder_level: "Exact Solver Oracle（独立 CP-SAT 实现，OPTIMAL+bound 验证，模型空间完全隔离）"

## 1. 独立性隔离声明
- **变量命名**：`ch_o_x_{zone}_{format}`，与生成器 `f2_ch_x_*` 严格隔离。
- **目标推导**：独立构建三级字典序标量化模型（$L2 \times 10^6 + L3 \times 1$）。
- **代码隔离**：不引用渠道模型生成器的任何模型对象或约束逻辑。

## 2. 最优性判定准则
- 必须求得 `status=OPTIMAL` 且 `best_bound` 相等（Gap=0）。
- 输出 `(L1_status, L2_strategic_score, L3_expected_revenue_k)` 供异构求解器严格比对。

## 3. 外部现实扰动仲裁界限（World Model Arbitration）
- **Data Variation**：商圈人口密度微调 $\pm 5\%$、商圈潜能指数微调 $\pm 10\%$ $\implies$ 判定为 Data Variation，战略布局结构保持。
- **Semantic Variation**：总预算腰斩 50%（Capex 降为 900k）、T1 核心商圈协议解约 $\implies$ 迫使战略决策结构重组，走异常链。
