# SVDE 销售拜访本体层设计（Ontology Layer Blueprint v0.1）

**Document ID:** SVDE-SALES-VISIT-ONTOLOGY-V0.1
**Date:** 2026-08-24
**Status:** DRAFT — PENDING REVIEW
**Reviewer:** 待业务方与架构组联合审核
**Scope:** 销售拜访业务的本体层、决策层级与目标优先关系设计

---

## 0. 文档目的

在不动任何算法/求解器的前提下，把以下三点显式建模成机器可校验的本体与决策层级关系，供业务方与架构组审核：

1. 销售拜访业务对象是否完整
2. 业务对象与技术结构是否发生错误折叠
3. 决策层级是否显式、目标与硬约束的优先关系是否机器可验证

---

## 1. 本体设计三大原则

| 原则 | 描述 | 反例 |
| :--- | :--- | :--- |
| **不折叠原则** | `Customer ≠ VisitOccurrence ≠ RouteStop ≠ RoutePlan ≠ DecisionArtifact`，任一层语义不可被另一对象覆盖 | 把客户直接当成 `Task` 或 `RouteStop` |
| **决策层级原则** | 业务决策层（辖区 / 周期 / 单日路线）**先于**技术结构层（`Assignment` / `Routing` / `Periodic`） | Runtime 跳过 `BusinessDecision` 分发直接调用算力 |
| **目标优先原则** | `ObjectiveProfile` 显式建模硬约束 → 业务价值 → 距离 → 稳定性的分层优先级 | 距离最小化覆盖锁定承诺或频次 |

---

## 2. 业务对象定义（Business Objects）

所有对象必须能映射到以下 4 层之一：`Identity`（身份）/ `Policy`（规则）/ `Event`（发生）/ `Plan`（计划）。

| 对象 | 层级 | 关键属性 | 不允许的映射 |
| :--- | :--- | :--- | :--- |
| `Customer` | Identity | `id, tier, commercial_value, location, required_cadence_class` | 不允许被映射为 `Task` 或 `RouteStop` |
| `VisitPolicy` | Policy | `id, customer_id, cadence_spec_id, weekly_availability, time_window, min/max_interval_days` | 不允许被映射为 `COMMITTED_TASK` |
| `CadenceSpec` | Policy | `id, visits_per_week, visits_per_month, tolerance_days` | 同上 |
| `OwnershipPolicy` | Policy | `customer_id, rep_id, is_locked, tenure_months` | 不允许被映射为 `assignments` 中的"软偏好" |
| `ExistingCommitment` | Policy (Hard) | `id, customer_id, rep_id, date, time_window, is_hard` | **绝对不可降级为软偏好** |
| `VisitDemand` | Event | `id, customer_id, policy_id, requested_window` | 不允许被映射为 `COMMITTED_TASK.demand` |
| `VisitOccurrence` | Event | `id, customer_id, date, rep_id, time_window, is_locked, frequency_compliance` | 区别于 `VisitDemand`：是"已发生项"不是"待发生项" |
| `ResourceDayProfile` | Policy | `rep_id, date, total_capacity_minutes, available_minutes` | 不允许被映射为资源 `capacity` |
| `TravelCost` | Policy | `source, matrix, captured_at` | 不允许被默认化为"距离最短" |
| `RouteStop` | Plan | `id, occurrence_id, planned_arrival, actual_arrival, service_duration` | 是 `VisitOccurrence` 的物理落地，不是 Customer 本身 |
| `RoutePlan` | Plan | `id, target_date, rep_id, sequence[RouteStop], depot_id, total_distance_km, total_in_transit_min, total_service_min, total_wait_min` | 不允许直接保存 `Customer[]`，只保存 `Stop[]` |
| `ObjectiveProfile` | Policy | `priority_levels[], deprioritize_distance, forbid_relaxing_locked` | 必须显式声明 `must_not_override` 关系 |
| `DeferralPolicy` | Policy | `customer_id, allowed_deferral_days, requires_approval, business_cost_per_day` | 不允许被简化为"无延期"硬约束 |

---

## 3. 业务对象关系（Relations）

