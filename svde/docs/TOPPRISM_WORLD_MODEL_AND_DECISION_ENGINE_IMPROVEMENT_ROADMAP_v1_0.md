---
**Status:** PROPOSED CANONICAL — INTERNAL CONFLICT DETECTED
**Conflict:** 本文档内部同时含 L0-L6 与 L0-L7 表述
**Resolution:** 当前活跃层级以 L0-L7（PROPOSED CANONICAL）为权威；L0-L6 表述仅作为"World Model 子集"的过渡描述；待 Phase 0 完成全文档统一清理
**Date:** 2026-08-25

---

# TopPrism 世界模型与决策引擎提升计划清单 v1.0

状态：执行路线图（设计与实现前置基线）  
日期：2026-08-24  
适用范围：Prism Enterprise World Model、Prism Decision Engine、SVDE Sales Visit Decision Engine

## 1. 计划目标

将当前“世界模型规范 + 状态原型 + 领域求解器”提升为：

```text
可定义企业状态
→ 可追溯地接收观测
→ 可执行状态转移
→ 可分叉情景并推演后果
→ 可生成和比较候选决策
→ 可审计、审批和执行
→ 可将执行反馈回写世界模型
```

最终产品结构：

```text
TopPrism
└── Prism Enterprise Decision Intelligence
    ├── Prism Enterprise World Model (L0-L6)
    ├── Prism Decision Engine (L7)
    └── Domain Decision Engines
        └── SVDE Sales Visit Decision Engine
```

## 2. 当前基线

| 模块 | 当前成熟度 | 主要问题 |
|---|---:|---|
| L0 基础架构 | 3/5 | 文档已形成，需清理跨文档边界矛盾 |
| L1 通用元模型 | 3/5 | 需要与 L2/L3/L6 做最终一致性校验 |
| L2 销售拜访本体 | 3/5 | 3 次/月、SOP、承诺和政策仍需业务确认 |
| L3 状态转移 | 3/5 | DeferralPolicy、证据和事件持久化需完善 |
| L4 Canonical WorldState | 3/5 | 需建立正式查询、反馈和版本接口 |
| L5 Scenario Engine | 1/5 | 当前主要是改派原型，不是通用多分支仿真引擎 |
| L6 Planner Projection | 3/5 | 仍缺真实路网矩阵和完整状态投影门禁 |
| L7 Decision Engine | 1/5 | 目前主要停留在文档和现有管道归位设计 |
| SVDE Domain Solver | 3/5 | 需要降级为领域能力并接入 L7 |

五级成熟度定义：

```text
1  设计草案
2  代码原型
3  测试验证
4  真实业务验证
5  生产运行能力
```

## 3. 总体执行原则

1. 先修边界和契约，再改代码；
2. 业务规则和技术实现分开签署；
3. 事实、政策、承诺、计划、执行和推断不可折叠；
4. World Model 拥有 Canonical State，Decision Engine 不直接持有或修改它；
5. L5 通过 Scenario API 向 L7 提供推演结果，不直接暴露分支状态；
6. L6 只输出 PlannerStateProjection，不输出 DecisionArtifact；
7. 测试通过不能替代业务验证；
8. 所有收益必须来自同数据、同约束、同目标的对照实验。

## 4. Phase 0：规范一致性清理（P0，立即执行）

### 目标

消除现有 8 份上位约束文档之间的术语和接口矛盾。

### 任务清单

- [ ] 统一 L7 是否可以临时只读查询 WorldState 的定义；
- [ ] 明确 Decision Engine 不拥有、不修改、不持久化 Canonical WorldState；
- [ ] 将 L5 对外接口定义为 Scenario API + ScenarioResult/StateDelta；
- [ ] 将 L6 输出固定为 PlannerStateProjection；
- [ ] 将 CandidatePlan 和 DecisionArtifact 归入 L7；
- [ ] 区分 World Model 的约束定义和 Decision Engine 的目标权衡；
- [ ] 删除所有 `datetime.now()` 示例和默认值；
- [ ] 统一测试数量口径（313/314 等）；
- [ ] 统一 L0-L7 命名和文档引用；
- [ ] 明确每个接口的所有权、读写权限和版本号。

