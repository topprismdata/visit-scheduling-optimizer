# sp_cg（对偶驱动列生成，算法行）

> 类别：线性规划（LP，Linear Programming）列生成框架 | 实现：`algos/sp_matheuristic.py`（编排）+ `VisitModel/src/visitmodel/sp/{formulation,pricing}.py` | 矩阵身份：km + 下界

## 它解决什么

**列生成（CG，Column Generation）技术**的完整算法行实现——对偶 π/μ 引导定价供列，循环直到找不到负约简成本（rc，Reduced Cost）列。CG 技术本身（原理、rc 公式、能力边界）见概念文档 [../concepts/column-generation.md](../concepts/column-generation.md)——本页只写算法行特有内容。

## 输入 / 输出

- 输入：起始池（原计划重排）、`r2_prime=True`、`contract`、走廊。
- 输出：`(rmp_lp, generated_columns, cg_iters, converged)`；编排层再交 Contract-SP 终闸。

## 机制（算法行参数档）

```
column_generate（algos/sp_matheuristic.py）:
  loop max_iter 轮（机制档 = 6）:
    lp = sp_solve_lp(...)          # RMP LP + 对偶（π_d, μ_c）
    cols = price_columns(duals)    # 启发式定价（每日期候选 24、对偶截断 top_m=40、内部迭代 col_iter=60）
    若无负 rc 列 → converged，退出
    回灌 cols（(date,店集) 去重）
```

- 复杂度：每轮 = 一次 LP（GLOP，池线性）+ 一次定价（O(日期数 × top_m × 插入)）。
- 确定性：GLOP 对偶数值稳定；定价贪心平局按店号——同输入同输出。

## 已知边界与陷阱

1. **受限池不可行（INFEASIBLE）≠ 业务不可行**：池过滤可能饿死店（有测试钉住：剥除店全部列后必须返回不可行而非缺店解）。
2. 下界是 RMP 值（已探索列空间），不是全局下界——报告只许写 `pool_gap_pct`。
3. z 只是覆盖 RHS 线性化装置，不参与分支；z 定义域只开有槽位的星期几。

## 引用论文

见 [../concepts/column-generation.md](../concepts/column-generation.md)（Desrochers 1992 / Lübbecke 2005 / Barnhart 1998）。

## 相关文件与测试

- `algos/sp_matheuristic.py`（编排 + dedupe_pool + check_r2prime）
- `VisitModel/src/visitmodel/sp/formulation.py`（sp_solve_lp/ip + z 线性化）、`visitmodel/sp/pricing.py`
- `tests/test_mathmodel_sp_contract.py`（合同池过滤、定价合法性、零合法列反例）
- 设计：`docs/design/SP_MATHEURISTIC_DESIGN.md`
