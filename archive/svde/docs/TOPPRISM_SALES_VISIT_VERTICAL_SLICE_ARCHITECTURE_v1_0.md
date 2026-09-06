# TopPrism 销售拜访垂直切片架构 v1.0.1

**Document ID:** TOPPRISM-SALES-VISIT-VERTICAL-SLICE-ARCHITECTURE-v1_0_1
**Date:** 2026-08-25
**Status:** **VERTICAL SLICE TARGET FLOW — DESIGN-ONLY, NOT PROVEN (架构演示，非已端到端验证闭环)**
**上游约束:** `TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md`
**作用域:** 以"代表请假 3 天重排"为唯一垂直验收场景，验证 L0-L7 端到端闭环
**严格红线:** 本文档描述架构能力边界，不修改 runtime，不实现代码

---

## 一、垂直切片场景（唯一验收场景）

```text
代表【仁军】（南通片区负责人）请假 3 天（2026-07-21 ~ 2026-07-23；DESIGN DEMO，未实现）
→ 识别受影响客户、频次和承诺
→ 生成延期、改派、保持原计划等情景
→ L3 校验动作合法性
→ L5 执行多个反事实推演
→ L6 生成规划投影
→ L7 生成候选决策
→ 三维审计
→ 人工审批
→ 更新 Commitment
→ 下发执行
→ 接收 ExecutionEvent
→ 生成新的 L4 WorldState Snapshot
```

---

## 二、14 步目标架构流程（DESIGN DEMO，NOT PROVEN）

> **纠偏声明**：本节为**目标架构流程演示**，**不是已证明的端到端闭环**。原因：
> 1. 步骤 1-2 涉及未实现的资源可用性实体；
> 2. 步骤 4-5 涉及未实现的通用 L5 反事实引擎；
> 3. 步骤 11 涉及违反时间契约的旧 decision_pipeline；
> 4. 步骤 12 涉及未实现的 SFA/CRM Execution Adapter；
> 5. 步骤 13-14 涉及未实现的 Canonical API `submit_execution_feedback` / `request_transition` 多实体包装层。
> 因此本节每步标注的设计意图**不可作为已闭环能力证明**，仅作为架构收敛目标。

### 步骤 1：资源可用性事件进入系统（DESIGN DEMO — 当前 NOT IMPLEMENTED）

> **纠偏声明**：本步骤当前在 Baseline v1.0 + Slice v1.0 中属**目标架构演示**。原因：
> - "请假"不是拜访事实，不是 `ActualVisitEvent`；
> - `LifecycleStatus` 当前不含资源可用性状态（不存在 `AVAILABILITY_BLOCKED` 等）；
> - `transition_visit_status` 仅支持 visit 实体，未实现多实体 Transfer。
>
> 当前步骤使用假设性枚举 `ResourceAvailabilityStatus.ABSENT_PLANNED` 与假设性接口 `submit_resource_event`，**均未实现**。下方仅为架构目标。

| 项 | 内容（DESIGN TARGET） |
|---|---|
| **输入** | HR/SFA 推送 `ResourceAvailabilityObservation(resource_id="仁军", status=ResourceAvailabilityStatus.ABSENT_PLANNED, valid_time: BitemporalPeriod(2026-07-21, 2026-07-23), evidence_refs=["LEAVE_REQUEST_LEAD_2026_07_18.pdf"], source_system="HR_SYSTEM", reason="已批年假")` |
| **调用** | L7 `submit_resource_event(context, observation)`（**DESIGN TARGET — 当前 NOT IMPLEMENTED**） |
| **输出** | `ResourceEventReceipt(event_id, new_snapshot_id="SNAP_2026_07_21_RESOURCE_AVAILABILITY_UPDATED", transition_required=True)` |
| **状态所有者** | L4（资源可用性快照 —— **当前混入 execution_fact_stream 字段 DEPRECATED**；DESIGN 目标：应独立 `ResourceAvailabilityStream`） |
| **事实来源** | HR/SFA 工单系统 |
| **政策来源** | `HRPolicy("请假规则", version="v2.3")`（HR 政策属 World Model 政策；DESIGN 目标下需新增） |
| **证据** | `LEAVE_REQUEST_LEAD_2026_07_18.pdf` |
| **分类** | **事实 (FACT)** —— 请假事件已真实发生 |