### 交付物

```text
TOPPRISM_L0_L7_CONTRACT_CONSISTENCY_REVIEW_v1_0.md
TOPPRISM_WORLD_MODEL_DECISION_ENGINE_INTERFACE_CONTRACT_v2_0.md
```

### 门禁

没有完成 Phase 0，不得启动代码重构。

## 5. Phase 1：业务语义签署（P0，和 Phase 0 并行）

### 目标

由业务责任人确认销售拜访领域的硬约束、软约束和例外政策。

### 必须确认

- [ ] 3 次/月的真实节奏语义；
- [ ] DeferralPolicy：允许顺延次数、期限、审批和补偿；
- [ ] Key/A 级门店的失访处理；
- [ ] GPS 偏差阈值；
- [ ] 工作时长和长途日弹性；
- [ ] 客户归属冲突优先级；
- [ ] 多产品线拜访是否合并；
- [ ] 决策审批层级；
- [ ] 大仓配送日历的权威来源；
- [ ] 真实路网成本的业务使用口径。

### 每个签署项必须包含

```text
业务问题
选定规则
适用范围
生效时间
责任人
例外条件
违反后的处理
证据来源
```

### 交付物

```text
BUSINESS_SIGNOFF_REQUIREMENTS.md（更新版）
SVDE_SALES_VISIT_POLICY_DECISION_LEDGER_v1_0.md
SVDE_SALES_VISIT_EXCEPTION_CATALOG_v1_0.md
```

### 门禁

未经业务签署的内容只能标记为 `PROPOSED`，不得进入硬约束和生产规划。

## 6. Phase 2：Canonical World Model API（P0）

### 目标

将 L4 从数据类集合提升为具备正式读写边界的世界模型运行时。

### 任务清单

- [ ] 唯一化 `OperationalDecisionWorldState`；
- [ ] 建立只读快照查询接口；
- [ ] 建立政策按 valid time 查询接口；
- [ ] 建立承诺查询和冲突查询接口；
- [ ] 建立执行反馈接收接口；
- [ ] 引入结构化 `Observation`、`EvidenceRecord`、`StateTransitionRecord`；
- [ ] 状态快照不可变，状态更新生成新版本；
- [ ] valid time 与 transaction time 分离；
- [ ] 状态变更引用政策版本和证据；
- [ ] 清理 `planned_frequency` 等过渡字段的实际使用；
- [ ] 建立旧 DTO 到 Canonical State 的显式转换器。

### 交付物

```text
TOPPRISM_CANONICAL_WORLD_STATE_API_SPEC_v1_0.md
TOPPRISM_EVIDENCE_AND_PROVENANCE_CONTRACT_v1_0.md
```

### 验收标准

- 同一个快照不可被原地修改；
- 所有状态变化可追溯到事件和证据；
- 任意时间点可重建有效状态；
- 政策、承诺、观察和推断没有隐式转换。

## 7. Phase 3：L3 Dynamics & Transition Engine（P0/P1）

### 目标

将状态机升级为真正的企业业务状态转移引擎。

### 任务清单

- [ ] 定义通用 `Action`、`Event`、`Transition` 契约；
- [ ] 完成所有状态转移守卫；
- [ ] 完成 DeferralPolicy；
- [ ] 缺少关键证据时 Fail-Closed；
- [ ] transition record 结构化持久化；
- [ ] 哈希覆盖事件、动作、证据、政策版本和基线快照；
- [ ] 所有时间参数显式传入；
- [ ] 禁止系统当前时间成为隐式业务时间；
- [ ] 校验 transaction time 不早于记录事件时间；
- [ ] 支持幂等重放；
- [ ] 支持失败转移和拒绝原因；
- [ ] 对业务例外保留人工升级路径。

### 交付物

```text
TOPPRISM_STATE_TRANSITION_ENGINE_SPEC_v2_0.md
TOPPRISM_EVENT_SOURCING_AND_REPLAY_SPEC_v1_0.md
```

### 验收标准

```text
相同基线状态 + 相同事件 + 相同时间 + 相同模型版本
→ 完全一致的新状态和审计摘要
```

