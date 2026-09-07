# 走廊投影动态插单工具（Corridor Dynamic Insertion）

> 类别：动态重优化（毫秒级在途工具） | 实现：`algos/agentic/corridor_insertion.py`（`CorridorDynamicInsertionTool`） | 生产定位：**当天临时插单**（Agent 专用工具）

## 它解决什么

业代已经在路上，临时要加几家店：**不允许重排整个月**，也不允许动已走过的部分。要求毫秒级响应、绝对尊重已执行前缀。

## 机制（三步）

```
1. 前缀冻结（Prefix Freezing）：active_route[:visited_prefix_len] 严禁触碰
2. 走廊弧段投影（Corridor Arc Projection）：
   对每个临时店，枚举剩余路线上所有相邻对 (u,v)，
   绕行代价 = D[u][x] + D[x][v] − D[u][v]，取最小弧段插入
3. 顺路微链拼接 + 接缝抛光（Chain Splicing & Local Polish）：
   多店批量插入后，仅对剩余段做 two_opt（≤15 轮），前缀仍冻结
```

- 输出：`{full_route, old_km, new_km, dur_ms, insertion_details(每店插入弧段与代价)}`——Agent 可直接向业务解释"把店 X 插在了谁和谁之间、多绕了多少米"。
- 剩余为空时：临时店链内部 two_opt 后直接拼尾。

## 复杂度与预算

- 单店插入 O(剩余段长)；实测 75–330 μs（K=1/3/5 中位 200μs；真实 7/1 全月最大样本 K=13：327μs）——**微秒级**，可进 Agent 实时循环。

## 已知边界与陷阱

1. **纯顺序层工具**：不检查合同、频次、走廊——插谁不插谁是上游决策；本工具只回答"插进去最顺路的位置"。
2. 投影贪心不保证全局最优：多店批量是逐店顺序插入 + 接缝抛光，非重解 TSP。
3. `visited_prefix_len` 由调用方负责保证正确（打卡口径）。

## 引用论文

- Cook, Held, Helsgaun (2024). *Constrained local search for last-mile routing*. Transportation Science 58(1)（Amazon last-mile：道路走廊一序思想）。
- Pillac, Gendreau, Guéret, Medaglia (2013). *A review of dynamic vehicle routing problems*. EJOR 225(1)（动态 VRP 术语与分类）。

## 相关文件

- `algos/agentic/corridor_insertion.py`；性能口径：PERFORMANCE_BENCHMARK.md §C 场景
