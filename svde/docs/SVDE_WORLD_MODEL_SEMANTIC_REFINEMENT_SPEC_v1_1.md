---
**Status:** HISTORICAL SNAPSHOT — NOT A CURRENT CANONICAL SPECIFICATION
**Title:** SVDE World Model Semantic Refinement Spec v1.1
**Superseded By:** TOPPRISM_CANONICAL_TYPES_SPEC v1.0
**Date:** 2026-08-24

> This document is a frozen historical report from a previous engineering phase.
> It may contain outdated terminology, obsolete version numbers, or superseded methodology claims.
> All current canonical specifications are governed by:
> TOPPRISM_WORLD_MODEL_AND_DECISION_ENGINE_IMPROVEMENT_ROADMAP_v1_0.md
---

# SVDE 世界模型语义精化规格书 v1.1 (World Model Semantic Refinement Spec)
**Document ID:** SVDE-WORLD-MODEL-SEMANTIC-REFINEMENT-SPEC-v1.1  
**Date:** 2026-08-24  
**Status:** **ACTIVE SPECIFICATION (世界模型核心语义与关系拓扑规范)**  
**核心原则:** 
1. **缺失 ≠ 默认值**: 缺少数据必须显式标记 `MISSING` 或触发数据门禁，严禁静默填入默认值；
2. **冲突 ≠ 静默覆盖**: 多代表重叠归属必须显式记录为 `OwnershipConflictEvent`，严禁后行覆盖先行；
3. **历史事实 ≠ 当前政策**: 历史打卡记录（`ActualVisit`）是事实流，不能等同于未来的规划政策（`VisitPolicy`）；
4. **候选对象 ≠ 已冻结对象**: DCR 扩展对象必须具备完整的实体类、属性与关系映射，严禁仅停留在元数据注册。

---

## 1. 重建世界模型五大核心层级 (Five-Layer Architectural Taxonomy)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. 身份与拓扑层 (IDENTITY LAYER) — 企业静态经营主体与空间网络                          │
│    • Customer: 零售终端门店 (唯一主键: store_code)                                     │
│    • AccountHierarchy: 连锁大客户总部与层级 (NKA / RKA / Local Key)                    │
│    • Resource: 销售代表实体 (rep_id, 真实城市基准 Depot, 资质能力)                    │
│    • Territory: 地理辖区拓扑 (大区 / 区域 / 城市群 / 区县网格)                          │
│    • SupplyNode: 供应链供货大仓 (dc_id, dc_name, 服务 KA 清单)                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. 政策与契约层 (POLICY LAYER) — 约束业务行为的规则与意图                              │
│    • OwnershipPolicy: 客户-代表专管与分配政策 (带生效期与版本号)                       │
│    • VisitPolicy: 拜访频次与周期要求 (1次/周, 1次/2周, 1次/4周)                       │
│    • CadenceSpec: 节奏与日期间隔契约 (严格等距 7天/14天/28天)                          │
│    • Commitment: 锁定承诺 (FREE / RESOURCE_LOCKED / DAY_LOCKED / SEQUENCE_LOCKED)     │
│    • ProductLineScope: 多产品线组合政策 (皇家美素爆品 vs 源悦新品战略定位)             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. 动态事件与执行层 (EVENT LAYER) — 业务意图的具象化与现场事实流                       │
│    • VisitDemand: 拜访需求 (由客户等级、合同对赌、补货预警综合驱动)                    │
│    • PlannedVisit: 计划拜访时隙 (计划指派的日期、顺序与服务要求)                       │
│    • ActualVisit: 实际拜访事实 (真实进店/离店时间戳、在店时长、在途时长、线内/线外)    │
│    • InStoreAction: 现场作业动作明细 (开新派样/缺货处置/效期防损/陈列核销/店长订单)    │
│    • MerchandisingObservation: 现场陈列采集事实 (端架拍照、排面计数、空罐风险)        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. 观测与度量层 (MEASUREMENT LAYER) — 对物理与商业世界的感知测量                       │
│    • TravelCostMatrix: 真实路网通勤耗时与通行距离矩阵 (基于真实路网，非直线估算)       │
│    • ServiceDurationObservation: 在店作业时长历史统计分布与动作耗时基线                │
│    • MerchandisingCompliance: 合同陈列资产达标率核销测量 (目标数 vs 达标数 vs 达成率)  │
│    • CapacityObservation: 代表单日工作负荷与工时消耗测量                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. 规划与决策产物层 (PLAN LAYER) — 运筹引擎输出与人机协同审批成果                      │
│    • PeriodVisitPlan: 4 周周期性客户排班计划 (CandidatePlan)                           │
│    • DailyRoutePlan: 单日闭环路径与停靠序列                                            │
│    • DecisionArtifact: 经过三维独立审计与业务主管人工签署发布的最终执行决策             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心实体关系与基数矩阵 (Entity Relationships & Cardinality)

