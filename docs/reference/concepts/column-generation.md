# Column Generation：从候选扩展到可证明的路线搜索

> CG（Column Generation）的概念、直觉、数学机制与在 VisitModel
> 中的角色  
> 类别：横切概念——所有“供列”类算法文档的共同入口  
> 实现： - `VisitModel/src/visitmodel/sp/pricing.py` (`price_columns`) -
> `algos/sp_matheuristic.py` (`column_generate`)

------------------------------------------------------------------------

# 0. 30 秒理解

Column Generation（CG，列生成）解决的问题是：

> 当候选方案数量巨大，无法一次性全部放入优化模型时，如何只生成真正有价值的候选？

在本项目中：

- Contract-SP 是 Master Problem；
- route column 是变量；
- CG 负责发现新的、有可能改善目标的 route column。

核心循环：

``` mermaid
flowchart LR
    RMP["Restricted Master Problem<br/>当前 Column Pool"]
    LP["LP Solve<br/>得到 Dual"]
    PRICE["Pricing<br/>寻找有价值新路线"]
    NEW["New Columns"]

    RMP --> LP
    LP --> PRICE
    PRICE --> NEW
    NEW --> RMP
```

一句话：

> CG 不是直接优化路线，而是不断询问：“当前方案还缺哪一种路线？”

------------------------------------------------------------------------

# 1. 为什么需要 Column Generation

如果所有可能路线都提前枚举：

    门店数量增加
            ↓
    可能路线数量爆炸
            ↓
    Master Problem 无法直接建立

例如：

10 家店：

可能路线有限。

1000 家店：

理论 route 数量巨大。

因此不能：

    生成全部 route
            ↓
    一次性求 SP

而是：

    先放少量 route
            ↓
    看看缺什么
            ↓
    针对性生成新 route

这就是 Column Generation。

------------------------------------------------------------------------

# 2. CG 在整个系统中的位置

``` mermaid
flowchart TB

    Producers["Route Producers<br/>ALNS / HGS / Rules"]

    Pool["Column Pool"]

    SP["Contract-SP<br/>Master Problem"]

    CG["Column Generation"]

    Producers --> Pool
    CG --> Pool

    Pool --> SP

    SP -->|"LP Dual"| CG
```

关系：

- SP 决定哪些 route 最终被选择；
- CG 决定还有哪些 route 值得加入候选池。

因此：

> SP 是选择器；CG 是候选发现器。

------------------------------------------------------------------------

# 3. RMP：受限主问题

完整 SP：

    所有可能 route columns
            ↓
    Master Problem

现实：

    当前已发现 route columns
            ↓
    Restricted Master Problem

RMP 只看到当前 column pool。

例如：

    理论 route:

    1,000,000 条


    当前 pool:

    1,500 条

RMP 优化的是：

> 当前知道的路线集合。

------------------------------------------------------------------------

# 4. Dual（影子价格）为什么重要

LP 求解 RMP 后，会产生 dual values。

它们代表：

> 当前约束对目标函数的价值。

直觉：

如果某家店很难满足：

    store A dual = 高

意味着：

> “如果出现一个包含 A 的好路线，它很有价值。”

如果某天资源紧张：

    date D dual = 高

意味着：

> “覆盖这一天的新路线更有价值。”

所以 dual 是 pricing 的搜索方向。

------------------------------------------------------------------------

# 5. Pricing：寻找新 Column

标准 reduced cost：

\[ rc(r)=c_r-y^Ta_r \]

在本项目简化形式：

\[ rc(r@d)=km(r)-\_{cr}\_c-\_d \]

其中：

| 符号  | 含义              |
|-------|-------------------|
| km(r) | 路线成本          |
| μ_c   | 门店覆盖约束 dual |
| π_d   | 日期约束 dual     |

解释：

    路线成本
            -
    它解决的约束价值
            =
    真实边际价值

------------------------------------------------------------------------

# 6. 为什么负 Reduced Cost 值得加入

如果：

\[ rc \< 0 \]

意味着：

加入这个 column 后：

    Master objective 可以下降

因此：

    生成
     ↓
    加入 pool
     ↓
    重新优化

直到：

    没有新的负 reduced cost column

------------------------------------------------------------------------

# 7. CG 循环

