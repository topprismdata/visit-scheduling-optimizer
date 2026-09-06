# SVDE / TopPrism Ontology Engineering Framework
## 独立运行框架与 GitHub 技术栈组件设计规范 v1.1

**Document ID:** SVDE-OEF-COMPONENT-SPEC-V1.1  
**Status:** DESIGN BASELINE — 待业务裁决与外部评审，不宣称已通过  
**Date:** 2026-08-24  
**Target component:** `prism-ontology`

---

## 0. 结论先行

本规范定义一个可以脱离 SVDE Core 单独运行的本体工程组件：

```text
prism-ontology
  = 证据管理 + 需求/CQ + 参考本体工程 + 运行本体编译
  + SHACL 验证 + 推理适配 + PROV-O 溯源 + 版本治理
```

正式方法组合为：

| 层 | 采用方案 | 责任 |
|---|---|---|
| 主工程方法 | SABiO 2.0 | 参考本体与运行本体分离、需求、捕获、形式化、实现、测试 |
| 资料复用与整合 | NeOn | 多来源资料、既有知识库、外部本体和模块复用 |
| 演化治理 | DILIGENT | 业务裁决、变更请求、版本演化、冲突论证 |
| 形式化表达 | RDF/OWL 2 | 类、属性、关系和可推理语义 |
| 实例验证 | SHACL | 数据形状、结构约束和业务准入 |
| 溯源 | PROV-O | 证据、生成活动、人工裁决和运行结果来源 |
| 上层分类 | BFO 轻量对齐，可选 | 区分实体、过程和信息对象；不作为强依赖 |

