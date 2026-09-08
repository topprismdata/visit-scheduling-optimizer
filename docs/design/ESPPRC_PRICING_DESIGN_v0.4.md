# ESPPRC Pricing Oracle 与 Column Contract 设计

> **状态**：已批复进入 Benchmark · v0.4 · 2026-09-08（v0.3→v0.4 修订依据：独立 B&P/CG 架构复审；生产实现前置条件 = §3.4 CandidateNormalizer + §4.2a PricingCertificate / CG 终止契约 + §4.5 Column Lineage 全部落地）
> **缘起**：bp 全线路 BOUND_HEURISTIC / root_lb=None——根因是精确定价 oracle（`_price_exact`）在真实规模（91-176 店/日，max_daily 21-37）下无法在 `exact_tl=1.0s` 内证明"无负 rc 列"。
> **归属**：`OptiCore` 仓（新模块 `opticore.pricing`）+ 母仓 `algos/branch_and_price.py` 接入
> **参照**：Feillet et al. (2004)；Baldacci et al. (2011) ng-route relaxation；Muter et al. (2013) column-and-row generation。

---

## 0. Executive Summary

**本设计解决两个正交问题：**

1. **Pricing Oracle 选择**：同一冻结实例上对比 5 种 oracle（§2），用 benchmark 数据决定走哪条路——不盲写 ESPPRC。
2. **Column Contract 层**：定价产出 ≠ master 列——中间必须有 ColumnValidator 验证 elementary 合法性，否则 RMP 可行域被污染（§1）。

**v0.3 核心修正**（相对 v0.2，依据独立 B&P/CG 架构评审）：
- 新增 Column Contract 层（P0）：PricingResult → ColumnCandidate → ColumnValidator → MasterColumn
- 修正 ng-route 语义（P0）：ng-route 输出 = relaxed candidate route，非 master column
- 修正 exact labeling 精确条件：complete state + sound dominance + complete extension（非"支配充分"）
- 删除 reward 术语：solver 层使用 duals（数学语言），不使用业务语言
- Benchmark 增加 pricing gap / candidate validity rate / columns accepted rate

---

## 1. 背景

### 1.1 当前定价子问题

对日期 d，给定合法店集 S_d ⊆ C 和逐店对偶 link_dual_cd（来自 v2 链接行）：

```
min  Σ_{(i,j)∈route} D[i][j]  −  Σ_{c∈route} link_dual_cd
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

| 参数 | 当前 | 需要的 | 差距 |
|---|---|---|---|
| exact_tl | 1.0s | 估计 30-300s/日 | 30-300× |
| 日数 × exact_tl | 23s | 690-6900s | 30-300× |

加大到 30s 可能有效（n ≤ 35 时 CP-SAT 通常能在 30s 内证优）。但：
- 一次完整定价 = 23 日 × 30s = **11.5 分钟**
- 每次节点 CG 需要完整定价 → B&P 仍不实际
- 但对 **root node 单次证明**已足够

---

## 2. 五种定价 Oracle（Pricing Benchmark 候选）

| Oracle | 原理 | 质量 | 速度 | 适用场景 |
|---|---|---|---|---|
| 贪心启发式 | dual 引导贪心插入 | 低（发现≠证明） | 快 | CG 循环内每轮调用 |
| CP-SAT AddCircuit | 全弧布尔 + AddCircuit + 奖励收集 | 精确（n≤35）/ 超时（n>100） | 慢 | n≤35 或 root proof |
| **Exact Labeling** | ESPPRC 前向支配标签 | 精确（条件见 §5） | 取决于支配效率 | 认证模式 |
| **ng-route Labeling** | 限制 visited 集合为邻域 | 近精确（松弛） | 较快 | **生产候选** |
| 2-cycle elimination | 仅消除 2-cycle，不做 elementary | 松弛 | 快 | 下界参考 |

**Benchmark 指标**（按评审修订，含 pricing gap）：

| 指标 | 定义 | 目的 |
|---|---|---|
| 证完率 | 能证明"无负 rc"的日期占比 | 可行性 |
| min rc 精度 | 与全枚举真值差（微型实例） | 正确性 |
| **pricing gap** | exact_min_rc − found_min_rc | 松弛质量损失 |
| 耗时 | 墙钟时间（日级 + 全线累计） | 效率 |
| 列质量 | 产出的负 rc 列数及其 SP 价值 | 有效性 |
| 内存 | 峰值用量 | 可扩展性 |
| **candidate validity rate** | 非法候选占比（ng-route） | 过滤成本 |
| **columns accepted rate** | 经 ColumnValidator 后实际贡献率 | 实际贡献 |

**Benchmark 结果决定走哪条路**：
- 如果 CP-SAT 60s 够 → 不需要 ESPPRC，只需要调参数
- 如果 ng-route 够 → 实现简化版 labeling（不做 elementary）
- 如果只有 exact labeling 够 → 实现完整 ESPPRC

**Benchmark 实例选择**：02/09/11 三线（覆盖最难/中等/最小）+ 自动选择 worst-case（`max(store_count, dual_entropy, distance_diameter)` 最高分日期）。

---

## 3. Column Contract 层（评审 P0 新增；v0.4 补 Normalizer/Certificate/终止契约）

### 3.1 问题

定价 oracle 的输出 ≠ master problem 的变量。ng-route 松弛可能产生**非 elementary 路径**（含重复访问或子回路）——这些如果直接进入 RMP，会改变 master 的可行域，导致后续对偶与最优性证书失效。

### 3.2 流水线
```
PricingResult
       │
       ▼
