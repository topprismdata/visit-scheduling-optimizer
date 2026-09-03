# TopPrism 本体与世界模型设计评审 — 对照 Palantir Foundry Ontology 最佳实践

**Document ID:** TOPPRISM-ONTOLOGY-DESIGN-REVIEW-VS-PALANTIR-v1_0
**Version:** v1.0
**Date:** 2026-08-26
**Status:** 设计评审报告 (已获所有者同意, 建议项待逐项立项)
**评审对象:** `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2) + `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` (34 类型) + L3/L5/L7 详细规范

**证据源:**
- Palantir Foundry 官方文档 (深读 6 篇):
  - Why create an Ontology? (decision-centric: Data/Logic/Action/Security)
  - Ontology design: Best Practices (四原则 + 务实权衡)
  - Ontology design: Structural Guidance (规范化/Structs/Interfaces/Object-backed Links/命名/安全)
  - Ontology design: Anti-Patterns (8 反模式)
  - Action Types Overview (动词类型化)
  - Ontology Scenarios Overview [Beta] (沙盒/合并/执行上下文治理)
- 学术: Ding et al., "Understanding World or Predicting Future? A Comprehensive Survey of World Models", arXiv:2411.14499 (2024-11)

**检索限制声明:** 本评审期间 web 搜索通道大部分不可用 (供应商封锁/MCP 订阅失效); Palantir 文档为深读一手证据, 学术文献仅获得综述摘要, Ha & Schmidhuber (1803.10122) 与 LeCun JEPA 立场文件未重读原文。引用 Palantir 原文处均为直读摘录。

---

## 一、验证结论: 现有设计与行业最佳实践的吻合点

| 我们的纪律/设计 | Palantir 对应物 | 结论 |
|---|---|---|
| 四要素分离 (事实约束/业务目标/动作集归 World Model; Trade-off 归 Decision Engine) | 决策四要素 Data/Logic/Action/Security, "Ontology represents the decisions, not simply the data" | **同构, 保留** |
| 三层纪律 (Business→Math→Algorithm 严禁混淆) | Golden Hammer 反模式 + 工具选择表 (action=人的决策 / pipeline=自动变换 / function=实时逻辑) | **同构, 保留** |
| L6 纯数学投影 (预计算, 只读) | Pre-computed vs dynamically derived values 二分; 投影属预计算类 | **吻合, 保留** |
| WorldState 全量快照 + 双时态 | Scenarios 显式声明 "不是版本工具"; 历史走 linked amendment | **部分吻合, 需显式区分声明 (见建议 3)** |
| 五级成熟度诚实声明 | "Pragmatism and tradeoffs": 在用的不完美本体 > 在设计的完美本体 | **文化一致** |

---

## 二、建议清单 (按优先级)

### 建议 1: 把 Action 提升为本体一等公民 [最大缺口]

**Palantir 证据** (Action Types Overview / Why Ontology):
> "If the data elements in the Ontology are 'the nouns' of the enterprise, then the actions can be considered 'the verbs'."
> Action Type = 参数 (parameters) + 规则 (rules) + 提交标准 (submission criteria) + 副作用 (side effects: 通知/webhook) 的类型化业务操作。

**我们的缺口**: `TOPPRISM_CANONICAL_TYPES_SPEC_v1_0.md` 类型库 (本评审时点 34 主类型; 同日修订后含 §37 PolicyAmendment / §38 OwnershipAssignment) 全部是名词 (实体/记录/凭证)。业务动作 (拜访顺延/归属转移/排班审批/方案合并) 仅以 API 参数包形态存在 (`TransitionRequest`), 不是本体类型, 无规则/提交标准/副作用的类型化承载。

**行动项**: 新建 `TOPPRISM_ACTION_TYPE_REGISTRY_v1_0.md`, 首批登记:
- `DeferVisit` (参数: visit_id, deferral_policy_id; 规则: BIZ-02; 提交标准: 角色窗口; 副作用: 通知经理)
- `TransferStoreOwnership` (参数: store_code, from_rep, to_rep, effective_date; 规则: BIZ-06; 副作用: 重算归属冲突)
- `ApprovePlanAdjustment` (参数: plan_id, approver; 规则: BIZ-08)
- 每个动作声明: 读哪些对象 / 写哪些对象 / 写回哪些外部系统

**依赖**: 需 BIZ-01~08 签署 (动作规则引用业务语义)。

### 建议 2: 归属关系升级为带元数据的关联对象

**Palantir 证据** (Structural Guidance / Links):
> "Object-backed link: the relationship carries its own metadata (dates, roles, status, allocation) → Employee → VentureStaffing → Venture"

**我们的缺口**: `PolicyRegistry.ownership_map: Dict[str, str]` (store_code → rep_id) 是无元数据直接映射。2026-08-26 业务方案B 分析实证: 归属调整是高频核心业务动作 (NT23 等 4 家店摘牌、欣/晓敏 40 店频率调整), 归属变更需生效日期/原因/审批, 当前类型无法承载。

**行动项**: 新增 `OwnershipAssignment` 关联对象:
```python
@dataclass(frozen=True)
class OwnershipAssignment:
    assignment_id: str
    store_code: str
    rep_id: str
    effective_from: datetime.date      # 双时态 valid time
    effective_to: Optional[datetime.date]
    reason: str                        # 方案调整/摘牌/冲突裁决
    approved_by: str
    transaction_from: datetime.datetime  # 带时区
    status: str                        # ACTIVE / SUPERSEDED
