---
**Status:** PROPOSED CANONICAL — INTERNAL CONFLICT DETECTED
**Conflict:** 本文档内部同时含 L0-L6 与 L0-L7 表述
**Resolution:** 当前活跃层级以 L0-L7（PROPOSED CANONICAL）为权威；L0-L6 表述仅作为"World Model 子集"的过渡描述；待 Phase 0 完成全文档统一清理
**Date:** 2026-08-25

---

# TopPrism 架构差异矩阵 v1.0.1

**Document ID:** TOPPRISM-ARCHITECTURE-ALIGNMENT-MATRIX-v1_0_1
**Date:** 2026-08-25
**Status:** **DESIGN-TIME GAP MATRIX — 当前架构差异清单（含 Baseline v1.0 语义纠偏后的状态）**
**上游约束:** `TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md`、`TOPPRISM_SALES_VISIT_VERTICAL_SLICE_ARCHITECTURE_v1_0.md`
**比较对象:** 当前文档设计 vs 当前代码实现 vs Canonical 架构要求
**严格红线:** 本文档不修改 runtime，不修复代码问题

---

## 一、对比框架

**四级成熟度口径（强制区分）**：

| 成熟度等级 | 定义 | 文档标记 |
|---|---|---|
| **组件代码存在** | Compiler / Auditor / IntentRouter 等组件代码已存在但未接入子系统 | `IMPLEMENTED` |
| **数据链路已接通** | 代码存在且与 WorldState 数据契约完整连接 | `DATA_LINK_CONNECTED` |
| **子系统已实现** | L0/L1/L2/.../L7 任一子系统内部所有模块已上线 | `SUBSYSTEM_IMPLEMENTED` |
| **Runtime 已验证** | 在真实数据影子模式下完整跑通 | `RUNTIME_VERIFIED` |

**严禁将"组件代码存在"误判为"子系统已实现"**。

**对比框架标记**：

```text
DESIGN CONFIRMED              — 文档设计与 Canonical 要求一致
DESIGN GAP                    — 文档设计与 Canonical 要求有差异
DOCUMENT_CONTRACT_INCONSISTENCY — 文档内部自相矛盾（同一文档内不同节冲突）
IMPLEMENTED                   — 组件代码存在（仅指第四级口径第 1 项）
DATA_LINK_CONNECTED           — 数据链路已接通
SUBSYSTEM_IMPLEMENTED         — 子系统已实现
RUNTIME_VERIFIED              — Runtime 已验证
PARTIALLY IMPLEMENTED         — 代码部分实现
NOT IMPLEMENTED               — 代码层尚未实现
CONTRADICTORY                 — 代码实现与文档设计/Canonical 相反
RUNTIME PARTIAL               — 代码可运行但与新架构有冲突
BUSINESS DECISION REQUIRED    — 需业务方裁决
```

---

## 二、模块差异矩阵

### 2.1 L0 Foundational Architecture

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 八大不变量 | DESIGN CONFIRMED（SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC §4） | NOT IMPLEMENTED（无代码级不变量校验） | DESIGN CONFIRMED | 仅文档级，未强制到代码 | 中 | 在 L3 Transfer 与 L5 Rollout 入口增加 invariant assertions |
| 时间模型（valid/transaction/forecast/scenario/execution） | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（BitemporalPeriod 类已定义） | DESIGN CONFIRMED | 文档覆盖完整；代码仅实现 valid/transaction 两时间 | 中 | 在 WorldState 增加 forecast_time / scenario_time 字段 |
| 证据与不确定性（PROV-O） | DESIGN CONFIRMED（§7） | NOT IMPLEMENTED（无 EvidenceRecord 类） | DESIGN CONFIRMED | 缺统一证据结构 | 高 | Phase 2 增加 EvidenceRecord 与 SourceManifest 统一 |

