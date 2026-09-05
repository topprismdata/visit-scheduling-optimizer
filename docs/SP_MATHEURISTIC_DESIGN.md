# SP/SC Matheuristic 设计文档（论文驱动 · 2026-09-05）

状态：**已实现并实验**（对照实验结果见 `docs/ALGORITHM_GUIDE.md` 附录 A/B）

## 论文 → 本问题映射

**输入论文**
1. Villegas, Arenas-Vasco, Alcázar (2025). *A meta-analysis of set partitioning/set covering based matheuristics for VRP*. OR Perspectives 15, 100357.（下称 [META]）
2. Paradiso, Roberti, Laganá, Dullaert (2020). *An Exact Solution Framework for Multitrip VRPTW*. Operations Research 68(1).（下称 [ESF]）

## 数学模型（[META] 式(1)-(3) + 本问题业务约束）

主问题（集合划分，等式覆盖）：

```
min   Σ_r  c_r · x_r                       c_r = 路线 r 的骑行里程
s.t.  Σ_{r ∈ R_d} x_r = 1     ∀ 工作日 d    （每日恰选一条路线）
      Σ_{r ∋ c}   x_r = k_c   ∀ 门店 c      （每店出现次数精确覆盖，[META] 约束(2)的等式形态）
      x_r ∈ {0,1}
```

- R_d：日期 d 的候选路线池（列）。列=完整日路线，路线内约束（开放链 TSP）由生成器保证，
  主问题不含路径结构 → [META] §4.1 指出的 SP 组件"属性透明性"。
- 与经典 SP 的差异：多了"每日恰一条"基数约束（我们的业务=每日一条开放链）。

## 池生成（[META] Algorithm 1/2 + [ESF] 结构枚举精神的启发式版）

- 多样性来源：v3 多种子 × hgs 多种子 × greedy × nn2opt × cpsat_route（日级精确序）。
- α 门槛（[META] Alg.1 第 6 行）：仅 f(s) ≤ (1+α)·f* 的解的路线入池，α=0.15。
- 去重：同 (date, 精确序列) 只留一条；同 (date, 店集合) 保留 km 更小的前 K 条。

## 迭代精化（[META] Algorithm 2 + [ESF] Step 7 启发式版）

```
while 迭代预算:
    s* ← SP(IP) over Ω̄
    s* ← 改进算法(s*)            # 冷 SA 打磨 + 2-opt
    Ω̄  ← Ω̄ ∪ ω(s*)             # 新路线回灌
```

对偶引导（[ESF] 式(8) 约简成本的启发式近似）：解 SP 的 LP 松弛得对偶 u_c，
生成新列时对高对偶店加权——本版以"SP 解作 v3 冷爆发暖启动"替代显式定价
（全尺寸 ESPPRC 定价在 163 店规模不可行，[ESF] 精确上限 ~50 客户）。

## 结构保证（[META] §4.3 funnel 讨论原文）

任一历史完整解的路线集合都是 SP 的可行点 ⇒ **SP 结果永不劣于池内最佳单解**。

## 预期效应（[META] Table 3 量化）

| 基线类型 | SP 平均提升 |
|---|---|
| 局部搜索类（=v3 所在类） | +0.37% |
| 后优化式用法 | +0.62% |
| SP（等式）vs SC | +1.08% vs +0.23% |

v3 三种子基线 264.6（最优 263.3）→ 预期 SP ≈ 262~263.3，且**保证 ≤ 263.3**。