| 源实体 (Source) | 关系名称 (Relation) | 目标实体 (Target) | 基数 (Cardinality) | 业务语义与约束规则 |
| :--- | :--- | :--- | :--- | :--- |
| **`AccountHierarchy`** | `aggregates_stores` | `Customer` | $1 : N$ | 连锁总部统管多间子店，子店继承总部的全国性陈列协议 |
| **`Customer`** | `assigned_to` | `Resource` | $N : 1$ *(主)*<br>$N : M$ *(历史)* | 任意有效时间片内严格单一专管；历史变更沉淀为版本化归属记录 |
| **`Customer`** | `governed_by` | `VisitPolicy` | $1 : N$ | 一家门店可绑定多条政策（如常规月频政策 + 大促专项政策） |
| **`Customer`** | `supplied_by` | `SupplyNode` | $N : 1$ | 门店绑定其唯一对应供货总仓，协同到货与巡店时序 |
| **`Customer`** | `carries_portfolio` | `ProductLineScope` | $N : M$ | 门店销售多种产品线（如某店同时销售皇家美素与源悦） |
| **`VisitDemand`** | `materialized_as`| `PlannedVisit` | $1 : N$ | 一个月度需求按频次分解为多次具体的计划拜访时隙 |
| **`PlannedVisit`** | `fulfilled_by` | `ActualVisit` | $1 : 0..1$ | 计划拜访可能被实际履约（1），也可能失访（0，判定为 MISSED） |
| **`ActualVisit`** | `contains_actions` | `InStoreAction` | $1 : N$ | 一次现场拜访包含 1~5 个具体业务动作（如盘效期 + 调陈列） |
| **`ActualVisit`** | `measures_display` | `MerchandisingCompliance` | $1 : 0..1$ | 具有陈列考核的拜访输出一份量化陈列核销度量事实 |

---

## 3. 原始字段 $\rightarrow$ 事实对象 $\rightarrow$ 本体对象 溯源映射矩阵

```
┌─────────────────────────┬─────────────────────────────┬──────────────────────────┬──────────────────────────────────────────┐
│ 原始 Excel 字段          │ 提取事实对象 (Fact Object)  │ 映射本体对象 (Ontology)  │ 业务解释与规则判定                       │
├─────────────────────────┼─────────────────────────────┼──────────────────────────┼──────────────────────────────────────────┤
│ 主数据_门店编码 (Col 25) │ RawCustomerRecord.code      │ Customer.id              │ 门店全局唯一业务主键                     │
│ 主数据_门店名称 (Col 29) │ RawCustomerRecord.name      │ Customer.name            │ 门店官方登记名称                         │
│ 门店级别 (Col 4)         │ RawCustomerRecord.tier      │ Customer.tier            │ Key/A/B/C/D 级别 -> 决定履约等级 REQUIRED │
│ 拜访频率 (Col 5)         │ RawCustomerRecord.freq      │ VisitPolicy.cadence      │ 1/2/3/4 次/月 -> 决定严格 7/14/28 天周期  │
│ 门店负责人 (Col 6)       │ RawVisitRecord.rep          │ OwnershipPolicy.rep_id   │ 历史拜访执行人 -> 验证是否专管一致       │
│ 对应总仓 (Col 12)        │ RawCustomerRecord.dc        │ SupplyNode.dc_name       │ 18 个供货总仓 -> 协同大仓配货日历        │
│ 主数据_KA名称 (Col 32)   │ RawCustomerRecord.ka        │ AccountHierarchy.name    │ 爱婴室/孩子王等 13 大连锁总部体系         │
│ 主数据_媒体投放 (Col 39) │ RawCustomerRecord.media     │ ProductLineScope.brand   │ 皇家美素/源悦/纯悦 多产品线组合          │
│ 合同陈列目标数 (Col 21)  │ RawVisitRecord.disp_target  │ MerchandisingCompliance  │ 端架/地堆合同排面目标数                  │
│ 合同陈列达标数 (Col 22)  │ RawVisitRecord.disp_actual  │ MerchandisingCompliance  │ 现场实际核销达标排面数                   │
│ 拜访小结 (Col 20)        │ RawVisitRecord.summary      │ InStoreAction.action_type│ 5 大动作语义抽取 (开新/缺货/防损/陈列/客情)│
│ 进店/离店时间 (Col 13-14)│ RawVisitRecord.timestamps   │ ActualVisit.timestamps   │ 真实在店打卡时间戳                       │
│ 经度 / 纬度 (Col 26-27)  │ RawCustomerRecord.geo       │ Customer.location        │ 经纬度 -> 缺失必须触发 UNPLANNABLE 门禁  │
└─────────────────────────┴─────────────────────────────┴──────────────────────────┴──────────────────────────────────────────┘
```

