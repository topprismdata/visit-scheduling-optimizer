# Branch-and-Price：从列生成到全局最优证书

> 类别：精确优化框架（Exact Optimization Framework）  
> 实现：`algos/branch_and_price.py`  
> 系统定位：证明层（Certificate Layer）  
> 核心职责：回答“当前方案距离数学最优还有多少，以及是否可以证明最优”

------------------------------------------------------------------------

# 0. 30 秒理解

Branch-and-Price（B&P）解决的问题：

> 当 Set Partitioning + Column Generation 只能证明当前 column pool
> 最优时，如何进一步获得整数问题的全局最优证书。

整体关系：

``` mermaid
flowchart LR

SP["Contract-SP<br/>Master"]
CG["Column Generation<br/>扩展变量"]
BP["Branch-and-Price<br/>整数证明"]

SP --> CG
CG --> BP
```

一句话：

> CG 负责扩大搜索空间；Branch 负责处理整数性；两者结合产生全局证明。

------------------------------------------------------------------------

# 1. 它在系统中的位置

``` mermaid
flowchart TB

IR["VisitIR Contract"]

Producer["Candidate Producers"]

Pool["Column Pool"]

SP["Contract-SP"]

CG["Column Generation"]

BP["Branch-and-Price"]

Certificate["Optimality Certificate"]

IR --> Producer
Producer --> Pool
Pool --> SP
SP --> CG
CG --> BP
BP --> Certificate
```

职责：

| 模块              | 负责         |
|-------------------|--------------|
| ALNS/HGS/R2′-ALNS | 产生候选     |
| SP                | 选择候选     |
| CG                | 发现缺失变量 |
| B&P               | 证明整数最优 |

------------------------------------------------------------------------

# 2. 为什么需要 Branch-and-Price

普通 SP + CG：

可以得到：

    当前 column pool 最优

但不能自动证明：

    所有可能 column 中最优

原因：

当前 pool：

    有限变量空间

完整问题：

    巨大隐含变量空间

Branch-and-Price 通过：

    Branch-and-Bound
    +
    Column Generation

逐步建立证明。

------------------------------------------------------------------------

# 3. 核心思想

每个 branch node：

执行：

    Solve LP Relaxation

            ↓

    Column Generation

            ↓

    获得 node bound

如果：

- bound 不优于 incumbent；
- 或节点不可行；

则剪枝。

否则继续分支。

------------------------------------------------------------------------

# 4. 本项目分支规则

经典 Ryan-Foster：

    两个客户是否在同一路线

但本项目使用：

> customer-date assignment branching

即：

定义：

y_cd = Σ_{r∈R_d: c∈r} x_r

表示：

门店 c 是否安排在日期 d。

------------------------------------------------------------------------

## 分支

如果：

0 < y_cd < 1

则：

两子节点：

### Forced

    customer c 必须在 date d

### Forbidden

    customer c 禁止在 date d

------------------------------------------------------------------------

# 5. 下界语义（最重要）

节点 LP 值只有满足：

    精确定价

    +

    没有负 reduced cost column

才是：

    有效 node lower bound

否则：

它只是：

    RMP LP value

即：

当前受限 column 空间最优。

不能：

- 剪枝；
- 宣称 global gap；
- 生成最优证书。

------------------------------------------------------------------------

# 6. Pricing Oracle：B&P 的生命线

B&P 的关键不是 branch。

而是：

> 是否拥有精确定价 oracle。

三种模式：

------------------------------------------------------------------------

## 1. Heuristic Pricing

例如：

- top-m dual reward；
- 贪心插入。

用途：

快速发现好列。

不能证明：

无负列。

------------------------------------------------------------------------

## 2. Exact Pricing

需要：

完整搜索 column space。

例如：

ESPPRC：

    Elementary Shortest Path Problem
    with Resource Constraints

只有：

    exact pricing
    +
    无负 rc

才能宣布：

node LP optimal。

------------------------------------------------------------------------

## 3. Feasibility Recovery

当 branch 产生：

    forced constraint

导致池中无列。

需要补充：

可行列。

注意：

可行恢复列不等于负 reduced cost 列。

------------------------------------------------------------------------

# 7. 状态诚实性

| 状态            | 含义                 |
|-----------------|----------------------|
| PROVEN_OPTIMAL  | 完整证明链闭合       |
| BOUND_HEURISTIC | 探索完成但证书不完整 |
| TIME_LIMIT      | 预算限制             |

不能：

    树结束
    =
    最优

------------------------------------------------------------------------

# 8. 当前实现状态

当前：

    algos/branch_and_price.py

实现：

- branch framework；
- node LP；
- forced/forbidden propagation；
- heuristic pricing。

限制：

真实规模：

    exact pricing

尚未完成。

因此当前主要能力：

    BOUND_HEURISTIC

而不是完整 global proof。

------------------------------------------------------------------------

# 9. 工程不变量

## Column 去重

按：

    (date, frozenset(store))

去重。

原因：

同店集不同顺序：

会造成：

    x = 0.5 + 0.5

节点空转。

------------------------------------------------------------------------

## z 定义域

只允许：

    f_cw > 0

的星期槽。

------------------------------------------------------------------------

## incumbent

只有：

    y 全整数

才能抽取。

------------------------------------------------------------------------

## 成本精度

树内：

必须保持：

    raw floating cost

不能：

    round()

否则：

污染：

- node bound；
- pruning；
- certificate。

------------------------------------------------------------------------

# 10. 热启动边界

生产模式：

允许：

    initial_pool

    +
    external columns

例如：

R2′ 提供候选。

但是：

研究矩阵：

    bp_solo

禁止隐藏组合。

原因：

实验必须保持归因独立。

------------------------------------------------------------------------

# 11. 与其他模块关系

``` text
Candidate Generator

        ↓

Contract-SP

        ↓

Column Generation

        ↓

Branch-and-Price

        ↓

Optimality Certificate
```

完整链路：

    发现方案

    ↓

    组合方案

    ↓

    扩展变量

    ↓

    证明方案

------------------------------------------------------------------------

# References

- Barnhart et al. (1998), Branch-and-Price
- Ryan & Foster (1981), Pairwise Branching
- Lübbecke & Desrosiers (2005), Column Generation Review
- Feillet et al. (2004), ESPPRC
- Rothenbächer, Drexl, Irnich (2019), PVRP Branch-and-Price-and-Cut

------------------------------------------------------------------------

# Related Files

- `algos/branch_and_price.py`
- `tests/test_branch_and_price.py`
- `Column Generation`
- `Contract-SP Final Gate`
