# VisitModel Formulation vNext：固定 (店,日期) 行空间的 Contract-SP 重构

> **状态**：v0.4 · 2026-09-07（已采纳入母仓 docs/design/；公式符号已修复）
>  
> **前序版本**：v0.1 → v0.2 → v0.3  
> **本版定位**：在 v0.3
> 已采纳评审结论基础上，进一步收口数学定义、证明语义、状态分类与实施门禁。  
> **核心决策**：将现行 column-dependent-row master 重构为固定
> `(store, date)` linkage row space，使 Contract-SP、Column Generation
> 与 Branch-and-Price 在同一代数模型上闭环。

------------------------------------------------------------------------

# 0. Executive Decision：这次重构到底改变什么

当前 v1 Master 的问题不是 SP-IP 本身不会求，而是：

> **Column Generation 与 Branch-and-Price 使用的 LP / dual /
> reduced-cost 解释，与当前 master 的列特定绑定行不完全闭合。**

vNext 不改：

- VisitIR 合同本体；
- R2′ 业务语义；
- 上游 ALNS/HGS/R2′-ALNS 的接口；
- 历史可行计划的 km 数字。

vNext 改：

``` text
CURRENT v1

route column x_r
      │
      ├── date row
      ├── store coverage row
      └── x_r ≤ z_cw
              ↑
        row 随 column 增长
```

为：

``` text
vNext

route column x_r
      │
      ▼
fixed linkage row
y_cd = Σ route-column incidence
      │
      ├── contract frequency
      ├── weekday consistency
      ├── phase/legal-domain
      └── branch fixing
```

最终目标：

``` mermaid
flowchart LR
    IR["VisitIR Contract"]
    RMP["Fixed-row Contract-SP"]
    CG["Column Generation"]
    BP["Branch-and-Price"]
    CERT["Certified Bounds / Proof"]

    IR --> RMP
    RMP <--> CG
    RMP <--> BP
    BP --> CERT
```

------------------------------------------------------------------------

# 1. 背景：为什么必须重构

## 1.1 现行 Master（v1）

当前 LP/IP 结构：

\[ min Σ_r c_r·x_r \]

subject to：

\[ Σ_{r∈R_d} x_r = 1   ∀ 工作日 d \]

\[ Σ_w z_{cw} = 1   ∀ 门店 c \]

\[ Σ_{r∋c} x_r = Σ_w f_{cw}·z_{cw}   ∀ c \]

以及：

\[ x_r ≤ z_{c,wd(r)}   ∀ 列 r、∀ c∈r \]

最后一组约束是当前问题的核心：

> 每新增一个 route column，同时新增若干条与该 column 绑定的结构行。

因此它属于 **column-dependent rows** 形态，而不是本文前面 Concept
文档所讲的普通 fixed-row Column Generation。

------------------------------------------------------------------------

# 2. 已确认缺口与未确认事项

## 2.1 已确认缺口

### 缺口 A：Row Space 随 Column Space 增长

当前：

``` text
new column

↓

new x variable

+

new x≤z rows
```

所以：

``` text
Master rows
```

不是固定集合。

这不满足经典 Dantzig-Wolfe / fixed-row Column Generation
的基本实现形态。

------------------------------------------------------------------------

### 缺口 B：Reduced Cost 与当前 Master 不完整闭合

现行 pricing 使用近似形式：

\[ rc = c_r − π_d − Σ_{c∈r} μ_c \]

但当前 master 还存在：

\[ x_r ≤ z_{c,wd(r)} \]

列特定约束。

因此：

> 该 rc 不是当前完整 master 中 route column 的完整代数 reduced cost。

------------------------------------------------------------------------

### 缺口 C：RMP LP 曾被过度解释

历史代码路径中存在：

``` text
heuristic pricing stop

↓

RMP LP value

↓

当作 node true lower bound
```

的问题。

正确：

``` text
RMP LP value
```

只能说明当前 column pool。

只有完成精确定价证明：

    no negative reduced-cost column

才能得到该节点完整 master LP 的有效 lower bound。

