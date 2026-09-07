# ALNS v4（稳定化 / 增量重优化 / 帕累托精修器）

> 类别：元启发式（增量重优化） | 实现：`algos/alns_v4.py` | 生产定位：**月度微调**（改 1~16 家店的场景），矩阵身份：微调层

## 它解决什么

全量重规划之外的高频场景：**以现有计划为锚点做最小改动**。任意算法输出 X（或历史计划）都可作起点，在"里程"、"改动成本（稳定性 λ）"、"每日工作量均衡度（μ）"三者间求帕累托最优。

## 目标函数

```
min  J = 里程 + λ · Δ(改动店数) + μ · Var(每日拜访量)
```

- **日内顺序优化免费**（Δ=0、Var=0，只要降里程就采纳）——与两层架构一致。
- **λ 旋钮（稳定性）**：每挪 1 家店的最低里程收益门槛（km/店）。λ 大 → 贴紧现计划。
- **μ 旋钮（均衡度）**：每日拜访量方差惩罚（km/var）。μ 大 → 强行平摊店数。
- `max_changes`：改动店数硬上限（模式 B）；`same_weekday_only=True` 只允许同星期几互挪。

## 输入 / 输出

- 输入：`incumbent`（锚点 X⁰，默认 SRP 现计划）、`start`（起点解，默认=锚点，可为任意算法产出）、`lam/mu/max_changes`。
- 输出：`AlgoResult(days, km, metadata{plan_km, start_km, moved 数, var})`。

## 机制

```
two_opt 暖启动（日内免费优化） → moved 集合计算（相对锚点的日期集差异）
主循环 SA（复用 v3 骨架：worst/cross/segment/random + 自适应权重 + 分段降温）
  估价 J = km + λ·|moved| + μ·Var；接受准则基于 J
```

## 复杂度与预算

- 实测（PERFORMANCE_BENCHMARK）：30s 预算 → 30.0s 交付；预算 5-10s 可拿到与 30s 档基本同水平的解。
- 定位 = "按预算交付"，不会自动提前结束。

## 已知边界与陷阱

1. **λ 门槛式设计的历史缺陷**（V4_PARETO_REPORT §4）：从原始计划出发的 λ 门槛曾结构性失效 → v4 已重设计为"以 v3 结果为基准、在其邻域内演化"。Clustered TSP 与跨区率目标（f4）一并废弃。
2. 与 R2′ 的关系：`same_weekday_only=True` 近似 R2′ 但不完全等价（R2′ 允许整店换星期几，v4 的该开关禁止换）——微调场景语义，勿与主矩阵口径混用。
3. `check_freq` 频次校验在内（微调不破坏拜访次数）。

## 引用论文

- Groër, Golden, Wasil (2009)：Consistent VRP（一致性 = λ 旋钮的业务原型）。
- Ritzinger, Puchinger, Hartl (2016)：动态/随机 VRP 与重优化综述（增量重优化定位）。
- Kirkpatrick et al. (1983)：SA 骨架。

## 相关文件与测试

- `algos/alns_v4.py`；变体 `algos/mo_alns_v4.py`（多目标版）
- 报告：`docs/benchmarks/V4_PARETO_REPORT.md`