---

### 步骤 2：L3 触发资源可用性状态转移（L3 → L4，DESIGN DEMO）

| 项 | 内容（DESIGN TARGET） |
|---|---|
| **输入** | ResourceEventReceipt 携带 `transition_required=True`；L7 调用 `request_transition(TransferRequest(entity_type=EntityType.RESOURCE, entity_ref="仁军", target_status=ResourceAvailabilityStatus.ABSENT_PLANNED, event_time, transaction_time, policy_version_snapshot="HR_v2.3"))` |
| **调用** | L3 `request_transition(context, workflow, transition_request)` |
| **输出** | `TransitionResult(new_snapshot_id="SNAP_2026_07_21_LEAVE_ACKNOWLEDGED", transition_record, audit_hash)` + 新 `OperationalDecisionWorldState` 快照 |
| **状态所有者** | L3（StateTransitionRecord） + L4（新快照） + 独立 ExecutionEventStore（外部事件流；非 L4 字段） |
| **守卫** | **当前 NOT IMPLEMENTED**：现有 Guard A-E 仅适用于 `LifecycleStatus`（拜访状态）；资源可用性状态需独立守卫实现（如：HR 政策合规性、最大资源下线比例、上下游代表覆盖等） |
| **证据** | 步骤 1 的 `LEAVE_REQUEST_LEAD_2026_07_18.pdf` + L3 自动产生的 StateTransitionRecord.record_hash |
| **分类** | **事实 (FACT)** —— 代表真实请假已确认，资源可用性状态变化 |

---

### 步骤 3：识别受影响客户与承诺（L7 Read-Only 查询）

| 项 | 内容 |
|---|---|
| **输入** | L7 业务事件：`RepAbsenceDetected(rep_id="仁军", absence_from=2026-07-21, absence_to=2026-07-23)` |
| **调用** | L4 `query_customer_universe_view(context, rep_id="仁军", snapshot_id="SNAP_2026_07_21_LEAVE_ACKNOWLEDGED")` + L4 `resolve_active_policies(context, store_code=..., valid_time, transaction_time, snapshot_id)` |
| **输出** | `FrozenCustomerUniverseView`（32 家门店，每家带 `tier/fulfillment_class/geo_quality/cadence_policy_ref`） + `Tuple[OperationalVisitPolicy, ...]`（每家的频次要求与 lock_level） |
| **状态所有者** | L4 快照（只读消费） |
| **业务计算** | L7 内部计算"请假窗口内的承诺"：调用 `commitments` 过滤 `locked_time_slot ∈ [2026-07-21, 2026-07-23]` 且 `rep_id == "仁军"`，得到 `affected_commitments: List[OperationalCommitment]` |
| **事实来源** | L4 snapshot（=真实历史 + 已确认承诺） |
| **政策来源** | `CadenceRule(target_frequency_per_month=N)` × `DeferralPolicy(max_deferrals_per_period, max_deferral_window_days)` × `OperationalVisitPolicy(policy_version)` |
| **证据** | L4 snapshot 的 `source_manifest.source_file_sha256`（保证来源可追溯） |
| **分类** | **事实 (FACT)** —— 客户与承诺来自真实基线 |

---

### 步骤 4：生成多个候选情景（L5）