```
`ownership_map` 降级为 `OwnershipAssignment` 的当前态投影。

### 建议 3: Time Machine 自查 — 区分"版本对象"与"状态检查点"

**Palantir 证据** (Anti-Patterns / The Time Machine):
> 历史版本建模为独立对象/类型是反模式; 正确做法 = 单一当前对象 + linked amendment 历史对象 (Contract → Contract Amendments: amendmentDate/previousValue/newValue/changeReason)。

**自查结论 (两项, 结论不同)**:
1. `OperationalVisitPolicy` 按 `policy_version` 建多版本对象 → **命中反模式**。重构为: 单一当前 `OperationalVisitPolicy` + linked `PolicyAmendment` (amended_at/previous_frequency/new_frequency/reason/approved_by)。
2. `WorldState` 全量快照链 → **不是反模式**: 这是世界状态检查点 (event-sourcing 语义), Palantir 无对应物 (其 Object Storage 是当前态 + edits history)。**行动项**: 在 L4 规范增加显式区分声明: "WorldState 快照是决策检查点, 不是实体版本; 实体级历史一律走 linked amendment 对象" — 防止后续评审误判。

### 建议 4: L5 场景语义补全 (对标 Palantir Scenarios)

**Palantir 证据** (Ontology Scenarios [Beta]):
- Merge 是独立动作, 有独立提交标准 ("Applying approved scenario edits to the main Ontology is controlled separately through the submission criteria of the merge action")
- Execution context 治理: "submission criteria can distinguish between actions executed within a scenario and actions executed against the main Ontology" — 场景内宽松、合并严格
- 显式边界: "Scenarios are not data versioning tools. They cannot provide a snapshot of your Ontology at a historical point in time"
- 生命周期: auto-rebase (10 分钟) / TTL (30 天) / merge / discard

**我们的缺口** (`TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_DETAILED_SPEC_v1_0.md`): 只有 rollout 出 `ScenarioResult(delta)`, 缺:
1. 合并回主干的类型化路径 (`MergeScenario` 动作 + 独立提交标准)
2. 动作授权不区分"场景内执行" vs "主干执行"
3. 无场景与 bitemporal 历史查询的边界声明

**行动项**: L5 规范 v1.0-draft.3 增补 `ScenarioLifecycle` (FORKED → EDITING → COMPARED → MERGED/DISCARDED) + `MergeScenario` Action Type + 边界声明。

### 建议 5: 统一 Decision Lineage (决策谱系)

**Palantir 证据** (Why Ontology):
> "The end-to-end 'decision lineage' of when a given decision was made, atop which version of enterprise data, and through which application, is automatically captured and securely accessible to both human developers and agents."

**我们的缺口**: 审计锚点分散四层 — `RequestFingerprint` (API §2.2/§5.2.1) / `StateTransitionRecord.record_hash` (L3) / `TransitionResult.audit_hash` / `SourceManifest.source_file_sha256` (L4) — 无贯通结构。

**行动项**: 新增 `DecisionLineageRecord`:
```python
@dataclass(frozen=True)
class DecisionLineageRecord:
    lineage_id: str
    decision_id: str
    data_snapshot_ref: str        # WorldState snapshot_id
    logic_asset_ref: str          # 求解器/模型/规则版本
    action_ref: str               # Action Type + 实例 id
    actor_id: str
    approval_ref: Optional[str]   # 审批记录
    occurred_at: datetime.datetime  # 带时区
