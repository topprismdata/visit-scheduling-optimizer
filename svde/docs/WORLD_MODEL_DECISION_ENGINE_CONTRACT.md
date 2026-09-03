# World Model ↔ Decision Engine Interface Contract

**Document ID:** TOPPRISM-WM-DE-CONTRACT-v1.0  
**Version:** v1.0-draft.5.2 (Contract Freeze Preflight)
**Date:** 2026-08-24  
**Status:** **MANDATORY INTERFACE CONTRACT**

---

## 一、接口分类

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         World Model ↔ Decision Engine 双向接口                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│ World Model  ──── L6 Projection / Read Queries ────▶ Decision Engine                 │
│                                                                                        │
│ Decision Engine ──── L3 Transition / L4 Feedback ──▶ World Model                       │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、WorldModel 暴露给 DecisionEngine 的只读接口

### 1. `get_worldstate_snapshot(snapshot_id)` → `WorldStateSnapshot`
- 返回不可变的世界状态快照（IMMUTABLE）；
- **严禁 DecisionEngine 修改、缓存、持有或传递给其他组件；调用后即释放引用。**
- **DecisionEngine 仅可通过此接口获得"只读 + 临时"访问，不能将 WorldState 作为内部状态字段。**

### 2. `query_customer_universe(rep_id)` → `Dict[store_code, CustomerEntity]`
- 严格基于 WorldState 中的 `OwnershipPolicy.ownership_map`；
- 不允许 DecisionEngine 自行拼接客户列表。

### 3. `resolve_active_policies(context, store_code, valid_time, transaction_time, snapshot_id)` → `Tuple[OperationalVisitPolicy, ...]`
- 按 Bitemporal 命中所有有效政策；
- DecisionEngine 必须基于此结果选择频次。

### 4. `compile_planner_projection(context: ApiRequestContext, snapshot_id: str, intent: PlanningIntent, partial_auth: Optional[PartialProjectionAuthorization] = None)` → `PlannerStateProjection`
- **CONTR-3: L6 接口仅返回 PlannerStateProjection（轻量纯数学载荷）；CandidatePlan 与 DecisionArtifact 属于 L7 输出**
- L6 包含: 严格同周几模式空间、路网矩阵、锁定承诺掩码、动作合成时长；
- L7 收到 Projection 后调用 Domain Solver 生成 CandidatePlan（业务富语义）并经审计后发布 DecisionArtifact。

---

## 三、DecisionEngine 调用 WorldModel 的写操作接口

### 1. `request_transition(context: ApiRequestContext, workflow: WorkflowContext, transition_request: TransitionRequest)` → `TransitionResult`
- DecisionEngine 提交状态转移请求；
- WorldModel 在 L3 执行 5 大守卫（A/B/C/D/E），全部通过后才接受；
- 失败时返回明确拒绝原因，不允许 DecisionEngine 绕过守卫。

### 2. `submit_execution_feedback(context, feedback: ActualVisitEvent)` → `ExecutionFeedbackReceipt`
- 接收来自 SFA/CRM 的实际拜访结果；
- 更新 `execution_fact_stream`；
- 触发新的世界状态演化。

### 3. `request_scenario_rollout(context: ApiRequestContext, base_snapshot_id: str, intent: PlanningIntent, perturbation_events: Tuple[PerturbationEvent, ...], simulation_time: datetime.datetime)` → `ScenarioResult`
- L5 受控 Scenario API；
- 仅供 DecisionEngine 进行"如果改变决策会怎样"的离线仿真；
- **严禁返回 BranchedWorldState 实例本身**（不允许 L7 持有分支状态）；
- 严禁用于生产路径实时决策；
- 返回 **单值 `ScenarioResult`**（其 `delta_state` 字段包含 `StateDelta`），严禁 `Tuple[ScenarioResult, StateDelta]` 双返回。

---

## 四、接口强制性约束

### 1. 不可变性
```python
# ❌ 严禁修改 WorldState 实例
worldstate.customer_universe["NEW_STORE"] = ...  # 错误：违反不变量

# ✅ 必须通过 Canonical API 接口
result: TransitionResult = worldmodel.request_transition(context, workflow, transition_request)
```