------------------------------------------------------------------------

## 2.2 不预设结论的历史审计

本重构不自动宣布：

> 所有历史 B&P 证书全部无效。

历史证书单独审计：

- dual 条件；
- pricing 完整性；
- 新增绑定行可能的零对偶延拓；
- 节点剪枝依据。

审计前：

``` text
可行计划 km

与

证明资格

分开处理
```

------------------------------------------------------------------------

# 3. 为什么选择 Fixed-row Reformulation

理论上存在两条路线。

## Route A：Fixed-row Reformulation

提前建立固定 `(store,date)` linkage rows。

优势：

- Master row space 固定；
- reduced-cost 代数简单；
- pricing dual 语义稳定；
- Branch 直接落在 `y_cd`；
- audit / test / certificate 更容易。

------------------------------------------------------------------------

## Route B：Column-and-Row Generation

保留 column-dependent-row 结构，同时动态生成：

- columns；
- structural rows。

这在运筹优化文献中是合法的正式方法，并非理论上不可行。

但当前项目不选它。

原因不是：

> “Column-and-Row Generation 不正确。”

而是：

> 对 VisitModel 当前规模、Agent 可审计性和 B&P 证书目标而言，fixed-row
> linkage formulation 更简单、更透明、更容易证明。

因此：

# Design Decision

> vNext 采用 Route A。

------------------------------------------------------------------------

# 4. 数学对象与符号

## 4.1 集合

| 符号    | 含义                                    |
|---------|-----------------------------------------|
| \(C\)   | 门店集合                                |
| \(D\)   | 工作日集合                              |
| \(W\)   | 星期几集合                              |
| \(R\)   | 当前 route column pool                  |
| (R_d：日期 d 的候选列)   | 日期 (d) 的 route columns               |
| (W_c⁺：门店 c 的正频次星期域) | 门店 c 的正频次星期域：({w : f_{cw} > 0}) |
| (L_c)   | 门店 c 的合同合法日期集合               |

------------------------------------------------------------------------

## 4.2 Column Membership

定义：

\[ a_{cr} = 1 若门店 c ∈ 路线 r；否则 0 \]

------------------------------------------------------------------------

## 4.3 合同合法日期域

`L_c` 必须来自同一版本 VisitIR：

``` text
contract_slot_dates(
    κ_c,
    φ_c,
    weekday slots
)
```

跨所有允许重新分配的 weekday 合并。

因此：

``` text
contract ontology
        ↓
legal date domain
        ↓
optimization model
```

不能反过来由优化器自行解释合同。

------------------------------------------------------------------------

# 5. vNext 变量

| 变量      | LP 域   | IP 域                         | 含义                       |
|-----------|---------|-------------------------------|----------------------------|
| (x_r)     | (x_r)   | {0,1}                         | 是否选择 route column      |
| (y_{cd}) | \[0,1\] | {0,1} 或由 x 传导             | 门店 c 是否在日期 d 被访问 |
| (z_{cw}) | \[0,1\] | 连续即可，由整数 x/y 传导整分 | 门店 c 选择星期几 w        |

说明：

### 关于 x 的上界

数学上：

\[ _{rR_d}x_r=1,x_r \]

已经蕴含：

\[ x_r \]

因此 vNext LP 可不显式创建 x 的 upper bound。

这样 pricing 时所有“尚未生成的 column”天然从 lower bound 0
进入，reduced-cost 语义更干净。

实现若保留 UB=1，也必须在 reduced-cost 测试中正确处理 bound 状态。

------------------------------------------------------------------------

# 6. vNext Master

## (A) 日期覆盖

\[ Σ_{r∈R_d} x_r = 1   ∀ 工作日 d \]

对偶：

\[ π_d \]

------------------------------------------------------------------------

## (B) 店-日链接

\[ y_{cd} − Σ_{r∈R_d} a_{cr}·x_r = 0   ∀ (c,d) \]

对偶：

\[ β_{cd} \]

这是 vNext 的关键 fixed row。

------------------------------------------------------------------------

## (C) 星期几一致绑定

只对：

