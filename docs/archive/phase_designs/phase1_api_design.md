# Phase 1 API 设计 (Human-led Planning / Plan vs Actual)

> 基于 P0 修复后的求解器与 Phase 1 数据契约，设计可执行的 Plan vs Actual 管道。
> 日期：2026-08-27
> 关联：`algos/pvrp_cg/planning.py` / `algos/pvrp_cg/plan_vs_actual.py` / `algos/pvrp_cg/policy.py`

## 架构

```text
求解器输出 (solve_time_cg / solve_distance_cg / ALNS)
    │
    ▼
SolverAdapter ───→ PlanVersion (新版本)
    │                     │
    │                     ├── PlannedVisit[]
    │                     ├── DecisionEvidence
    │                     └── policy_version → PlanningPolicy
    │
    ▼
Execution (外部系统)
    │
    ▼
ActualVisit[] ←─── GPS / 打卡 / ERP 反馈
    │
    ▼
PlanVsActualMetrics ───→ 经理 Dashboard
    │
    ▼
ManualOverride ───→ 触发局部重算 → 新 PlanVersion
```

## 核心接口

### 1. SolverAdapter — 求解器 → PlanVersion 适配器

```python
@dataclass(frozen=True)
class SolverRun:
    run_id: str
    solver_type: str              # "CG" / "ALNS" / "CP-SAT"
    policy: PlanningPolicy
    plan_id: str
    representative_id: str
    status: str
    evidence: DecisionEvidence

def solve_to_plan(
    *,
    solver_type: str = "CG",
    lats: Sequence[float],
    lons: Sequence[float],
    depot: tuple[float, float],
    freq: Sequence[int],
    svc: Sequence[float],
    policy: PlanningPolicy,
    segments: Sequence | None = None,
    counties: Sequence[str] | None = None,
    overrides: list[ManualOverride] | None = None,
    locked_visits: set[tuple[int, int]] | None = None,
    existing_plan: PlanVersion | None = None,
    **solver_kwargs,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解 → PlanVersion 一步完成。
    
    - 无 existing_plan: 全新求解，全部客户按 policy 排程
    - 有 existing_plan + locked_visits: 增量/局部重算，锁定客户不移动
    - 有 overrides: 人工调整后的二次求解（保持调整、优化其余）
    """
```

### 2. PlanExecution — 执行回放管道

```python
def replay_plan(
    plan: PlanVersion,
    planned_visits: list[PlannedVisit],
    actual_visits: list[ActualVisit],
    overrides: list[ManualOverride] | None = None,
    evidence: DecisionEvidence | None = None,
) -> PlanVsActualMetrics:
    """Plan vs Actual 全量指标计算。
    
    已实现为 `plan_vs_actual.compute_plan_vs_actual()`。
    """
```

### 3. 增量重算

```python
def incremental_replan(
    existing_plan: PlanVersion,
    new_actuals: list[ActualVisit],
    overrides: list[ManualOverride],
    policy: PlanningPolicy,
    **solver_kwargs,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """基于执行反馈的增量重算 → 新版本 PlanVersion@v+1。
    
    - 已完成拜访固定
    - 已锁定拜访不移动
    - 未受影响的客户尽量保持原日期
    - 新版本号 = existing_plan.version + 1
    """
```

## 验收标准 (Phase 1)

- [ ] 求解器输出可被 `solve_to_plan` 包装为 `PlanVersion` + `PlannedVisit[]`
- [ ] `compute_plan_vs_actual` 在真实历史数据上可运行（仁军 2026-06）
- [ ] 人工调整不覆盖原始求解结果（原始值在 PlanVersion 中可追溯）
- [ ] 所有汇报指标都能追溯到输入、策略和求解版本
- [ ] 增量重算产生的新版本号 = v+1，不覆盖旧版本