### 2.2 L1 General Metamodel

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 8 个基础元类型（Entity/Relation/Policy/Demand/Commitment/Action/Event/Observation） | DESIGN CONFIRMED（SVDE_WORLD_MODEL_METAMODEL_SPEC §2） | PARTIALLY IMPLEMENTED（state_snapshot.py 含 Customer/Resource/AccountHierarchy/ProductLineScope/SupplyNode/InStoreActionFact/MerchandisingComplianceFact/ActualVisitEvent） | DESIGN CONFIRMED | **缺 MetaRelation / MetaPolicy 通用基类**（Relation 仅隐式存在于 OwnershipPolicy；Policy 仅 CadenceRule/OperationalVisitPolicy/DeferralPolicy 三种具体类） | 中 | Phase 2 引入通用 Policy/Relation 基类或确认现有具体类已充分 |
| 3 个衍生元类型（DerivedEstimate/Plan/Scenario） | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（DerivedDepotEstimate 已实现；Plan 仅 CandidatePlan 具体类；Scenario 缺统一类） | DESIGN CONFIRMED | 缺通用 Scenario 类（当前 OperationalDecisionWorldState.active_scenario_branches: Dict[str, Any] 不规范） | 高 | Phase 2 引入通用 Scenario 类，并从 L4 WorldState 移除 active_scenario_branches |
| L1 严禁出现业务词 | DESIGN CONFIRMED | 部分违规（state_snapshot.py OperationalCustomer 含 `planned_frequency` 业务字段） | DESIGN CONFIRMED | **违反 L1 严禁领域词铁律**（planned_frequency 属于 L2/L3 业务规则） | 中 | Phase 2 将 planned_frequency 从 L1/L2 实体移除，改由 L3 CadenceRule 提供 |
| Entity 身份稳定性 | DESIGN CONFIRMED | IMPLEMENTED（state_snapshot.py 用 store_code / rep_id / visit_id 等业务主键） | DESIGN CONFIRMED | OK（业务主键稳定） | 低 | — |

### 2.3 L2 Domain Ontology

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 24 个核心对象（Customer/Resource/AccountHierarchy/ProductLineScope/SupplyNode/CadenceSpec/VisitPolicy/OwnershipPolicy/InStoreActionTaxonomy/Commitment/VisitDemand/ActualVisit/InStoreActionFact/MerchandisingCompliance/TravelCostMatrix 等） | DESIGN CONFIRMED（SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC §2） | PARTIALLY IMPLEMENTED（state_snapshot.py 含 18+ 对象；**缺 CadenceSpec / VisitPolicy / OwnershipPolicy / TravelCostMatrix / Territory / StartEndPolicy**） | DESIGN CONFIRMED | 多个 L2 对象缺失或被合并 | 中 | Phase 2 补齐缺失 L2 对象 |
| L2 严禁混入转移/求解 | DESIGN CONFIRMED | CONTRADICTORY（CustomerEntity 含 planned_frequency 业务规则） | DESIGN CONFIRMED | 违反 L2 严禁动作/控制 | 中 | Phase 2 分离 |

### 2.4 L3 Dynamics & State Transition

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| Transfer 守卫（Guard A-E） | DESIGN CONFIRMED | IMPLEMENTED（transition_engine.transition_visit_status 含 Guard A approver_id / Guard B duration≥10 / Guard C GPS≤500m / Guard D time-cond / Guard E DeferralPolicy） | DESIGN CONFIRMED | OK | 低 | — |
| Transfer 函数命名 | DESIGN CONFIRMED（Canonical: `request_transition`） | **CONTRADICTORY**（当前实现名 `transition_visit_status`，仅服务 visit_lifecycle_records；不服务承诺/政策/分配） | DESIGN CONFIRMED | **缺 Canonical API 包装层**；函数只处理 visit 转移，不处理 ownership 冲突、policy 升级、commitment 状态等 | 高 | Phase 3 引入 `request_transition` 包装器，支持所有可转移实体 |
| Transfer 多实体支持 | DESIGN CONFIRMED（visit / ownership / policy / commitment 都可转移） | **NOT IMPLEMENTED**（transition_visit_status 仅支持 visit 实体） | DESIGN CONFIRMED | 严重缺口 | 高 | Phase 3 实现 |
| 事件溯源 StateTransitionRecord | DESIGN CONFIRMED | IMPLEMENTED（含 audit_hash） | DESIGN CONFIRMED | OK | 低 | — |
| 哈希算法 RFC 8785 + 双路径 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（_deterministic_hash 用 SHA256 但未 RFC 8785） | DESIGN CONFIRMED | 跨语言一致性未保证 | 中 | Phase 3 等 A.2 RFC 8785 选型完成 |
| DeferralPolicy | DESIGN CONFIRMED | IMPLEMENTED | DESIGN CONFIRMED | OK | 低 | — |
| L3 严禁包含规划选择 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（transition_engine 含 `_resolve_active_frequency_v2` 通过 PolicyRegistry 查 OperationalVisitPolicy.target_frequency_per_month — OK；但不应内嵌业务判断） | DESIGN CONFIRMED | 边界基本正确 | 低 | — |

