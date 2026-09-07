# ALNS v4（稳定性权衡精修器）

> 类别：元启发式（增量重优化，加权单目标） | 实现：`algos/alns_v4.py` | 生产定位：**月度微调**（改 1~16 家店的场景）
> ⚠ **P0 已知缺陷（2026-09-07 评审，修复排期中）**：`same_weekday_only=True` 只保证星期几不换，**不保证双周（κ=双周+相位）合同的相位合法**——双周店跨周同星期移动即破相位合同；当前输出只过 `check_freq`，未过 `check_contract`。修复方向：移动候选改由 VisitIR `contract_slot_dates` 生成，输出加 `check_contract` 闸。修复前**不得用于含双周合同客户的月度微调生产**。

## 它解决什么

全量重规划之外的高频场景：**以现有计划为锚点做最小改动**。任意算法输出 X（或历史计划）都可作起点，在"里程"、"改动成本（稳定性 λ）"、"每日工作量均衡度（μ）"三者间做**加权权衡**：

```
min  J = 里程 + λ · Δ(改动店数) + μ · 每日拜访量方差（Var，Variance）
```

- **日内顺序优化免费**（Δ=0、Var=0，只要降里程就采纳）——与两层架构一致。
- **λ 旋钮（稳定性）**：每挪 1 家店的最低里程收益门槛（km/店）。λ 大 → 贴紧现计划。
- **μ 旋钮（均衡度）**：每日拜访量方差惩罚（km/var）。μ 大 → 强行平摊店数。
- `max_changes`：改动店数硬上限（模式 B）；`same_weekday_only=True` 只允许同星期几互挪。

**命名说明（2026-09-07 评审）**：这是加权单目标（weighted-sum）启发式精修，**不宣称"帕累托最优"**——加权标量化的 SA 求解既不精确，也覆盖不了全部非支配解。"帕累托"留给真正维护非支配解档案的 `mo_alns_v4` 变体（其档案机制待核）。

## 输入 / 输出

- 输入：`incumbent`（锚点 X⁰，默认 SRP 现计划）、`start`（起点解，默认=锚点）、`lam/mu/max_changes/same_weekday_only`。
- 输出：`AlgoResult(days, km, metadata{plan_km, start_km, moved 数, var})`。

## 机制

```
two_opt 暖启动（日内免费优化）→ moved 集合计算（相对锚点的日期集差异）
SA 主循环（T0·(Tend/T0)^el 指数降温）三算子：
  oropt: 日内 two_opt 微调（免费）
  shift: 跨日单店移动（worst_edge 选店 + best_insert 插入）
  swap:  两日间交换
  每步按 J 增量做自适应权重更新与退火接受
```

## 复杂度与预算

- 实测（PERFORMANCE_BENCHMARK）：30s 预算 → 30.0s 交付；预算 5-10s 可拿到与 30s 档接近的解（接近程度待专项标定）。
- 定位 = "按预算交付"，不会自动提前结束。

## 已知边界与陷阱

1. **P0 缺陷见文档头**：双周相位不保证（修复排期中）。
2. 与 R2′ 的关系：`same_weekday_only=True` ≠ R2′（R2′ 允许整店换星期几，v4 该开关禁止换）——微调场景语义，勿与主矩阵口径混用。
3. `check_freq` 在内（不破坏拜访次数）；`check_contract`/`check_capacity` 不在循环内。
4. 加权求和的机制局限：非支配解可能被标量化掩盖；需要真多目标时用 `mo_alns_v4`。

## 引用论文

- Groër, Golden, Wasil (2009)：Consistent VRP（一致性 = λ 旋钮的业务原型）。
- Ritzinger, Puchinger, Hartl (2016)：动态/随机 VRP 与重优化综述（增量重优化定位）。
- Kirkpatrick et al. (1983)：SA 骨架。
- 加权求和标量化的取舍（supported/unsupported 非支配解）：多目标优化通论（Ehrgott, *Multicriteria Optimization*, Springer）。

## 相关文件与测试

- `algos/alns_v4.py`；变体 `algos/mo_alns_v4.py`
- 报告：`docs/benchmarks/V4_PARETO_REPORT.md`（其中"帕累托最优"表述随本次评审降级为"加权权衡"）
