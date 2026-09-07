# 概念：列生成（Column Generation, CG）

> 类别：横切概念——**所有"供列"类算法文档都引用本页**。实现：`VisitModel/src/visitmodel/sp/pricing.py`（`price_columns`）+ `algos/sp_matheuristic.py`（`column_generate` 编排）

## 一句话

列生成（CG，Column Generation）是"问对偶"的供列技术：解一遍受限主问题（RMP，Restricted Master Problem）的线性规划（LP，Linear Programming）松弛 → 对偶（dual，影子价格）告诉你**当前最缺什么列** → 定价子问题专找这种列 → 回灌重解 → 循环直到找不到为止。

## 直觉（新人版）

想象一个采购员（SP）只看手头目录下订单。目录越全，买得越划算。列生成的思路是：让会计（LP 对偶）先算一笔账——"如果你能搞到**这样的**路线，我愿意出这个价"（影子价格 π、μ）——然后采购员按这个"寻货单"（负约简成本）定向去找新路线，找到就加进目录重算。直到会计说"目录已经够好了"，收敛。

## 定价子问题（rc 公式）

```
rc(r@d) = km(r) − Σ_{c∈r} μ_c − π_d
```

- rc（约简成本，Reduced Cost，检验数）< 0 的列，加入池后能降低 SP 目标 → 值得加入。
- 合同模式下 μ_c 已包含合同覆盖影子价；R2′ 的 z 绑定行不进定价（合法性由列生成时的合法域保证）。

## 能力边界（最容易踩的坑）

启发式定价下，CG 收敛只意味着"**当前定价器找不到负列**"，**不是**"不存在更好的列"。因此：
- 只报告 RMP 值与池内差距 `pool_gap_pct`；`is_global_certified` 恒 False。
- 精确定价（如 ESPPRC，基本最短路问题）才能证明"无负列"——那是 bp 签发全局证书的前提，见 [branch-and-price.md](../algorithms/branch-and-price.md)。

## 编排循环（`column_generate`）

```
loop max_iter 轮:
    lp = sp_solve_lp(...)          # RMP LP + 对偶（π_d, μ_c）
    cols = price_columns(duals)    # 启发式定价：对偶引导贪心插入
    若无负 rc 列 → converged，退出
    回灌 cols（(date, 店集) 去重）
```

机制档参数：`max_iter=6, col_iter=60, top_m=40, candidates_per_date=24`（col_iter 是定价器内部迭代数，不是回灌列数）。

## 引用论文

- Desrochers, Desrosiers, Solomon (1992)：CG 求解 VRP 的开山之作。
- Lübbecke & Desrosiers (2005)：CG 选题综述（"定价器找不到 ≠ 不存在"的严谨表述）。
- Barnhart et al. (1998)：CG 嵌入精确框架（分支定价）。

## 相关文件与测试

- `algos/sp_matheuristic.py`、`VisitModel/src/visitmodel/sp/{formulation,pricing}.py`
- `tests/test_mathmodel_sp_contract.py`
- 应用实例：`docs/reference/algorithms/sp-cg.md`（算法行）、`branch-and-price.md`（节点 CG）
