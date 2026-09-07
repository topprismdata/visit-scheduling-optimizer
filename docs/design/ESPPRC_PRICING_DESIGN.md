# ESPPRC 精确定价 oracle 设计

> **状态**：草稿 v0.1 · 2026-09-08（待评审）
> **缘起**：bp 全线路 BOUND_HEURISTIC / root_lb=None——根因是精确定价 oracle（`_price_exact`）在真实规模（91-176 店/日，max_daily 21-37）下无法在 `exact_tl=1.0s` 内证明"无负 rc 列"。
> **归属**：`OptiCore` 仓（新模块 `opticore.pricing`）+ 母仓 `algos/branch_and_price.py` 接入
> **参照**：Feillet, Dejax, Gendreau, Gueguen (2004) *An exact algorithm for the elementary shortest path problem with resource constraints*. Transportation Science 38(3). Chalasani & Ramesh (2007)。Baldacci et al. (2011) ng-route relaxation。

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
- 变量：n_d² 有向弧布尔 + n_d 自环 + 2·n_d dummy 弧 ≈ 1300-2800 vars（n_d = 91-176）
- 目标：min(路径 km − Σ 奖励)
- `exact_tl = 1.0s` → **CP-SAT 无法在该时限内证明 OPTIMAL**
- 结果：10/10 线 `converge_proven = 0` → `PROVEN_OPTIMAL` 不可达

### 1.3 为什么不能简单加大时限

| 参数 | 当前 | 需要的 | 差距 |
|---|---|---|---|
| exact_tl | 1.0s | 估计 30-300s/日 | 30-300× |
| 日数 × exact_tl | 23s | 690-6900s | 30-300× |

加大到 30s 可能有效（n ≤ 35 时 CP-SAT 通常能在 30s 内证优）。但：
- 一次完整定价 = 23 日 × 30s = **11.5 分钟**
- 每次节点 CG 需要完整定价 → B&P 仍不实际
- 但对 **root node 单次证明**已足够

## 2. 两步走策略

### Step 1（快速验证，~1 行代码改动）

将 `_price_exact` 的 `exact_tl` 提升至 **60s**。在 02 线（172 店，最难之一）上跑一次 root node 精确定价：

- 如果 23 日全部 OPTIMAL → `converge_proven > 0` → `root_lb` 签发 → **PROVEN_OPTIMAL 立即可达**（不需要 ESPPRC）
- 如果仍有日期无法证明 → 需要 Step 2

### Step 2（ESPPRC Labeling Algorithm）

当 CP-SAT 在 n > 100 时无法在合理时间内证明（预计），切换到专用 labeling 算法。

---

## 3. ESPPRC Labeling Algorithm 设计

### 3.1 核心思想

用**动态规划 + 支配剪枝**替代 CP-SAT 的全局搜索：

```
状态（Label）= (路径成本, 已访问店集, 当前末尾店)
扩展 = 从末尾店延伸到下一个未访问店
支配 = Label L1 支配 L2 当 cost(L1) ≤ cost(L2) 且 visited(L1) ⊆ visited(L2)
```

目标：找到 min(cost − Σ rewards) 的完整路径。

### 3.2 关键设计：利用 max_daily 有界性

标准 ESPPRC 的困难在于 visited_set 是指数级的。但我们的问题有额外结构：

- **max_daily ≤ 37**（实际 21-37）→ 路径长度有界
- 每日期独立定价 → 可并行
- 奖励 reward_cd 已知 → 可预排序

**方案：按路径长度分轮扩展**（BFS 式而非 DFS）

```
Round 1: 长度 1 的路径（单店起点）
Round 2: 长度 2 的路径（扩展到 2 店）
...
Round k: 长度 k 的路径
停止条件: k = max_daily 或 无新非支配标签
```

每轮：
1. 对每个 Label (cost, visited, last)：
2. 枚举 last 的未访问邻居 c ∉ visited
3. 新 Label = (cost + D[last][c] − reward_c, visited ∪ {c}, c)
4. 支配剪枝：删除被支配的标签

### 3.3 剪枝策略（控制标签爆炸）