### 2. 时间参数强制显式
```python
# ❌ 严禁使用 datetime.now() 默认值
new_state = worldmodel.request_transition(context, workflow, transition_request)

# ✅ 必须显式传入（参考 v1.0-draft.5.2 新签名）
context = ApiRequestContext(api_version="WM-API-v1.0-draft.5.2", request_id=uuid4(),
                           caller_id="user_001", source_system="L7", timezone="Asia/Shanghai")
workflow = WorkflowContext(expected_snapshot_version=12, idempotency_key="uuid4()",
                          fingerprint=server_computed_fingerprint)
transition_request = TransitionRequest(
    visit_id="V_001", target_status=LifecycleStatus.COMMITTED,
    triggering_event_ref="EVT_APPROVE",
    event_time=datetime(2026, 6, 4, 9, tzinfo=ZoneInfo("Asia/Shanghai")),  # 必须带 tz
    transaction_time=datetime(2026, 6, 4, 9, 0, 1, tzinfo=ZoneInfo("Asia/Shanghai")),
    approver_id="DIR_GHB", policy_version_snapshot="v2.0",
    evidence_refs=("DOC_001",)
)
result = worldmodel.request_transition(context, workflow, transition_request)
```

### 3. 决策产物的原子性
```python
# 决策发布必须是原子的：审计通过 + 人工签署 + 状态提交 必须捆绑
artifact = decision_engine.approve_and_publish(
    candidate_plan=candidate_plan,
    audit_report=audit_report,
    approver_id="DIR_GHB",
    approval_timestamp=approval_timestamp  # MUST be explicit, no datetime.now()
)
# WorldModel 必须在同一事务中提交：
# 1. 审计哈希写入 transition_records
# 2. 状态置为 COMMITTED
# 3. 发布物锁入 WorldState.active_decision_artifacts
```

---

## 五、接口契约的版本化与兼容性

| 接口 | 当前版本 | 兼容性策略 |
| :--- | :--- | :--- |
| L6 Projection | v1.0 | 严格冻结数学结构，仅递增添加字段 |
| L3 Transition | v3.0 | 守卫列表可扩展，但不能删除已有守卫 |
| L4 Feedback | v1.0 | ActualVisitEvent 字段向后兼容 |
| L5 Scenario | v1.0 (草案) | 实验性 API，可能变动 |

---

## 六、当前 svde/ 代码中哪些已经符合 / 不符合接口契约

| 接口 | 当前状态 | 处理 |
| :--- | :--- | :--- |
| L4 → L6 Projection | `planner_projection.py` 已基本合规 | 微调 Fail-Closed |
| L7 → L3 Transition | `transition_engine.py` 已实现 v3.0 全守卫 | 持续合规 |
| L7 → L4 Feedback | `execution_fact_stream` 数据流存在 | 需要包装为 `submit_execution_feedback` 公开方法 |
| L7 → L5 Scenario | `rollout_reallocation_scenario` 是简化版 | 待升级为真正的多分支引擎 |

---

## 七、接口契约的代码体现

```python
# DecisionEngine 调用 WorldModel 接口的标准模板
class DecisionEngine:
    def approve_and_publish(self, candidate_plan: CandidatePlan,
                            audit_report: PlanAuditReport,
                            approver_id: str) -> DecisionArtifact:
        # 1. 通过 WorldModel 接口提交状态转移 (PLANNED -> COMMITTED)
        worldstate = candidate_plan.derived_worldstate
        # v1.0-draft.5.2: Canonical API 调用
        result: TransitionResult = self.worldmodel.request_transition(
            base_state=worldstate,
            visit_id=candidate_plan.target_visit_id,
            target_status=LifecycleStatus.COMMITTED,
            triggering_event_ref=f"DECISION_{candidate_plan.plan_id}",
            event_time=event_time,                # 必须由调用方显式传入
            transaction_time=transaction_time,    # 必须由调用方显式传入
            approver_id=approver_id,
            policy_version_snapshot=audit_report.policy_version
        )
        # 2. 发布 DecisionArtifact
        return DecisionArtifact(
            plan_id=candidate_plan.plan_id,
            audit_report_id=audit_report.plan_id,
            published_at=published_at,  # 必须由调用方显式传入
            approved_by=approver_id,
            published_worldstate_hash=new_worldstate.snapshot_id,
            ...
        )
```


---

> **同步声明**: 本文档的所有 API 签名必须与 `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2) 及 `CANONICAL_TYPE_REGISTRY.md` 完全对齐。


---

> **同步声明**: 本文档所有调用示例必须使用 Canonical API (`request_transition`, `request_scenario_rollout`)；旧的 `transition_engine.transition_visit_status(...)` 内部实现示例已标注为“内部实现，不属于 Canonical API”。