### 2.5 L4 BaselineWorldState

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 不可变快照 | DESIGN CONFIRMED（@dataclass(frozen=True) + 不可原地修改） | IMPLEMENTED（state_snapshot.py OperationalDecisionWorldState @dataclass(frozen=True)） | DESIGN CONFIRMED | OK | 低 | — |
| 双时态（BitemporalPeriod） | DESIGN CONFIRMED | IMPLEMENTED | DESIGN CONFIRMED | OK | 低 | — |
| 三类状态物理分离 | DESIGN CONFIRMED | **设计目标**：BaselineWorldState 应仅含基线；execution_fact_stream 应迁移至独立 `ExecutionEventStore`；`active_scenario_branches` 必须从 L4 移除。**当前实现**：旧字段仍存在于 `OperationalDecisionWorldState`，已标 DEPRECATED。**状态**：NOT IMPLEMENTED（修复 P0-2/P0-9） | DESIGN CONFIRMED（统一为方案 B：ExecutionEventStream 独立子资源） | 严重（语义混合导致基线被污染） | 高 | Phase 2 完整拆分：移除旧字段、独立 ExecutionEventStore、L5 沙箱接口化 |
| Ownership Conflict Records | DESIGN CONFIRMED | IMPLEMENTED | DESIGN CONFIRMED | OK | 低 | — |
| WorldState alias | DESIGN CONFIRMED | IMPLEMENTED（WorldState = WorldStateSnapshot = OperationalDecisionWorldState） | DESIGN CONFIRMED | OK | 低 | — |
| 严防 derived 冒充 fact | DESIGN CONFIRMED | IMPLEMENTED（DerivedDepotEstimate 含 CognitiveCategory.DERIVED_ESTIMATE） | DESIGN CONFIRMED | OK | 低 | — |
| SourceManifest | DESIGN CONFIRMED | IMPLEMENTED | DESIGN CONFIRMED | OK（已拒绝 `datetime.now()` 默认值） | 低 | — |

### 2.6 L5 Scenario & Counterfactual Engine

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 通用多分支反事实引擎 | DESIGN CONFIRMED（TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_DETAILED_SPEC §1） | **NOT IMPLEMENTED**（transition_engine.rollout_reallocation_scenario 是单点改派函数，不是通用多分支引擎） | DESIGN CONFIRMED | **严重缺口**：当前实现未支持多分支并行、PerturbationEvent 序列、StateDelta 结构化、Capacity Impact 摘要 | **高** | Phase 4 实现完整 L5 引擎 |
| Scenario API 单值返回 | DESIGN CONFIRMED（仅返回 ScenarioResult，不返回 BranchedWorldState） | NOT IMPLEMENTED | DESIGN CONFIRMED | — | 高 | Phase 4 |
| simulation_time 显式 | DESIGN CONFIRMED | NOT IMPLEMENTED | DESIGN CONFIRMED | — | 高 | Phase 4 |
| 严禁写回 baseline | DESIGN CONFIRMED | **CONTRADICTORY**（当前 rollout_reallocation_scenario 实际返回新 WorldState，违反"不写回"原则——它不是 scenario，是另一种 transfer） | DESIGN CONFIRMED | 严重 | 高 | Phase 4 重命名函数为 `_apply_ownership_change` 并移至 L3 transfer 范畴 |

