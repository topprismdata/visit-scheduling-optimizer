# 业务开放问题 — 需要业务方裁决

> 来源：Sales Visit Planning 本体与世界模型设计 §14
> 背景：这些问题直接决定世界模型中哪些状态是事实、哪些是策略，以及 Phase 2/3 的评价方式。
> **不应由算法团队自行猜测。**
> 状态：待业务方回复

## Q1: "客户"是什么粒度？

- A) 客户公司 (Account)
- B) 客户地点 (Location / Store)
- C) HCP (Healthcare Professional，如医生、采购主管)

**影响**: 本体类型定义、路线排列粒度、归属关系模型

## Q2: 拜访频次是合规要求还是动态建议？

- A) 硬性合规要求（必须严格执行，不满足即违规）
- B) 动态建议（可根据机会价值调整）

**当前证据**: 方案B 中频次仅认 {1, 2, 4}；黄金基准严格同周几硬锁定

**影响**: BIZ-01 签署内容重写；`CoveragePolicy.required_visits` 的刚性等级

## Q3: 哪些拜访一旦确认就不可移动？

- A) 已确认门店+日期全部冻结
- B) 未来 3 天内冻结
- C) 仅经理手动锁定的冻结
- D) 以上组合（请说明组合规则）

**影响**: Phase 3 Rolling-horizon 重算的冻结规则和稳定性预算参数

## Q4: 机会价值的来源

- A) 现有 CRM 字段直接映射（如 store_tier → priority_score）
- B) 商业规则引擎计算（如 tier × potential × recency）
- C) 独立建模（机器学习预测客户响应概率）

**影响**: BusinessSignal 数据管线的复杂度、Phase 2 上线时间表

## Q5: 前 3 个 KPI 是什么？

| 候选 | 排序 |
|---|---|
| 价值覆盖 | [ ] 第___ |
| 销量提升 | [ ] 第___ |
| 工时优化 | [ ] 第___ |
| 里程减少 | [ ] 第___ |
| 频次合规 | [ ] 第___ |

**影响**: ScenarioEngine 对比报告的维度排序；Phase 2 成功评估标准

## Q6: 人工覆盖计划的原因码

以下是候选原因码清单，请确认是否完整或需要增补：

- CUSTOMER_REQUESTED_CHANGE
- TIME_CONFLICT
- WEATHER_DISRUPTION
- VEHICLE_ISSUE
- REP_UNAVAILABLE
- URGENT_VISIT_REQUIRED
- ROUTE_OPTIMIZATION_REJECTED
- OTHER (请补充)

**影响**: ManualOverride.reason_code 字典；Phase 3 计划接受模型的训练信号分类