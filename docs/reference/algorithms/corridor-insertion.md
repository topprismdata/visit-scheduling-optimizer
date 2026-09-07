# Corridor Dynamic Insertion：从计划执行到实时自适应的局部路线优化

> 类别：动态重优化（毫秒级在途工具）  
> 实现：`algos/agentic/corridor_insertion.py`
> (`CorridorDynamicInsertionTool`)  
> 生产定位：**当天临时插单（Execution-time Agent Tool）**

------------------------------------------------------------------------

# 0. 30 秒理解

销售拜访计划存在三个不同时间尺度：

``` mermaid
flowchart LR
    A["Monthly Planning<br/>月度计划"]
    B["Daily Routing<br/>当天路线"]
    C["Execution Adaptation<br/>执行调整"]

    A --> B --> C
```

对应：

``` text
Monthly Planning
    Contract-SP

Daily Routing
    TSP / Route Optimization

Execution Adaptation
    Corridor Dynamic Insertion
```

一句话：

> Contract-SP 决定“今天拜访谁”；TSP 决定“今天怎么走”；Corridor Dynamic
> Insertion 决定“路上临时增加一家店时怎么插入”。

------------------------------------------------------------------------

# 1. 它解决什么问题

典型场景：

    业代已经在路上
            ↓
    业务临时要求增加门店
            ↓
    不能重排整个月计划
            ↓
    不能修改已经执行路线
            ↓
    需要毫秒级响应

因此：

Corridor Dynamic Insertion 的核心约束：

> 已执行部分必须绝对冻结，只优化剩余路线。

------------------------------------------------------------------------

# 2. 为什么不能重新跑 TSP

传统 TSP：

    所有节点重新排序

    A-B-C-D-E

    可能变成：

    C-A-E-B-D

但是执行场景不允许。

因为：

    A-B-C

可能已经：

- 到店；
- 打卡；
- 完成拜访。

因此：

``` text
已执行 prefix
        |
        | 冻结
        v

剩余 suffix
        |
        | 局部优化
        v
新路线
```

这是一种：

> partial route reoptimization

而不是重新求解整条路线。

------------------------------------------------------------------------

# 3. 三步机制

## Step 1：Prefix Freezing

冻结：

``` python
active_route[:visited_prefix_len]
```

禁止修改。

保证：

    历史执行事实
    ≠
    模型重新规划结果

------------------------------------------------------------------------

## Step 2：Corridor Arc Projection

对于临时门店 x：

遍历剩余路线相邻节点：

    (u,v)

计算：

\[ = D(u,x)+D(x,v)-D(u,v) \]

选择：

\[ argmin() \]

即：

> 找到对当前路线破坏最小的插入位置。

示意：

原路线：

    A -------- B -------- C -------- D

插入 X：

    A -------- B --- X --- C -------- D

新增成本：

    B→X→C - B→C

------------------------------------------------------------------------

## Step 3：Chain Splicing & Local Polish

多店插入：

    逐店插入
            +
    边界局部优化

仅优化剩余段。

不触碰：

    visited prefix

------------------------------------------------------------------------

# 4. 输出契约

输出：

``` json
{
  "full_route": "...",
  "old_km": "...",
  "new_km": "...",
  "dur_ms": "...",
  "insertion_details": [
    {
      "store": "...",
      "insert_between": ["u","v"],
      "extra_cost": "..."
    }
  ]
}
```

因此 Agent 可以解释：

> “把门店 X 插入在 A 和 B 之间，额外增加 420 米。”

------------------------------------------------------------------------

# 5. 它在系统中的位置

``` mermaid
flowchart TB

    IR["VisitIR Contract"]

    SP["Contract-SP<br/>Monthly Decision"]

    TSP["Daily Route Optimization"]

    CDI["Corridor Dynamic Insertion<br/>Execution Tool"]

    IR --> SP
    SP --> TSP
    TSP --> CDI
```

职责边界：

| 层          | 负责         | 不负责   |
|-------------|--------------|----------|
| VisitIR     | 合同语义     | 路线顺序 |
| Contract-SP | 跨日计划     | 当天插单 |
| TSP         | 当天排序     | 合同判断 |
| Corridor    | 局部执行调整 | 重新规划 |

------------------------------------------------------------------------

# 6. 为什么叫 Corridor

这里的 corridor 不是行政区域或销售区域。

它表示：

> 当前路线已经形成一条可执行走廊，新门店只需要寻找最小破坏的进入点。

因此优化目标不是：

    寻找全局最短路线

而是：

    保持既有路线结构
    +
    最小增量代价

------------------------------------------------------------------------

# 7. 复杂度与性能

单店插入：

\[ O(n) \]

因为只需要扫描剩余路线弧段。

当前实测：

    K=1/3/5

    中位约 200μs

    最大真实样本 K=13：

    327μs

适合：

- Agent 实时循环；
- 手机端交互；
- 执行中快速决策。

------------------------------------------------------------------------

# 8. 已知边界

## 8.1 它不是合同优化器

不检查：

- 合同频次；
- phase；
- R2′；
- 跨日约束。

这些属于：

    VisitIR
    +
    Contract-SP

------------------------------------------------------------------------

## 8.2 它不是全局 TSP 求解器

多店批量：

    逐店贪心插入
    +
    suffix local polish

不保证全局最优。

它优化的是：

> 当前执行状态下的快速可用解。

------------------------------------------------------------------------

## 8.3 Prefix 正确性由调用方保证

`visited_prefix_len`

必须来自真实执行状态：

- 打卡；
- GPS；
- 业务确认。

工具本身不判断：

“哪些店已经完成”。

------------------------------------------------------------------------

# 9. 与动态 VRP 的关系

该工具属于：

    Static Plan
    +
    Dynamic Execution Adjustment

而不是重新规划整个 VRP。

对应动态车辆路径问题中的：

- real-time insertion；
- partial route reoptimization；
- dynamic request handling。

------------------------------------------------------------------------

# 10. 常见误区

## 误区 1

“插单后重新跑 SP。”

错误。

SP 属于计划层。

------------------------------------------------------------------------

## 误区 2

“插单就是重新优化当天 TSP。”

错误。

因为 prefix 已冻结。

------------------------------------------------------------------------

## 误区 3

“找到最短插入点就是全局最优。”

错误。

它保证：

> 局部增量代价最小。

不保证：

> 整体路线全局最优。

------------------------------------------------------------------------

# 11. Agent 使用模式

典型 Agent Loop：

``` mermaid
flowchart LR

A["业务请求<br/>增加门店"]
B["读取当前执行状态"]
C["Corridor Insertion"]
D["解释增量成本"]
E["确认执行"]

A --> B
B --> C
C --> D
D --> E
```

Agent 可以回答：

- 为什么插这里？
- 增加多少距离？
- 是否影响已完成拜访？
- 是否需要人工确认？

------------------------------------------------------------------------

# References

- Psaraftis (1988), Dynamic Vehicle Routing Problems
- Pillac et al. (2013), A Review of Dynamic Vehicle Routing Problems
- Cook, Held, Helsgaun (2024), Constrained local search for last-mile
  routing

------------------------------------------------------------------------

# Related Files

- `algos/agentic/corridor_insertion.py`
- `PERFORMANCE_BENCHMARK.md`
- `Contract-SP Final Gate`
- `Column Generation`
- `Branch-and-Price`
