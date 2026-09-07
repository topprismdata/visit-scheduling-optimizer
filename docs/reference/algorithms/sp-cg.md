# sp-cg：对偶驱动列生成算法实现行

> 类别：算法实现文档（Algorithm Layer）  
> 上游概念：Column Generation / Contract-SP  
> 实现： - `algos/sp_matheuristic.py` -
> `VisitModel/src/visitmodel/sp/formulation.py` -
> `VisitModel/src/visitmodel/sp/pricing.py`

------------------------------------------------------------------------

# 0. 30 秒理解

`sp-cg` 不是解释 Column Generation 是什么。

它回答的是：

> 在 VisitModel 当前实现中，CG
> 算法如何运行、调用哪些组件、输出什么、有哪些工程边界？

概念层：

    Column Generation
            |
            v
    为什么需要 CG
    什么是 reduced cost
    什么是 pricing

算法层：

    sp-cg

    RMP LP
      |
      v
    读取 dual
      |
      v
    pricing
      |
      v
    生成新 columns
      |
      v
    回灌 pool

------------------------------------------------------------------------

# 1. 它在系统中的位置

``` mermaid
flowchart TB

    Contract["VisitIR Contract"]

    Producer["Route Producers"]

    Pool["Column Pool"]

    CG["sp-cg<br/>Column Generation"]

    SP["Contract-SP Final Gate"]

    Validator["Independent Validation"]

    Contract --> Producer
    Producer --> Pool

    CG --> Pool
    Pool --> CG

    Pool --> SP

    SP --> Validator
```

职责：

- Producer：产生候选；
- sp-cg：发现更有价值候选；
- Contract-SP：选择最终组合；
- Validator：验证业务契约。

------------------------------------------------------------------------

# 2. 输入 / 输出

## 输入

包括：

- 初始 column pool；
- `r2_prime=True`；
- contract；
- corridor。

这些输入定义：

- 合法 column 空间；
- pricing 搜索边界；
- Contract-SP 约束。

------------------------------------------------------------------------

## 输出

返回：

``` text
(
 rmp_lp,
 generated_columns,
 cg_iters,
 converged
)
```

然后由编排层交给：

    Contract-SP Final Gate

------------------------------------------------------------------------

# 3. 主循环

当前实现：

``` python
for iteration:

    lp = sp_solve_lp(...)

    cols = price_columns(duals)

    if no_negative_rc:
        converged = True
        break

    add_columns(cols)
```

对应：

``` mermaid
flowchart LR

    RMP["Solve RMP LP"]

    Dual["Extract dual π/μ"]

    Pricing["price_columns"]

    Check{"negative rc?"}

    Add["Add columns"]

    Stop["converged"]

    RMP --> Dual
    Dual --> Pricing
    Pricing --> Check

    Check -->|yes| Add
    Add --> RMP

    Check -->|no| Stop
```

------------------------------------------------------------------------

# 4. RMP 求解

每轮首先解决：

    Restricted Master Problem

即：

> 当前 column pool 对应的 LP。

输出：

- LP objective；
- dual values。

当前 dual：

    π_d
    日期约束价格

    μ_c
    门店覆盖约束价格

------------------------------------------------------------------------

# 5. Pricing 定价

Pricing 的目标：

寻找：

> 加入 Master 后可以改善目标函数的 column。

标准：

\[ rc(r)=c_r-y^Ta_r \]

当前项目使用：

- route cost；
- store dual；
- date dual。

如果：

\[ rc \< 0 \]

表示：

    当前 pool 仍有改进空间

生成该 column。

------------------------------------------------------------------------

# 6. 当前参数档

当前实现：

    max_iter = 6

    pricing:

    candidates_per_date = 24

    top_m = 40

    col_iter = 60

含义：

- max_iter：CG 外层循环次数；
- candidates_per_date：每日候选搜索规模；
- top_m：dual 关注门店截断；
- col_iter：pricing 内部搜索次数。

------------------------------------------------------------------------

# 7. 定价流程

当前 pricing 是启发式：

``` text
读取 dual
    |
    v
选择高价值门店
    |
    v
构造候选 route
    |
    v
计算 reduced cost
    |
    v
返回负 rc columns
```

它不是：

    exact pricing solver

因此：

找到新列：

证明存在改进。

找不到新列：

只表示当前搜索没有发现。

------------------------------------------------------------------------

# 8. 收敛语义

必须区分：

## Exact CG

    pricing exact

    没有负 rc column

    ↓

    LP optimum proven

------------------------------------------------------------------------

## 当前 heuristic CG

    pricing heuristic

    没有找到负 rc

    ↓

    当前搜索停止

不能写：

    global optimal

正确：

    RMP / pool-level result

------------------------------------------------------------------------

# 9. 工程边界

## 9.1 受限池不可行

情况：

    某义务店
        |
        v
    所有合法 column 被过滤

结果：

必须：

    INFEASIBLE

不能产生：

    缺店但可执行

------------------------------------------------------------------------

## 9.2 下界语义

当前：

    RMP value

只代表：

> 已探索 column space。

不是：

> 完整 route space global lower bound。

因此报告：

允许：

    pool_gap_pct

禁止：

    global_gap

------------------------------------------------------------------------

## 9.3 z 变量

当前：

z 是覆盖 RHS 的线性化工具。

它：

- 表达 weekday contract；
- 不参与 branch；
- 只允许真实合同槽位。

------------------------------------------------------------------------

# 10. 与 Contract-SP 的关系

二者关系：

``` text
Column Generation

负责：
发现变量


Contract-SP

负责：
选择变量
```

因此：

    CG ≠ SP solver

    CG + SP = 完整 route-based optimization framework

------------------------------------------------------------------------

# 11. 与 Branch-and-Price 的关系

当前：

    sp-cg

解决：

    LP column generation

未来：

    Branch-and-Price

需要：

- branch；
- node LP；
- exact pricing；
- bound proof。

所以：

heuristic CG 是基础组件，不等于完整 B&P。

------------------------------------------------------------------------

# 12. 代码映射

| 职责      | 位置                                          |
|-----------|-----------------------------------------------|
| CG 编排   | `algos/sp_matheuristic.py`                    |
| LP master | `VisitModel/src/visitmodel/sp/formulation.py` |
| pricing   | `VisitModel/src/visitmodel/sp/pricing.py`     |
| 测试      | `tests/test_mathmodel_sp_contract.py`         |

------------------------------------------------------------------------

# 13. References

- Desrochers et al. (1992)
- Barnhart et al. (1998)
- Lübbecke & Desrosiers (2005)

------------------------------------------------------------------------

# Related Concepts

- Set Partitioning
- Contract-SP Final Gate
- Column Generation
- Branch-and-Price
