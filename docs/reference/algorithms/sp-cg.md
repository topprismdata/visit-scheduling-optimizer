# SP + 列生成（sp_cg，对偶驱动供列）

> 类别：LP 列生成框架 | 实现：`algos/sp_matheuristic.py`（编排）+ `VisitModel/src/visitmodel/sp/{formulation,pricing}.py`（公式与定价） | 矩阵身份：km + 下界

## 它解决什么

启发式供列是"盲搜"；列生成（CG）是"问对偶"：解一遍受限主问题（RMP）LP → 对偶 π/μ 指出**当前最缺什么列**（reduced cost < 0）→ 定价子问题专找负 rc 列 → 回灌重解 → 循环到找不到为止。`sp_cg` 是 CG 的完整实现，也是全系统对偶语义（`{store, date}`）的权威出处。

## 定价子问题（rc 公式）

```
rc(r@d) = km(r) − Σ_{c∈r}(μ_c) − π_d      （合同模式：μ_c 已含合同覆盖影子价；R2′ z 绑定不进定价）
```

- `price_columns`：top-m 对偶引导贪心插入产列（启发式定价）；批量 ≤60 列/轮。
- 能力边界（SCIP heuristic/exact pricer 口径）：启发式定价下 CG 收敛只意味着"当前定价器找不到负列"，**不是**"不存在更好的列"——`is_global_certified` 恒 False。

## 输入 / 输出

- 输入：起始池（原计划重排）、`r2_prime=True`、`contract`、走廊。
- 输出：`(rmp_lp, generated_columns, cg_iters, converged)`；编排层再交 Contract-SP 终闸。

## 机制

```
column_generate（algos/sp_matheuristic.py）:
  loop max_iter 轮:
    lp = sp_solve_lp(...)          # RMP LP + 对偶
    cols = price_columns(duals)    # 启发式定价（top-m 贪心）
    若无负 rc 列 → converged，退出
    回灌 cols（(date,店集) 去重）
```

## 复杂度与预算

- 每轮 = 一次 LP（GLOP，池线性）+ 一次定价（O(dates × top_m × 插入)）；`max_iter=6, col_iter=60, top_m=40` 为现行机制档。
- 确定性：GLOP 对偶数值稳定；定价贪心平局按店号——同输入同输出。

## 已知边界与陷阱

1. **受限池 INFEASIBLE ≠ 业务不可行**：池过滤可能饿死店（有测试钉住：剥除店全部列后必须返回不可行而非缺店解）。
2. 下界是 RMP 值（已探索列空间），不是全局下界——报告只许写 `pool_gap_pct`。
3. z 只是覆盖 RHS 线性化装置，不参与分支；z 定义域只开有槽位的星期几。

## 引用论文

- Desrochers, Desrosiers, Solomon (1992)：CG 求解 VRP 的开山之作。
- Lübbecke & Desrosiers (2005)：CG 选题综述（"为什么定价器找不到 ≠ 不存在"的严谨表述）。
- Barnhart et al. (1998)：分支定价（CG 嵌入精确框架的下一步，见 branch-and-price.md）。

## 相关文件与测试

- `algos/sp_matheuristic.py`（编排 + dedupe_pool + check_r2prime）
- `VisitModel/src/visitmodel/sp/formulation.py`（sp_solve_lp/ip + z 线性化）、`visitmodel/sp/pricing.py`
- `tests/test_mathmodel_sp_contract.py`（合同池过滤、定价合法性、零合法列反例）
- 设计：`docs/design/SP_MATHEURISTIC_DESIGN.md`
