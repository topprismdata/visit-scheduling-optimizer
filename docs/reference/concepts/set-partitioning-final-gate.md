# Set Partitioning：从候选路线到最终拜访计划

> Contract-SP Final Gate 的概念、由来、数学模型与系统角色

## 0. 核心认知

本项目中：

- R2′-ALNS、ALNS、HGS-PVRP、CG Pricing 等算法负责产生候选拜访路线；
- Set Partitioning 负责从候选路线中选择最终组合；
- Validator 负责独立验证业务契约。

核心原则：

> 候选生成与最终组合决策分离。

``` mermaid
flowchart LR
    A["Route Producers"]
    P["Column Pool"]
    S["Contract-SP Final Gate"]
    O["Final Calendar"]

    A --> P
    P --> S
    S --> O
```

------------------------------------------------------------------------

# 1. 为什么需要 Set Partitioning

销售拜访计划不是寻找一条最短路线，而是在大量候选方案中选择一个整体可行组合。

需要同时满足：

- 工作日安排；
- 门店合同频次；
- 双周 phase；
- R2′ 星期几一致；
- 工作量约束。

因此：

## 候选如何产生？

由各种搜索算法完成。

## 候选如何组合？

由 Set Partitioning 完成。

------------------------------------------------------------------------

# 2. 什么是 Column

Column 是一个完整候选日计划：

    (date, route, cost)

例如：

    日期：
    2026-09-08

    路线：
    A → F → C → H

    成本：
    13.7 km

Column 有两个身份：

## 集合身份

决定：

- 覆盖哪些门店；
- 属于哪个日期；
- 在数学矩阵中的系数。

## 路线身份

决定：

- 访问顺序；
- 距离成本。

因此：

> SP 不生成路线，只选择路线。

------------------------------------------------------------------------

# 3. Set Covering / Packing / Partitioning

## Set Covering

至少覆盖一次：

    Ax >= 1

## Set Packing

最多覆盖一次：

    Ax <= 1

## Set Partitioning

恰好覆盖：

    Ax = 1

车辆路径、排班等问题大量使用 route-based set partitioning。

------------------------------------------------------------------------

# 4. 从标准 SP 到 Contract-SP

标准 SP：

    对象
     ↓
    集合选择
     ↓
    恰好覆盖

本项目扩展：

    Standard SP
          ↓
    Date SP
          ↓
    Periodic SP
          ↓
    Contract-SP
          ↓
    R2′ Contract-SP

Contract-SP 是本项目命名。

从运筹优化角度：

> route-based set partitioning master with business side constraints。

------------------------------------------------------------------------

# 5. Contract-SP 数学模型

目标：

min Σ_r c_r x_r

其中：

- x_r：是否选择路线 column；
- c_r：路线成本。

## 每个工作日选择一条路线

Σ_{r∈R_d} x_r = 1

## 合同覆盖

Σ_{r∋c} x_r = Σ_w f_cw z_cw

## R2′ 星期选择

Σ_w z_cw = 1

变量：

x_r ∈ {0,1}

z_cw ∈ [0,1]

------------------------------------------------------------------------

# 6. 为什么叫 Final Gate

Contract-SP 是最终组合闸门。

``` mermaid
flowchart TB
    P["Candidate Columns"]
    A["Column Admission"]
    M["Contract-SP"]
    V["Independent Validation"]
    O["Final Plan"]

    P --> A
    A --> M
    M --> V
    V --> O
```

注意：

这些约束属于同一个优化模型，不是流水线逐个执行。

------------------------------------------------------------------------

# 7. Optimizer 与 Validator 分离

Solver 返回：

    FEASIBLE
    OPTIMAL

不代表业务已经验证。

最终必须重新执行：

- check_freq；
- check_capacity；
- check_contract。

原则：

> Optimizer 负责求解，Validator 负责证明业务契约。

------------------------------------------------------------------------

# 8. LP、IP、RMP 与 Column Generation

## IP

用于获得最终执行计划。

## LP Relaxation

用于：

- dual price；
- pricing；
- bound analysis。

## RMP

Restricted Master Problem：

当前 column pool 对应的受限主问题。

## Column Generation

流程：

    Solve RMP
        ↓
    Read Dual
        ↓
    Pricing
        ↓
    New Columns
        ↓
    RMP

------------------------------------------------------------------------

# 9. 最优性证书层级

必须区分：

    RMP LP Optimal
        ↓
    当前 pool LP 最优

    Pool IP Optimal
        ↓
    当前 pool 整数最优

    Exact Pricing 完成
        ↓
    完整 master LP 最优

    Branch-and-Price 完成
        ↓
    Global PROVEN_OPTIMAL

因此：

    pool optimum ≠ global optimum

------------------------------------------------------------------------

# 10. Engineering Invariants

## z domain

只允许真实合同槽位。

## 零合法列

义务店没有合法 column：

    INFEASIBLE

不能静默跳过。

## 成本口径

必须区分：

- semantic cost；
- raw km；
- solver integer cost。

禁止混合计算 gap。

------------------------------------------------------------------------

# Appendix A：当前 formulation 技术债

当前：

x_r ≤ z_{c, wd(r)}

属于 column-dependent rows。

这不是普通 fixed-row Column Generation。

理论上存在两条路线：

1.  Fixed-row reformulation；
2.  Column-and-row generation。

项目 vNext 选择：

y_cd = Σ_{r∈R_d: c∈r} x_r

将合同和 R2′ 语义放入固定 row space。

------------------------------------------------------------------------

# Appendix B：系统位置

    Route Producers
           |
           v
    Column Pool
           |
           v
    Contract-SP
           |
           v
    Monthly Calendar
           |
           v
    Independent Validation

------------------------------------------------------------------------

# References

- Dantzig & Wolfe (1960), Decomposition Principle for Linear Programs
- Balinski & Quandt (1964), On an Integer Program for a Delivery Problem
- Ribeiro & Soumis (1994), Set Partitioning with Side Constraints
- Barnhart et al. (1998), Branch-and-Price
- Lübbecke & Desrosiers (2005), Selected Topics in Column Generation
- Pessoa et al. (2020), Generic Exact Solver for VRP
- Muter, Birbil & Bülbül (2013), Simultaneous Column-and-Row Generation