| 项 | 内容 |
|---|---|
| **输入** | L7 构造多个 `PerturbationEvent` 序列：<br>① `SEQUENCE_KEEP_ORIGINAL`（保持原计划）<br>② `SEQUENCE_DEFER_ALL_AFFECTED`（窗口内全部承诺延期到 7-24）<br>③ `SEQUENCE_REASSIGN_TO_NEARBY_REP`（改派给佳佳 / 晓敏）<br>④ `SEQUENCE_HYBRID_PARTIAL_DEFER_PARTIAL_REASSIGN`（混合）<br>每个序列含时间参数 |
| **调用** | 对每个序列 L7 调用 `request_scenario_rollout(context, base_snapshot_id, intent=PlanningIntent(decision_scope="REP_ABSENCE_REPLAN"), perturbation_events, simulation_time=2026-07-21T09:00+08:00)` |
| **输出** | 每个情景返回 `ScenarioResult(scenario_id, branch_hash, delta_state, aggregate_metrics_delta, guard_violations_count, convergence_status, capacity_impact_summary)` |
| **状态所有者** | L5 内部沙箱（不持久化） |
| **事实来源** | L4 baseline（snapshot_id 引用） + 假设（assumptions） |
| **政策来源** | 同 L4 政策的 `policy_version_snapshot`（场景不可修改政策，只能应用扰动） |
| **证据** | `branch_hash`（情景分支指纹，由 L5 内部生成） |
| **分类** | **情景 (SCENARIO)** —— 不写回 baseline；只产出 `StateDelta` 与指标差异；ScenarioResult 严禁升级为现实事实 |

---

### 步骤 5：L5 内部反事实推演（L5 内部）

每个情景内部：
1. 从 `SNAP_2026_07_21_LEAVE_ACKNOWLEDGED` 副本创建分支 `BranchedWorldState`（**仅 L5 内部持有，不暴露给 L7**）；
2. 依次应用 perturbation_events，应用 L3 Transfer 规则（注意：scenario 内部仍可调 transfer 函数，但不持久化）；
3. 计算每种扰动后的 `StateDelta` 与业务指标变化（频次达成率、单日在途工时、Commitment 履约率、Key 店覆盖率、未履约业务代价）；
4. 收集所有守卫违规（如：改派超出佳佳的单日容量、延期超出 DeferralPolicy 配额、改派导致原代表产能骤降等）。

---

### 步骤 6：L6 生成规划投影（L7 → L6）

| 项 | 内容 |
|---|---|
| **输入** | L7 从 4 个 `ScenarioResult` 中选出 2~3 个"未违规"或"违规可接受"的方案，对每个方案构造 `PlanningIntent(intent_id, decision_scope="REP_ABSENCE_REPLAN", target_agent_id="仁军", valid_time=2026-07-21T10:00+08:00, allowed_actions=("DEFER", "REASSIGN", "SKIP"))`，调用 `compile_planner_projection(context, snapshot_id, intent, partial_auth=None)` |
| **输出** | `PlannerStateProjection(projection_id, target_agent_id="仁军", time_slots_count=20, nodes: Tuple[PlannerNodeTopology,...], node_index_lookup, travel_cost_matrix, travel_distance_matrix, candidate_pattern_space, locked_commitments_mask, daily_stop_capacity=6, daily_workload_budget_min=480.0, is_projection_clean=True, unplannable_nodes_excluded=())` |
| **状态所有者** | L6（不可变 payload） |
| **事实来源** | L4 baseline + 路网来源标识（Haversine 估算或 OSRM 真实路网，待 OSRM 接入） |
| **政策来源** | `partial_auth.snapshot_id` 指向 L4；`partial_auth.policy_version_snapshot` 指向版本化政策 |
| **证据** | `projection_id` 与 `node_index_lookup`（可回溯） |
| **分类** | **纯数学载荷** —— 不是规划，不是决策 |

---

### 步骤 7：Domain Solver 执行（L7 调用 Domain Solver）

| 项 | 内容 |
|---|---|
| **输入** | L7 将 `PlannerStateProjection` 喂给 Domain Solver（`PeriodicPVRPSolver.solve(projection)`） |
| **输出** | 原始序列：`{(week, day): [0, store_idx_1, store_idx_2, ..., 0]}`（0 代表 Depot，1..N 代表客户节点） |
| **状态所有者** | 无（纯函数） |
| **事实来源** | 无 |
| **政策来源** | 无 |
| **证据** | solver 元数据（`solver_meta={"solver_name": "CP-SAT", "version": "9.x"}`） |
| **分类** | **算法输出** —— Solver 不读业务语义，不解释承诺，只解 CP-SAT 数学问题 |