### 2.7 L6 Planner Projection

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| 仅返回纯数学载荷 | DESIGN CONFIRMED | IMPLEMENTED（PlannerStateProjection 不含 CandidatePlan 字段） | DESIGN CONFIRMED | OK | 低 | — |
| 频次来源：版本化政策 | DESIGN CONFIRMED | **组件代码存在**（`_resolve_active_frequency_v2` 从 PolicyRegistry.operational_policies 读取 OperationalVisitPolicy.target_frequency_per_month） | **数据链路未完全接通**：WorldStateAssembler 生成 cadence_rules，planner_projection 读 PolicyRegistry.operational_policies，两者数据契约未同步 | 数据契约需同步 | 中 | Phase 5 完整接通数据契约 |
| 服务时长来源：观测均值 | DESIGN CONFIRMED | IMPLEMENTED（synthesize_service_duration_from_observations） | DESIGN CONFIRMED | OK | 低 | — |
| 路网来源标识 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（haversine_distance_km + estimated_transit_time_min 标注 "speed_kmh=35.0" 默认值） | DESIGN CONFIRMED | 需补"OSRM/真实路网"标识 | 中 | Phase 5 接入 OSRM 或保留 Haversine 估算但标注"ESTIMATED" |
| 缺坐标门禁 | DESIGN CONFIRMED | IMPLEMENTED（unplannable_nodes_excluded 字段已存在；但当前未在 compile_projection 中真正剔除 UNMAPPED 门店） | DESIGN CONFIRMED | 需代码层验证 | 中 | Phase 5 |
| 节点拓扑 + 矩阵 + 模式空间 + 锁定掩码 + 容量预算 | DESIGN CONFIRMED | IMPLEMENTED | DESIGN CONFIRMED | OK | 低 | — |

### 2.8 L7 Enterprise Decision Engine

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| Intent Diagnosis | DESIGN CONFIRMED | IMPLEMENTED（diagnostics/intent_router.py） | DESIGN CONFIRMED | OK | 低 | — |
| Capability Orchestration | DESIGN CONFIRMED | NOT IMPLEMENTED as separate module | DESIGN CONFIRMED | 缺独立编排模块 | 中 | Phase 6 |
| Trade-off 多目标字典序 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（内嵌在 PeriodicPVRPSolver，未独立） | DESIGN CONFIRMED | 需独立 | 中 | Phase 6 |
| 三维独立审计 | DESIGN CONFIRMED | IMPLEMENTED（diagnostics/plan_auditor.py） | DESIGN CONFIRMED | OK | 低 | — |
| HITL 人工审批 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（decision_pipeline.human_approve_and_publish 使用 `datetime.datetime.now()` **违反时间契约**） | DESIGN CONFIRMED | **严重**：违反"时间参数强制显式"铁律 | 高 | Phase 6 修复：`approval_timestamp` 必须由调用方传入；DecisionArtifact 使用 ApprovalStatus enum 而非 string |
| DecisionArtifact Storage | DESIGN CONFIRMED | NOT IMPLEMENTED as persistent storage（仅生成对象） | DESIGN CONFIRMED | 缺持久化 | 中 | Phase 6 |
| Approval Lifecycle enum | DESIGN CONFIRMED（DESIGN 草案 DRAFT/EVALUATED/APPROVED/PUBLISHED/REVOKED/EXPIRED） | **NOT IMPLEMENTED**（当前 DecisionArtifact.status 是 string "APPROVED_FOR_EXECUTION"） | DESIGN CONFIRMED | 状态机退化 | 中 | Phase 6 |
| Execution Adapter | DESIGN CONFIRMED | NOT IMPLEMENTED（缺 SFA/CRM REST 适配器） | DESIGN CONFIRMED | 缺独立模块 | 中 | Phase 6 |
| DecisionArtifact 严禁绕过审计 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（pipeline 强制要求 approver_id 但未强制 audit_report） | DESIGN CONFIRMED | 缺校验 | 中 | Phase 6 |
| L7 严禁持有 WorldState | DESIGN CONFIRMED | **CONTRADICTORY**（decision_pipeline.generate_candidate_and_audit 接收 `world_state: WorldState` 参数并直接读取其字段；这是 L7 Enterprise Decision Engine 子系统未实现的子症状，**IntentRouter 组件存在但未接入子系统**） | DESIGN CONFIRMED | 严重 | 高 | Phase 6 改为只接收 ReadOnlyWorldStateView |
| L7 严禁内嵌守卫 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（pipeline 未直接内嵌，但 PeriodicPVRPSolver 含 `_resolve_active_frequency_v2` 调用——属于合理频次解析，但仍依赖 PolicyRegistry） | DESIGN CONFIRMED | 边界模糊 | 中 | Phase 6 |
| Solver 接受 L6 投影 | DESIGN CONFIRMED | **CONTRADICTORY**（PeriodicPVRPSolver.solve(payload) 接受 bridge 拼装的 dict 而非 L6 PlannerStateProjection） | DESIGN CONFIRMED | 严重：绕过 L6 直接喂数据 | 高 | Phase 6 改签名为 `solve(projection: PlannerStateProjection)` |
| Bridge 直接读 WorldState | DESIGN CONFIRMED | **CONTRADICTORY**（bridge.dispatch_planning_intent 读取 `world_state.resources[rep_id].home_depot_coord` 与 `world_state.policies.chongchuan_depot`） | DESIGN CONFIRMED | 严重：违反 L7 边界 | 高 | Phase 6 Bridge 改为接受 L6 PlannerStateProjection 输入 |

