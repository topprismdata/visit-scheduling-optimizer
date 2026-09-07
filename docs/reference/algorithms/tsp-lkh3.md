# LKH-3：大规模开放路径启发式排序引擎

> 类别：启发式路线优化（Large-scale Lin-Kernighan Heuristic）  
> 实现：`algos/lkh_engine.py`（外部二进制封装）  
> 系统定位：**TSP 规模扩展备用档（Scale-up Heuristic Backup）**

------------------------------------------------------------------------

# 0. 30 秒理解

LKH-3 解决的问题：

> 当精确
> TSP（CP-SAT）在大规模节点下无法及时证明最优时，提供高质量、快速的路线近似解。

它不是：

- 精确求解器；
- 最优性证明工具。

它提供：

    大规模路线质量

    vs

    求解时间

    之间的折中

------------------------------------------------------------------------

# 1. 它在系统中的位置

``` mermaid
flowchart LR

A["Daily Store Set"]

B["TSP Solver Layer"]

CPSAT["CP-SAT Exact<br/>Quality Anchor"]

LKH["LKH-3<br/>Large Scale Heuristic"]

NN["NN + 2opt<br/>Fallback"]

A --> B
B --> CPSAT
B --> LKH
B --> NN
```

职责：

| 模块       | 作用             |
|------------|------------------|
| CP-SAT TSP | 小规模精确质量锚 |
| LKH-3      | 大规模快速近似   |
| NN+2opt    | 最低级回退       |

------------------------------------------------------------------------

# 2. 为什么需要 LKH-3

CP-SAT 的优势：

    OPTIMAL certificate

但随着：

    节点数量增加

证明成本快速增长。

因此：

    小规模

    CP-SAT

    ↓

    大规模

    LKH-3

形成规模分层。

------------------------------------------------------------------------

# 3. 核心机制

LKH-3 基于：

    Lin-Kernighan
    variable neighborhood search

核心增强：

- 5-move；
- patching；
- candidate set search。

目标：

快速改善 tour。

------------------------------------------------------------------------

# 4. 开放路径建模

业务路线：

    Depot

    ↓

    Store A

    ↓

    Store B

    ↓

    Store C

通常不要求回 Depot。

LKH 原生处理：

    closed tour

因此转换：

## Dummy Node 方法

加入：

    Dummy

边权：

    C = 10 × max(D)

求解：

    Hamiltonian Cycle

之后：

    从 Dummy 处切开

得到：

    Open Path

------------------------------------------------------------------------

# 5. ATSP + FULL_MATRIX

当前实现必须使用：

    ATSP

    +

    EXPLICIT FULL_MATRIX

原因：

LKH 对普通 TSP：

    读取下三角矩阵

而业务距离矩阵：

可能：

- 非对称；
- 路网约束；
- 方向相关。

错误配置可能：

    静默产生错误路线

------------------------------------------------------------------------

# 6. 当前参数

默认：

    RUNS=10

    MAX_TRIALS=5000

    MAX_CANDIDATES=20

    MOVE_TYPE=5

    PATCHING_A=2

目标：

在固定时间预算内获得稳定近似。

------------------------------------------------------------------------

# 7. 预算与性能

矩阵口径：

    5s / 日

封装默认：

    240s

包含：

- 外部子进程；
- 超时处理；
- 输出解析。

------------------------------------------------------------------------

# 8. 结果状态必须诚实

LKH 输出：

    heuristic solution

不存在：

    OPTIMAL

因此：

允许：

    LKH_SUCCESS

禁止：

    证明最优

------------------------------------------------------------------------

# 9. 回退机制

如果：

- LKH 二进制不存在；
- 超时；
- 没有 tour 输出；

执行：

    NN + 2opt

状态：

    LKH_FALLBACK_NN2OPT

重要：

不能把 fallback 结果标记为：

    LKH result

------------------------------------------------------------------------

# 10. 已知性能边界

LKH 优势：

    大规模

    +

    欧氏距离实例

弱项：

    小规模

    +

    非对称路网矩阵

实际测试：

某线路：

    LKH:
    17.4 km

    CP-SAT:
    14.03 km

说明：

LKH 不一定优于精确模型。

------------------------------------------------------------------------

# 11. 与 CP-SAT 的关系

两者不是竞争关系。

正确定位：

``` text
CP-SAT

质量天花板


LKH-3

规模扩展工具
```

比较时必须注明：

    solver status
    +
    time budget

------------------------------------------------------------------------

# 12. 许可边界

LKH-3：

公开许可限制：

- 学术/非商业研究用途；
- 商业生产发行需要单独确认授权。

因此：

当前：

    研究矩阵可使用

生产部署：

必须：

    license review

------------------------------------------------------------------------

# 13. 在整体体系中的位置

``` mermaid
flowchart TB

Contract["VisitIR"]

Plan["Contract-SP"]

Route["Daily Route"]

Exact["CP-SAT TSP"]

Heuristic["LKH-3"]

Execute["Execution"]

Contract --> Plan
Plan --> Route
Route --> Exact
Route --> Heuristic
Exact --> Execute
Heuristic --> Execute
```

------------------------------------------------------------------------

# References

- Helsgaun (2000), An Effective Implementation of the Lin-Kernighan
  Traveling Salesman Heuristic
- Helsgaun (2017), LKH-3 Technical Report

------------------------------------------------------------------------

# Related Files

- `algos/lkh_engine.py`
- `route_with_tsp(mode="lkh3")`
- `TSP-CP-SAT Quality Anchor`
- `Base Benchmark`
