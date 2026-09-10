# BP 分层定价体系设计

> **状态**：设计定稿 · 2026-09-09 · 方案 A（分层定价）已确认
> **前置**：ESPPRC_PRICING_DESIGN_v0.4.md、本周全部实验数据

---

## 1. 目标

| 目标 | 手段 | 对应 Tier |
|---|---|---|
| 找更好的方案 | GRASP 启发式 + ALNS 列注入 | Tier 0 + 1 |
| ALNS + BP 协作 | ALNS 产出列 → BP 列池共享 | Tier 0 |
| 证明最优性 | ng-route 标注（后续实现） | Tier 2 |

---

## 2. 分层定价流程

```
CG 迭代开始
  │
  ├─ Tier 0: ALNS 列注入（一次性, warm start）
  │    ALNS 的 23 天方案 → 转为列 → 注入列池
  │
  ├─ Tier 1: GRASP 启发式定价（每轮 CG 调用）
  │    贪心插入 + 随机重启 + 2-opt → 找负 rc 列
  │    找到 → 加入列池, 继续下一轮 CG
  │    找不到 → 触发 Tier 2
  │
  ├─ Tier 2: ng-route 标注（后续实现）
  │    精确标注 → 证明无负 rc 列
  │    证明成功 → EXACT_NO_NEGATIVE_RC → CG 收敛
  │    证明失败 → 找到负 rc 列, 加入列池
  │
  └─ 终止: CG 终止契约 (§4.2a)
       EXACT_NO_NEGATIVE_RC → PROVEN_OPTIMAL
       其他 → BOUND_HEURISTIC (诚实报告)
```

---

## 3. 各层设计

### Tier 0: ALNS 列注入

- R2-ALNS 跑完后，将 `best_routes` 转为列格式 `(date, route, km)`
- 通过 `add_columns(cols, source="ALNS")` 注入 BP 列池
- 走 ColumnValidator（频次/走廊/结构检查）
- **实现**：`svc/stages/solve.py` 的 `solve_line()` 调用 ALNS 后将结果传给 BP

### Tier 1: GRASP 启发式定价

- 现有 `_price_heuristic`（贪心插入）+ `_price_grasp`（随机贪心 + 2-opt）
- **改进**：
  - GRASP 迭代从 60 → 200/店
  - 2-opt 邻域扩展（加入 or-opt 移动）
  - 多起点（从 top-5 dual 值店出发）

### Tier 2: ng-route 标注（后续）

- Feillet et al. (2004) ESPPRC + Baldacci et al. (2011) ng-route 松弛
- 状态 = (current_node, ng_set, visited_count, cost)
- 支配规则：同 (node, ng_set, count) 内 cost ≤ → 支配
- 邻域大小 Δ = 8（可调）
- 输出：精确 min rc 或 PROVEN 无负列

---

## 4. 与现有代码的集成

| 组件 | 现有 | 修改 |
|---|---|---|
| `algos/r2_alns.py` | df85da0 版本 | 不改动 |
| `algos/branch_and_price.py` | 合同耦合版 | 解除 legal 限制，加 Tier 调度 |
| `svc/stages/solve.py` | 独立 ALNS | 加 ALNS→BP 列注入 |
| `algos/pricing_contract.py` | ColumnValidator | 保留，验证所有来源的列 |
| `tests/` | 已有守卫 | 加 Tier 切换测试 |

---

## 5. 验证标准

| 指标 | Tier 0+1 后 | Tier 2 后 |
|---|---|---|
| 09 线 km | ≤ 312 | ≤ 312 |
| 09 线 root_lb | ≠ None | ≠ None 且 gap ≤ 5% |
| 10 线 FEASIBLE | ≥ 8/10 | ≥ 8/10 |
| CG 收敛率 | ≥ 30% | ≥ 80% |

---

## 6. 排期

| 步骤 | 内容 | 工作量 |
|---|---|---|
| S1 | ALNS→BP 列注入（Tier 0） | 2h |
| S2 | GRASP 改进（Tier 1） | 2h |
| S3 | 09 线验证 + 对比 | 1h |
| S4 | 全量 10 线 | 4h |
| S5 | ng-route 标注（Tier 2，后续） | 1-2 周 |