\[ wd(d) ∈ W_c⁺ \]

且 `(c,d)` 在业务候选星期域内的 pair 建：

\[ y_{cd} ≤ z_{c,wd(d)} \]

如果：

\[ wd(d) ∈ W_c⁺ \]

则：

> 不创建不存在的 `z_cw` 引用；直接由合法域令 `UB(y_cd)=0`。

这样避免 v0.3 中“z 未定义但公式仍引用”的形式缺口。

------------------------------------------------------------------------

## (D) 合同频次

\[ Σ_d y_{cd} = Σ_{w∈W_c⁺} f_{cw}·z_{cw}   ∀ c \]

其中：

\[ f_{cw} = |contract_slot_dates(κ_c, φ_c, w)| \]

必须与合法日期域来自同一合同版本。

------------------------------------------------------------------------

## (E) 唯一星期几

\[ Σ_{w∈W_c⁺} z_{cw} = 1   ∀ c \]

如果：

\[ W_c⁺ = ∅ \]

返回明确不可行状态。

不得静默跳过门店。

------------------------------------------------------------------------

## (F) 合法域

\[ 0 ≤ y_{cd} ≤ UB_{cd} \]

其中：

\[ UB_{cd} =
\]

这使合同合法性成为模型自身的一部分，而不再依赖 pool filter 才正确。

------------------------------------------------------------------------

# 7. 固定行空间成立

定义：

\[ E_{bind} = {(c,d) : wd(d) ∈ W_c⁺} \]

则 Master row 数：

\[ |D| + |C|·|D| + |E_bind| + 2|C| \]

不依赖 column pool 大小。

新 route column 进入时只需要：

``` text
(A) 日期行        +1

(B) 对包含门店    -1
```

不增加新的结构行。

因此：

``` text
row space

固定


column space

动态增长
```

回归标准 fixed-row Column Generation 形态。

------------------------------------------------------------------------

# 8. Reduced Cost：完整代数闭环

对于日期 d 的 route r：

目标系数：

\[ c_r \]

1)  行系数：

\[ +1 \]

2)  对每个包含门店 c：

\[ -1 \]

因此：

\[ rc(r@d) = c_r − π_d + Σ_{c∈r} β_{cd} \]

定义：

\[ reward_{cd} = −β_{cd} \]

则：

\[ rc(r@d) = c_r − π_d − Σ_{c∈r} reward_{cd} \]

------------------------------------------------------------------------

# 9. Pricing 子问题应该优化什么

对固定日期 d：

\[ π_d \]

是常数。

因此 Pricing 实际寻找：

\[ min over r ( c_r − Σ_{c∈r} reward_{cd} ) \]

再计算：

\[ rc = pricing_objective − π_d \]

如果：

\[ rc < 0 \]

则发现值得加入的新列。

重要：

> Pricing 不是“先最大化 reward，再最小化距离”的词典序问题。

它优化的是一个统一 reduced-cost objective：

``` text
route cost

-

dual reward
```

------------------------------------------------------------------------

# 10. Reduced-cost 守卫测试

测试分两类。

## 10.1 已存在变量

比较：

``` text
hand-computed rc

vs

solver reduced_cost()
```

必须按 variable/basis/bound 状态解释。

------------------------------------------------------------------------

## 10.2 未生成变量

微型实例：

    完整枚举所有合法 route

对每一条未进池列手算：

\[ rc \]

并核对：

    exact pricing minimum rc

与枚举真值一致。

这才真正测试：

> Pricing 是否覆盖完整 reduced-cost 语义。

------------------------------------------------------------------------

# 11. v2 与 v1 的数学关系

前提：

- 同一合法 column pool；
- 同一成本；
- 同一正频次星期域；
- v1 已应用合法域。

则：

## IP

v1 与 v2：

> 整数可行解投影等价。

------------------------------------------------------------------------

## LP

v2 的 `(x,z)` 投影可行域：

\[ P_{v2} ⊆ P_{v1} \]

因此 minimization：

\[ z_{LP}^{v2} ≥ z_{LP}^{v1} \]