标准流程：

``` mermaid
flowchart TD

A["Solve RMP LP"]

B["Extract Dual Prices"]

C["Pricing Problem"]

D{"找到负 rc column?"}

E["Add Columns"]

F["Stop"]

A --> B
B --> C
C --> D

D -->|Yes| E
E --> A

D -->|No| F
```

------------------------------------------------------------------------

# 8. VisitModel 当前实现

当前编排：

``` python
for iteration:

    lp = sp_solve_lp()

    cols = price_columns(duals)

    if no_negative_rc:
        stop

    add_columns(cols)
```

当前参数：

    max_iter=6

    col_iter=60

    top_m=40

    candidates_per_date=24

注意：

`col_iter`

表示 pricing 内部搜索次数。

不是每轮回灌数量。

------------------------------------------------------------------------

# 9. 启发式 CG 与精确 CG 的区别

这是最容易误解的地方。

## 精确 CG

Pricing 子问题：

    exact solve

如果证明：

    不存在负 reduced cost column

则：

    当前 RMP = 完整 Master LP optimum

------------------------------------------------------------------------

## 启发式 CG

Pricing：

    heuristic search

如果没有找到：

    负 rc column

只能说明：

> 当前搜索没有找到。

不能说明：

> 不存在。

因此：

    heuristic CG convergence
    ≠
    global proof

------------------------------------------------------------------------

# 10. 当前项目证据口径

启发式供列时：

允许报告：

    RMP value

    pool_gap_pct

不允许报告：

    global optimality gap

并保持：

    is_global_certified = False

------------------------------------------------------------------------

# 11. 与 Branch-and-Price 的关系

Branch-and-Price：

    Branch-and-Bound
            +
    Column Generation

在每个节点：

    solve node LP
            ↓
    pricing
            ↓
    prove no negative column

只有完成完整 pricing：

才能产生节点 LP bound。

因此：

> CG 是 B&P 获得精确证书的核心组件。

------------------------------------------------------------------------

# 12. 当前 formulation 注意事项

当前 Contract-SP formulation 存在：

x_r ≤ z_{c, wd(r)}（见 FORMULATION_VNEXT_DESIGN_v0.3.md 的重构方案）

这样的 column-dependent rows。

因此：

当前系统不能简单按照经典 fixed-row CG 解释。

理论上有两种路线：

## Route A：Fixed-row Reformulation

引入：

y_cd = Σ_{r∈R_d: c∈r} x_r

将合同语义放入固定 row space。

## Route B：Column-and-Row Generation

同时生成：

- columns
- rows

两者理论均可。

当前 VisitModel vNext 选择：

> Route A，因为它更容易保持 dual 语义、审计能力和 B&P 证书链。

------------------------------------------------------------------------

# 13. 常见误区

## 误区 1

“CG 找不到新列，所以已经最优。”

错误。

只有 exact pricing 才成立。

------------------------------------------------------------------------

## 误区 2

“RMP 最优，所以整个问题最优。”

错误。

RMP 只代表当前 pool。

------------------------------------------------------------------------

## 误区 3

“CG 生成路线。”

不准确。

CG 生成的是：

> 对 Master 有价值的变量。

在本项目里这些变量表现为 route columns。

------------------------------------------------------------------------

# 14. References

- Dantzig & Wolfe (1960), Decomposition Principle for Linear Programs
- Desrochers, Desrosiers & Solomon (1992), A New Optimization Algorithm
  for the Vehicle Routing Problem with Time Windows
- Barnhart et al. (1998), Branch-and-Price: Column Generation for
  Solving Huge Integer Programs
- Lübbecke & Desrosiers (2005), Selected Topics in Column Generation
- Muter, Birbil & Bülbül (2013), Simultaneous Column-and-Row Generation
  for Large-Scale Linear Programs with Column-Dependent-Rows

------------------------------------------------------------------------

# 15. Related Files

- `algos/sp_matheuristic.py`
- `VisitModel/src/visitmodel/sp/formulation.py`
- `VisitModel/src/visitmodel/sp/pricing.py`
- `tests/test_mathmodel_sp_contract.py`
- `docs/reference/algorithms/sp-cg.md`
- `docs/reference/algorithms/branch-and-price.md`
