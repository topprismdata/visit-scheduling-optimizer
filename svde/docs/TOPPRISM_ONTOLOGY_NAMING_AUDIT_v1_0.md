# TopPrism 本体命名与字段审计报告 (Kitchen Sink / Misnomer 审计)

**Document ID:** TOPPRISM-ONTOLOGY-NAMING-AUDIT-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 审计完成 — 处置项待立项 (代码修改受签署门禁约束)
**审计对象:** `svde/ontology/src/prism_ontology/world_model/state_snapshot.py` 全部 22 类型 / 130 字段
**方法论:** TOPPRISM_ONTOLOGY_DESIGN_REVIEW_VS_PALANTIR_v1_0.md 建议 7; Palantir Anti-Patterns (Kitchen Sink / Misnomer / God Object) + Naming Conventions
**工具:** 机械扫描 (裸名词 / DEPRECATED / 源系统命名残留 / 管道元数据) + 全字段人工复核

---

## 一、审计结论总览

| 检查项 | 结果 |
|---|---|
| 裸歧义名词 (value/quantity/score/type/date/name 裸用) | **0 处** ✅ |
| 源系统命名残留 (dtLastInspMod 式) | **0 处** ✅ |
| 管道元数据字段 (extracted_at/batched_at 等) | **0 处** ✅ |
| DEPRECATED 字段 | **1 处** ⚠️ |
| stringly-typed 枚举 (裸 str 应为 Enum) | **6 处** ⚠️ |
| **类型封闭红线违规 (Any 入公共字段)** | **1 处** 🔴 P0 |
| DDD 存疑 (源系统概念 vs 领域概念) | **2 项** ⚠️ |

---

## 二、P0 违规 (签署后首批修复)

### P0-1: `OperationalDecisionWorldState.active_scenario_branches: Dict[str, Any]`

- **违规**: 项目红线 "严禁 `Any` 进入公共 API 字段; 使用 `FrozenValue` 递归不可变联合类型"
- **旁证**: 架构基线 §十一 已标注 "Baseline–Event–Scenario: BLOCKED (代码层 execution_fact_stream/scenario_branches 仍混入 L4)"
- **处置**: L5 场景引擎实现时删除该字段 — 场景分支状态由 L5 Scenario Engine 持有 (WorldState 三权分离: L5 严禁暴露分支状态), WorldState 不携带场景状态。**不是改类型, 是删字段**。

---

## 三、⚠️ 处置项 (规范层可先行定义目标, 代码迁移待签署)

### A-1: `OperationalCustomer.planned_frequency: Optional[int]` [Kitchen Sink]

- 现状: 自带 `# DEPRECATED: Kept for back-compat. Source must be PolicyRegistry, not observation.` 注释
- 消费方核查: `planner_projection.py` 已改走 PolicyRegistry (FIX-1), 无生产读取方
- **处置**: 删除字段; 保留 `PolicyRegistry.operational_policies` 为频次唯一事实源

### A-2: stringly-typed 枚举 (6 处裸 `str` 应为 Enum)

| 字段 | 现值域 | 处置 |
|---|---|---|
| `OperationalCustomer.tier` | Key/A/B/C/D | 新增 `StoreTier` 枚举; 同时消除与 `AccountHierarchyEntity.channel_tier` (NKA/RKA 体系) 的歧义 — 两个"tier"是不同概念, Misnomer 风险 |
| `OperationalVisitPolicy.cadence_type` | STRICT_WEEKLY/BIWEEKLY/MONTHLY | 与 `CadenceRule.cadence_type` 共用新增 `CadenceType` 枚举 |
| `CadenceRule.cadence_type` | 同上 | 同上 |
| `OperationalCommitment.lock_level` | FREE/DAY_LOCKED/SEQUENCE_LOCKED | 新增 `LockLevel` 枚举 |
| `OwnershipConflictRecord.resolution_status` | FLAGGED_FOR_REVIEW/... | 新增 `ConflictResolutionStatus` 枚举 |
| `SupplyNodeEntity.delivery_status` | UNCALIBRATED/... | 新增 `DeliveryStatus` 枚举 |

### A-3: `PolicyRegistry.ownership_map: Dict[str, str]` [结构升级]

- **处置**: 评审报告建议 2 已立项 — `OwnershipAssignment` (§38) 落地后, `ownership_map` 降级为 §38 当前态投影, 最终删除裸映射。

### A-4: DDD 存疑 — `CognitiveCategory` 全类型铺开

- 现状: `category: CognitiveCategory` (OBSERVATION/POLICY/COMMITMENT/MEASUREMENT/DERIVED_ESTIMATE) 出现在 8 个类型上
- **问题**: 这是"认知来源标签" (数据溯源语义), 不是领域实体自身的业务属性 — 按 DDD 原则属**数据血缘**, 应归属 `DecisionLineageRecord` / `SourceManifest` 体系, 而非散布在领域实体上
- **处置**: 评审后裁决 — 保留 (若业务确认其运营语义) 或迁移至 Lineage 体系

### A-5: DDD 存疑 — `OperationalDecisionWorldState` 容器性质

- 现状: 15 个字段的世界状态容器, 含 `Dict[str, X]` 五个实体字典
- **裁定**: **不判 God Object** — 它是状态快照 (检查点), 不是领域实体; Palantir God Object 反模式针对"单类型承载多实体", 快照容器不适用。但需在 §十二.2 反模式禁令下持续监督: 新字段进入 WorldState 须过"这是世界状态还是实体属性"审查 (P0-1 的 `active_scenario_branches` 即反例)。

---

## 四、通过项 (无需处置)

- 命名质量整体良好: 全部字段为自解释业务语言, 无编码前缀, 无系统列名残留
- `BitemporalPeriod` / `SourceManifest.assembled_at` 等时间字段已符合时间契约 (2026-08-26 修复)
- `FrozenScalar`/`FrozenValue` 体系符合类型封闭目标 (唯 P0-1 例外)

---

## 五、处置顺序与依赖

| 序 | 项 | 层 | 依赖 |
|---|---|---|---|
| 1 | P0-1 删 `active_scenario_branches` | 代码 | **L5 场景引擎实现** (签署后) |
| 2 | A-1 删 `planned_frequency` | 代码 | 无生产消费方已验证; 随下一版本号递增执行 |
| 3 | A-2 六处 Enum 化 | 规范+代码 | 规范层可先行 (新增枚举类型登记); 代码迁移待签署 |
| 4 | A-3 ownership_map 投影化 | 规范+代码 | 依赖 §38 OwnershipAssignment (已登记) |
| 5 | A-4 CognitiveCategory 裁决 | 评审 | 待业务/架构确认 |
| 6 | A-5 WorldState 字段准入审查 | 流程 | 纳入 §十二.2 日常裁决 |

---

## 六、成熟度声明

未覆盖: 无 (2026-08-26 补审 contracts/ 别名层: world_state.py 为纯再导出门面,
4 个向后兼容别名 CustomerEntity/ResourceEntity/WorldState/WorldStateSnapshot,
无新字段无新语义 — 通过, 唯一注记: WorldState/WorldStateSnapshot 与
OperationalDecisionWorldState 双名并存属过渡期兼容, Phase 7 收敛)
审计覆盖: state_snapshot.py 全部 22 类型 / 130 字段 (机械扫描 + 人工复核)
处置实施: 0 项 (全部待立项; 代码项受签署门禁)
```
