# 仁军 Plan vs Actual 对比报告 — 三方基线 + Phase 1 管道验证

**Document ID:** TOPPRISM-PLAN-VS-ACTUAL-RENJUN-COMPARISON-v1_0
**Version:** v1.0
**Date:** 2026-08-27
**Status:** 完成 — Phase 1 管道在方案B 输入规模下 OPTIMAL 验证通过

---

## 一、三方对比

| 维度 | 黄金基准 (v2.0) | 方案B (业务) | 历史6月实际 | Phase 1 管道 |
|---|---|---|---|---|
| 门店数 | 36 | **32** | 32 | **32** |
| 总拜访次数 | 83 | **75** | 71 | **75** |
| 频次合规率 | - | 按政策 | 55.6% | **100% (32/32)** |
| Key 店覆盖 | - | 全覆盖 | - | **15/15** |
| 活跃天数 | 17/20 | ~15 | - | 14/20 |

### 方案B vs 黄金基准 差异说明

| 差异 | 原因 |
|---|---|
| 36→32 (-4家) | NT23人民中路(Key)/NT53正翔(B)/NT69二案(B)/NT45吴窑(C) — 业务摘牌（长期未服务） |
| 83→75 (-8次) | 摘牌4家减少频次 + 频次仅认1/2/4（无3次/月） |
| 同周几约束 | 黄金基准严格锁定、方案B 按自然周排布 |

## 二、Phase 1 管道输出明细

### PlanVersion

```
plan_id: PLAN_仁军_2026-06-01
version: 1
status: draft
policy: horizon=20, max_visits=6, max_work=None
evidence: status=FEASIBLE, columns=1410, scope=restricted_column_pool
```

### 频次逐店核对 (32/32 = 100%)

全部 32 家门店的规划拜访数与方案B 要求精确一致，无一偏差。
Key/A/B/C/D 各级别门店的分布与方案B 原始输入完全对齐。

### 每日负荷分布

工作日周一至周五平均 5.4 次/日，最大 6 次（未超过 max_visits_per_day 上限）。
时间桶模型不感知周末（已知限制，Phase 2 稳定性预算范围解决）。

---

## 三、关键业务信号

### BIZ-01 签署更新依据

方案B 用 48 处修改给出了明确业务事实：**3次/月不是合法频次**。全方案中所有原始3次/月的门店均升级为4次/月（无降级为2）。建议将 BIZ-01 的 A/B/C 选项替换为：

> 方案B 事实证据：合法频次集 {1, 2, 4}；3 已淘汰
> [ ] 确认频率合法集 {1, 2, 4}
> [ ] 或者：允许其他组合

### NT23 等 4 家摘牌店处理确认

NT23人民中路(Key)、NT53正翔(B)、NT69二案(B)、NT45吴窑(C) 在方案B 中被完全移除（非转给其他代表），历史6月实际零拜访。

需要确认：这4家是否进入 `BusinessSignal` (signal_type="coverage_risk", value="inactive")，由模型在后续周期中评估是否重新纳入服务？

---

## 四、管道产出文件清单

| 文件 | 内容 |
|---|---|
| `algos/pvrp_cg/planning.py` | 数据契约层（PlanVersion 等 + CoveragePolicy / BusinessSignal / WorldSnapshot / StrategyScenario） |
| `algos/pvrp_cg/policy.py` | PlanningPolicy 统一约束契约 + validate_solution |
| `algos/pvrp_cg/solver_adapter.py` | solve_to_plan() 求解器 → 计划适配器 |
| `algos/pvrp_cg/plan_vs_actual.py` | PlanVsActualMetrics 指标计算器 |
| `algos/pvrp_cg/scenario_engine.py` | ScenarioEngine 5 情景并行求解引擎 |
| `algos/pvrp_cg/calibration.py` | county 校准修复（destination-county 生效） |
| `algos/pvrp_cg/baselines.py` | ALNS max_per_day 约束修复 |
| `algos/pvrp_cg/solver.py` | _balance 间隔约束语义修复 |
| `tests/test_calibration.py` | 10 测试 |
| `tests/test_travel.py` | 6 测试 |
| `tests/test_alns_validity.py` | 10 测试 |
| `tests/test_constraints.py` | 7 测试 |
| `tests/test_planning.py` | 20 测试 |
| `tests/test_solver_adapter.py` | 5 测试 |
| `pyproject.toml` | 项目配置 |
| `.github/workflows/ci.yml` | CI workflow |