```
L3 转移 / L7 动作执行 / L5 合并均写入。

### 建议 6: 采纳四原则裁决顺序 + 务实条款 (写入设计规范)

**Palantir 证据** (Best Practices, 带显式优先级, 冲突时高位胜出):
1. Domain-driven design (建模现实, 不建模源系统)
2. Do not repeat yourself (rule of three: 一次是巧合, 两次是模式, 三次必须重构)
3. Open for extension, closed for modification (保护核心模型, 允许扩展)
4. Composition over deep hierarchies (接口组合, 能力接口如 Inspectable/Schedulable)

**Pragmatism 条款** (原文采纳):
- "命名质量、语义清晰、安全设计是后期难以修复的 — 可以在实现细节上妥协, 不能在这三样上妥协"
- "在用并产生价值的不完美本体, 优于仍在设计中的理论完美本体"
- "显式命名权衡: 一次反规范化在当前规模可行, 超过 1 万对象需重审"

**行动项**: 写入 `TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE` 作为类型设计裁决顺序。

### 建议 7: Kitchen Sink / 命名审计 (一轮全类型自查)

**Palantir 证据** (Anti-Patterns: Kitchen Sink / Misnomer; Structural Guidance / Naming):
- 只保留有业务语义的字段; ETL/管道元数据不入本体
- 禁裸歧义名词: `value` → `monetaryValue` / `quantityOnHand`; 链接双向可读命名
- 每个属性问一句: "有人需要按它查看/搜索/过滤吗?"

**自查发现 (2026-08-26 即时扫描)**:
- `OperationalCustomer.planned_frequency` — 自带 `# DEPRECATED` 注释, Kitchen Sink 残留 → 删除 (消费方: planner_projection 已改走 PolicyRegistry, FIX-1 完成)
- 裸名词待查: `status` (多处, 语义各异: LifecycleStatus / OwnershipConflict resolution / Authorization), `category` (CognitiveCategory) — 逐一加限定或改名
- `CognitiveCategory.OBSERVATION/POLICY/COMMITMENT` 标签体系: 按 DDD 原则审视是领域概念还是源系统概念, 评审后决定去留

### 建议 8: 学术定位声明 (防范围漂移)

**证据** (arXiv:2411.14499 综述): 世界模型两分 — (1) 构建内部表示理解世界机制; (2) 预测未来状态模拟并引导决策。主流文献集中于游戏/自动驾驶/机器人/社会模拟 (生成式路线: Sora/Genie/DriverDreamer 等)。

**定位声明** (建议写入产品规范): TopPrism World Model 是 **(1)+(2) 的企业离散语义实例**: 状态表示 (L4 双时态快照) + 动力学 (L3 守卫转移) + 推演 (L5 场景), 核心约束是可审计/带授权/可回写, 而非连续信号生成。**不追逐**生成式世界模型路线; 该路线文献仅提供概念框架。

### 建议 9: Registry 锚点引用完整性自动校验 [立即执行]

**教训**: 2026-08-26 发现 `WorkflowContext`/`RequestFingerprint` 在 Registry 中为悬空引用 (指向从未定义的 §5.2), 已手工补全 (主 API §5.2.1 + TECH-08)。

**行动项**: 编写 `svde/tools/validate_registry_anchors.py`:
- 扫描 `CANONICAL_TYPE_REGISTRY.md` 全部 `文档名 + §x.x` 引用
- 解析目标文档标题/章节锚点, 验证存在且非空
- 输出违规清单; 纳入文档变更 CI

---

## 三、执行顺序 (已获同意)

| 序 | 项 | 工作量 | 依赖 |
|---|---|---|---|
| 1 | 建议 9: 锚点校验脚本 | ~0.5h | 无 |
| 2 | 建议 6: 四原则 + 务实条款写入架构基线 | ~1h 文档 | 无 |
| 3 | 建议 3: Time Machine 自查声明 + PolicyAmendment 重构设计 | ~2h | 无 (重构实施待签署后) |
| 4 | 建议 2: OwnershipAssignment 类型 + 规范登记 | ~2h | 无 (方案B 已证业务必要性) |
| 5 | 建议 7: Kitchen Sink / 命名审计报告 | ~2h | 建议 6 裁决顺序 |
| 6 | 建议 1: Action Type 注册表 | 大 | **BIZ-01~08 签署** |
| 7 | 建议 4: L5 Scenarios 语义补全 (draft.3) | 中 | 建议 1 (MergeScenario 依赖动作类型) |
| 8 | 建议 5: DecisionLineageRecord | 中 | 建议 1 (action_ref 依赖) |

**红线不变**: 建议 1/4/5 的代码实现仍受双轨签署门禁约束 (API 冻结前不写实现); 本文档中的类型设计均为规范层工作。

---

## 四、成熟度声明

```
本评审: 证据充分 (Palantir 一手文档 6 篇直读 + 综述摘要)
学术覆盖: 部分 (搜索通道受限, 经典原文未重读)
建议 1-9: 设计已定义 — 均未实施
与业务签署的关系: 建议 1 依赖 BIZ 签署; 其余为规范层可先行
```
