# SVDE 销售拜访领域本体规范 v2.0 (Sales Visit Domain Ontology Specification)
**Document ID:** SVDE-SALES-VISIT-DOMAIN-ONTOLOGY-SPEC-v2.0  
**Date:** 2026-08-24  
**层级定位:** L2: 领域本体层 (Domain Ontology Layer)  
**前置基础:** `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md` (L1), `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md` (L0)  
**设计定位:** 本规范是通用世界模型（L0/L1）在“快消与现场销售拜访（FMCG / Field Sales & Merchandising）”领域的具体具象化。所有销售拜访对象均为 L1 通用元模型的严格特化实例，严禁反向污染通用基础架构。

---

## 1. L2 领域对象对 L1 通用元模型的特化继承拓扑

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        L2 领域对象与 L1 通用元模型的特化映射关系                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ L1 通用元类型 (General Meta-Type) │ L2 销售拜访领域特化实体 (Sales Visit Domain Object)  │
├───────────────────────────────────┼────────────────────────────────────────────────────┤
│ • MetaEntity.TargetEntity         │ ──> Customer (零售终端门店)                        │
│ • MetaEntity.AgentEntity          │ ──> Resource (现场销售代表)                        │
│ • MetaEntity.FacilityEntity       │ ──> SupplyNode / CentralDC (供货总仓与中心基地)    │
│ • MetaEntity.HierarchicalOrg      │ ──> AccountHierarchy (连锁大客户总部层级)          │
│ • MetaPolicy.CadencePolicy        │ ──> CadenceSpec (严格同周几 7/14/28 天节奏契约)    │
│ • MetaPolicy.PortfolioPolicy      │ ──> ProductLineScope (皇家美素爆品 vs 源悦新品)    │
│ • MetaPolicy.ActionStandard       │ ──> InStoreActionTaxonomy (现场五大标准动作分类学) │
│ • MetaDemand.ServiceDemand        │ ──> VisitDemand (由级别、合同、缺货驱动的拜访需求) │
│ • MetaCommitment.LockedSlot       │ ──> Commitment (锁定拜访承诺)                      │
│ • MetaEvent.CheckInFact           │ ──> ActualVisit (现场真实打卡与在店作业事实)       │
│ • MetaAction.DiscreteTask         │ ──> InStoreActionFact (开新/缺货/防损/陈列/客情)   │
│ • MetaObservation.ComplianceData  │ ──> MerchandisingComplianceFact (合同陈列对赌核销) │
│ • MetaPlan.DecisionOutput         │ ──> DecisionArtifact (不可变决策发布产物)          │
└───────────────────────────────────┴────────────────────────────────────────────────────┘
```

---

## 2. 销售拜访领域核心对象目录 (Domain Object Catalog: 24 Core Entities)

### 2.1 身份与拓扑类 (Identity & Topology: 5 对象)
1. **`Customer`**: 被服务的终端零售门店（主键 `store_code`，包含空间坐标、客户分级、履约等级）；
2. **`Resource`**: 执行拜访的销售代表（主键 `rep_id`，包含战区归属、城市中心 Depot 坐标、单日容量红线）；
3. **`AccountHierarchy`**: 连锁大客户总部组织（如孩子王、爱婴室、高鑫零售等 13 大连锁体系）；
4. **`SupplyNode`**: 供应链上游供货总仓（如嘉善大仓、南京总仓等 18 个大仓）；
5. **`Territory`**: 地理辖区网络（大区 $\rightarrow$ 区域 $\rightarrow$ 城市群 $\rightarrow$ 行政区县）。

### 2.2 政策与契约类 (Policy & Contract: 7 对象)
6. **`OwnershipPolicy`**: 客户-代表专管政策（严格单一所有权，版本化归属与冲突记录）；
7. **`VisitPolicy`**: 周期性拜访频次要求（1次/周、1次/2周、1次/4周）；
8. **`CadenceSpec`**: 拜访节奏契约（1A 严格同周几硬锁定，7天/14天/28天等距）；
9. **`ProductLineScope`**: 多产品线组合政策（皇家美素现金牛 vs 源悦拉新战略定位）；
10. **`InStoreActionTaxonomy`**: 现场五大动作分类学标准时长基线；
11. **`Commitment`**: 锁定拜访承诺（`RESOURCE_LOCKED`, `DAY_LOCKED`, `SEQUENCE_LOCKED`）；
12. **`StartEndPolicy`**: 起终点政策（专属城市中心 Depot 往返闭环）。

### 2.3 需求与动态事件类 (Demand & Events: 4 对象)
13. **`VisitDemand`**: 终端拜访需求实体（绑定客户、产品线、频次要求与履约等级）；
14. **`PlannedVisit`**: 计划拜访时隙实体（指派的具体日期、次序、在店服务时长）；
15. **`ActualVisit`**: 实际拜访打卡事实（真实进店/离店时间戳、在途耗时、线内/线外）；
16. **`InStoreActionFact`**: 现场执行的具体业务动作明细事实。

### 2.4 观测与度量类 (Measurement: 5 对象)
17. **`TravelCostMatrix`**: 真实路网通勤耗时与通行距离拓扑矩阵；
18. **`TravelCostEstimate`**: 两点间单段通行时间与距离测量；
19. **`ServiceDurationObservation`**: 在店服务时长历史统计与动作耗时基线；
20. **`MerchandisingComplianceFact`**: 端架与地堆合同陈列量化核销度量事实；
21. **`CapacityObservation`**: 代表工作负荷与工时消耗测量。

### 2.5 规划产物类 (Plan Artifacts: 3 对象)
22. **`PeriodVisitPlan`**: 4 周周期性客户排班候选计划（`CandidatePlan`）；
23. **`DailyRoutePlan`**: 单日闭环路径与停靠站点序列（`PlannedDailyRoute`）；
24. **`DecisionArtifact`**: 经三维独立审计与业务主管人工签署发布的不可变终态决策产物。

---

## 3. 销售拜访专属业务规则与状态演化 (Domain Business Rules)

### 规则 1: 1A 严格同周几 7 天等距周期规则 (Same-Weekday Regularity Rule)
- 4 访/月门店：必须每周在同一个周几进店（严格间隔 7 天）；
- 2 访/月门店：必须隔周在同一个周几进店（严格间隔 14 天）；
- 1 访/月门店：必须全月特定周在同一个周几进店（严格间隔 28 天）；
- **业务目的**: 建立零售店长对品牌代表巡店的绝对稳定预期，杜绝前紧后松。

### 规则 2: 核心大店 REQUIRED 强履约零脱访规则 (Key Store Zero-Miss Guard)
- `Key` 级与 `A` 级门店强制赋予 `FulfillmentClass = REQUIRED`；
- 任何规划周期内若发生 `REQUIRED` 门店拜访频次 $< F_i$ 或零拜访，审计算子直接触发 `CRITICAL_INCIDENT` 阻断发布。

### 规则 3: 供应链大仓配货日历时序协同规则 (DC Replenishment Coupling)
- 门店巡店计划必须与上游大仓送达窗口对齐（到货后 24 小时内进店协助上架搭建地堆）；
- 未经供应链实测校准的大仓配送日显式标记为 `UNCALIBRATED`，不作虚假假设。

---

## 4. 与 A01~A06 / A03 v1.0.1 规范的演进兼容性声明

本规范是 A03 领域契约（v1.0.1 47 对象）在 L0~L6 分层世界模型架构下的**系统性升维与完全兼容版本**：
1. **完全向下兼容**: 原 A03 中冻结的 47 个领域概念定义 100% 保持有效；
2. **消除了元数据与实例割裂**: 将 Phase 2 引入的 5 大 DCR 对象正式纳入 L2 领域核心实体编目；
3. **架构解耦彻底**: 销售拜访领域规范完全通过 L1 通用元模型特化构建，奠定了多行业决策引擎的通用底座。