| 剪枝 | 规则 | 效果 |
|---|---|---|
| 支配 | cost ≤ 且 visited ⊆ | 指数级剪枝 |
| 路径长度 | len(visited) ≤ max_daily | 硬截断 |
| 下界剪枝 | cost + LB(剩余) ≥ 0 → 剪（不可能产生负 rc） | 需要预计算下界 |
| 奖励阈值 | 如果剩余可选店的 reward 总和 < 当前最优 | 需要维护全局 upper bound |

### 3.4 与 CP-SAT 的比较

| 维度 | CP-SAT (当前) | ESPPRC Labeling |
|---|---|---|
| n=35 可证优？ | 通常可（30s） | 是（毫秒-秒级） |
| n=163 可证优？ | 不能（1s）/ 可能（300s+） | 取决于支配效率 |
| 实现复杂度 | 低（已有） | 中（~200-300 行） |
| 确定性 | 是（1 worker） | 是（纯 DP） |
| 最坏复杂度 | NP-hard | NP-hard（支配可指数爆炸） |
| 实测建议 | 先试 exact_tl=60s | CP-SAT 不够时再做 |

---

## 4. 接口设计

### 4.1 OptiCore 新模块

```
OptiCore/src/opticore/pricing.py

def exact_pricing_date(
    stores: list[int],           # 当日合法店集
    D: list[list[float]],        # 距离矩阵
    rewards: dict[int, float],   # {store: reward_cd}
    min_stores: int,             # 走廊下限
    max_stores: int,             # 走廊上限
    time_limit: float,           # 秒
) -> PricingResult
```

```python
@dataclass
class PricingResult:
    status: str                  # "PROVEN_OPTIMAL" | "TIME_LIMIT" | "INFEASIBLE"
    best_rc: float | None        # min(路径 km − Σ rewards)
    best_route: list[int] | None
    labels_explored: int
    labels_pruned: int
```

### 4.2 bp 接入

`_price_exact` 改为调用 `opticore.pricing.exact_pricing_date`：

```python
# 旧: CP-SAT AddCircuit
# 新: opticore.pricing.exact_pricing_date
result = exact_pricing_date(
    stores=eligible, D=self.D, rewards={c: -link_dual.get((c,dd), 0)},
    min_stores=self.min_daily, max_stores=self.max_daily,
    time_limit=self.exact_tl
)
if result.status == "PROVEN_OPTIMAL" and result.best_rc >= -1e-6:
    pass  # 该日无负列
elif result.best_rc < -1e-6:
    out.append((dd, result.best_route, day_km(result.best_route, self.D)))
else:
    self._exact_all_proven = False
```

---

## 5. 守卫测试

| 测试 | 钉死什么 |
|---|---|
| 微型全枚举 | n=4 店全排列，labeling 最优 == 枚举最优 |
| 支配正确性 | 构造支配对，验证被支配标签确实不产生更优解 |
| 合法域 | 非法店不进路径 |
| 走廊 | 路径长度 ∈ [min, max] |
| 确定性 | 同输入两次运行逐位一致 |
| 与 CP-SAT 对照 | 同实例 labeling 最优 ≤ CP-SAT 最优 |

---

## 6. 排期

| 步骤 | 内容 | 预估 |
|---|---|---|
| Step 1 | exact_tl 1→60s 快速验证 | **1 小时**（改 1 行） |
| Step 1a | 如果 60s 够 → PROVEN_OPTIMAL 立即可得，不需要 ESPPRC | — |
| Step 2 | ESPPRC labeling 设计 + 实现（OptiCore） | 2-3 天 |
| Step 3 | bp 接入 + 回归测试 | 1 天 |
| Step 4 | 全线路 PROVEN_OPTIMAL 验证 | 1 天 |

---

## 7. 风险

| 风险 | 缓解 |
|---|---|
| 支配剪枝不够，标签爆炸 | 先跑 Step 1 验证 CP-SAT 是否够；不够再做 ESPPRC |
| ng-route 松弛引入不精确 | v1 版本不做 ng-route（保持精确），后续按需 |
| max_daily 大导致标签长度深 | 路径长度截断 + 奖励上界剪枝 |
| OptiCore 仓并发修改 | 与模块剥离计划协调 |
