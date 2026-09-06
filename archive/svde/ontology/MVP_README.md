# Sales Visit Vertical Slice MVP — Internal Replay Only

## 1. 范围

销售拜访领域最小可运行 Vertical Slice MVP。**不对外执行，不写回真实基线，不宣称 Canonical API 已实现。**

```
输入数据 (WorldState fixture / 离线样本)
   ↓
WorldStateAssembler (已有)
   ↓
当前 WorldState (基线)
   ↓
VerticalSliceRunner.run()        ← 内部编排，含 MVP 元数据 + scenario_effect_applied 结构化字段
   ↓
[业务事件路径 — 显式情景输入，不伪造状态机]
   ↓
SVDEOntologyAdapter.dispatch_planning_intent (legacy)
   ↓
PeriodicPVRPSolver.solve (legacy)
   ↓
ThreeDimensionalPlanAuditor.audit_candidate_plan (legacy)
   ↓
DecisionArtifact (preview only — status=MVP_PREVIEW, NOT dispatched)
   ↓
MVPResult (含 execution_mode / canonical_api_status / external_dispatch / baseline_writeback / runtime_scope / error_kind / scenario_effect_applied)
```

## 2. MVP 元数据（每次输出都包含）

| 字段 | 值 | 含义 |
|---|---|---|
| `execution_mode` | `INTERNAL_VERTICAL_SLICE_MVP` | MVP 内部回放模式 |
| `canonical_api_status` | `NOT_IMPLEMENTED` | Canonical API 包装层尚未实现 |
| `external_dispatch` | `false` | 不实际下发到 SFA/CRM |
| `baseline_writeback` | `false` | 不写回真实 WorldState |
| `runtime_scope` | `LEGACY_SVDE_PIPELINE` | 当前走的是旧 decision_pipeline，未走新 L7 |
| `error_kind` | `FEASIBLE / PARTIALLY_FEASIBLE / INFEASIBLE / PIPELINE_ERROR` | 系统执行状态（区分业务可行性 vs 系统执行失败） |
| `scenario_effect_applied` | `bool` (结构化字段) | 情景是否真实改变计划 — MVP 始终为 `False` (no-writeback control case) |

## 3. 本轮范围与禁区

### 本轮**实现**（已落盘）
- `svde/ontology/src/prism_ontology/engine/vertical_slice_mvp.py` — `VerticalSliceRunner` / `ScenarioParameters` / `MVPResult` (含 `error_kind` 与 `scenario_effect_applied` 结构化字段) / inline `DecisionArtifact` 构造
- `svde/ontology/tests/test_vertical_slice_mvp.py` — 7 个端到端测试（含 `scenario_effect_applied` 结构化断言）
- `svde/ontology/tests/evidence/vertical_slice_mvp_demo.json` — 3 case 实际运行的 JSON 证据

### 本轮**不实现**（明确禁区，8 项）
- ❌ L5 通用反事实引擎
- ❌ L7 Enterprise Decision Engine
- ❌ ResourceAvailabilityLifecycle（资源不可用仅作为显式测试输入）
- ❌ Multi-Entity Transfer
- ❌ ExecutionEventStore
- ❌ SFA/CRM 实际下发（`external_dispatch=false`）
- ❌ Canonical API Freeze（`canonical_api_status=NOT_IMPLEMENTED`）
- ❌ 真实 WorldState 写回（`baseline_writeback=false`）

## 4. 关键设计决策

### 4.1 资源不可用 = 显式测试输入，**不是**状态机

MVP 不实现 `ResourceAvailabilityLifecycle`。代表"请假 3 天"在 MVP 中表达为：

```python
ScenarioParameters(
    scenario_id="...",
    scenario_unavailable_rep_ids=frozenset(仁军),  # 显式输入
    ...
)
```

不构造 `ActualVisitEvent(event_type="REP_ABSENCE")`；不引入 `LifecycleStatus.AVAILABILITY_BLOCKED`；不构造虚构的 `ResourceAvailabilityObservation`。

MVPResult 提供结构化布尔字段 `scenario_effect_applied=False`，下游解析时直接读取该字段，不依赖解析 `notes` 文本。

