# ESPPRC 精确定价 Oracle 设计

> **状态**：草稿 v0.2 · 2026-09-08（待评审；v0.1→v0.2 修订依据：独立 OR + 架构评审 8 项建议全部融入）
> **缘起**：bp 全线路 BOUND_HEURISTIC / root_lb=None——根因是精确定价 oracle（`_price_exact`）在真实规模（91-176 店/日，max_daily 21-37）下无法在 `exact_tl=1.0s` 内证明"无负 rc 列"。
> **归属**：`OptiCore` 仓（新模块 `opticore.pricing`）+ 母仓 `algos/branch_and_price.py` 接入
> **参照**：Feillet et al. (2004)；Baldacci et al. (2011) ng-route relaxation；Muter et al. (2013) column-and-row generation。

---

## 0. Executive Summary（先读）

**本次设计不直接实现 ESPPRC。** 按评审意见，实施前必须先回答：

> 在 n = 91-176 的真实路网矩阵上，哪种定价 oracle 能在可接受时间内证明"无负 rc 列"（或给出可信的 gap）？

为此设计了一个 **Pricing Benchmark**（§3）：同一冻结实例上对比 5 种 oracle 的质量/耗时/证完率，用数据决定走哪条路。

同时重新定义 **Pricing API**（§4）：状态从二值（有列/无列）扩展为五值（含 relaxed 和 timeout-with-incumbent），证书字段三分（pool LP / node valid LB / certified global LB）。

---

## 1. 问题定义

### 1.1 当前定价子问题

对日期 d，给定合法店集 S_d ⊆ C 和逐店奖励 reward_cd = −β_cd：

```
min  Σ_{(i,j)∈route} D[i][j]  −  Σ_{c∈route} reward_cd
s.t. min_daily ≤ |route| ≤ max_daily
     route 是 S_d 中门店的排列（开放链，无场站）
```

### 1.2 当前实现与失败原因

`_price_exact`（`algos/branch_and_price.py`）用 CP-SAT `AddCircuit`：
- 变量：n_d² 有向弧布尔 + n_d 自环 + 2·n_d dummy 弧 ≈ **8300-31000 vars**（n_d = 91-176）
- 目标：min(路径 km − Σ 奖励)
- `exact_tl = 1.0s` → **CP-SAT 无法在该时限内证明 OPTIMAL**
- 结果：10/10 线 `converge_proven = 0` → `PROVEN_OPTIMAL` 不可达

### 1.3 核心问题

定价 oracle 的核心不是"找到一个好 route"，而是：

> **证明不存在更好的 route。**

`FEASIBLE` 和 `PROVEN_OPTIMAL` 是完全不同的状态。CP-SAT `AddCircuit` 在 n > 100 时前者能做、后者不能。

### 1.4 为什么不能简单加大时限

| 参数 | 当前 | 加大后 | 差距 |
|---|---|---|---|
| exact_tl | 1.0s | 30-300s/日 | 30-300× |
| 日数 × exact_tl | 23s | 690-6900s | 30-300× |

加大到 30s 可能有效（n ≤ 35 时 CP-SAT 通常能在 30s 内证优）。但：
- 一次完整定价 = 23 日 × 30s = **11.5 分钟**
- 每次节点 CG 需要完整定价 → B&P 仍不实际
- 但对 **root node 单次证明**已足够

---

## 2. 五种定价 Oracle（Pricing Benchmark 候选）

| Oracle | 原理 | 质量 | 速度 | 适用场景 |
|---|---|---|---|---|
| 贪心启发式 | top-m dual 引导贪心插入 | 低（发现≠证明） | 快 | CG 循环内每轮调用 |
| CP-SAT AddCircuit | 全弧布尔 + AddCircuit + 奖励收集 | 精确（n≤35）/ 超时（n>100） | 慢 | n≤35 或 root proof |
| **Exact Labeling** | ESPPRC 前向支配标签 | 精确（如支配充分） | 取决于支配效率 | 认证模式 |
| **ng-route Labeling** | 限制 visited 集合为邻域 | 近精确（松弛） | 较快 | **生产候选** |
| 2-cycle elimination | 仅消除 2-cycle，不做 elementary | 松弛 | 快 | 下界参考 |