---

### 步骤 8：反向投影（L7 内部）

| 项 | 内容 |
|---|---|
| **输入** | 步骤 7 的原始序列 + 步骤 6 的 `PlannerStateProjection` + ReadOnlyWorldStateView |
| **输出** | `CandidatePlan(plan_id, intent_id, target_agent_id="仁军", period_label="2026-07-21_LEAVE_REPLAN", daily_routes=(PlannedDailyRoute(date_str, weekday_name, rep_id, stops=(PlannedStop(stop_idx, store_code, store_name, district, planned_service_min, leg_distance_from_prev_km, leg_transit_from_prev_min), total_daily_distance_km, total_daily_transit_min, total_daily_service_min, total_daily_workload_min), ...), solver_name, solver_status, total_scheduled_visits, total_monthly_transit_min, total_monthly_distance_km, trade_off_metrics)` |
| **状态所有者** | L7 决策库（候选区） |
| **事实来源** | ReadOnlyWorldStateView（用于把 store_idx 反查 store_code/store_name/district） |
| **政策来源** | 无 |
| **证据** | ReadOnlyWorldStateView 的来源 snapshot |
| **分类** | **候选规划 (PLAN)** —— 尚未审批，不可执行 |

---

### 步骤 9：多目标权衡评估（L7 内部）

| 项 | 内容 |
|---|---|
| **输入** | 步骤 8 的 `CandidatePlan` |
| **调用** | L7 内部 LexMin 字典序评估（Level 0 物理 → Level 1 业务价值 → Level 2 交通 → Level 3 节奏 → Level 4 均衡） |
| **输出** | `trade_off_metrics={"physical_violation_count": 0, "missed_key_stores": 0, "missed_committed_count": 0, "total_transit_min": ..., "cadence_compliance_rate": ..., "daily_workload_variance": ...}` |
| **分类** | **评估结果 (EVALUATION)** —— 不修改任何状态 |

---

### 步骤 10：三维独立审计（L7 Domain Audit）

| 项 | 内容 |
|---|---|
| **输入** | `CandidatePlan` + ReadOnlyWorldStateView |
| **调用** | `ThreeDimensionalPlanAuditor.audit_candidate_plan(candidate_plan, world_state)` |
| **输出** | `PlanAuditReport(plan_id, is_fully_compliant, cadence_compliance_rate, physical_feasibility_passed, business_compliance_passed, semantic_purity_passed, violations: Tuple[str,...], summary_message)` |
| **审计维度** | **Physical**（≤6 家/日、≤480min/日、Depot 闭环、无子回路）<br>**Business**（Key/A 店 0 脱访、频次达成率 100%、Deferral 配额）<br>**Semantic**（Solver 不内嵌业务规则、字段来源可追溯） |
| **分类** | **审计结论 (AUDIT)** —— 不修改任何状态 |

---

### 步骤 11：人工审批（HITL）

| 项 | 内容 |
|---|---|
| **输入** | `PlanAuditReport` 通过 + `CandidatePlan` + approver_id（业务主管 ID） + approval_timestamp（必须显式传入，禁用 `datetime.now()`） |
| **调用** | L7 `human_approve_and_publish(candidate_plan, audit_report, approver_id, approval_notes, approval_timestamp)` |
| **输出** | `DecisionArtifact(artifact_id, candidate_plan_ref, audit_report_ref, approved_by, approved_at, published_schedule: Mapping[date_str, Tuple[store_code,...]], status="APPROVED_FOR_EXECUTION")` |
| **状态所有者** | L7 决策库 |
| **事实来源** | **N/A（治理动作）** —— HITL 本身是治理事件，不依赖外部事实源 |
| **政策来源** | **N/A（治理动作）** —— 治理动作不引用业务政策；政策在步骤 3/10 已生效 |
| **证据** | `approver_id` + `approval_timestamp` + `approval_notes`（HITL 自身即为证据） |
| **分类** | **决策产物 (DECISION)** —— 仅"已批准"，**未执行** |

