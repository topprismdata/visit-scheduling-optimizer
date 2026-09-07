# TSP-CP-SAT：开链精确旅行商质量锚

> 类别：精确顺序优化（Exact Route Ordering）  
> 实现： - `VisitModel/src/visitmodel/tsp/open_chain.py` -
> `ExactTSPEngine` - `_exact_open_tsp_status`
>
> 系统定位：**日内路线质量锚（Quality Anchor）**

------------------------------------------------------------------------

# 0. 30 秒理解

在整个拜访计划系统中，不同层解决不同问题：

``` mermaid
flowchart LR

A["Contract-SP<br/>决定今天拜访谁"]
B["TSP-CP-SAT<br/>决定今天怎么走"]
C["Corridor Insertion<br/>执行中动态调整"]

A --> B --> C
```

TSP-CP-SAT 不负责：

- 合同频次；
- 跨日安排；
- R2′ 星期约束。

它只回答：

> 给定当天门店集合，访问顺序的数学最优是什么？

因此它是：

> **顺序层的质量锚。**

------------------------------------------------------------------------

# 1. 它解决什么问题

输入：

    当天门店集合
    +
    距离矩阵

输出：

    最短开放路径
    +
    求解状态

开放路径：

    Depot 不要求返回

    A → C → B → D

而不是：

    A → C → B → D → A

应用：

- 基线方案质量评估；
- km 优化效果衡量；
- 算法排序质量验证。

------------------------------------------------------------------------

# 2. 为什么需要精确 TSP

整个优化体系存在多个层：

    计划层：

    Contract-SP

    决定：
    访问哪些店


    顺序层：

    TSP

    决定：
    访问顺序

如果没有精确 TSP：

无法回答：

> 一个算法生成的门店集合，到底是真的更好，还是只是排序更差？

因此：

TSP-CP-SAT 提供：

    给定门店集合

    理论最佳 km

作为比较基准。

------------------------------------------------------------------------

# 3. 开链 TSP 建模

标准 TSP：

    起点
     ↓
    所有节点
     ↓
    回起点

是 Hamiltonian Cycle。

但销售拜访通常：

    当天出发
     ↓
    访问门店
     ↓
    结束

无需回场站。

因此需要：

> Open TSP / Hamiltonian Path

------------------------------------------------------------------------

# 4. CP-SAT 建模方式

当前实现：

使用 OR-Tools CP-SAT：

    AddCircuit

构造 Hamiltonian 圈。

开放路径转换：

``` text
原问题：

A → B → C → D


加入 dummy depot：

A → B → C → D → Dummy
```

其中：

    Dummy 边权 = 0

因此：

    Cycle
    =
    Open Chain
    +
    Zero Cost Dummy Node

------------------------------------------------------------------------

# 5. 求解状态是结果的一部分

输出必须包含：

    status

例如：

    OPTIMAL

    FEASIBLE

    UNKNOWN

含义：

## OPTIMAL

可以声明：

> 当前距离矩阵下，该日路线已证明最优。

------------------------------------------------------------------------

## FEASIBLE

只能声明：

> 在时间限制内找到可行解。

不能声明：

> 已达到最优。

------------------------------------------------------------------------

# 6. 为什么它是质量锚

系统中：

    算法生成门店集合

            ↓

    TSP 精确排序

            ↓

    得到理论最低 km

因此：

TSP 提供：

    Best Possible Ordering

其他算法只能比较：

    距离精度
    +
    搜索质量

------------------------------------------------------------------------

# 7. 当前实现

实现：

``` text
VisitModel/src/visitmodel/tsp/open_chain.py
```

核心：

    _exact_open_tsp_status

    ExactTSPEngine

求解：

    OR-Tools CP-SAT
    +
    AddCircuit

------------------------------------------------------------------------

# 8. 性能与预算

当前测试口径：

    cp_timeout = 30s / 日

结果：

    n <= 35

    全部 OPTIMAL

    22ms ~ 1.06s

n \> 35：

尚未形成最优性结论。

原则：

    非 OPTIMAL

    ↓

    只能 FEASIBLE 报告

禁止：

    限时未证明

    等价于

    已最优

------------------------------------------------------------------------

# 9. 并行与确定性

当前：

    8 workers

优势：

- 提升搜索速度。

影响：

即使：

    cost 相同

不同运行：

    route sequence

可能不同。

因此：

## 搜索阶段

可以使用并行。

## 确定性红线测试

使用：

    1 worker
    +
    确定性时限

------------------------------------------------------------------------

# 10. 与其他排序方法比较

系统曾比较：

    CP-SAT
    vs
    LKH
    vs
    NN+2opt

结论：

LKH 并不一定优于 CP-SAT。

例如：

某线路：

    LKH:
    17.4 km

    CP-SAT:
    14.03 km

因此当前精确排序锚选择：

    CP-SAT

有实验依据。

------------------------------------------------------------------------

# 11. 已知边界

## 11.1 TSP 不能解决计划问题

TSP 不知道：

- 合同；
- phase；
- 星期模式。

它只优化：

    固定门店集合

------------------------------------------------------------------------

## 11.2 km 比较必须带排序因子

同一个日历：

不同排序器：

可能产生：

    +11% ~ +16%

因此报告必须注明：

    TSP factor

------------------------------------------------------------------------

## 11.3 成本口径必须隔离

必须区分：

    sp_km_pool

    sp_km_recomputed

以及：

    TSP solver integer cost

禁止跨口径计算 gap。

------------------------------------------------------------------------

# 12. 在 Agentic Scheduling 中的位置

完整链：

``` mermaid
flowchart TB

IR["VisitIR Contract"]

SP["Contract-SP"]

TSP["Exact TSP CP-SAT"]

EXEC["Execution Tools"]

IR --> SP
SP --> TSP
TSP --> EXEC
```

职责：

    Contract-SP

    世界约束


    TSP-CP-SAT

    数学排序天花板


    Execution Tool

    现实变化适应

------------------------------------------------------------------------

# References

- Google OR-Tools CP-SAT Documentation
- Applegate et al., The Traveling Salesman Problem
- Helsgaun, An Effective Implementation of the Lin-Kernighan Heuristic

------------------------------------------------------------------------

# Related Files

- `VisitModel/src/visitmodel/tsp/open_chain.py`
- `algos/tsp_engine.py`
- `algos/tsp_engine.py` shim
- `algos/r2_alns.py`
- `route_with_tsp`