调用方负责处理"unavailable rep"的下游含义（不重排该 rep 的计划；或保留该 rep 的现有计划）。

### 4.2 DecisionArtifact 是 preview，**不是** publish

MVP runner **inline 构造** `DecisionArtifact` 对象（**不**调 `DecisionPipelineRunner.human_approve_and_publish()`，因为该方法使用 `datetime.now()` 违反时间契约）并加入 `decision_artifact_preview` 字段。preview 字段包含：

```
status: "MVP_PREVIEW"          # 不是 APPROVED_FOR_EXECUTION — 避免业务方误解为已批准
approval_simulated: true      # 显式声明是模拟批准，非真实审批
external_dispatch: false
baseline_writeback: false
_preview_warning: "...INTERNAL MVP preview...NOT dispatched..."
```

**不**：
- 持久化到 DecisionArtifact 存储
- 推到 SFA/CRM REST 端点
- 创建 ApprovalEvent / DispatchCommand / ExecutionEvent
- 写回新 L4 WorldState snapshot

## 5. 测试覆盖（7 case，全部通过）

| # | Case | 期望 |
|---|---|---|
| 1 | 可行重排 (基线代表) | PARTIALLY_FEASIBLE 或 FEASIBLE；含 CandidatePlan + AuditReport + DecisionArtifact preview (MVP_PREVIEW + approval_simulated=True) |
| 2 | 不可行 (nonexistent rep) | feasibility=INFEASIBLE + error_kind=PIPELINE_ERROR；notes 含 BRIDGE_DISPATCH_FAILED；artifact 为 None |
| 3 | 资源不可用 (情景注入) | feasibility=PARTIALLY_FEASIBLE + error_kind=FEASIBLE；MVPResult.scenario_effect_applied=False（结构化布尔字段） |
| 4 | MVP 元数据完整性 | 全部 22 个必填字段存在（含 `error_kind` 与 `scenario_effect_applied` 布尔） |
| 5 | JSON 可序列化 | `execution_mode=INTERNAL_VERTICAL_SLICE_MVP` 在 JSON 中可见 |
| 6 | 约束违约记录 | `constraint_violations` 字段始终存在 |
| 7 | run_timestamp 必填校验 | 拒绝 None 与非 datetime 类型 |

## 6. 运行结果（实测，os.stat 实测字节数）

| 文件 | 字节 |
|---|---:|
| `svde/ontology/src/prism_ontology/engine/vertical_slice_mvp.py`（VerticalSliceRunner + ScenarioParameters + MVPResult 含 error_kind 与 scenario_effect_applied 结构化字段 + inline DecisionArtifact 构造）| **17,020** |
| `svde/ontology/tests/test_vertical_slice_mvp.py`（7 个端到端测试，含结构化字段断言）| **19,626** |
| `svde/ontology/tests/evidence/vertical_slice_mvp_demo.json`（3 case 实际运行 JSON 证据）| **28,636** |
| `svde/ontology/MVP_README.md`（MVP 实现说明）| **10,067** |

## 7. 测试与演示案例区分

### 7.1 测试（7 个，每个对应一个测试函数）

测试函数与 MVP 能力一一对应：

| # | 测试函数 | 验证目标 |
|---|---|---|
| 1 | `test_mvp_feasible_replan_basic` | 基线代表可行重排 |
| 2 | `test_mvp_infeasible_replan_nonexistent_rep` | INFEASIBLE vs PIPELINE_ERROR 区分 |
| 3 | `test_mvp_resource_unavailable_as_explicit_scenario_input` | scenario_effect_applied=False（no-writeback control case） |
| 4 | `test_mvp_result_has_all_required_metadata_fields` | MVPResult 22 个必填字段 + 类型 |
| 5 | `test_mvp_serializable_to_json` | JSON 序列化含 MVP 元数据 |
| 6 | `test_mvp_constraint_violations_are_recorded` | constraint_violations 字段 |
| 7 | `test_mvp_run_timestamp_required_no_silent_default` | run_timestamp 显式必填 |