ColumnCandidate ──► CandidateNormalizer   ← 去重 / elementary repair / 简化（新增 v0.4）
       │
       ▼
ColumnValidator          ← 检查：elementary？合法域？走廊？
       │
       ├── pass ──→ MasterColumn    ← 合法列（含 lineage，§4.5），可进 RMP
       └── fail ──→ discard（记录 rejection reason）
```

### 3.3 数据结构

```python
@dataclass
class ColumnCandidate:
    route: list[int]             # 定价产出的原始路径
    reduced_cost: float          # rc（定价 oracle 计算）
    source: str                  # EXACT / NG / HEURISTIC

@dataclass
class MasterColumn:
    date: date
    route: list[int]             # 已验证合法路径
    km: float                    # 精确重算（有向矩阵）
    is_elementary: bool          # True（通过验证后必然 True）
    source: str
```

**禁止** pricing oracle 直接写 RMP——必须经过 ColumnValidator。

### 3.4 ColumnValidator 检查项与 Normalizer

**discard 不是唯一处置**（评审 P0 修正）：非法候选包含大量定价信息，直接丢弃浪费。流水线在 Validator 前增加 **CandidateNormalizer**：

| Normalizer 操作 | 说明 |
|---|---|
| duplicate removal | 与既有列去重 |
| elementary repair | 去除重复访问店（如 A-B-C-B-D → 投影/重优化） |
| route simplification | 子路径合并 |

Validator 仅对 Normalizer 后仍非法的候选 discard：

| 检查 | 失败处置 |
|---|---|
| elementary（repair 后仍重复） | discard |
| 每店在该日期合同合法 | discard |
| 走廊 | discard |

---

## 4. Pricing API 设计

### 4.1 状态枚举（五值）

```python
from enum import Enum

class PricingStatus(Enum):
    EXACT_NO_COLUMN = "exact_pricing_proven_no_negative_rc"
    EXACT_COLUMN_FOUND = "exact_pricing_found_negative_rc"
    RELAXED_COLUMN_FOUND = "relaxed_pricing_found_negative_rc"
    HEURISTIC_COLUMN_FOUND = "heuristic_pricing_found_negative_rc"
    TIMEOUT_WITH_INCUMBENT = "timed_out_with_best_incumbent_route"
