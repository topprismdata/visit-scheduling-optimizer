# World Model System Boundary

**Document ID:** TOPPRISM-WM-BOUNDARY-v1.0  
**Version:** v1.0-draft.5.2 (Preflight Final Synced)  
**Date:** 2026-08-24  
**Status:** **MANDATORY SUBSYSTEM BOUNDARY DEFINITION**

---

## 一、World Model System 包含与不包含

### ✅ World Model System **内部必须拥有**

```
Semantic State                  — 当前企业状态
Evidence and Provenance        — 状态可追溯
Business Policies and Commitments — 政策与锁定承诺
Business Dynamics              — 业务动力学
State Transition Engine        — 状态转移
Scenario / Simulation Engine   — 反事实情景
Constraints (事实约束)          — 物理与业务规则的事实声明 (如"每月拜访3次")
Business Objectives (定性目标)  — 表达"应该怎样"的定性目标集
Feasible Action Space (允许动作集)— 允许发生的动作枚举 (如"是否可改派")
Planner Projection Interface   — L6 投影接口契约
Execution Feedback Subscriber  — 接收执行反馈
```
*(注：上述约束/目标/动作集由 World Model 定义，Decision Engine 仅在其集合内进行权衡选择)*

### ❌ World Model System **严禁包含**

```
Plan Intent / Action Choice      — 属于 L7 决策引擎
Human Approval Workflow         — 属于 L7 决策引擎
Execution Orchestration         — 属于 L7 决策引擎
Solver-Specific Algorithms      — 属于 L7 决策引擎 (消费 L6 接口)
Domain-Specific Vocabulary      — 仅允许出现在 L2 领域本体层
Capability Orchestration        — 属于 L7 决策引擎
```

---

## 二、World Model System 对外暴露的 Canonical API 接口

### Read-Only Query Interface (供 L7 消费 - 严禁持有)

**Ownership: World Model 是 WorldState 的唯一所有者**  
**Read Access: Decision Engine 仅可临时、只读、不带副本所有权地查询 WorldState**  
**Mutation: 任何状态变更必须通过 World Model 写接口**

- `get_worldstate_view(context, snapshot_id, scope, fields)` → 返回**不可变** `ReadOnlyWorldStateView`（DecisionEngine **不可修改、不可缓存、不可传递给其他组件**）；
- `query_customer_universe_view(context, rep_id, snapshot_id)` → 返回代表管辖客户全集（`FrozenCustomerUniverseView` 只读快照）；
- `resolve_active_policies(context, store_code, valid_time, transaction_time, snapshot_id)` → 返回当前有效政策集合（`Tuple[OperationalVisitPolicy, ...]` 只读元组）。

### Write / Mutate Interface (供 L7 调用)
- `request_transition(context, workflow, transition_request)` → 触发 L3 状态转移并返回 `TransitionResult`；
- `submit_execution_feedback(context, feedback)` → 提交执行反馈并返回 `ExecutionFeedbackReceipt`；
- `request_scenario_rollout(context, base_snapshot_id, intent, perturbation_events, simulation_time)` → **L5 受控推演入口：返回单值 `ScenarioResult`（其内部 `delta_state` 字段包含 `StateDelta`），严禁返回 `BranchedWorldState` 实例本身。**

### Read-Only Projection Interface (供 L7 消费)
- `compile_planner_projection(context, snapshot_id, intent, partial_auth)` → 返回轻量纯数学 `PlannerStateProjection`。

---

## 三、L5 Scenario API 严格边界

- **禁止直接持有 BranchedWorldState**: DecisionEngine 不可接收或保存分支 WorldState 实例；
- **允许调用受控 Scenario API**: `request_scenario_rollout(context, base_snapshot_id, intent, perturbations, simulation_time)`；
- **单值结果返回**: 仅返回单值 `ScenarioResult`（其 `delta_state` 字段包含 `StateDelta` 差异键值对）；
- **严禁持久化分支状态**: 推演结果必须在 L7 内部使用，不得作为长期缓存或审计源。

---

## 四、World Model System 的不变量 (Invariants)

1. **状态不可变**: 任何状态修改必须通过 Canonical API `request_transition(context, workflow, transition_request)` 提交并返回 `TransitionResult`，底层状态保持不可变快照；
2. **双时态严格**: Valid Time 与 Transaction Time 不可混淆；
3. **类别隔离**: Observation 与 Policy 与 Commitment 不可相互转化；
4. **可追溯**: 任何状态变更必须产生 `StateTransitionRecord` 包含审计哈希；
5. **可重放**: 相同输入 + 显式时间参数必须产生完全一致的状态与哈希。

---

## 五、当前 World Model System 在 svde/ 中的实际代码位置

```
svde/ontology/src/prism_ontology/world_model/
├── state_snapshot.py    ← L4 Canonical WorldState 实例定义
├── transition_engine.py ← L3 状态转移引擎
├── planner_projection.py ← L6 规划器投影接口契约
└── (待添加) scenario_engine.py ← L5 真正的多分支情景仿真
```

---

## 六、与现有代码的对应与边界审查

| 现有代码 | 归属定位 | 处理方案 |
| :--- | :--- | :--- |
| `diagnostics/cadence_auditor.py` | L3 状态合规审计 | 保留在 World Model |
| `diagnostics/schedule_verifier.py` | L3 物理可行性审计 | 保留在 World Model |
| `diagnostics/plan_auditor.py` | L7 三维独立审计 | 从 World Model 移出，归入 L7 Decision Engine |
| `engine/decision_pipeline.py` | L7 决策与审批编排 | 从 World Model 移出，归入 L7 Decision Engine |
| `engine/periodic_pvrp_solver.py` | Domain Solver | 降级为 Domain Solver，不属于 World Model |

---

## 七、Partial Projection Authorization (防重放绑定)

```python
@dataclass(frozen=True)
class PartialProjectionAuthorization:
    authorization_id: str
    actor_id: str
    reason: str
    approved_by: str
    scope: Tuple[str, ...]
    snapshot_id: str
    intent_id: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    nonce: str
    purpose: str
    status: AuthorizationStatus  # 声明字段，服务端以 Storage CAS 为准
    audit_record_ref: str
```

---

## 八、内部实现与 Canonical API 声明

> **同步声明**: 本文档所有对外接口必须严格使用 Canonical API 形式；底层代码中可能存在的 `emit_execution_feedback(...)` 或 `transition_engine.transition_visit_status(...)` **仅作为明确标注的内部实现示例，不属于 Canonical API**。Canonical API 规范请严格参见 `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md`。