### 7.2 演示案例（3 个，验证主流程可审计）

| Case | feasibility | error_kind | artifact.status | approval_simulated | scenario_effect_applied (struct) |
|---|---|---|---|---|---|
| MVP_DEMO_FEASIBLE | PARTIALLY_FEASIBLE | FEASIBLE | MVP_PREVIEW | true | False |
| MVP_DEMO_INFEASIBLE | INFEASIBLE | **PIPELINE_ERROR** | (NULL — audit 失败) | – | False |
| MVP_DEMO_RESOURCE_UNAVAIL | PARTIALLY_FEASIBLE | FEASIBLE | MVP_PREVIEW | true | False (no-writeback control case) |

**WorldState 修改验证**：3 个 demo case 跑完后 `world_state.snapshot_id` / `execution_fact_stream` 长度 / `policies.operational_policies` 长度全部与初始值一致（Case 3 即便标记 rep 不可用，也未修改 WorldState）。


## 8. 全量回归测试（确认无回归）

```
svde/ontology/tests/test_vertical_slice_mvp.py   9 passed   (2026-08-26 刷新: 7 原始 case + 2 后续增补: biz_registry 签名 / biz 违规叠加)
svde/ontology/tests/ (其他 163 测试)             163 passed (含 shadow/canonical_api 增量, 无回归)
svde/tests/                                       37 passed
svde-bench/                                      121 passed
                                                  ---
合计                                              330 passed
```

## 9. 准确状态声明

```
MVP Core Path:               VERIFIED (Projection / Solver / Audit 主链路)
DecisionArtifact Preview:    VERIFIED (MVP_PREVIEW + approval_simulated=True + scenario_effect_applied 结构化字段=False)
Preview Approval Semantics:  OK (status=MVP_PREVIEW, 非 APPROVED_FOR_EXECUTION)
错误分类:                     OK (feasibility vs error_kind 已分离; PIPELINE_ERROR 区分于 INFEASIBLE)
资源不可用驱动重排:          NOT IMPLEMENTED (仅 no-writeback control case; scenario_effect_applied=False)
Shadow Input Contract:       READY (MVPResult JSON 序列化可作为 Shadow Mode 输入契约)
Shadow Execution Harness:    NOT IMPLEMENTED (无 replay runner / 数据预检 / 输入快照 hash / baseline 对照 / 独立只读安全闸门)
Real Data Replay:            NOT RUN (本轮未执行真实历史数据离线回放)
MVP 不代表生产可用:           YES (canonical_api_status=NOT_IMPLEMENTED)
MVP 不代表 Canonical API:     YES
架构冻结 (Freeze Review):     BLOCKED
```

## 10. 下一步建议（不在本轮范围）

下一步是**单独实现只读 `ShadowReplayRunner`**（独立于 MVP），至少包含：
- 真实数据预检入口（WorldState 是否有效、字段是否完整）
- 输入快照 hash（确保 replay 可重复）
- baseline / counterfactual 对照指标（不只是 MVP 内部可行性）
- 独立只读安全闸门（`external_dispatch` / `baseline_writeback` 运行时硬约束）
- MVPResult JSON 仅作为输入契约，不作为执行入口

**当前真实状态**：
- MVP Output JSON 可作为 ShadowReplayRunner 输入契约（Shadow Input Contract READY）
- ShadowReplayRunner 未实现（Shadow Execution Harness NOT IMPLEMENTED）
- 真实历史数据离线回放未执行（Real Data Replay NOT RUN）

**保持**：`external_dispatch=false` / `baseline_writeback=false` / `canonical_api_status=NOT_IMPLEMENTED` 三项硬约束不变。

**MVP 与 Shadow Mode 边界**：MVP 仅验证系统"输入 — 规划 — 求解 — 审计 — 结果"闭环在 LEGACY_SVDE_PIPELINE 下可跑通；**不**代表新架构 L0-L7 已落地，**不**代表 Shadow Mode 已实现。等候业务方签署 BIZ-01~09 后，方可启动 Phase 2（Canonical WorldState API 包装层）。