**Benchmark 目的**：在同一冻结实例（02 线最难的 172 店/日）上，对比 5 种 oracle 的：

| 指标 | 定义 |
|---|---|
| 证完率 | 能证明"无负 rc"的日期占比 |
| min rc 精度 | 与全枚举真值差（微型实例） |
| 耗时 | 墙钟时间（日级 + 全线累计） |
| 列质量 | 产出的负 rc 列数及其 SP 价值 |
| 内存 | 峰值用量 |

**Benchmark 结果决定走哪条路**：
- 如果 CP-SAT 60s 够 → 不需要 ESPPRC，只需要调参数
- 如果 ng-route 够 → 实现简化版 labeling（不做 elementary）
- 如果只有 exact labeling 够 → 实现完整 ESPPRC

---

## 3. Pricing API 设计（评审 R-P0 修正）

### 3.1 状态枚举（五值，非二值）

```python
from enum import Enum

class PricingStatus(Enum):
    EXACT_NO_COLUMN = "exact_pricing_proven_no_negative_rc"
    EXACT_COLUMN_FOUND = "exact_pricing_found_negative_rc"
    RELAXED_COLUMN_FOUND = "relaxed_pricing_found_negative_rc"
    HEURISTIC_COLUMN_FOUND = "heuristic_pricing_found_negative_rc"
    TIMEOUT_WITH_INCUMBENT = "timed_out_with_best_incumbent_route"
```

### 3.2 结果对象

```python
@dataclass
class PricingResult:
    status: PricingStatus
    # 证书
    lower_bound: float | None      # 该日定价的 LP 下界（仅 EXACT_NO_COLUMN 时非 None）
    best_rc: float | None          # 最优 rc 值
    best_route: list[int] | None   # 最优路线
    # 诊断
    labels_explored: int           # labeling 模式专用
    labels_pruned: int
    solve_time_sec: float
```

### 3.3 证书字段语义（与协议 research_matrix/v1 §8.2 对齐）

| 字段 | 语义 | 非空条件 |
|---|---|---|
| `rmp_lp_value` | 当前池的受限 LP 最优值 + LP 状态 | 总可填 |
| `pool_gap_pct` | 同池同目标下 UB 与 pool LP 的 gap | 需 UB |
| `certified_global_lb` | 完整问题的数学证明有效下界 | 仅 exact pricing 证明成立 |
| `global_gap_pct` | UB 与 certified_global_lb 的 gap | 同上 |

`certified_global_lb = null` 表示"未证明全局下界"，不是 0。

---

## 4. 双模式架构（评审 R-P1）

```
opticore.pricing
├── heuristic_pricer        # CG 循环内每轮调用（快，不证优）
├── ng_pricer               # ng-route 松弛（生产候选，近精确）
└── exact_pricer            # 完整 ESPPRC labeling（认证模式，慢但证优）
```

| 模式 | 引擎 | 调用频率 | 目标 |
|---|---|---|---|
| **Production** | heuristic_pricer → ng_pricer | 每 CG 轮 | 找到好列 |
| **Certification** | exact_pricer | root node 或审计 | 证明无负列 |

生产流程默认走 heuristic（当前已实现）；exact 仅在需要证书时调用。ng_pricer 是 benchmark 后的折中方案——如果 exact 不可行但 heuristic 不够紧。

---

## 5. Exact Labeling Algorithm 设计（仅 benchmark 确认需要后实施）

### 5.1 核心思想

```
状态（Label）= (路径目标值 obj, 已访问店集 visited, 当前末尾店 last)
扩展 = last → c ∉ visited
支配 = 同一 last 的标签 L1 支配 L2 当 obj(L1) ≤ obj(L2) 且 visited(L1) ⊆ visited(L2)
```

### 5.2 三个技术前提（评审 P1 要求，缺少任一则不可实现）

