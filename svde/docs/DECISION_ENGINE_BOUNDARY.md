# Decision Engine Boundary

**Document ID:** TOPPRISM-DE-BOUNDARY-v1.0  
**Version:** v1.0-draft.5.2 (Preflight Final Synced)  
**Date:** 2026-08-24  
**Status:** **MANDATORY SUBSYSTEM BOUNDARY DEFINITION**

---

## 一、Decision Engine 包含与不包含

### ✅ Decision Engine **内部必须拥有**

```
Business Intent Diagnosis   — 业务意图诊断
Capability Orchestration     — 能力编排与路由
Candidate Generation        — 候选方案生成
Planning / Optimization     — 规划与求解
Trade-off Evaluation        — 多目标权衡
Physical / Business / Semantic Audit — 三维独立审计
Human Approval              — HITL 人工审批
Execution Orchestration     — 执行编排
Execution Feedback Publisher — 执行反馈发布
Decision Artifact Storage   — 决策产物持久化
```

### ❌ Decision Engine **严禁包含**

```
WorldState Snapshot Instance — 严禁持有（仅持有 L6 Projection 局部视图）
State Transition Logic      — 严禁内嵌（必须调用 L3 WorldModel）
Scenario Branch State        — 严禁持有（必须查询 L5 WorldModel）
Business Dynamics Definition — 严禁定义（必须从 L4 WorldModel 读取）
Customer Master Data Storage — 严禁存储（必须从 L4 WorldModel 查询）
```

---

## 二、Decision Engine 不变量

1. **不可直接修改 WorldState**: 任何对状态的变更必须通过 WorldModel 暴露的接口；
2. **不可持有策略版本**: 策略版本是 WorldModel 的事实，Decision Engine 仅消费；
3. **不可绕过三维审计**: 所有候选方案必须流经 Physical/Business/Semantic 三维审计；
4. **不可省略人工审批**: 凡涉及 `REQUIRED` 履约级别或敏感承诺的决策必须通过审批；
5. **不可丢失执行反馈**: 已下发的 DecisionArtifact 必须接受 ExecutionFeedback 并写回 WorldModel。

---

## 三、World Model 与 Decision Engine 在四要素上的严格分离

| 概念类型 | 归属 | 定义 | 业务示例 |
| :--- | :--- | :--- | :--- |
| **事实约束 (Fact Constraints)** | **World Model (L2/L3)** | 物理与业务规则的事实声明 | "客户每月必须拜访 3 次"（这是 CadencePolicy 事实） |
| **业务目标 (Business Objectives)** | **World Model (L2/L3)** | 表达"应该怎样"的定性目标 | "距离和覆盖哪个优先"（这是 Policy 目标集） |
| **可行动作空间 (Feasible Action Space)** | **World Model (L2/L3)** | 允许发生的动作枚举 | "改派客户"是否允许（这是 DeferralPolicy 配额约束） |
| **目标权衡与选择 (Trade-off Evaluation)** | **Decision Engine (L7)** | 如何选择动作与目标 | "这次是否选择改派"（这是 L7 的 Trade-off Evaluation） |

---

## 四、Decision Engine 内部 Pipeline (强制顺序)

```
1. Intent Diagnosis
   ↓
2. Capability Orchestration (TERRITORIAL_ALIGNMENT / PERIODIC_VISIT_PLANNING / DAILY_ROUTE_OPTIMIZATION)
   ↓
3. compile_planner_projection(context, snapshot_id, intent, partial_auth)
   ↓ (接收 L6 PlannerStateProjection 纯数学载荷)
4. OR Solver (CP-SAT / Held-Karp / PyVRP)
   ↓ (返回原始序列)
5. Trade-off Evaluation (Lexicographic objectives)
   ↓
6. Three-Dimensional Audit (Physical / Business / Semantic)
   ↓
7. Human Approval Gate (if required)
   ↓
8. DecisionArtifact Storage (Immutable)
   ↓
9. Execution Orchestration (SFA/CRM dispatch)
   ↓
10. Execution Feedback Loop (writes to L4 WorldState)
```

---

## 五、Decision Engine 与 WorldModel 的接口契约

```
WorldModel → DecisionEngine (Read-Only Projections / Views):
- PlannerStateProjection (L6)
- ReadOnlyWorldStateView (L4)
- FrozenCustomerUniverseView (L4)
- OperationalVisitPolicy (L4 Tuple)
- OwnershipConflictRecord (L4 Tuple)

DecisionEngine → WorldModel (Mutations / Requests):
- request_transition(context, workflow, transition_request) → returns TransitionResult
- submit_execution_feedback(context, feedback) → returns ExecutionFeedbackReceipt
- request_scenario_rollout(context, base_snapshot_id, intent, perturbations, simulation_time) → returns ScenarioResult
```

---

## 六、当前代码归位

| 当前代码 | 现行位置 | 必须归位 |
| :--- | :--- | :--- |
| `engine/decision_pipeline.py` | 误归位 SVDE | 必须移至 L7 `decision_engine/pipeline/` |
| `engine/periodic_pvrp_solver.py` | 误归位 SVDE | 降级为 Domain Solver，位于 SVDE Domain 内部 |
| `diagnostics/plan_auditor.py` | 误归位 SVDE | 必须移至 L7 决策引擎命名空间 |
| `bridge.py` | 适配层 | 保持（WorldModel ↔ DecisionEngine 适配器） |

---

## 七、严禁跨越 Decision Engine 边界的行为

1. **不允许** DecisionEngine 直接修改 WorldState 实例（必须通过接口请求修改）；
2. **不允许** DecisionEngine 在 WorldState 之上"伪造"事件（必须通过 L3 接口生成 StateTransitionRecord）；
3. **不允许** DecisionEngine 内嵌状态转移守卫（守卫属于 L3 WorldModel）；
4. **不允许** DecisionEngine 内嵌 BaseInstance Domain Specific 求解算法（必须作为 Domain Solver 调用）；
5. **不允许** DecisionEngine 跳过三维审计直接发布 DecisionArtifact。

---

## 八、调用方契约示例 (Canonical API)

```python
# ✅ 允许的调用方式 (通过 Canonical API 接口)
from prism_ontology.world_model.planner_projection import compile_planner_projection
from prism_ontology.world_model import transition_engine
from prism_ontology.engine.svde_solver import UniversalPeriodicPVRPSolver  # Domain Solver

# 1. 编译纯数学投影
projection: PlannerStateProjection = compile_planner_projection(
    context=context,
    snapshot_id=snapshot_id,
    intent=intent,
    partial_auth=partial_auth
)

# 2. 求解候选方案
candidate_plan = UniversalPeriodicPVRPSolver.solve(projection)

# 3. 三维独立审计
audit_report = ThreeDimensionalPlanAuditor.audit(candidate_plan, worldstate_view)

# 4. 提交状态转移
result: TransitionResult = worldmodel.request_transition(
    context=context,
    workflow=workflow,
    transition_request=transition_request
)
```
