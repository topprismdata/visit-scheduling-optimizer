# Phase 2 设计：AI-assisted Decision / Resource Effectiveness

> 从"减少里程和工时"升级为"把有限资源投向更有价值的机会"
> 日期：2026-08-27
> 证据源：Palantir Foundry Scenarios (深读) / 优化建议 §4 / arXiv:2411.14499 世界模型综述

## 一、核心设计原则

### 1.1 动态价值模型（学习产出，非静态字段）

客户价值不是预设的静态标签，而是从执行结果中持续学习的动态模型。

**输入信号：**
- 拜访完成率（Plan vs Actual 偏差）
- 服务时长合规性（实际 vs 估计偏差）
- 频次遵守率（policy 要求的频率 vs 实际执行）
- 业务结果（品类配合度、补货完成率、陈列合规 — 来自 `MerchandisingComplianceFact`）
- 历史趋势（以上指标随时间的变化方向）

**输出：**
- `customer_value_score: float` (0-1) — 归一化价值评分
- `value_confidence: float` (0-1) — 模型置信度（样本量/时效性）
- `value_components: dict` — 可解释的各维度贡献

### 1.2 动态优先级（加权，非词典序）

优先级 = 价值评分 × 动态权重。权重来自优化目标的反向传播，不是硬编码的词典序。

**权重学习：**
- 初始权重：均匀分布（所有维度等权）
- 滚动优化：每轮执行后，对比 Plan vs Actual 的偏差分布，调整权重使偏差最小的维度获得更高权重
- 约束：权重变化幅度受稳定性预算限制（避免每轮剧烈波动）

### 1.3 情景比较（Palantir Scenarios 模式）

```text
Baseline (当前业务计划)
    │
    ├── Efficiency First (最小化里程/工时, 权重=里程优先)
    ├── Value First (最大化高价值覆盖, 权重=价值优先)
    ├── Stability First (最小化变更, 权重=偏差最小化)
    ├── Balanced (平衡模式)
    └── Manager-adjusted (经理手动调整)
```

每个情景输出：
- 价值覆盖
- 总里程
- 总工时
- 活跃工作日
- 频次合规
- 每日容量违例
- 负荷公平
- 相对当前计划的变更数量
- 被影响的高优先级客户

---

## 二、与现有架构的关系

### 2.1 PlanningPolicy 扩展

```python
@dataclass(frozen=True)
class DynamicPlanningPolicy(PlanningPolicy):
    # 价值层
    value_scores: dict[int, float] = {}         # customer_idx → score [0,1]
    value_confidence: dict[int, float] = {}     # customer_idx → confidence [0,1]
    priority_weights: dict[str, float] = {}     # 目标维度 → 权重
    # 稳定性层
    stability_budget: int = 0                    # 最多改变的客户数
    change_penalty: float = 0.0                # 变更惩罚系数
    freeze_committed: bool = True               # 已确认拜访是否冻结
```

### 2.2 Solver 目标函数扩展

当前 `solve_time_cg` 最小化总工时。Phase 2 扩展为：

```python
def solve_weighted_cg(
    n, T, t0, svc, freq, days, daily_cap, value_scores, policy,
    time_limit=30,
) -> tuple:
    # 目标: 最小化 (里程+工时) - λ × 价值覆盖
    # 其中 λ 由 dynamic_priority_weights 决定
```

### 2.3 Scenario Engine

基于 Palantir Scenarios 模式：

```python
@dataclass(frozen=True)
class ScenarioRun:
    scenario_id: str
    label: str                    # "Efficiency First" / "Value First" / ...
    policy: DynamicPlanningPolicy
    solver_input: ProjectionToSolverInput
    result: tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]
    metrics: PlanVsActualMetrics  # 对比基线

def run_scenarios(
    base_policy: DynamicPlanningPolicy,
    scenario_configs: list[ScenarioConfig],
    solver_input: ProjectionToSolverInput,
) -> tuple[ScenarioRun, ...]:
    """并行运行多个情景, 返回可比较的 ScenarioRun 列表。"""
    ...
```

---

## 三、验收标准

- [ ] 动态价值模型在仁军 2026-06 数据上可训练（从 ActualVisit 中提取信号）
- [ ] `solve_weighted_cg` 在相同输入下，价值导向 vs 效率导向产出不同排程
- [ ] 5 种情景可并行求解并输出对比报告
- [ ] 经理可锁定特定客户，触发局部重算后锁定客户不移动
- [ ] 推荐采纳率和人工修改率可被持续统计