---

### 步骤 12：执行编排（L7 → SFA/CRM）

| 项 | 内容 |
|---|---|
| **输入** | `DecisionArtifact(APPROVED_FOR_EXECUTION)` + SFA/CRM 接口约定 |
| **调用** | L7 `ExecutionAdapter.dispatch(decision_artifact)`（具体实现为 SFA/CRM REST 调用） |
| **输出** | SFA/CRM 端产生 DispatchAck + 同步产生 `ApprovalEvent(status="PUBLISHED", published_at, published_by)` |
| **状态所有者** | L7 dispatch log + SFA/CRM 端 |
| **分类** | **执行编排事件 (EXEC)** —— 决策产物已下发，但 **PUBLISHED 仅表示决策已审批 + 已下发到 SFA/CRM；VisitLifecycle 仍为 PLANNED（不是 IN_PROGRESS）**。Approval.PUBLISHED 严禁直接驱动 VisitLifecycle.IN_PROGRESS；必须等 SFA/CRM 实际推送现场打卡后经 L3 Transfer 事件溯源 |

---

### 步骤 13：执行反馈接收（L7 → L3 → L4）

| 项 | 内容 |
|---|---|
| **输入** | SFA/CRM 推送 `ActualVisitEvent(event_id, store_code, rep_id, visit_date, occurred_at, timezone, captured_at, transaction_time, valid_time, source_system="SFA", idempotency_key, service_duration_min, transit_duration_min, is_line_internal, actions, evidence_refs)` 或 `MISSED_FLAG` |
| **调用** | L7 `submit_execution_feedback(context, feedback)` |
| **输出** | `ExecutionFeedbackReceipt` + 触发 L3 `request_transition(target_status=COMPLETED/MISSED, ...)` + 新 snapshot |
| **状态所有者** | L4（**execution_fact_stream DEPRECATED 字段**；DESIGN 目标：独立 `ExecutionEventStore`）+ 新 snapshot |
| **守卫** | Guard B（时长 ≥10min）/ Guard C（GPS ≤500m）/ Guard D（MISSED 时间≥当天 23:59） |
| **证据** | SFA/CRM 推送的 GPS 时间戳 + 照片 |
| **分类** | **事实 (FACT)** —— 真实执行结果已确认 |

---

### 步骤 14：新 L4 Snapshot 生成（L3 → L4）

| 项 | 内容 |
|---|---|
| **输入** | 步骤 13 的 TransitionResult |
| **调用** | L3 守卫通过后自动生成新 `OperationalDecisionWorldState` snapshot |
| **输出** | `SNAP_2026_07_24`（**execution_fact_stream 字段 DEPRECATED**：DESIGN 目标为独立 `ExecutionEventStore`，当前快照描述其包含 7-21~7-23 期间的真实拜访事实，含 32 家门店频次达成率） |
| **状态所有者** | L4 snapshot store |
| **分类** | **事实 (FACT)** —— 现实世界已变化，L4 baseline 必须经 L3 Transfer 升级（现实状态变化必经 L3 守卫的事件溯源路径） |

---

## 三、事实归属全景表

