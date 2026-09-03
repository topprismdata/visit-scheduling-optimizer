# L6 Projection → Solver 集成契约

**Document ID:** TOPPRISM-L6-SOLVER-INTEGRATION-CONTRACT-v1_0
**Version:** v1.0-draft
**Date:** 2026-08-27
**Status:** **DESIGN ONLY** — 待 Phase 1 求解器集成时实现

**关联:**
- svde 侧: `PlannerStateProjection` (Canonical Types §34) / `PlannerStateProjectionCompiler` (planner_projection.py)
- algos 侧: `solve_time_cg(n, T, t0, svc, freq, ...)` (solver.py) / `PlanningPolicy` (policy.py)
- 数据契约: `PlanVersion` / `PlannedVisit` / `DecisionEvidence` (planning.py)

---

## 一、为什么需要这个契约

当前两个系统各自演进：

| 层 | 输出 | 消费者 |
|---|---|---|
| L6 PlannerStateProjection | `nodes, travel_cost_matrix, candidate_pattern_space, daily_stop_capacity` | 未连接（MVP 未使用） |
| algos PVRP solver | `n, T, t0, svc, freq, days, daily_cap` | 合成示例、研究证据 |

没有适配器，L6 投影无法成为求解器的输入，求解器输出也无法成为 L7 决策引擎的输入。

---

## 二、数据类型映射

| PlannerStateProjection 字段 | 求解器输入 | 转换规则 |
|---|---|---|
| `nodes: Tuple[PlannerNodeTopology, ...]` | `n: int` | `len(nodes)` |
| `nodes[].service_duration_min` | `svc: Sequence[float]` | `[n.service_duration_min for n in nodes]` |
| `travel_cost_matrix` | `T: list[list[float]]` | frozen Tuple → list (无精度损失) |
| `time_slots_count` | `days: int` | 直接映射 |
| `daily_stop_capacity` | `max_visits_per_day` | 映射到 `PlanningPolicy.max_visits_per_day` |
| `daily_workload_budget_min` | `daily_cap: float` | 映射到 `PlanningPolicy.max_work_minutes_per_day` |
| `candidate_pattern_space` 派生 | `freq: list[int]` | 模式空间推导频次（见 §三） |
| `locked_commitments_mask` | `locked_visits` | 映射到 `PlanVersion` 的 `is_locked` 标志 |

---

## 三、频次推导

`PlannerStateProjection` 不直接包含 `freq[]`，而是通过 `candidate_pattern_space` 间接表达。

**推导规则:**
```python
def derive_freq(projection: PlannerStateProjection) -> list[int]:
    """从 candidate_pattern_space 推导每个客户的目标月频次。"""
    freq = [0] * len(projection.nodes)
    for node_idx, patterns in projection.candidate_pattern_space.items():
        # 每个 pattern 是 (w, k) 的元组列表 — 代表该客户在规划期内的拜访次数
        # 方式一: 取最长 pattern 的长度
        max_pattern_len = max(len(p) for p in patterns) if patterns else 0
        freq[node_idx] = max_pattern_len
    return freq
```

**或显式传入:** `ProjectionCompilationRequest` 增加 `freq: Sequence[int] | None` 字段，显式传入时跳过推导。

---

## 四、适配器接口

```python
@dataclass(frozen=True)
class ProjectionToSolverInput:
    """L6 投影 → 求解器输入的适配结果 (frozen, 可审计)。"""
    projection_id: str
    target_rep_id: str
    n_customers: int
    travel_cost_matrix: tuple[tuple[float, ...], ...]
    service_times: tuple[float, ...]
    freq: tuple[int, ...]
    horizon_days: int
    locked_visits: tuple[tuple[int, int], ...]  # (customer_idx, day_idx)
    # 派生策略
    policy: PlanningPolicy


def adapt_projection(
    projection: PlannerStateProjection,
    freq: Sequence[int] | None = None,
    locked_visits: set[tuple[int, int]] | None = None,
    **policy_overrides,
) -> ProjectionToSolverInput:
    """PlannerStateProjection → ProjectionToSolverInput 适配。

    Args:
        projection: L6 编译的投影。
        freq: 显式频次列表 (None = 从 candidate_pattern_space 推导)。
        locked_visits: 已锁定 (customer_idx, day_idx) 集合。
        **policy_overrides: 覆盖 PlanningPolicy 默认值 (如 max_visits_per_day)。

    Returns:
        ProjectionToSolverInput (frozen, 可审计)。
    """
    ...
```

---

## 五、求解器输出 → PlanVersion 适配

```python
def adapt_solution_to_plan(
    solver_input: ProjectionToSolverInput,
    solver_output: tuple[list | None, float, str, dict],
    solver_type: str,
    run_id: str,
    policy: PlanningPolicy,
    existing_plan: PlanVersion | None = None,
) -> tuple[PlanVersion, list[PlannedVisit], DecisionEvidence]:
    """求解器输出 → PlanVersion + PlannedVisit[] + DecisionEvidence。

    Args:
        solver_input: 适配后的求解器输入。
        solver_output: solver.solve_time_cg 的返回值 (assigns, total, status, stats)。
        solver_type: "CG" / "ALNS" / "CP-SAT"。
        run_id: 求解运行标识。
        policy: 使用的约束策略。
        existing_plan: 已有计划 (用于增量重算的版本号递增)。

    Returns:
        (PlanVersion, PlannedVisit[], DecisionEvidence) — 可审计的三元组。
    """
    ...
```

---

## 六、验收标准

- [ ] `adapt_projection` 将 `PlannerStateProjection` 正确转换为 `solve_time_cg` 的输入参数
- [ ] 频次推导与显式传入两种方式均通过测试
- [ ] `adapt_solution_to_plan` 将求解器输出包装为 `PlanVersion` + `PlannedVisit[]` + `DecisionEvidence`
- [ ] 两种适配均不修改原始数据（frozen dataclass 不变性）
- [ ] 适配器运行在仁军 2026-06 真实数据上（`PlannerStateProjectionCompiler` → `solve_time_cg` → `PlanVersion`）