### 2.9 SVDE Domain Components

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| Domain Adapter 职责 | DESIGN CONFIRMED（仅适配、不读 WorldState、不解释语义） | **CONTRADICTORY**（bridge.py 直接读 WorldState 字段） | DESIGN CONFIRMED | 严重 | 高 | Phase 7 Bridge 重写 |
| Domain Solver 签名 | DESIGN CONFIRMED（接受 PlannerStateProjection） | CONTRADICTORY（接受 dict payload） | DESIGN CONFIRMED | 严重 | 高 | Phase 7 Solver 重签 |
| Domain Audit 位置 | DESIGN CONFIRMED（cadence_auditor + schedule_verifier 归 L3；plan_auditor 归 L7） | PARTIALLY IMPLEMENTED（cadence_auditor + schedule_verifier 在 diagnostics/，归属未明确；plan_auditor 在 diagnostics/ 但应归 L7） | DESIGN CONFIRMED | 命名/归属混乱 | 中 | Phase 7 目录重构 |
| WorldStateAssembler | DESIGN CONFIRMED（归 L4 数据装载） | IMPLEMENTED（real_data/world_state_assembler.py） | DESIGN CONFIRMED | OK | 低 | — |
| FrequencyAudit | DESIGN CONFIRMED（归 L3 Dynamics 审计） | NOT IMPLEMENTED as separate（cadence_auditor 当前是 L7 内部工具，需归位 L3） | DESIGN CONFIRMED | 归位错误 | 中 | Phase 7 目录重构 |

### 2.10 跨文档一致性

| 维度 | 当前文档设计 | 当前代码实现 | Canonical 要求 | 差异 | 风险 | 下一步 |
|---|---|---|---|---|---|---|
| L0-L7 分层唯一化 | **DESIGN GAP → 部分迁移**（旧 FOUNDATIONAL SPEC v1.0 已加 HISTORICAL+MIGRATED-TO 头；仍有 5 份 L0-L6 文件名文档 + 3 份同含 L0-L6 与 L0-L7 的新文档未修订） | — | DESIGN CONFIRMED（统一 L0-L7） | **DOCUMENT_CONTRACT_INCONSISTENCY** | 中 | Phase 0 完成 9 份 B/D 类文档迁移 |
| COMMITTED 状态语义 | DESIGN GAP（COMMITTED 既指"承诺"又指"拜访执行锁"，混用） | IMPLEMENTED（LifecycleStatus.COMMITTED 用作拜访状态） | DESIGN CONFIRMED（Commitment 生命周期用 COMMITTED；Visit 生命周期用 COMMITTED 但语义是"已下发执行"——需分离） | 术语歧义 | 高 | Phase 0 引入 CommitmentLifecycle.COMMITTED 与 VisitLifecycle.DISPATCHED 等不同术语 |
| 时区处理 | DESIGN CONFIRMED | PARTIALLY IMPLEMENTED（transition_engine 已禁 naive datetime） | DESIGN CONFIRMED | OK | 低 | — |