## 8. Phase 4：L5 Scenario & Simulation Engine（P1）

### 目标

将当前单一改派函数升级为通用、多分支、可复现的情景推演引擎。

### 任务清单

- [ ] 定义 `Scenario`、`Perturbation`、`Rollout`、`ScenarioResult`；
- [ ] 从基线快照创建只读分支；
- [ ] 支持多个候选分支并行运行；
- [ ] 支持动作序列而非单个动作；
- [ ] 记录每个分支的假设和模型版本；
- [ ] 计算状态差异（State Delta）；
- [ ] 计算容量、距离、覆盖、承诺和风险变化；
- [ ] 传播不确定性和数据质量问题；
- [ ] 基线状态与情景状态严格隔离；
- [ ] 支持分支重放和结果比较；
- [ ] 通过 Scenario API 向 L7 返回结果，不暴露内部状态对象。

### 首批情景

- [ ] 客户改派；
- [ ] 代表请假；
- [ ] 突发插单；
- [ ] 客户延期；
- [ ] 大仓配送日变化；
- [ ] 路网成本变化；
- [ ] 频次政策变化。

### 交付物

```text
TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_SPEC_v1_0.md
```

### 验收标准

每个情景必须返回：

```text
base_snapshot_id
scenario_id
assumptions
transition_trace
expected_state_delta
constraint_violations
objective_delta
uncertainty
```

## 9. Phase 5：L6 Planner Projection（P1）

### 目标

将世界模型状态安全编译为领域无关的规划投影。

### 任务清单

- [ ] Projection 只输出数学载荷；
- [ ] 明确 Projection 的来源快照和政策版本；
- [ ] 真实路网矩阵接口化；
- [ ] 接入 OSRM、高德或其他经批准的成本来源；
- [ ] 保留距离、时间、来源和版本；
- [ ] 完成承诺日期到计划槽位的通用映射；
- [ ] 完成工作日历和时区处理；
- [ ] 缺少坐标、成本、政策或承诺时 Fail-Closed；
- [ ] 服务时长区分观测均值、规则估计和默认值；
- [ ] 不允许默认值伪装成真实观测；
- [ ] Projection ID 和内容摘要完全确定性。

### 验收标准

投影必须能回答：

```text
这个数学输入来自哪个 WorldState？
使用了哪个政策版本？
哪些节点被排除，为什么？
成本矩阵来自哪里？
哪些承诺被锁定？
哪些值是观测，哪些值是估计？
```

## 10. Phase 6：L7 Enterprise Decision Engine（P0/P1）

### 目标

把当前散落在 `decision_pipeline`、`plan_auditor` 和领域 solver 周围的能力，重构为独立的企业决策引擎。

### 建议模块

```text
l7_decision_engine/
├── intent/
├── capability_registry/
├── candidate_generation/
├── tradeoff/
├── audit/
├── approval/
├── execution/
└── artifacts/
```

### 任务清单

- [ ] Intent Diagnosis；
- [ ] Capability Orchestration；
- [ ] Candidate Generation；
- [ ] Planner Invocation；
- [ ] Trade-off Evaluation；
- [ ] 三维审计；
- [ ] HITL 审批；
- [ ] DecisionArtifact 持久化；
- [ ] 执行编排；
- [ ] ExecutionFeedback 发布；
- [ ] 失败和人工升级；
- [ ] 决策全过程可审计。

### 强制调用链

```text
Intent
→ Query World Model
→ Request Scenario Rollout (optional)
→ Compile Planner Projection
→ Domain Solver
→ Evaluate Trade-offs
→ Three-Dimensional Audit
→ Human Approval
→ DecisionArtifact
→ Execution
→ Feedback to World Model
```

### 验收标准

- L7 不直接修改 WorldState；
- L7 不内嵌状态转移守卫；
- L7 不绕过审计和审批；
- L7 可替换不同领域 solver；
- 每个 DecisionArtifact 可追溯到输入快照、投影、情景和审计结果。

### 交付物

```text
TOPPRISM_L7_ENTERPRISE_DECISION_ENGINE_SPEC_v1_0.md
TOPPRISM_DECISION_ARTIFACT_CONTRACT_v1_0.md
```