是否严格：

> 取决于实例与 column pool。

不能宣称普遍严格强化。

------------------------------------------------------------------------

# 12. 为什么 v2 LP 更紧

v1：

对每条 column 单独约束：

\[ x_r ≤ z \]

如果同一天存在多个 fractional columns：

它们每个都可能分别满足：

``` text
x_r ≤ z
```

但合计覆盖：

\[ x_r \]

可能超过 z。

v2：

先聚合：

\[ y_{cd} = Σ_{r∋c} x_r \]

然后：

\[ y_{cd} ≤ z \]

因此把：

> 同一天同店的 fractional mass

统一约束。

------------------------------------------------------------------------

# 13. Pool Filter 从 Correctness 依赖降级为 Hygiene

v1：

非法 column 必须预先过滤，否则模型正确性可能依赖过滤。

v2：

非法 `(c,d)`：

\[ UB(y_{cd})=0 \]

任何包含非法访问的 column：

通过链接行自动无法被选择。

因此 `_contract_pool_filter` 仍然保留：

用于：

- 减少垃圾列；
- 提高求解效率；
- 保持 pool 清洁。

但它不再承担：

> “模型是否合法”的唯一责任。

------------------------------------------------------------------------

# 14. 必须区分两种 Infeasible

这是 vNext 的状态设计硬要求。

## RMP_INFEASIBLE

表示：

> 当前 column pool 无法满足 Master。

可能原因：

- 缺列；
- branch 后 pool 饿死；
- pricing 尚未恢复。

它不等于：

> 业务实例不可行。

------------------------------------------------------------------------

## NODE / INSTANCE PROVEN INFEASIBLE

只有完整可行性证明成立，例如：

- exhaustive pricing / feasibility proof；
- 完整 route domain 已证明不存在合法恢复列。

才能使用：

``` text
PROVEN_INFEASIBLE
```

因此：

> 受限池不可行 ≠ 业务不可行。

------------------------------------------------------------------------

# 15. Branch-and-Price 接入

Branch 直接作用：

\[ y_{cd} \]

分支：

``` text
forced:
y_cd = 1

forbidden:
y_cd = 0
```

实现优先：

> 修改 y variable bounds，而不是动态新增结构 row。

这样节点之间仍共享同一 Master row topology。

------------------------------------------------------------------------

# 16. Node Valid Lower Bound 的完整资格

只有全部满足：

1.  Node LP 状态 = `OPTIMAL`
2.  Dual / column pool / column costs / branch state 属于同一 solve
    snapshot
3.  全部日期 exact pricing 完成
4.  所有日期最小 rc：

\[ rc_{min} ≥ −容差（容差内非负） \]

5.  feasibility-recovery artificial variables：
    - 已移除；或
    - 在最优解中为 0，并完成等价性检查

才能：

``` text
node_valid_lb = LP objective
```

否则：

``` text
node_valid_lb = UNKNOWN
```

------------------------------------------------------------------------

# 17. Global Lower Bound 与 PROVEN_OPTIMAL 必须分开

这是 v0.4 的重要语义修正。

## 17.1 根节点

如果 root node：

    LP OPTIMAL
    +
    exact pricing proven

那么：

> Root LP 本身已经是整个整数问题的 **certified global lower bound**。

即使：

    branch tree 尚未搜索完

也成立。

------------------------------------------------------------------------

## 17.2 分支后的 Frontier Bound

若当前所有未解决 active nodes：

- 完整覆盖剩余搜索空间；
- 每个都拥有 `node_valid_lb`；

则：

\[ certified_global_lb = min_{n∈frontier} node_valid_lb(n) \]

可用于强化全局下界。

如果某个 frontier node：

    bound UNKNOWN

不能忽略它。

此时：

保留最近一次已经合法证明的：

``` text
certified_global_lb
```

例如 root bound。

------------------------------------------------------------------------

## 17.3 PROVEN_OPTIMAL

需要：

- 有合法 incumbent；
- 所有剩余搜索区域被合法 fathom；
- 不存在 unresolved proof debt；
- certified gap 在容差内闭合。