---

## 三、P0/P1 架构缺口汇总

### P0（必须先修复才能继续）

| 缺口 | 影响 | 修复工作量 |
|---|---|---|
| **P0-1: L7 Decision Engine 未实现 Canonical API 包装层** | 步骤 1/2/3/4/6/13 无 Canonical API 入口 | M |
| **P0-2: `OperationalDecisionWorldState.active_scenario_branches` 字段必须从 L4 移除** | Scenario 污染 Baseline | S |
| **P0-3: `decision_pipeline.human_approve_and_publish` 使用 `datetime.now()`** | 违反时间契约 | S |
| **P0-4: `bridge.dispatch_planning_intent` 直接读 WorldState 字段** | 违反 L7 边界 | M |
| **P0-5: `PeriodicPVRPSolver.solve(payload)` 接受 dict 而非 PlannerStateProjection** | 绕过 L6 | M |
| **P0-6: `transition_engine.transition_visit_status` 仅服务 visit 实体，缺多实体 Transfer** | 承诺/政策/分配无法通过统一守卫 | M |
| **P0-7: `rollout_reallocation_scenario` 不是真正的 L5 反事实引擎** | 严重缺口 | L |

### P1（架构层修复，可在 P0 后启动）

| 缺口 | 影响 | 修复工作量 |
|---|---|---|
| **P1-1: DecisionArtifact.status 用 string 而非 enum** | 状态机退化 | S |
| **P1-2: L1/L2 OperationalCustomer.planned_frequency 业务字段违规** | 违反 L1/L2 铁律 | S |
| **P1-3: cadence_auditor 仍读 `info.get("planned_frequency")` 观测字段** | 与版本化 CadenceRule 冲突 | S |
| **P1-4: 缺通用多分支反事实引擎** | 步骤 4/5 不可实现 | L |
| **P1-5: 缺 SFA/CRM Execution Adapter** | 步骤 12 不可实现 | M |
| **P1-6: 缺独立 Capability Orchestration 模块** | L7 缺编排能力 | M |
| **P1-7: 缺独立 Trade-off 模块（当前内嵌 Solver）** | L7 缺独立权衡 | M |
| **P1-8: 缺独立 DecisionArtifact Storage** | 决策不可审计 | M |

### P2（生产化阶段，可延后）

| 缺口 | 影响 | 修复工作量 |
|---|---|---|
| **P2-1: 真实路网矩阵接入 OSRM** | 步骤 6 路网估算不精确 | L |
| **P2-2: 跨语言 RFC 8785 一致性哈希** | 跨语言一致性 | M（待 A.2 选型） |
| **P2-3: WorldState 时间模型扩展（forecast/scenario/execution_time）** | 多时间维度完整 | M |
| **P2-4: ExecutionEvent Stream 与 Baseline 分离** | 语义边界更清晰 | M |

---

## 四、需业务方签署的 9 项（BIZ-01~BIZ-09，统一编号）**

| ID | 业务问题 | 影响步骤 | 状态 |
|---|---|---|---|
| **BIZ-01** | CADENCE 频次语义（1A/2A/3A/B/C/D 各级别实际节奏与误差窗口） | 步骤 1/3/10 | PENDING |
| **BIZ-02** | 3 次/月频次具体语义 | 步骤 3/10 | PENDING |
| **BIZ-03** | DeferralPolicy：允许顺延次数、期限、审批层级、补偿 | 步骤 4/10 | PENDING |
| **BIZ-04** | Key/A 级门店零脱访刚性（REQUIRED 强履约） | 步骤 4/10 | PENDING |
| **BIZ-05** | GPS 偏差阈值与降级策略 | 步骤 13 (Guard C) | PENDING |
| **BIZ-06** | 工作时长双重红线（普通日 / 长途日弹性上限） | 步骤 10 | PENDING |
| **BIZ-07** | 归属冲突优先级（同店多人 vs 多店归属一人） | 步骤 4 (REASSIGN) | PENDING |
| **BIZ-08** | 多产品线拜访是否合并（皇家美素 + 源悦同访 vs 分访） | 步骤 3 | PENDING |
| **BIZ-09** | 决策审批层级（哪些场景需主管审批 vs 系统自动批准） | 步骤 11 | PENDING |