## 11. Phase 7：SVDE 领域迁移（P1）

### 目标

将 SVDE 从当前混合式代码结构降级为领域决策引擎，消费 Prism World Model 和 Prism Decision Engine。

### 任务清单

- [ ] 将周期 PVRP solver 标记为 SVDE Domain Solver；
- [ ] 将领域对象全部放入 L2；
- [ ] 将销售业务规则放入 L3 Domain Dynamics；
- [ ] 将三维审计归入 L7；
- [ ] 将 `decision_pipeline` 迁移到 L7；
- [ ] 将 `bridge.py` 改为正式领域适配器；
- [ ] 清理 SVDE 对 Canonical WorldState 的直接修改；
- [ ] 通过 Projection 接口调用 solver；
- [ ] 通过 DecisionArtifact 输出结果；
- [ ] 通过 ExecutionFeedback 更新状态。

### 验收标准

```text
SVDE 删除后，Prism World Model 和 Prism Decision Engine 仍可运行；
新增第二个领域 Decision Engine 时，不需要修改 L0/L1/L3 核心语义。
```

## 12. Phase 8：真实数据与业务验证（P1/P2）

### 目标

从测试验证进入真实业务验证，不把测试通过等同于生产能力。

### 验证顺序

- [ ] 真实数据质量预检；
- [ ] 主数据、政策、承诺和执行数据分源；
- [ ] 建立历史基线；
- [ ] 建立影子模式；
- [ ] 固定硬约束和业务目标；
- [ ] 运行方案推演；
- [ ] 人工复核；
- [ ] 小范围执行；
- [ ] 对比预期和实际后状态；
- [ ] 评估漂移和异常；
- [ ] 决定是否进入生产。

### 必须记录的指标

```text
频次合规率
覆盖率
锁定承诺履约率
计划变动量
在途时间
在途距离
客户面对面时间
代表工作负荷
未履约业务代价
预测与实际状态差异
```

收益百分比只有在同一数据、同一时间范围、同一硬约束和同一目标函数下才允许发布。

## 13. Phase 9：生产与对外发布门禁（P2）

### 生产门禁

- [ ] 所有核心业务规则已签署；
- [ ] L0-L7 契约一致；
- [ ] L3 转移可重放；
- [ ] L5 情景结果可比较；
- [ ] L6 投影来源可追溯；
- [ ] L7 决策产物可审计；
- [ ] 真实数据影子模式通过；
- [ ] 人工升级和回滚路径可用；
- [ ] 安全、权限和数据治理完成；
- [ ] 领域 owner 和平台 owner 明确。

### 对外发布门禁

未达到 Level 4 前，只能宣传：

```text
architecture
prototype
reference implementation
research and engineering framework
```

达到 Level 4 后，才可宣传真实业务验证案例；达到 Level 5 后，才可宣传生产级产品能力。

## 14. 近期执行顺序

### 现在立即做

1. [ ] 修复 8 份规范之间的契约矛盾；
2. [ ] 完成 L5 和 L7 两份详细规范；
3. [ ] 将业务签署和技术决策分开；
4. [ ] 向业务 owner 发出 10 项签署清单；
5. [ ] 建立 Decision Engine 代码迁移清单。

### 业务签署后做

6. [ ] 提交代码实现计划；
7. [ ] 先实现 World Model API 和事件转移；
8. [ ] 再实现 L5 Scenario Engine；
9. [ ] 再实现 L7 Decision Engine；
10. [ ] 最后迁移 SVDE Domain Solver。

### 代码重构后做

11. [ ] 真实路网接入；
12. [ ] 真实数据影子模式；
13. [ ] 销售拜访业务回放；
14. [ ] 预期/实际后状态对比；
15. [ ] 生产门禁评审。

## 15. 最终路线判断

当前最重要的不是增加测试数量，而是完成以下三个结构性转变：

```text
从“状态对象”升级为“可执行世界模型”
从“领域管道”升级为“企业决策引擎”
从“测试通过”升级为“真实业务状态闭环验证”
```

在这三个转变完成前，SVDE 应保持为第一个领域参考实现，不应重新包装成已经完成的通用企业决策平台。