```

### 4.2 结果对象

```python
@dataclass
class PricingResult:
    status: PricingStatus
    # 证书
    lower_bound: float | None      # 该日定价的 LP 下界（仅 EXACT_NO_COLUMN 时非 None）
    best_rc: float | None          # 最优 rc 值
    best_route: list[int] | None   # 最优路线
    # 诊断
    labels_explored: int
    labels_pruned: int
    solve_time_sec: float
```

### 4.2a PricingCertificate 与 CG 终止契约（v0.4 新增，评审 P0）

**核心风险**：生产 CG 用 relaxed/heuristic pricing 时，"没有 accepted 负列" ≠ "没有负 rc 列"——ng-route 漏掉 rc=-2 的列而 validator 丢弃了 rc=-10 的非法候选时，CG 会**假收敛（false convergence）**。

```python
@dataclass
class PricingCertificate:
    has_negative_column: bool
    proof_level: str   # EXACT / RELAXED / HEURISTIC / UNKNOWN

class CGTerminationStatus(Enum):
    RELAXED_NO_CANDIDATE = "relaxed_pricing_found_no_candidate_not_a_proof"
    RELAXED_ONLY_INVALID = "relaxed_candidates_all_invalidated_by_validator"
    EXACT_NO_NEGATIVE_RC = "exact_pricing_proven_no_negative_rc"
    TIMEOUT_UNKNOWN = "timed_out_convergence_state_unknown"
```

**终止契约**：CG 仅允许在 `proof_level == EXACT 且 has_negative_column == False` 时声明收敛；否则只能以 `RELAXED_*` / `TIMEOUT_UNKNOWN` 状态退出——下游据此决定是否触发 exact_pricer 认证（root node 或按需审计）。

### 4.3 双重语义（评审 P0 修正）

**ng-route 的输出是 Candidate Column（候选列），不是 Master Column。** 必须经 CandidateNormalizer → ColumnValidator 验证后才可进 RMP。禁止直接回灌。

### 4.4 证书字段语义（与协议 research_matrix/v1 §8.2 对齐）

| 字段 | 语义 | 非空条件 |
|---|---|---|
| `rmp_lp_value` | 当前池的受限 LP 最优值 + LP 状态 | 总可填 |
| `pool_gap_pct` | 同池同目标下 UB 与 pool LP 的 gap | 需 UB |
| `certified_global_lb` | 完整问题的数学证明有效下界 | 仅 exact pricing 证明成立 |
| `global_gap_pct` | UB 与 certified_global_lb 的 gap | 同上 |

`certified_global_lb = null` 表示"未证明全局下界"，不是 0。

### 4.5 Column Lineage（v0.4 新增，评审 P1）

```python
@dataclass
class ColumnLineage:
    column_id: str
    source_oracle: str        # EXACT / NG / HEURISTIC
    candidate_rc: float       # 定价时 rc
    validated_at: str         # ISO 时间戳
    validator_result: str     # PASS / NORMALIZED / DISCARD