| 步骤 | 涉及层 | 状态所有者 | 分类 | 不可绕过性 |
|---|---|---|---|---|
| 1 请假事件 | L4 (独立 ExecutionEventStore — DESIGN) / L4 (execution_fact_stream — 当前 DEPRECATED) | L4 | FACT | 必须经 L7 **submit_resource_event**（Canonical API，与 submit_execution_feedback 分离） |
| 2 Transfer | L3 + L4 | L3 + L4 | FACT | 必须经 L3 守卫 |
| 3 客户识别 | L4 (ReadOnly) | L4 (只读消费) | FACT | L7 必须经 query_customer_universe_view |
| 4 情景生成 | L5 (内部沙箱) | L5 | SCENARIO | 不写回 baseline |
| 5 反事实推演 | L5 (内部) | L5 | SCENARIO | 不暴露 BranchedWorldState |
| 6 投影编译 | L6 | L6 | 纯数学载荷 | 必须引用 snapshot_id |
| 7 Solver | L7 内部 Domain Solver | 无 | ALGO | Solver 不解释业务语义 |
| 8 反向投影 | L7 内部 | L7 决策库 | PLAN (CANDIDATE) | 未经审计与审批不可发布 |
| 9 Trade-off | L7 内部 | L7 决策库 | EVALUATION | 不修改任何状态 |
| 10 三维审计 | L7 Domain Audit | L7 决策库 | AUDIT | 任意维度失败即阻断 |
| 11 人工审批 | L7 | L7 决策库 | DECISION (APPROVED) | REQUIRED 级别必须 HITL |
| 12 执行编排 | L7 → SFA/CRM | L7 dispatch log | EXEC | Approval.PUBLISHED 不等于 VisitLifecycle 启动 |
| 13 执行反馈 | L7 → L3 → L4 + 独立 ExecutionEventStore | L4 + Store | FACT | ExecutionEvent 必须经 L3 Transfer；事件应写入独立 ExecutionEventStore 而非 L4 execution_fact_stream 字段 |
| 14 新 Snapshot | L4 + L3 + 独立 ExecutionEventStore | L4 + L3 | FACT | **StateTransitionRecord（由 L3 Transfer 生成）+ 新 L4 snapshot**；严禁将 IN_PROGRESS/COMPLETED 状态转移结果命名为"ExecutionEvent" |

---

## 四、缺失能力清单（Vertical Slice 闭环所需但当前未实现）

**P0-8** | ResourceAvailabilityLifecycle 独立枚举与多实体 Transfer 支持 | 步骤 1-2 | M | 否



| 缺失能力 | 影响的步骤 | 实现工作量等级 | 业务裁决需求 |
|---|---|---|---|
| **P0-8** | ResourceAvailabilityLifecycle 独立枚举与多实体 Transfer 支持 | 步骤 1-2 | M | 否 |
| **P0-9** | `ExecutionEventStore` 独立子资源（执行事件流从 `OperationalDecisionWorldState.execution_fact_stream` 字段剥离） | 步骤 13-14 | M | 否 |
| **P0-10** | 双入口分离：`submit_execution_feedback`（拜访事实）≠ `submit_resource_event`（资源可用性）；严禁混用 | 步骤 1 vs 13 | S | 否 |
| **Canonical API 包装层**（`request_transition` / `submit_execution_feedback` / `request_scenario_rollout` / `compile_planner_projection` / `get_worldstate_view` / `resolve_active_policies` 当前代码层未实现） | 步骤 1/2/3/4/6/13 | M（中等） | 否 |
| **L5 通用多分支反事实引擎**（当前 `rollout_reallocation_scenario` 是改派单点函数） | 步骤 4/5 | L（较大） | 否 |
| **`active_scenario_branches` 从 L4 移除**（当前 OperationalDecisionWorldState 混合 baseline 与 scenario） | 步骤 5/6 | S（小） | 否 |
| **`_resolve_active_frequency_v2` 与 cadence_auditor 双向使用版本化政策**（当前 cadence_auditor 仍读 `planned_frequency` 观测字段） | 步骤 3/10 | S（小） | 是（确认 CadenceRule vs OperationalVisitPolicy 谁是唯一权威频次来源） |
| **`datetime.now()` 在 decision_pipeline.py human_approve_and_publish 中** | 步骤 11 | S（小） | 否 |
| **HITL 审批 API 形式化**（当前 DecisionArtifact 用 status 字符串而非 enum） | 步骤 11 | S（小） | 否 |
| **L4 OperationalDecisionWorldState 的 immutable 校验**（@dataclass(frozen=True) 已设但 Default_factory 仍允许构造后修改） | 步骤 14 | S（小） | 否 |
| **真实路网矩阵接入**（当前 Haversine 估算） | 步骤 6 | L（较大） | 是（确认 OSRM 接入路径与许可） |
| **CADENCE 频次语义签署（1A/2A/3A/B/C/D 各级别实际节奏与误差窗口）** | 步骤 1/3/10 | — | **是（BIZ-01）** |
| **CADENCE_3_PER_MONTH 业务语义签署** | 步骤 3/10 | — | **是（BIZ-02）** |
| **DEFER 配额与延期窗口签署** | 步骤 4/10 | — | **是（BIZ-03）** |
| **REQUIRED 店零脱访刚性签署** | 步骤 10 | — | **是（BIZ-04）** |
| **GPS 偏差阈值签署** | 步骤 13 (Guard C) | — | **是（BIZ-05）** |
| **工时双重红线签署** | 步骤 10 | — | **是（BIZ-06）** |
| **归属冲突优先级签署** | 步骤 4 (REASSIGN) | — | **是（BIZ-07）** |
| **多产品线拜访策略签署** | 步骤 3 | — | **是（BIZ-08）** |
| **决策审批层级签署** | 步骤 11 | — | **是（BIZ-09）** |

