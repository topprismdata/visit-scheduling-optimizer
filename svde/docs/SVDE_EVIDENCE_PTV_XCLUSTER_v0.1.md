# SVDE Sales Visit — PTV xCluster/xTerritory/xTour Evidence Bundle
**Document ID:** SVDE-EVIDENCE-PTV-XCLUSTER-V1.0
**Date:** 2026-08-24
**Status:** COLLECTED — PENDING CROSSWALK INTEGRATION
**Source:** PTV xServer Manual (xtour-eu-n-test.cloud.ptvgroup.com)

---

## [REF-PTV-001] PTV xCluster 多周拜访规划 — Order/Visit/Rhythm/Pattern 模型
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025 (manual copyright)
- **Type**: `PRODUCT_FACT`
- **Scope**: Multi-week visit planning with week rhythms and weekday patterns
- **Source / Page**: Use Cases > PTV xCluster > How to Plan Multi Weeks
- **Original quote**:
  > "The method performs clusters for visits with more than one week. Hereby, a list of orders is defined whereby each location is visited one or more times within the given weeks (an order is assigned at least to one visit). Thereby all visits of an order have the same location and follow specified week rhythms (e.g. every week or biweekly) and within a week specified weekday patterns. The cluster optimization groups these visits into the given weeks and weekdays assigning every visit to exactly one day. Every day corresponds to one cluster."
- **Key attributes**:
  > "assignmentRules: All rules and restrictions to assign each visit of the order to exactly one day. These specifications must enable at least one valid multi-week assignment."
  > "visitSplits: Number of visits within one day by splitting the visit in several parts. This is relevant for the calculation of the corresponding quantities."
- **Supported business claim**: `CadenceSpec` 的 visits_per_week / visits_per_month / tolerance_days 建模方式与 PTV 的 week rhythms + weekday patterns + assignmentRules **高度一致**。
- **Evidence level**: `PRODUCT_FACT`

---

## [REF-PTV-002] PTV xCluster 单周拜访规划 — Weekday Pattern 模型
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Single-week visit planning with weekday patterns
- **Source / Page**: Use Cases > PTV xCluster > How to Plan a Week
- **Original quote**:
  > "The visits should be planned for a week in advance. Hereby, a list of orders is specified whereby each location is visited at least once a week (one or more visits can be assigned to an order). All visits of a certain order have the same location and follow specified weekday patterns (for example in case of two visits Monday-Wednesday or Tuesday-Friday). Each cluster corresponds to exactly one working day, and every visit is assigned to exactly one cluster."
- **Supported business claim**: `VisitPolicy.weekly_availability` 的 weekday pattern 建模方式与 PTV **一致**。
- **Evidence level**: `PRODUCT_FACT`

---

## [REF-PTV-003] PTV xTerritory 辖区规划 — Territory/Assignment/Center 模型
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Territory planning for sales representative management
- **Source / Page**: Use Cases > Cluster Planning > How to plan territories
- **Original quote**:
  > "The PTV xTerritory server allows you to plan and change territories and territory centres based on locations such as, for example, customer addresses, or based on smaller administrative area units such as postcode areas. Common use cases are in the management of sales representatives, the planning of warehouse locations and their delivery areas and in delivery planning."
  > Terminology: "location, customer, order — Addresses of which the position cannot be altered (e.g. customers) or reference points of administrative territorial units"
  > "assignment — Assignment of a location to a territory; multiple assignments are not possible"
  > "territory center, reference point, sales representatives — Fixed territory center which services the other locations in a territory"
- **Supported business claim**: `Customer`（不可移动）+ `OwnershipPolicy`（单一归属）+ `Resource`（territory center = sales rep）的三层拆分与 PTV **一致**。
- **Evidence level**: `PRODUCT_FACT`

---

## [REF-PTV-004] PTV xTerritory 固定分配与不兼容约束
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Fixed assignments and incompatibility restrictions in territory planning
- **Source / Page**: Use Cases > Cluster Planning > with fixed assignments / with restrictions
- **Original quote**:
  > "with fixed assignments — certain locations are pre-assigned to specific territories and cannot be moved"
  > "with restrictions / incompatibilities — certain locations must not be in the same territory"
- **Supported business claim**: `OwnershipPolicy.is_locked` + `EligibilityPolicy.excluded_customer_ids` 的建模方式与 PTV **一致**。
- **Evidence level**: `PRODUCT_FACT`

---

## [REF-PTV-005] PTV xTour 目标优先级 — 覆盖优先于距离
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Tour planning optimization goals
- **Source / Page**: Technical Concepts > About Tour Planning
- **Original quote**:
  > "The build in planning algorithms try to solve this problem considering several optimization goals: Assign as much as possible transport orders to vehicle tours. Minimise the number of vehicle tours. Minimise the distance and period of every vehicle tour."
- **Supported business claim**: PTV 的目标优先级（覆盖最大化 > 路线数最少 > 距离最短）与 SVDE v0.3 的 `Level 1 > Level 2` 分层目标 **结构一致**。这为 `DistanceMinimization.subordinateTo(CoverageCompliance)` 提供了独立 `PRODUCT_FACT` 证据。
- **Evidence level**: `PRODUCT_FACT`

---

## [REF-PTV-006] PTV xTerritory Tour Period Estimator — 辖区估算
- **Author / Org**: PTV Logistics GmbH
- **Year**: 2025
- **Type**: `PRODUCT_FACT`
- **Scope**: Tour period estimation without full route solving
- **Source / Page**: Use Cases > Cluster Planning > How to use the tour period estimation
- **Original quote**:
  > "With the PTV xTerritory server's tour period estimation, also time estimates for tour periods can be calculated. A common use case for the tour period estimation is in planning and management of sales representatives who travel from customer location to customer location to provide service."
  > "A Tour Period is a time estimate in seconds of a service tour"
- **Supported business claim**: 存在"不求解路线、只估算辖区工作量"的独立能力（估算器），对应 SVDE `DISTANCE_TIME_TRADEOFF` 决策层的输入。
- **Evidence level**: `PRODUCT_FACT`

---

## 新发现的候选概念（需 GAP 裁决）

### 候选 1: `visitSplits`（一天内多次拜访同一客户）
- **来源**: [REF-PTV-001] xCluster Multi-Week
- **原文**: "visitSplits: Number of visits within one day by splitting the visit in several parts."
- **SVDE 现状**: v0.3 无此概念
- **建议**: 发起 GAP-7 裁决

### 候选 2: `predefined groups`（预定义客户组）
- **来源**: [REF-PTV-004] xTerritory with predefined groups
- **原文**: "with predefined groups — locations can be grouped so they must be in the same territory"
- **SVDE 现状**: v0.3 无此概念
- **建议**: 发起 GAP-8 裁决

### 候选 3: `Tour Period Estimator`（辖区估算器，不求解）
- **来源**: [REF-PTV-006] xTerritory Tour Period Estimation
- **原文**: 不做路线求解，只输出辖区级别的时长估算
- **SVDE 现状**: v0.3 无独立估算能力
- **建议**: 可作为 `DISTANCE_TIME_TRADEOFF` 能力契约的参考，**不需** GAP（属 Capability 层非本体层）