```

每个 MasterColumn 携带 lineage——支撑治理问题"这个优化结果为什么可信？"的证据链。

---

## 5. 双模式架构

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

## 6. Exact Labeling Algorithm 设计（仅 benchmark 确认需要后实施）
### 6.1 精确性条件（评审修正）

精确性来自以下三个条件的**同时满足**，缺一不可：

1. **完整状态表示**：Label 记录完整的 visited 店集（非松弛）
2. **sound dominance**：支配规则保持正确性——被支配标签的最优延展不劣于支配标签
3. **complete extension**：每个可行扩展都被枚举（无遗漏）

不满足全部三条件 = 松弛 labeling（如 ng-route），不能签发全局证书。

### 6.2 核心思想

```
状态（Label）= (目标值 obj, 已访问店集 visited, 当前末尾店 last)
扩展 = last → c ∉ visited
支配 = 同一 last 的标签 L1 支配 L2 当 obj(L1) ≤ obj(L2) 且 visited(L1) ⊆ visited(L2)
```

### 6.3 三个技术前提

| # | 技术点 | 原因 | 注意 |
|---|---|---|---|
| 1 | **Bidirectional labeling** | n=176 单向标签可能指数爆炸 | 双向 meet 需要可行性检查 |
| 2 | **邻居预排序** | 按距离升序 + reward 降序缓存 | **仅用于扩展顺序**，不能用于剪枝（否则破坏精确性） |
| 3 | **强下界**（MST/1-tree bound） | 奖励总和上界太弱 | 需要预计算 MST |

### 6.4 剪枝策略

| 剪枝 | 规则 | 效果 |
|---|---|---|
| 支配 | cost ≤ 且 visited ⊆ 且同 last | 指数级剪枝 |
| 路径长度 | len(visited) ≤ max_daily | 硬截断 |
| 下界 | cost + MST_bound(剩余) ≥ incumbent_rc → 剪 | 需要预计算 MST |
| 奖励阈值 | 剩余 reward 总和 < 最优 | 维护全局 upper bound |

---

## 7. ng-route 松弛（生产候选，语义修正）

### 7.1 为什么 ng-route

Exact ESPPRC 的 visited_set 指数爆炸在 n > 100 时不可避免。ng-route（Baldacci et al. 2011）用大小为 Δ 的邻域集合替代完整 visited 集。

### 7.2 语义（评审 P0 修正）

**ng-route 的输出不是 Column，是 relaxed candidate route。**

正确表述：
> ng-route 输出可能有价值的 relaxed candidate route，经 ColumnValidator 验证 elementary 合法性后才可进 RMP。

### 7.3 与 Exact 的关系

| 维度 | ng-route | exact |
|---|---|---|
| 产出类型 | relaxed candidate route | elementary column |
| 速度 | 较快 | 较慢（或不可行） |
| 质量 | 可能遗漏最优 | 精确（如可行） |
| 用途 | **生产定价** | **认证/审计** |

---

## 8. 排期

| 步骤 | 内容 | 预估 | 前置 |
|---|---|---|---|
| Phase E | 协议字段对齐（已完成） | — | — |
| **Benchmark** | 5 oracle × 3 实例（02/09/11）× 2 预算档 | ~4h | — |
| **分析** | 确定哪条路（调参/简化 labeling/完整 ESPPRC/ng-route） | 分析 | Benchmark |
| **实施** | 选定路线的 runner 接入 | 1-3 天 | 分析定稿 |

---

## 9. 守卫测试

| 测试 | 钉死什么 |
| **CG 终止契约** | relaxed pricing 无候选时终止状态为 RELAXED_*，绝不签发 PROVEN_OPTIMAL |
| **Normalizer repair** | A-B-C-B-D 型重复访问候选经 repair 后合法且不丢高价值列 |
| **Lineage 完整性** | 每个 MasterColumn 可回溯 source/validator_result |
| 微型全枚举 | n=4 店全排列，labeling 最优 == 枚举最优 |
| 支配正确性 | 同 last_store、cost ≤、visited ⊆ → 被支配标签不产生更优解 |
| 合法域 | 非法店不进路径 |
| 走廊 | 路径长度 ∈ [min, max] |
| 确定性 | 同输入两次运行逐位一致 |
| 与 CP-SAT 对照 | 同实例 labeling 最优 ≤ CP-SAT 最优 |
| 上界态 rc | x=1 的变量 rc ≤ 0 合法（非 bug） |
| **端到端正确性**（n≤12） | Monolithic IP == B&P == Exact pricing（三者最优值相等） |
| **ColumnValidator** | 非法候选被正确 discard；合法候选 100% 通过 |

---

## 10. 风险

| 风险 | 缓解 |
|---|---|
| exact labeling 标签爆炸 | benchmark 先行验证；ng-route 备选 |
| ng-route 松弛引入不精确列 | ColumnValidator 过滤；报告松弛 gap |
| max_daily 大导致标签深 | 路径长度截断 + 奖励上界剪枝 |
| OptiCore 仓并发修改 | 与模块剥离计划协调 |
| ESPPRC 实现后仍不能证优（n>100） | ng-route 作为生产方案；exact 仅用于微型审计 |

---

## 11. 评审溯源

### v0.3 修订依据：2026-09-08 独立 B&P/CG 架构评审

| # | 级别 | 发现 | 处置 |
|---|---|---|---|
| 1 | P0 | Column Contract 层缺失（定价直接写 RMP） | 新增 §3 Column Contract 层 |
| 2 | P0 | ng-route 语义过强（"输出负 rc 列"→应为"relaxed candidate route"） | §7 语义修正 |
| 3 | P1 | benchmark 缺 pricing gap 指标 | §2 增加 pricing gap / candidate validity rate / columns accepted rate |
| 4 | P1 | "同 Δ 下 ng 列 ⊇ exact 列"测试表述错误 | 删除；改为 min_rc(ng) ≤ min_rc(exact) 对照 |
| 5 | P1 | 邻居预排序不能用于剪枝（破坏精确性） | §5.3 注明仅扩展顺序 |
| 6 | P1 | exactness 条件非"支配充分"而是三条件同时满足 | §6.1 修正 |
| 7 | P2 | reward 术语从 solver 层删除 | §1.1 改用 link_dual |
| 8 | P2 | 增加 Monolithic IP = B&P = Exact pricing 端到端正确性测试 | §9 测试守卫 |

### v0.2 修订依据：2026-09-08 独立 OR + 架构评审

8 项建议全部采纳：
1. P0 Pricing benchmark 先行 → §2
2. P0 Pricing API 丰富 → §3
3. P1 双模式架构 → §4
4. P1 exact 三技术前提 → §5.2
5. ng-route 重新考虑 → §6
6. reward 符号 → §3.3 改为标准 rc = distance − Σ duals
7. P2 无效反例替换 → §3.4
8. P2 历史证书审计措辞 → §1.2

---

## 12. Pricing Benchmark v1 实测结果（2026-09-08）

Runner: `experiments/pricing_benchmark.py`；对偶源 = bp 根节点 LP（`output/pricing_benchmark/v1/*.json`）。

### 12.1 实例有效性警示

| 线 | 根 LP link dual | 实例有效性 |
|---|---|---|
| 09 | 非零（质量 ~39） | **有效**（唯一真实例） |
| 02/11 | 全为 ~0（退化） | 平凡：raw=km≥0 恒无负列，"PROVEN"无信息量 |

**教训**：warm-start 根池的 LP 对偶在多线上退化。benchmark v2 必须取**真实 CG 迭代中段**的对偶（bp `_solve_node_cg` 若干轮后捕获）。另:OSM 距离矩阵含 1e9 不可达哨兵值，oracle 实现需过滤。

### 12.2 09 线真实实例结果（n=150，min_len=23，max_daily=35）

| Oracle | min rc（60s/120s） | 证明 | 标签数 | 耗时 |
|---|---|---|---|---|
| 贪心 | 无负列发现 | - | - | <1s |
| CP-SAT 60s | **−9.4 ~ −15.5**（发现负列） | FEASIBLE 未证 | - | 60s |
| exact labeling 120s | 未达深度 23 | TIMEOUT_CAPPED | 3.3-3.7×10⁵ | 120s |
| ng-route Δ=8/16 | 未达深度 23 | TIMEOUT_CAPPED | 1.5×10⁶（2-7s 即触顶） | - |
| 2-cycle | 未达深度 23 | TIMEOUT_CAPPED | 3.3-3.7×10⁵ | 120s |

### 12.3 正确性勘误（重大，已修复）

**跨深度支配在 min_len>1 时不 sound**：单店标签 (cnt=1) 支配 2-标签 (cnt=2) 时，复制相同后缀总店数少 1，可跌破 min_len——v1 首版因此假收敛（0.05s "PROVEN"）。修复：支配仅在同 `(last, cnt)` 桶内进行。微型全枚举守卫 60/60 通过。这正是评审 §6.1 "sound dominance" 条款的具体化。

### 12.4 Benchmark v1 决策

1. **精确定价认证在 n≥150/深度 23 上不可行**（朴素 labeling）——评审的不确定性 #2 得到实证答案
2. **生产定价 = CP-SAT**（发现负列能力最强），时限需 ≥60s 或配合贪心做首轮
3. **ng-route BFS 不可用**：广度优先在深度 23 前爆炸，需改 best-first + 完成下界（后续工作）
4. **认证模式开放**：需要更强的支配（ng-深度双桶 + 强完成下界）或分解，列为 v2 研究项

### 12.5 Benchmark v2 实测结果（2026-09-08，真实 CG 中段对偶）

对偶源修复: `--mid-cg` 从真实 CG 迭代捕获（`initial_days=None` 使 warm-start 日历搜索/伪对偶扰动生效——
此前传 `initial_days` 导致池仅 23 列、link dual 全退化为零；09 线修复后 link mass 2024.9）。

| 线 | link mass | CP-SAT 60s min rc | exact/ng/2-cycle (500k 标签帽) |
|---|---|---|---|
| 09 (n=150) | 97.9 | **−71.8 ~ −74.8** | 全部 TIMEOUT_CAPPED，未达深度 23 |
| 02 (n=172) | 71.2 | **−53.0 ~ −55.5** | 全部 TIMEOUT_CAPPED |
| 11 (n=91) | ≈0（中段仍退化） | −7.4 ~ −54.5 | 混合（ng8 EXHAUSTED 612k） |

**v2 结论（强化 v1）**:
1. 真实 CG 对偶下定价难度显著升级: CP-SAT 发现 rc −53~−75 的负列但 60s 无法证明;
   exact labeling 500k 标签仍未枚举到 min_len=23 的深度——**认证问题在当前算法栈下无解**。
2. 生产定价 = CP-SAT（发现能力最强、单调更好）+ 贪心兜底; 终止按 CG 终止契约签 RELAXED_*
   （诚实非证明），B&P 树不剪枝、只做 incumbent 改进。
3. line 11 中段对偶仍退化为零——该线 CG 从不产生链接对偶压力，与其历史行为一致
   （"11 线 lkh3 略优"反常的根源候选），列为独立研究项。
4. 工程教训: 后台长跑必须避免并发写同一 JSON/log（v2 期间两进程并发导致 11 线结果混合来源）。

### 12.6 Benchmark v3：best-first labeling 对照（2026-09-08）

新增 `oracle_labeling_bf`（cost 升序优先队列出栈 + 同 (last,cnt) 桶支配，微型守卫 40/40 与全枚举一致），
对照 BFS 版与 CP-SAT（mid-CG 对偶，09 线 3 日期 / 02 线 3 日期）：

| Oracle | 09 min rc | 02 min rc | elementary | 备注 |
|---|---|---|---|---|
| CP-SAT 60s | −74.1~−74.5 | −52.5~−55.6 | ✓ | **生产发现冠军** |
| bf_exact 120s | −58.9 | 未发现 | ✓ | 深探强于 BFS（BFS 500k 未达深度 23） |
| BFS ng/exact | 未达深度 23 | 未达深度 23 | - | 顺序缺陷实证 |
| **bf_ng8/16** | **−335.8** | **−306.9** | **✗（松弛列）** | 多日同值=奖励环收集；经 ColumnValidator 拒绝/修复 |

**v3 结论**:
1. **best-first 修复了 BFS 的搜索顺序缺陷**——同标签预算下能到达深度 23+ 并发现深负列；
   BFS 版在真实规模上不可用，生产若走 labeling 路线必须 best-first。
2. **bf_ng 的深负值是合法松弛下界**（min_rc(ng) ≤ min_rc(exact)），但作为列会被
   ColumnValidator 拦截（非 elementary）——契约层语义（v0.4 §3）在实践中得到验证。
3. **生产定价最终格局**: CP-SAT（发现 elementary 负列，60s）为主，
   bf_exact 作快速补充；bf_ng 仅作下界参考。认证（证明无负列）在所有路线下仍不可达，
   维持 RELAXED_* 诚实终止。
4. 运维: 后台 nohup 进程在本环境约 10 分钟后被 SIGKILL（前台不受影响）——
   长跑一律前台分线执行。
