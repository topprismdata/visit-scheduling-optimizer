# R2′-ALNS（合同同构局部搜索）

> 类别：元启发式 → 随机局部搜索（SLS，Stochastic Local Search） | 实现：`algos/r2_alns.py` | 矩阵身份：km 画像主力
> 概念前置：R2′ 契约见 [../concepts/r2-prime-contract.md](../concepts/r2-prime-contract.md)

## 它解决什么

Layer1 日历层的**主力引擎**：在"整店换星期几 + 同星期几槽位轮换"这个业务真实自由度上做随机局部搜索。它的移动集与业务合同可行域**同构**——每一步生成的候选天然合同合法，不存在被可行性检查拦下的无效搜索。

## 输入 / 输出

- 输入：`LineData`（原计划 `days_orig`、走廊）、距离矩阵 `D`；关键参数 `combo_mode="contract"`（合同槽位枚举）、`iteration_budget`（显式迭代上限，确定性）、`seed`、`final_reroute`（终局精排开关）。
- 输出：`AlgoResult(days, km, …, metadata{_columns})`——23 条日历列 `(date, route, km)` 供下游 SP 重组；`_columns` 为 raw 精度（下游 LP 界依赖）。

## 机制（五段式）

```
1. 起点：原计划店→日期集（init_days 可注入）
2. 邻域 move_candidates(c, sched, wd_g, contracts, "contract")：
   枚举目标星期几 w′（含原星期几）→ 取该 (合同,相位) 槽位集 = 候选新日期集
3. 估价：移除增益/插入代价 = 2-NN 三角恒等式（removal_gain/insertion_cost，
   纯 (成员集,D) 函数、次序无关、距离平局按店号升序 → 确定性）
4. 接受：delta < -1e-9 贪婪接受，或 5% 概率接受变差（防局部坑）；每 50 轮全量校准
5. 终局：状态门控精确重排（final_reroute=True 时逐日 CP-SAT，仅 OPTIMAL 才接受重排）
```

- **确定性红线**：搜索期零求解器调用；同 seed 逐位复现（CP-SAT 平局次序抖动曾致发散，故移出搜索期）。
- **R2′ 语义**：店可整月换星期几，改就全月一致；禁止同店跨星期几分裂。

## 复杂度与预算

- 单轮 O(邻域枚举 × 2-NN 估价)；机制档 25K/100K/360K 迭代（360K ≈ 600s 预算换算）；多 seed 并集是质量主要旋钮（1→4 seed：−10.7%→−13.0%）。
- 双向走廊硬约束内生于移动生成（放不下就不过滤丢弃，而是不生成）。

## 已知边界与陷阱

1. 局部最优无证书——界要靠 sp_cg/bp；km 主张必须过 Contract-SP 终闸与 beats_baseline。
2. `_columns` 与其 `km` 必须保持 raw 浮点（历史上 round(3) 曾污染下游 B&P 节点 LP 界，v1.0.1 修复）。
3. `iteration_budget` 显式给定；`time_budget` 只是旧 API 换算（×600），勿混用（曾致同预算对照失真）。

## 引用论文

- Groër, Golden, Wasil (2009)：Consistent VRP——R2′ 星期几一致的业务原型。
- Rothenbächer, Drexl, Irnich (2019)：PVRP 柔性日程结构的 B&P&C（R2′ 自由度的形式化出处）。
- Kirkpatrick et al. (1983)：模拟退火式接受准则。
- Rosenkrantz et al. (1977)：最近邻启发式（估计器的思想源头）。

## 相关文件与测试

- `algos/r2_alns.py`；`tests/test_algorithm_contract.py`（move_candidates 确定性/合法性、R2′ 合规、墙钟上限）
- 设计：`docs/design/MATRIX_PROTOCOL_V3_DESIGN.md` §4（身份卡）