---

## 五、下一阶段 Runtime 实施顺序（基于 P0/P1 优先级）

1. **Phase 2（已规划）**：Canonical WorldState API + L1/L2 实体清理（修复 P0-2、P1-2）+ **Baseline/ExecutionEventStream/ScenarioState 三类状态结构代码层拆分（修复 P0-2 实质部分）**
2. **Phase 3（已规划）**：L3 Dynamics & Transfer + **多实体 Transfer（含 ResourceAvailabilityLifecycle 与 ResourceAvailabilityObservation）** + 时间契约全面合规（修复 P0-3、P0-6、**P0-8 资源可用性多实体**）
3. **Phase 4（已规划）**：L5 通用反事实引擎（修复 P0-7、P1-4）+ **强制只返回 ScenarioResult/StateDelta，禁止返回新 WorldState**
4. **Phase 5（已规划）**：L6 Planner Projection + 真实路网接入（修复 P1-3 + P2-1）+ **WorldState → L6 数据契约完整接通**
5. **Phase 6（已规划）**：L7 Decision Engine 重构（修复 P0-1、P0-3、P0-4、P0-5、P1-1、P1-5、P1-6、P1-7、P1-8）+ **Canonical API 包装层**
6. **Phase 7（已规划）**：SVDE Domain 迁移（修复 P0-4、P0-5 剩余部分） + **bridge.py 改为接受 L6 Projection 输入而非读 WorldState**
7. **Phase 8（已规划）**：真实数据影子模式（**目标**：在受控环境下完整跑通"代表请假 3 天重排"14 步 DESIGN DEMO，**验证 Vertical Slice 从 DESIGN-ONLY 升级为 RUNTIME-PROVEN**）
8. **Phase 9（已规划）**：生产门禁（真实业务验证 → Level 4 → 对外发布）

---

## 六、当前架构准确状态（语义纠偏后 v1.0.1）

```
Architecture Baseline:             PROPOSED / PARTIALLY ALIGNED
Document Contract Consistency:     BLOCKED       (9 份 B/D 类文档未修订)
L0-L7 Canonical Sync:              BLOCKED       (旧 FOUNDATIONAL 已加头；5 份 L0-L6 文件名文档未改)
Baseline–Event–Scenario:           DESIGN DEFINED / RUNTIME NOT IMPLEMENTED
Resource Transfer Model:           DESIGN INCOMPLETE (P0-6 多实体 Transfer 未实现)
L5 Scenario Engine:                NOT IMPLEMENTED
L7 Decision Engine:                NOT IMPLEMENTED
IntentRouter 组件:                代码存在
SVDE Domain Pipeline:              RUNTIME PARTIAL (与新架构存在 7 处 P0 冲突)
Vertical Slice:                    DESIGN-ONLY, NOT PROVEN
Business Sign-off:                 PENDING       (BIZ-01~09 待签)
Freeze Review:                     BLOCKED
```

**冻结前置条件**：
1. 完成 9 份 B/D 类文档迁移（B 类 5 份：含 L0-L6 文件名文档加 MIGRATED-TO；D 类 4 份：清理内部 L0-L6 与 L0-L7 并存）
2. Baseline/Event/Scenario 代码层拆分（修复 P0-2/P0-9）
3. L5 通用反事实引擎实现（修复 P0-7）
4. L7 Canonical API 包装层 + 多实体 Transfer（修复 P0-1/P0-6）
5. BIZ-01~09 业务签署 + 双轨技术签署
6. → v1.0-FROZEN