| 关系 | 描述 | 提交条件 |
| :--- | :--- | :--- |
| `VisitPolicy` → `VisitDemand` | 政策生成待发生项 | `policy.customer_id == demand.customer_id` |
| `VisitDemand` ⊆ `PlanningHorizon` | 待发生项必须落在规划周期内 | `horizon.contains(demand.date)` |
| `VisitOccurrence` ⊆ `PlanningHorizon` | 已发生项同样必须落在周期内 | 同上 |
| `VisitOccurrence` → `Customer` | 发生项归属客户 | `occurrence.customer_id == customer.id` |
| `VisitOccurrence` ↔ `CadenceSpec` | 发生项受频次约束 | `occurrence.compliance_spec(spec)` |
| `VisitOccurrence` → `ResourceDayProfile` | 发生项占用代表日容量 | `profile.date == occurrence.date` |
| `VisitOccurrence` → `RouteStop` | 发生项被具象化为路线节点 | 必须在 RoutePlan 中 |
| `RoutePlan` → `RouteStop[]` | 路线排序节点 | 顺序可优化但 **不可改变发生项集合** |
| `RoutePlan` ↔ `TravelCost` | 路线由实际路网成本评估 | 不允许默认直线距离 |
| `ObjectiveProfile` → `RoutePlan` | 路线优化服从分层目标 | `level_0_hard_constraints > level_1_value > level_2_distance` |
| `DeferralPolicy` → `VisitOccurrence` | 延期需要审批 + 业务代价 | 不允许静默延期 |
| `ExistingCommitment` → `VisitOccurrence` | 锁定承诺具象化为不可移动项 | `is_hard == True` 严格不可降级 |
| `BusinessDecision` → `DecisionLevel` | 业务问题被分类为决策层 | **必经**分发层，不可跳过 |

---

## 4. 决策层级（Decision Levels）

| DecisionLevel | 输入对象集 | 输出对象集 | 候选 Capability | 不允许的越权 |
| :--- | :--- | :--- | :--- | :--- |
| `TERRITORY_ALIGNMENT` | `Customer, OwnershipPolicy, VisitPolicy, ResourceDayProfile` | `BusinessDecision(TERRITORY)` | `TerritoryAlignmentCapability` | 改变锁定归属 / 改变拜访频次 / 改变路线 |
| `PERIODIC_COVERAGE` | `VisitDemand, CadenceSpec, ExistingCommitment, ResourceDayProfile` | `BusinessDecision(PERIODIC)` | `PeriodicVisitPlanningCapability` | 改变单日路线 / 改变具体时段到分钟 |
| `DAILY_ROUTE_SEQUENCING` | `VisitOccurrence[], TravelCost, ResourceDayProfile, ExistingCommitment` | `BusinessDecision(DAILY)` | `DailyRouteOptimizationCapability` | 改变发生项集合 / 改变频次 / 改变代表 / 取消锁定项 |
| `ROLLING_REPLAN` | `ExistingCommitment + VisitDemand` | `BusinessDecision(ROLLING)` | 多能力组合 | 取消已批准延期 |
| `DISTANCE_TIME_TRADEOFF` | `RoutePlan + ObjectiveProfile` | `BusinessDecision(TRADEOFF)` | 距离 ↔ 时间 评估 | **任何降频 / 改锁定 / 改归属** |

---

## 5. 目标与硬约束优先关系（机器可验证）

| 优先关系 | 描述 | 机器验证方法 |
| :--- | :--- | :--- |
| `DistanceMinimization.subordinate_to(CoverageCompliance)` | 距离不可越级覆盖频次 | `coverage_compliance_pct == 100%` 才允许报告距离下降 |
| `DistanceMinimization.must_not_override(CommitmentLock)` | 距离不可移动锁定承诺 | 锁定项 `is_locked_window=True` 的到达时间必须落在窗口内 |
| `DistanceMinimization.cannot_reduce(CadenceSpec.min_interval_days)` | 距离不可压缩客户间隔 | 同一客户相邻拜访间隔 ≥ `min_interval_days` |
| `DailyRouteOptimization.requires(FixedVisitSet)` | 单日路线必须基于固定发生项 | 输入的 `RouteStop[]` 集合不可被修改 |
| `PeriodicVisitPlanning.requires(PlanningHorizon)` | 周期规划必须基于规划周期 | 必有 `start_date ≤ visit_date ≤ end_date` |
| `RouteOptimization ≠ VisitPlanning` | 路线优化 ≠ 拜访规划 | 两者 Capability ID、输入输出契约必须显式不同 |

---

## 6. 反伪证 + 错误降维阻断（核心本体测试）

> **任何错误降维必须被本体层主动拒绝**。