---

## 4. 十大核心业务语义冲突裁决规范 (Semantic Disambiguation)

### 冲突 1: 3 次/月的严格数学语义
- **裁决结论**: 在 4 周标准周期中，3 次/月定义为 **“在 4 周中选择 3 周，且必须固定在同一个周几（Same Weekday）进店”**。其相邻拜访间隔为严格的 **7 天或 14 天**，绝不能简单写为浮动的 9 天。

### 冲突 2: 客户分级与履约等级绑定
- **裁决结论**: 
  - `Key` 级与 `A` 级门店：强制绑定为 **`FulfillmentClass = REQUIRED`**（硬履约底线，0 拜访即触发重大事故）；
  - `B` 级与 `C` 级门店：绑定为 **`FulfillmentClass = COMMITTED`**（常规履约承诺）；
  - `D` 级及单体商超：绑定为 **`FulfillmentClass = OPTIONAL`**（弹性维护，长途日可灵活调优）。

### 冲突 3: 供应链大仓配货日历
- **裁决结论**: 大仓配送节奏严禁程序默认写死。未接入供应链 ERP 实时数据前，`SupplyNode` 配送日历显式标记为 **`STATUS: UNCALIBRATED`**，仅作为空间拓扑参考，不作为硬约束阻断排班。

### 冲突 4: 代表 Depot 归属
- **裁决结论**: Depot 是 **Resource 实体与战区拓扑绑定的属性**（如苏州代表归属苏州市中心 Depot，南通代表归属崇川中心 Depot），全月路线必须严格从专属 Depot 闭环往返。

### 冲突 5: 多产品线与拜访需求关系
- **裁决结论**: 一家门店的多个产品线（如皇家 + 源悦）在快消现场由同一名代表在**同一次拜访中合并执行（Single Merged Visit）**，但在店服务时长由各产品线绑定的 `InStoreAction` 显式累加合成。

### 冲突 6: 动作对服务时长的决定机制
- **裁决结论**: 在店时长严禁使用固定常数 50 分钟，必须由动作基线合成：
  $$\text{ServiceDuration} = \sum_{\text{action} \in \text{TaskSet}} \text{BaseDuration}(\text{action})$$
  （效期防损 45.7 min / 缺货补货 54.0 min / 陈列核销 61.5 min 等）。

### 冲突 7: 客户归属冲突版本化
- **裁决结论**: 同一门店出现多代表记录时，严禁静默覆盖。系统必须生成 `OwnershipHistory` 链表，并将当前有效归属标记为 `CURRENT_ACTIVE`，历史记录标记为 `HISTORICAL_RECORD`。

### 冲突 8: 1A 严格同周几的硬性地位
- **裁决结论**: 1A 严格同周几是 **最高优先级业务硬约束**，旨在为零售店长建立绝对稳定的业务预期，除不可抗力外严禁跨周几漂移。

### 冲突 9: 频次主数据来源与有效性
- **裁决结论**: 门店频次必须以主数据 `拜访频率` 为唯一基准，历史发生频次仅作为 `ExecutionFact` 留存审计，严禁把历史偷懒的频次当成未来的业务政策。

### 冲突 10: 决策发布审批人机协同
- **裁决结论**: 任何算法生成的计划均为 `CandidatePlan (PENDING_APPROVAL)`，必须经过业务主管明确输入审批人 ID 与审批意见后，方可生成 `DecisionArtifact (APPROVED_FOR_EXECUTION)`。