因此：

``` text
有 certified_global_lb

≠

PROVEN_OPTIMAL
```

树耗尽决定的是：

> 最优性证明是否完成。

不是：

> 有没有全局有效下界。

------------------------------------------------------------------------

# 18. 对外字段语义

协议字段：

## `rmp_lp_value`

当前 RMP 的 LP objective。

必须附：

- LP status；
- pool snapshot identity。

------------------------------------------------------------------------

## `node_valid_lb`

内部字段。

作用域：

``` text
single subtree
```

必须带：

- node id；
- proof metadata。

------------------------------------------------------------------------

## `certified_global_lb`

整个问题范围内已被数学证明有效的 lower bound。

它可以在：

> 搜索完成前存在。

------------------------------------------------------------------------

## `global_gap_pct`

若：

- incumbent 存在；
- certified_global_lb 存在；

定义：

\[ global_gap_pct = 100×(UB − certified_global_lb)/|UB| \]

数值容差内小于 0：

按 0 处理并记录 audit warning。

------------------------------------------------------------------------

## `pool_gap_pct`

只描述当前 pool：

不得与：

``` text
global_gap_pct
```

混用。

------------------------------------------------------------------------

# 19. B&P 状态

建议状态继续保持：

| 状态              | 含义                            |
|-------------------|---------------------------------|
| `PROVEN_OPTIMAL`  | 完整整数证明链闭合              |
| `BOUND_HEURISTIC` | 有搜索/界信息，但整数证书未闭合 |
| `TIME_LIMIT`      | 时间/节点预算截止               |

注意：

`BOUND_HEURISTIC` 并不意味着：

``` text
certified_global_lb = null
```

例如：

root LP 已精确定价完成，但 branch tree 尚未完成：

可以：

``` text
status = BOUND_HEURISTIC

certified_global_lb = valid
```

------------------------------------------------------------------------

# 20. 兼容与回滚

建议：

``` text
sp_solve_lp_v2
sp_solve_ip_v2
```

或：

``` text
formulation="linkage"
```

过渡期：

    v1
    +
    v2

双跑。

默认切换必须经过验收门禁。

------------------------------------------------------------------------

## 回滚原则

回滚只允许：

    formulation switch

不能：

> 因回滚到 v1 而重新启用未经证明的 node bound 剪枝。

证书资格规则：

独立于 formulation version。

------------------------------------------------------------------------

# 21. 测试守卫

## T1 Reduced-cost Algebra

验证：

- 手算 rc；
- solver reduced cost；
- sign；
- degeneracy；
- bound state。

------------------------------------------------------------------------

## T2 Full-column Truth

微型实例全列枚举：

    CG final LP

    ==

    full master LP

同时：

    exact pricing min rc

    ==

    enumerated min rc

------------------------------------------------------------------------

## T3 Frozen-pool IP Equivalence

同一合法 column pool：

    v1 IP

    vs

    v2 IP

均 `OPTIMAL` 后比较：

- objective；
- calendar projection；
- contract validity。

------------------------------------------------------------------------

## T4 LP Dominance

验证：

\[ LP_{v2}LP_{v1} \]

并保留已验证严格强化反例。

------------------------------------------------------------------------

## T5 Domain Edge Cases

覆盖：

- `W_c^+` 为空；
- `wd(d)∉W_c^+`；
- 非法 phase date；
- partial month；
- W53 / anchor phase。

------------------------------------------------------------------------

## T6 Infeasibility Taxonomy

验证：

    RMP_INFEASIBLE

    ≠

    PROVEN_INFEASIBLE

禁止错误升级。

------------------------------------------------------------------------

## T7 Certificate Gate

覆盖：

- LP FEASIBLE 非 OPTIMAL；
- heuristic pricing stop；
- exact pricing timeout；
- artificial variable positive；
- snapshot mismatch；
- rollback path。

全部：

不得错误创建：

``` text
node_valid_lb
```

------------------------------------------------------------------------

## T8 Global Bound Aggregation

覆盖：