| 触发场景 | 错误降维 | 正确分类 | 阻断机制 |
| :--- | :--- | :--- | :--- |
| 用户："缩短销售线路在途距离" | 直接归类为 VRP / TSP | 先判 `TERRITORY_ALIGNMENT` vs `PERIODIC_COVERAGE` vs `DAILY_ROUTE_SEQUENCING` | `IntentDiagnosticEngine` 强制三层分流 |
| 用户："客户被分错了代表" | 归类为路线问题 | `TERRITORY_ALIGNMENT` | 关键词权重 + Capability 候选集精确匹配 |
| 用户："四周拜访频次不均" | 归类为 `DAILY_ROUTE_SEQUENCING` | `PERIODIC_COVERAGE` | 频次类关键词优先映射周期能力 |
| 用户："今天 8 家店怎么排更顺路" | 归类为周期频次 | `DAILY_ROUTE_SEQUENCING` | "今天" + "顺路" 关键词定向单日 |
| 用户："临时新增一个高价值门店" | 归类为 `DAILY_ROUTE_SEQUENCING` | `ROLLING_REPLAN` | 触发条件含新增 |

---

## 7. 现有 SVDE 结构与本体的"折叠度"自检

> **必须诚实地标出现有代码与本体的折叠度**。

| 现有 SVDE 对象 | 实际折叠 | 应还原为 |
| :--- | :--- | :--- |
| `NormalizedEntity(entity_type="EXECUTION_RESOURCE")` | 折叠了 `Resource` 与 `ResourceDayProfile` | 分拆为两者 |
| `NormalizedEntity(entity_type="COMMITTED_TASK")` | 折叠了 `VisitDemand` / `VisitOccurrence` / `RouteStop` | 三者必须独立 |
| `DecisionContext.entities` | 折叠了 `Customer` / `VisitPolicy` / `CadenceSpec` / `OwnershipPolicy` | 业务字段必须显式建模 |
| `VisitDomainAdapter` | 直接把客户映射为 `COMMITTED_TASK` | 必须经 `VisitPolicy` / `VisitOccurrence` 显式转换 |
| `DiscreteAssignmentSolverCapability` | 折叠了"单日分配"与"周期规划" | 拆分独立能力 |
| `DecisionArtifact.decision` | 折叠了 `assignments` 与 `RoutePlan` | 必须分类返回 |

---

## 8. 拟提交审核的本体层自检问题（回归套件）

| ID | 用户问题 | 正确分类 | 反伪证断言 |
| :--- | :--- | :--- | :--- |
| ONT-1 | "客户被分给了错误代表" | `TerritoryAlignment` | 拒绝 `DailyRoute` |
| ONT-2 | "四周拜访频次不均匀" | `PeriodicCoverage` | 拒绝 `DailyRoute` |
| ONT-3 | "今天这8家店怎么排更顺路" | `DailyRouteSequencing` | 拒绝 `PeriodicCoverage` |
| ONT-4 | "路线很长但不能减少必访客户" | 距离 `subordinate_to` 必访集合 | 必访集合在结果中必须保持 |
| ONT-5 | "临时新增一个高价值门店" | `RollingReplan` | 拒绝 `DailyRoute` |
| ONT-6 | "把锁定件往后挪一天" | 显式拒绝 | `must_not_override CommitmentLock` 触发 |
| ONT-7 | "Customer 不允许被映射为 COMMITTED_TASK" | 类型折叠拒绝 | 类型断言 |
| ONT-8 | "RouteOptimization 不允许声称改变 PeriodPlan" | Capability 互斥 | Capability ID 不同 |

---

## 9. 待你审核的三个关键设计决策

请重点审核这三点，确认后再继续推进：

1. **业务对象是否完整？** 是否有遗漏的实体（例如 `Product` 拜访货物、Subsidiary 分公司、AP Route 审批项）？
2. **关系建模是否准确？** `VisitDemand` vs `VisitOccurrence` 的拆分是否符合你们真实业务流转（计划 vs 实际打卡）？
3. **反折叠自检是否过严或过宽？**  
   - 过严 → 现有代码大量无法通过；  
   - 过宽 → 错误折叠仍会漏网。

---

## 10. 下一步建议（待你拍板）

**A. 仅做本体层 review → 不动代码，等你验收**  
**B. 本体 review 通过后，迁移现有 DomainAdapter（不引入求解器）**  
**C. 同时启动周期 Capability（基于 `CadenceSpec`）与单日 Capability（基于 `VisitOccurrence`）的能力契约**  

请下达下一步具体指令。