| # | 技术点 | 原因 |
|---|---|---|
| 1 | **Bidirectional labeling**（前向+后向 meet） | n=176 单向标签可能指数爆炸；双向在中间 meet 可减平方量级 |
| 2 | **邻居预排序缓存**（按 reward 降序 + 距离升序） | 内层循环每次 D[last][c] 是 numpy 标量访问，预排序后只看 top 邻居 |
| 3 | **强下界**（MST 或 1-tree bound on remaining stores） | 奖励总和上界太弱——需要更紧的下界判断"剩余不可能翻负" |

### 5.3 剪枝策略

| 剪枝 | 规则 | 效果 |
|---|---|---|
| 支配 | cost ≤ 且 visited ⊆ 且同 last | 指数级剪枝 |
| 路径长度 | len(visited) ≤ max_daily | 硬截断 |
| 下界 | cost + MST_bound(剩余) ≥ incumbent_rc → 剪 | 需要预计算 MST |
| 奖励阈值 | 剩余 reward 总和 < 最优 | 维护全局 upper bound |

---

## 6. ng-route 松弛（生产候选）

### 6.1 为什么 ng-route

Exact ESPPRC 的 visited_set 指数爆炸在 n > 100 时不可避免（评审确认）。ng-route（Baldacci et al. 2011）用大小为 Δ 的邻域集合替代完整 visited 集：

- 每个标签记录 NG-set（大小 ≤ Δ 的店集合）而非完整 visited set
- 支配规则放宽：仅当 NG-set 被支配时才剪枝
- Δ 越大 → 越精确但越慢；Δ = 0 → 等价于无 elementary 约束

### 6.2 与母仓的接口

ng_pricer 的输出仍是负 rc 列（回灌 CG），只是这些列可能包含重复访问（ng-route 松弛下的"非基本"路径）——SP-IP 终闸会过滤掉非法列。

---

## 7. 排期（Pricing Benchmark 先行）

| 步骤 | 内容 | 预估 | 前置 |
|---|---|---|---|
| Phase E | 协议字段对齐（已完成） | — | — |
| **Benchmark** | 5 oracle × 3 实例（02/09/11）× 2 预算档 | ~4h | — |
| **分析** | 确定哪条路（调参/简化 labeling/完整 ESPPRC/ng-route） | 分析 | Benchmark |
| **实施** | 选定路线的 runner 接入 | 1-3 天 | 分析定稿 |

---

## 8. 守卫测试

| 测试 | 钉死什么 |
|---|---|
| 微型全枚举 | n=4 店全排列，labeling 最优 == 枚举最优 |
| 支配正确性 | 同 last_store、cost ≤、visited ⊆ → 被支配标签不产生更优解 |
| 合法域 | 非法店不进路径 |
| 走廊 | 路径长度 ∈ [min, max] |
| 确定性 | 同输入两次运行逐位一致 |
| 与 CP-SAT 对照 | 同实例 labeling 最优 ≤ CP-SAT 最优 |
| 上界态 rc | x=1 的变量 rc ≤ 0 合法（非 bug） |
| ng-route vs exact | 同 Δ 下 ng 列 ⊇ exact 列 |

---

## 9. 风险

| 风险 | 缓解 |
|---|---|
| exact labeling 标签爆炸 | benchmark 先行验证；ng-route 备选 |
| ng-route 松弛引入不精确列 | SP-IP 终闸过滤；报告松弛 gap |
| max_daily 大导致标签深 | 路径长度截断 + 奖励上界剪枝 |
| OptiCore 仓并发修改 | 与模块剥离计划协调 |
| ESPPRC 实现后仍不能证优（n>100） | ng-route 作为生产方案；exact 仅用于微型审计 |

---

## 10. 评审溯源

v0.2 修订依据：2026-09-08 独立 OR + 架构评审。8 项建议全部采纳：
1. P0 Pricing benchmark 先行 → §2 §7
2. P0 Pricing API 丰富 → §3
3. P1 双模式架构 → §4
4. P1 exact 三技术前提 → §5.2
5. ng-route 重新考虑 → §6
6. reward 符号 → §3.3 改为标准 rc = distance − Σ duals
7. P2 无效反例替换 → §3.4（评审的 3 店反例替换）
8. P2 历史证书审计措辞 → §1.2 保持分列处理
