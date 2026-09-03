# L0-L7 架构责任矩阵 (Architectural Responsibility Matrix)

**Document ID:** TOPPRISM-L0-L7-MATRIX-v1.0  
**Date:** 2026-08-24  
**Status:** **ARCHITECTURAL RESPONSIBILITY MATRIX (强制架构责任划分)**

---

## 一、L0-L7 分层定义与责任归属

| 层级 | 名称 | 所属子系统 | 核心责任 | 严禁跨界内容 |
| :--- | :--- | :--- | :--- | :--- |
| **L0** | 基础架构 | World Model | 整体拓扑与七大认知范畴隔离原则 | 严禁出现特定领域词汇 |
| **L1** | 通用元模型 | World Model | 定义领域无关的元类型与关系 | 严禁出现"拜访"、"频次"等业务词 |
| **L2** | 领域本体 | World Model | 各领域对象的特化定义 | 严禁混入动作、控制动作等实现细节 |
| **L3** | 动力学引擎 | World Model | 状态转移、反事实推演、约束求解空间 | 严禁包含规划器选择逻辑 |
| **L4** | 运行时状态实例 | World Model | 唯一 Canonical WorldState 实例 | 严禁包含执行器状态 |
| **L5** | 情景仿真 | World Model | 真正的多分支并行仿真与反事实链 | 严禁变成"单向未来推演" |
| **L6** | 规划器投影接口 | World Model → Decision Engine | 向决策引擎暴露**纯数学规划载荷**（PlannerStateProjection） | 严禁返回 CandidatePlan 或任何富语义业务对象 |
| **L7** | 企业决策引擎 | Decision Engine | 意图诊断、规划、审计、审批、执行反馈 | 严禁持有 WorldState 实例（仅持有 Projection） |

---

## 二、各层的输入输出与不可变契约

### L4 Operational WorldState（**World Model 持有的唯一快照**）
- **入参**: 真实业务主数据（客户、代表、合同、政策）
- **保持**: 不可变快照（immutable snapshot），业务主管通过版本化政策修改世界，而非直接修改 WorldState
- **出参**: 经查询接口被 L7 决策引擎读取、由 L5 情景推演分叉、由 L6 投影编译器消费

### L6 Planner Projection（**World Model 向 Decision Engine 暴露的纯数学切片**）
- **入参**: `L4 WorldState` + `L7 业务意图（DecisionIntent）`
- **保持**: 纯数学节点向量、路网成本矩阵、严格同周几模式空间、动作合成时长、锁定承诺掩码
- **出参（CONTR-3）**: **`PlannerStateProjection`（纯数学载荷）**
- **严禁 L6 返回 CandidatePlan 或任何富语义业务对象**；CandidatePlan 由 L7 消费 Projection 后调用 Domain Solver 求解生成

### L7 Enterprise Decision Engine（**消费 L6，不持有 WorldState**）
- **入参**: `L6 Projection`、`L7 Intent`、`L4 局部只读视图`（用于 Trade-off 评估）
- **保持**: 决策历史（DecisionArtifact）、审批记录、执行反馈队列
- **出参**: `DecisionArtifact`（含 audit_report_ref），下发到执行系统

### L5 Scenario / Simulation（**World Model 内部使用，不暴露给 L7**）
- 多分支并行 WorldState 副本，用于反事实推演
- 通过分支 ID（确定性 SHA-256）追溯

---

## 三、责任归属矩阵（责任分配）

| 操作 | 责任层 | 说明 |
| :--- | :--- | :--- |
| WorldState 实例化与版本化 | **L4 World Model** | 政策版本、归属冲突追踪、双时态 |
| 状态转移 (Transition) | **L3 World Model** | 守卫执行、事件溯源、审计哈希 |
| 情景反事实推演 | **L5 World Model** | 多维同步、容量影响、确定性时间 |
| 业务意图诊断 | **L7 Decision Engine** | IntentRouter 等 |
| 候选方案生成 | **L7 Decision Engine** | 消费 L6 Projection 调度 OR 求解器 |
| 多目标权衡评估 | **L7 Decision Engine** | 字典序目标函数 |
| 三维独立审计 | **L7 Decision Engine** | 物理/业务/语义审计（消费 L4 验证） |
| 人工审批 | **L7 Decision Engine** | HITL 防线 |
| 执行编排 | **L7 Decision Engine** | 向 SFA/CRM 下发 |
| 执行反馈闭环 | **L7 → L4** | ActualVisit 写回 WorldState |

---

## 四、当前代码归位与影响分析

| 当前文件 | 当前层位 | 实际应归位 |
| :--- | :--- | :--- |
| `contracts/world_state.py` | L4（已废弃） | **退役，改为 DTO 兼容层** |
| `world_model/state_snapshot.py` | **L4 Canonical** | OK |
| `world_model/transition_engine.py` | **L3 动力学** | OK |
| `world_model/planner_projection.py` | **L6 接口** | OK |
| `engine/periodic_pvrp_solver.py` | 误归位 SVDE | **必须降级为 Domain Solver（L7 内部组件）** |
| `engine/decision_pipeline.py` | 误归位 SVDE | **必须属于 L7 决策引擎（属于 Prism Decision Engine，不属于 SVDE）** |
| `diagnostics/cadence_auditor.py` | 误归位 SVDE | **必须属于 L3 动力学审计** |
| `diagnostics/schedule_verifier.py` | 误归位 SVDE | **必须属于 L3 物理可行性审计** |
| `diagnostics/plan_auditor.py` | 误归位 SVDE | **必须属于 L7 三维独立审计** |
| `real_data/world_state_assembler.py` | 误归位 SVDE | **必须属于 L4 数据装载** |
| `adapters/svde/bridge.py` | **SVDE 边界适配层** | OK（消费 L4 + 暴露给 L7） |