SABiO 明确区分 reference ontology 与 operational ontology，并覆盖需求、概念捕获、形式化、实现和测试。[SABiO](https://www.researchgate.net/publication/286670309_SABiO_Systematic_approach_for_building_ontologies) NeOn 适合场景化复用、整合和动态本体网络。[NeOn Methodology](https://oeg.fi.upm.es/index.php/en/methodologies/59-neon-methodology/index.html) DILIGENT 聚焦用户驱动的本体演化，而不是替代初始建模。[DILIGENT](https://researchportal.ulisboa.pt/en/publications/the-diligent-knowledge-processes/)

OWL 2 用于形式化类和关系，[W3C OWL](https://www.w3.org/TR/owl-guide/)；SHACL 用于验证 RDF 图，[W3C SHACL](https://www.w3.org/TR/shacl/)；PROV-O 用于 provenance，[W3C PROV-O](https://www.w3.org/TR/prov-o/)。ISO/IEC 21838-2 描述 BFO，但不规定本体开发方法或推理方法，因此这里只做 BFO 对齐。[ISO/IEC 21838-2](https://www.iso.org/standard/74572.html)

## 1. 目标、非目标与独立性

### 1.1 目标

`prism-ontology` 必须在不启动 SVDE Runtime、不加载求解器、不依赖 Bench 的情况下完成：

1. 注册和版本化外部证据；
2. 管理概念、定义、关系和禁止映射；
3. 管理 Competency Questions（CQ）；
4. 构建 reference ontology；
5. 编译 operational ontology 和领域数据契约；
6. 执行 SHACL、推理、CQ 和反折叠验证；
7. 输出业务意图、决策层级和缺失输入报告；
8. 为每个结论提供来源和裁决链；
9. 以 CLI、Python API 和 CI 方式独立运行；
10. 通过 adapter 被 SVDE Core 消费。

### 1.2 非目标

本组件不负责求解 CP-SAT/MIP/VRP，不生成路线，不替代 CRM/ERP/SFA，不自动冻结 LLM 产物，不将厂商字段、数学变量或算法名称升格为业务本体。

### 1.3 独立运行

```bash
prism-ontology check --bundle ./ontology-bundle
prism-ontology validate --data ./scenario.json --shape ./shapes.ttl
prism-ontology diagnose --question "缩短销售线路在途距离"
prism-ontology compile --reference ./reference.ttl --profile sales_visit
```

独立运行不导入 `svde`、`svde-bench` 或求解器，不要求网络访问，结果必须由输入、规则包和版本重现，失败必须结构化返回。

## 2. 方法论生命周期

| SABiO 活动 | `prism-ontology` 阶段 | 产物 |
|---|---|---|
| Purpose / Requirements | `specify` | 范围、利益相关者、CQ、禁止范围 |
| Ontology Capture / Formalization | `capture` | 概念、定义、关系、术语 |
| Design | `design` | 模块、约束、决策层、生命周期 |
| Implementation | `compile` | RDF/OWL、SHACL、JSON Schema、映射 |
| Test | `verify` / `validate` | reasoner、SHACL、CQ、反折叠测试 |

NeOn 负责 `source-import`、`crosswalk`、`reuse`、`merge`、`modularize`，但不替业务方作冻结裁决。DILIGENT 负责冻结后的变更请求、论证、审批、版本和迁移。

### 2.1 三层对象

```text
Reference Ontology  业务世界的共同概念
Operational Ontology 可计算的运行契约
Instance Graph      真实场景、计划、执行和审计实例
```

禁止直接替代：

```text
Customer != NormalizedEntity(COMMITTED_TASK)
VisitOccurrence != RouteStop
RoutePlan != DecisionArtifact
BusinessPolicy != SolverParameter
```

## 3. 独立架构

```text
Evidence Registry → Requirements/CQ → Reference Workbench
       ↓                   ↓                 ↓
       └────────────── Operational Compiler ─┘
                              ↓
              SHACL / Reasoner / CQ / Anti-collapse
                              ↓
              SVDE / Agent / Precheck / GitHub CI

DILIGENT Governance 覆盖所有可版本化层
```

| 组件 | 职责 | 独立运行 |
|---|---|---|
| `evidence` | 来源、主张、摘录、等级、冲突 | 是 |
| `requirements` | 范围、CQ、业务裁决、GAP | 是 |
| `reference` | 业务概念和关系权威定义 | 是 |
| `profiles` | 领域、决策层、接口配置 | 是 |
| `compiler` | Reference → OWL/SHACL/JSON Schema | 是 |
| `validator` | 图、形状、CQ、反折叠、一致性 | 是 |
| `diagnostics` | 问题 → 决策层、输入、能力状态 | 是 |
| `provenance` | PROV-O 兼容溯源和复现包 | 是 |
| `governance` | 变更、审批、兼容性、版本 | 是 |
| `adapters` | SVDE Core、GitHub CI、外部数据 | 可选 |

## 4. Sales Visit 参考本体

### 4.1 顶层分类

```text
Identity: Customer, Resource, OrganizationUnit, Location
Policy: VisitPolicy, CadenceSpec, OwnershipPolicy, EligibilityPolicy,
        SubstitutionPolicy, ResourceDayProfile, ObjectiveProfile, DeferralPolicy
Event: VisitDemand, VisitOccurrence, ActualVisit, ExecutionSignal, TimeDeviation
Commitment: ExistingCommitment
Plan: PlanningHorizon, PlannedVisit, RouteStop, RoutePlan,
      TerritoryAssignmentPlan, PeriodicVisitPlan, BusinessDecision
Measurement: TravelCostMatrix, TravelCostEstimate, CoverageMetric,
             StabilityMetric, DeferralCost
```

### 4.2 不可折叠对象

| 对象 | 定义 | 禁止替代 |
|---|---|---|
| `Customer` | 被服务的业务主体 | 不直接变成 Task/RouteStop |
| `VisitDemand` | 业务上需要一次拜访 | 不是已排路线访问 |
| `VisitOccurrence` | 周期内物化的一次计划拜访 | 不是实际打卡 |
| `PlannedVisit` | 已安排日期、代表、时段的计划 | 不是政策 |
| `ActualVisit` | 实际执行/打卡事件 | 不是未来计划 |
| `RouteStop` | 路线中的物理顺序节点 | 不是客户主数据 |
| `RoutePlan` | 固定拜访集合的排序计划 | 不改变周期频次 |
| `ExistingCommitment` | 具体日期/时段/代表的承诺实例 | 不得静默降级 |
| `TravelCostMatrix` | 路网成本输入事实 | 不是优化目标 |
| `ObjectiveProfile` | 目标和允许权衡政策 | 不是求解器参数 |

### 4.3 三层决策

```text
TERRITORY_ALIGNMENT
  输入 Customer + OwnershipPolicy + EligibilityPolicy + Resource
  输出 TerritoryAssignmentPlan

PERIODIC_COVERAGE
  输入 VisitDemand + CadenceSpec + PlanningHorizon + Commitment
  输出 PeriodicVisitPlan / VisitOccurrence 集合

DAILY_ROUTE_SEQUENCING
  输入固定 VisitOccurrence/PlannedVisit + TravelCostMatrix + ResourceDayProfile
  输出 RoutePlan

ROLLING_REPLAN
  输入 ExistingCommitment + ExecutionSignal + VisitDemand
  输出 ReplanProposal + ApprovalRequest（如需）
```

决策层之间的越权必须阻断：单日路线不得改变发生项集合、频次、代表或锁定项；周期规划不得直接重排 RouteStop。

### 4.4 目标优先级

```text
Level 0  硬承诺 / 覆盖 / 频次 / 节奏 / 资质
Level 1  商业价值 / 未履约后果
Level 2  在途时间 / 距离 / customer-facing time
Level 3  计划稳定性 / 变动代价
Level 4  次级偏好
```

```text
DistanceMinimization.subordinateTo(CoverageCompliance)
DistanceMinimization.mustNotOverride(CommitmentLock)
DistanceMinimization.cannotReduce(CadenceSpec.min_interval_days)
DailyRouteOptimization.requires(FixedVisitSet)
PeriodicVisitPlanning.requires(PlanningHorizon)
```

## 5. 证据、CQ 与治理

### 5.1 证据等级

```text
PRODUCT_FACT | DOMAIN_PRACTICE | EMPIRICAL_EVIDENCE
MATHEMATICAL_THEORY | DESIGN_INFERENCE | BUSINESS_DECISION
```

数学理论不等于业务硬规则，厂商字段不等于通用对象，设计推论不等于行业事实，单个案例不等于普遍规律。

### 5.2 Claim 结构

```yaml
claim_id: CLM-0001
statement: "Customer-facing time is distinct from travel time"
source_ids: [REF-003]
evidence_level: DOMAIN_PRACTICE
supports: [ObjectiveProfile.customer_facing_time]
confidence: HIGH
status: EVIDENCE_CONFIRMED
reviewed_by: domain_reviewer
```

### 5.3 冻结门槛

概念进入 `FROZEN` 必须有证据或 `BUSINESS_DECISION`、至少一个 CQ、正向和反向边界、SHACL/一致性验证、相邻排除概念及无未解决 LOCKED 冲突。Agent 只能输出 `CANDIDATE`、`PROPOSED`、`EVIDENCE_PENDING` 或 `CONFLICTED`，不能直接生成 `BUSINESS_APPROVED` 或 `FROZEN`。`BUSINESS_APPROVED` 只能由明确的业务方裁决记录产生，不能由 Agent、CI 或文档作者自行推断。

### 5.4 CQ 与诊断输出

```yaml
cq_id: CQ-DAILY-001
question: "今天固定的 8 家客户怎样排序更顺路？"
expected_decision_level: DAILY_ROUTE_SEQUENCING
required_classes: [VisitOccurrence, TravelCostMatrix, ResourceDayProfile]
forbidden_levels: [PERIODIC_COVERAGE, TERRITORY_ALIGNMENT]
expected_answer_shape: RoutePlan
```

```json
{
  "primary_level": "DAILY_ROUTE_SEQUENCING",
  "confidence": 0.86,
  "required_inputs": ["fixed_visit_set", "travel_cost_matrix"],
  "missing_inputs": ["travel_cost_matrix"],
  "hard_constraints_to_confirm": ["commitment_lock", "time_window"],
  "available_capabilities": [],
  "status": "DIAGNOSE_ONLY"
}
```

诊断必须综合时间尺度、业务对象、用户动作、目标指标、可变集合、承诺、输入完备性和不确定性，不能只用关键词。

反错误降维 CQ 至少包含：客户错配代表、四周频次不均、固定 8 家日内排序、必访集合不可减少、临时新增高价值客户、后移锁定件、距离下降但覆盖率下降、论文新 VRP 变体。

## 6. Operational Compiler

```text
ReferenceBundle + EvidenceBundle + Profile + CQRegistry + GovernanceState
  → OperationalCompiler
  → reference.ttl / operational.ttl / shapes.ttl / schema.json
    mapping.yaml / decision-levels.yaml / manifest.json / provenance.ttl
```

编译规则：

1. 参考概念必须先有定义和来源；
2. 运行字段必须有 `maps_to`；
3. 技术字段不能反向创建业务概念；
4. Solver 参数只能进入 capability profile；
5. 所有近似必须有 `ApproximationDeclaration`；
6. 无数据映射的对象不能宣称已接入；
7. 无 SHACL shape 的硬约束不能宣称已机器验证。

SVDE 只消费 `OntologyDecisionGate` 的 `BusinessDecisionIntent`、`OperationalContract` 和 `ValidationReport`；本体组件不反向修改 SVDE Runtime。

## 7. Prism GitHub 组件设计

### 7.1 目录

```text
prism-ontology/
├── pyproject.toml
├── README.md
├── src/prism_ontology/
│   ├── cli.py / api.py / models.py
│   ├── evidence/ requirements/ reference/
│   ├── compiler/ validation/ diagnostics/
│   ├── governance/ provenance/ adapters/
├── ontology/reference/ operational/ shapes/ vocab/ provenance/
├── bundles/sales_visit/
├── tests/competency_questions/ shacl/ anti_collapse/ provenance/
└── .github/workflows/ontology-ci.yml
```

当前仓库可先放在 `svde/ontology/`，但依赖方向必须保持：

```text
ontology → stable adapter interface
SVDE Core → ontology adapter
ontology ↛ planning/runtime solver internals
```

### 7.2 技术基线

```text
Python 3.10.14
rdflib       RDF/OWL 图读写
pyshacl      SHACL 验证
owlrl        可选轻量规则物化
jsonschema   运行契约验证
pytest       CQ 和回归测试
```

#### 技术栈选择论证

选择 Python + RDFLib + pySHACL + JSON Schema 的原因是：当前 TopPrism/SVDE 运行时以 Python 为主，需要在离线 CI 中同时处理 RDF/OWL 图、结构约束和面向 API 的契约。RDFLib 提供图读写与序列化，pySHACL 对应 W3C SHACL 验证语义，JSON Schema 负责非 RDF 消费者的边界校验；`owlrl` 作为可选规则物化层，不把重量级 reasoner 变成核心依赖。Protégé/TopBraid 适合作为人工建模和商业工作台，但不满足无 UI、可重复 CI、可审计退出码和 GitHub PR 门禁，因此作为可选 authoring 工具而不是运行时依赖。ShEx 可作为未来互操作格式，但本设计优先使用 SHACL 以承载现有数据形状、SPARQL 约束和报告机制。上述判断是工程设计推论，不是未经证明的“生态事实标准”断言。

本体框架不依赖求解器、`svde-bench` 或网络；reasoner 通过可选 adapter 接入。

### 7.3 CLI 与退出码

```bash
prism-ontology init --profile sales_visit --out ./bundle
prism-ontology ingest-source --file source.yaml --bundle ./bundle
prism-ontology add-claim --file claim.yaml --bundle ./bundle
prism-ontology add-cq --file cq.yaml --bundle ./bundle
prism-ontology compile --bundle ./bundle --out ./build
prism-ontology validate --bundle ./bundle --data scenario.json
prism-ontology diagnose --bundle ./bundle --question "..."
prism-ontology diff --from v0.1 --to v0.2 --bundle ./bundle
prism-ontology gate --bundle ./bundle --strict
```

CLI 必须返回可被 GitHub Actions 直接消费的 process exit code：

```text
0 通过
2 数据/形状失败
3 本体一致性失败
4 Provenance/证据门失败
5 Governance/GAP 未批准
6 编译失败
```

### 7.4 GitHub CI

PR 必须运行：数据解析、RDF/OWL 解析、SHACL、reasoner 一致性、CQ、anti-collapse、provenance 完整性和 gate 状态检查。

必须阻断：FROZEN 无来源、SHACL 失败、GAP 未裁决却改冻结对象、算法概念进入业务本体、诊断落入错误决策层、未实现能力被标为可用、破坏性变更无迁移说明。

## 8. 版本与演化

```text
EXTRACTED → EVIDENCE_PENDING → CANDIDATE → DOMAIN_REVIEW
→ BUSINESS_APPROVED → FROZEN → DEPRECATED → RETIRED
```

FROZEN 不能直接编辑，只能通过 `OntologyChangeRequest` 进入新版本。每个变更必须说明原因、证据、受影响 CQ、兼容性、旧/新行为和迁移方案。

新增非必填属性和子类可为 Minor；改名、改语义、删除冻结概念或改变硬约束优先级必须 Major。

## 9. 接入路线

### Phase 0：独立骨架

实现 CLI、Evidence/Claim/CQ/Governance 模型、bundle manifest 和 CI，不改 SVDE 运行链。

### Phase 1：Sales Visit Reference Ontology

落地 Customer、VisitDemand、VisitOccurrence、PlannedVisit、ActualVisit、PlanningHorizon、CadenceSpec、ExistingCommitment、三层决策和 ONT-1 至 ONT-8。

### Phase 2：Operational Profile

生成 JSON Schema、SHACL shapes、VisitDomainAdapter mapping manifest 和折叠度报告，不引入求解器。

### 迁移与退役路径

在 `prism-ontology` 的 operational bundle 和 adapter 契约通过 CI 后，以下旧资产进入 `DEPRECATED`，但不得立即删除：

| 旧资产 | 处理 |
|---|---|
| `svde/docs/SVDE_SALES_VISIT_ONTOLOGY_DESIGN_v0.1.md` | 保留为历史设计，标记 superseded by v1.1 |
| `svde/docs/SVDE_SALES_VISIT_CONCEPT_CROSSWALK_v0.1.md` | 迁移为 evidence/crosswalk bundle，禁止作为运行时真源 |
| `svde/docs/SVDE_SALES_VISIT_ONTOLOGY_GAP_REVIEW_v0.1.md` | 迁移为 governance/change records，未裁决 GAP 继续阻断 |
| `VisitDomainAdapter` 中的扁平映射 | 由 operational mapping manifest 逐步替换 |
| 直接消费 `NormalizedEntity(COMMITTED_TASK)` 的销售拜访路径 | 仅保留兼容层，禁止新能力依赖 |

退役条件必须同时满足：新 bundle 发布、adapter 契约通过、旧场景回放一致性通过、迁移说明发布、业务方批准。未满足时，新旧两套机制不得同时作为无差别真源；旧机制只能显式标记为 compatibility mode。

### Phase 3：SVDE Decision Gate

```text
DecisionRequest → OntologyDecisionGate
  → diagnosis / completeness / decision level / profile / provenance
  → DecisionCompiler
```

失败返回 typed `OntologyGateError`，不得降级到通用 assignment。

### Phase 4：Capability Contract

只定义并验证：`TerritoryAlignmentCapability`、`PeriodicVisitPlanningCapability`、`DailyRouteOptimizationCapability`、`RollingReplanCapability`。

### Phase 5：真实数据

先离线回放和影子模式。每次实验输出 baseline、counterfactual、coverage、cadence、commitment、distance、stability 和 deferral cost，生产写回另行审批。

## 10. 三轮独立自审

### 自审 1：本体语义自洽

检查对象不折叠、生命周期闭合、PlanningHorizon 归属、决策层输入输出、目标优先级和算法排除。

**结果：内部审查未发现阻断性矛盾，但不构成外部评审或业务批准。** 设计明确区分 reference/operational/instance，补齐计划与实际访问、规划周期和目标层级。

### 自审 2：工程独立性

检查无 SVDE Runtime/Bench 是否可运行、依赖方向、结构化失败、CLI/API/CI、OWL/SHACL/PROV-O 边界。

**结果：内部设计检查通过，但尚未实现验证。** 组件设计为独立 Python 包运行，SVDE 仅通过 adapter 消费编译结果。

### 自审 3：业务反例和错误降维

检查销售线路是否被误判 VRP、周期是否被误判日内排序、距离是否覆盖覆盖率、锁定是否可移动、算法是否升格、未实现能力是否被宣称可用。

**结果：反例覆盖设计完成，尚未由实现和外部评审证明。** CQ、forbidden level、capability availability 和 governance status 形成阻断链。

三轮内部审查结论：

```text
语义完整性：INTERNAL_REVIEW_NO_BLOCKER_FOUND
工程独立性：DESIGN_CHECKED_NOT_IMPLEMENTED
业务反例防线：DESIGNED_NOT_EXTERNALLY_VALIDATED
实现状态：DESIGN ONLY
业务批准：PENDING
生产状态：NOT YET
```

以上是内部设计审查记录，不是“自审通过”声明，不等于业务方批准、外部评审通过或组件已实现。

## 11. 验收标准与当前状态

### Phase 1 启动前的业务方裁决清单

以下项目是 `BUSINESS_PENDING`，必须由业务方/产品方产生有身份、有日期、有依据的裁决记录；Agent 和 CI 不得代替裁决：

| GAP | 待裁决问题 | 影响 |
|---|---|---|
| GAP-1 | Sales Visit 是否需要 `Product/SKU` 作为正式对象？ | 区分销售拜访与带货/交付型拜访 |
| GAP-2 | `Subsidiary/Region/Zone` 是否进入通用本体？ | 决定组织层级和辖区对齐语义 |
| GAP-3 | `ApprovalRequest` 是否属于本体，还是外部审批系统对象？ | 决定延期和重大改动的闭环 |
| GAP-4 | `TimeDeviation` 是正式对象还是执行指标历史？ | 决定滚动重排和校准输入 |
| GAP-5 | `BusinessCostPerDayPerCustomer` 是否显式进入 `DeferralPolicy`？ | 决定延期代价是否可计算 |

在 GAP-1 至 GAP-5 解决前，v1.1 只能作为设计基线，不能发布为 FROZEN operational profile。

设计验收必须包括：reference/operational/instance 三层、方法分工、OWL/SHACL/PROV-O 边界、Evidence/Claim/CQ/Governance、Sales Visit 对象、三层决策、反降维测试和 SVDE adapter 边界。

实现验收必须包括：无 SVDE Runtime 的 `check/validate/diagnose`、FROZEN provenance、GAP 阻断、GitHub CI、至少 8 个 CQ 和 adapter 契约测试。

真实数据验收必须包括：DataPrecheckValidator、baseline/counterfactual、覆盖/频次/承诺/节奏零违规、明确版本 TravelCostMatrix、人工审批和影子模式。

当前文档是 **component design baseline**，不是已实现代码包，也不是已冻结的 Sales Visit v0.3。本体实现前必须先完成业务方对 Crosswalk/GAP 的裁决。