- valid root bound；
- partial tree；
- frontier all-certified；
- frontier 有 UNKNOWN node；
- time limit。

------------------------------------------------------------------------

## T9 End-to-End 10 Lines

v1 / v2：

分别报告：

- final km；
- RMP LP；
- pool size；
- runtime；
- pricing completion；
- certified LB；
- final status。

不同动态 column pool：

不要求数值相等。

------------------------------------------------------------------------

# 22. 性能风险

v2 row 数近似：

\[ |D| + |C|·|D| + |E_bind| + 2|C| \]

真实线路可能达到数千行。

这是可接受风险，但必须实测，而不是用：

> “GLOP 应该没问题”

代替数据。

报告至少包含：

- rows；
- columns；
- simplex iterations；
- LP runtime；
- memory；
- pricing runtime。

------------------------------------------------------------------------

# 23. 实施顺序

``` mermaid
flowchart LR

A["Phase A<br/>v2 Master"]

B["Phase B<br/>Pricing β"]

C["Phase C<br/>CG Truth Tests"]

D["Phase D<br/>B&P Bound Gate"]

E["Phase E<br/>Protocol Fields"]

F["Phase F<br/>v1 Deprecation"]

A --> B --> C --> D --> E --> F
```

## Phase A

先完成：

- fixed rows；
- legal domain；
- v1/v2 frozen-pool IP equivalence。

------------------------------------------------------------------------

## Phase B

完成：

- β dual extraction；
- reduced-cost algebra；
- heuristic pricing migration。

------------------------------------------------------------------------

## Phase C

全列枚举：

先证明 CG 数学闭环。

------------------------------------------------------------------------

## Phase D

再允许 B&P：

使用 `node_valid_lb` 做剪枝。

在此之前：

> B&P 禁止基于未证 RMP value 剪枝。

------------------------------------------------------------------------

## Phase E

对齐：

- `rmp_lp_value`
- `pool_gap_pct`
- `certified_global_lb`
- `global_gap_pct`

------------------------------------------------------------------------

## Phase F

所有验收通过后：

再废弃 v1。

------------------------------------------------------------------------

# 24. 非目标

本设计不包含：

- ESPPRC exact pricing 的最终工程实现；
- ALNS/HGS 搜索器重写；
- VisitIR ontology 重构；
- 历史实验回填；
- ALNS v4 phase P0 修复；
- directed-safe 2-opt 修复。

这些是独立工作流。

------------------------------------------------------------------------

# 25. 核心不变量

最终必须长期保持五条：

## I1

``` text
Business legality
来自 VisitIR
```

## I2

``` text
Master row semantics
不随 route column 生成而改变
```

## I3

``` text
Reduced cost
必须由 Master 代数直接推出
```

## I4

``` text
RMP optimum
不自动等于 node/global lower bound
```

## I5

``` text
可行计划质量
与
最优性证明资格
永远分开记录
```

------------------------------------------------------------------------

# 26. References

- Dantzig, G. B. & Wolfe, P. (1960). *Decomposition Principle for Linear
  Programs*. Operations Research 8(1):101–111.
- Barnhart, C., Johnson, E. L., Nemhauser, G. L., Savelsbergh, M. W. P.
  & Vance, P. H. (1998). *Branch-and-Price: Column Generation for
  Solving Huge Integer Programs*. Operations Research 46(3):316–329.
- Lübbecke, M. E. & Desrosiers, J. (2005). *Selected Topics in Column
  Generation*. Operations Research 53(6):1007–1023.
- Muter, İ., Birbil, Ş. İ. & Bülbül, K. (2013). *Simultaneous
  Column-and-Row Generation for Large-Scale Linear Programs with
  Column-Dependent-Rows*. Mathematical Programming 142:47–82.

------------------------------------------------------------------------

# 27. Related Documents

- `set-partitioning-final-gate.md`
- `column-generation.md`
- `branch-and-price.md`
- `r2-prime-contract.md`
- `MATRIX_PROTOCOL_V3_DESIGN.md`
- `SP_MATHEURISTIC_DESIGN.md`