---

## 五、垂直切片可证明性矩阵

| 步骤 | 是否可在当前架构下被证明 | 证据 |
|---|---|---|
| 1 请假事件进入 | DESIGN ONLY（design 已定义；runtime 未实现） | L7 API spec §5.3 + ExecutionFeedbackReceipt 数据结构 |
| 2 L3 Transfer | PARTIALLY IMPLEMENTED | transition_engine.transition_visit_status 含 Guard A-E |
| 3 客户识别 | PARTIALLY IMPLEMENTED | query_customer_universe_view 已定义；OperationalCustomer + OperationalVisitPolicy 已实现 |
| 4 情景生成 | NOT IMPLEMENTED as L5 | 当前 rollout_reallocation_scenario 是改派函数 |
| 5 反事实推演 | NOT IMPLEMENTED | 缺通用多分支引擎 |
| 6 投影编译 | IMPLEMENTED | PlannerStateProjectionCompiler.compile_projection 已可用 |
| 7 Solver | IMPLEMENTED | PeriodicPVRPSolver.solve(payload) 可用 |
| 8 反向投影 | NOT IMPLEMENTED as separate step | 当前在 Solver 内部 |
| 9 Trade-off | NOT IMPLEMENTED as separate step | 当前在 Solver 内部 |
| 10 三维审计 | IMPLEMENTED | ThreeDimensionalPlanAuditor 已可用 |
| 11 人工审批 | PARTIALLY IMPLEMENTED | decision_pipeline.human_approve_and_publish 有 datetime.now() 违规 |
| 12 执行编排 | NOT IMPLEMENTED as separate adapter | 缺 SFA/CRM REST 适配器 |
| 13 执行反馈 | NOT IMPLEMENTED | OperationalVisitLifecycleRecord + ActualVisitEvent 已定义；submit_execution_feedback 函数未实现；且 execution_fact_stream 字段 DEPRECATED 须迁移至独立 ExecutionEventStore |
| 14 新 Snapshot | NOT IMPLEMENTED | execution_fact_stream DEPRECATED 字段仍混入 Baseline；transition_engine.transition_visit_status 仅返回新 WorldState（tuple 形式），尚未实现独立 ExecutionEventStore |

---

## 六、当前垂直切片准确状态

```
Vertical Slice:          DESIGN-ONLY, NOT PROVEN
                         (架构目标流程；14 步含 9 步依赖未实现项)
Implementation:         NOT STARTED        (Canonical API 包装层尚未启动)
RUNTIME:                PARTIAL            (步骤 2/6/7/10 可跑；步骤 1/4/5/8/11/12/13 依赖未实现能力)
Business Sign-off:      PENDING            (BIZ-01~09 待业务方签署)
Freeze Review:          BLOCKED            (依赖 BIZ 签署 + Baseline 旧文档迁移 + 代码层 Baseline/Event/Scenario 拆分)
```

**重点声明**：本垂直切片当前**不是已证明的端到端流程**，仅作为 L0-L7 架构在销售拜访领域的**目标架构演示**。真实闭环验证需 Phase 8 真实数据影子模式。
