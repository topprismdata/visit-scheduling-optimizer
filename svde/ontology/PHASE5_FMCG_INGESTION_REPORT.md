# SVDE Core Framework — Phase 5 FMCG 真实数据接入报告
**Document ID:** SVDE-PHASE5-FMCG-INGESTION-REPORT-V1.0
**Date:** 2026-08-24
**Status:** **PHASE 5 INGESTED & VERIFIED (108 prism tests + 37 Core + 121 Bench = 266 total PASS)**
**Source Data**: `data/real/fmcg_visit_history_with_geo.xlsx` (6,467 行真实拜访历史，53 列，7 位销售代表)

---

## 1. 真实数据特征摘要

| 维度 | 数据值 | 对应 v0.3 本体 |
| :--- | :--- | :--- |
| **总行数** | **6,467 行**（真实拜访事件记录） | `VisitEvent` / `PlannedVisit` / `ActualVisit` |
| **总列数** | **53 列**（其中 22 列精确映射，31 列列为未映射） | 详见 §2 字段映射表 |
| **销售代表数** | **7 位**（静、欣、许强、晓敏、仁军、超、佳佳） | `Resource`（7 位代表） |
| **代表工作日数** | 每位代表 208–246 工作日 | `ResourceDayProfile` |
| **代表覆盖门店数**| 每位代表 36–40 家门店 | `OwnershipPolicy`（客户-代表归属） |
| **客户分级** | Key (4289) / D (699) / B (659) / A (395) / C (371) | `Customer.tier`（STRATEGIC/CORE/STANDARD） |
| **拜访频次分布** | 4次/月 (2297), 2次/月 (2327), 1次/月 (979), 3次/月 (840) | `CadenceSpec.visits_per_month` |
| **经纬度质量** | 精确匹配 6374 行 (98.6%)，未匹配 93 行 (1.4%) | `Customer.location` / `TravelCostMatrix` |
| **单店在店时长** | 均值 51.5 分钟（47.3 ~ 56.0 分钟） | `RouteStop.service_duration` |
| **单段路程耗时** | 均值 41.7 分钟（30.7 ~ 53.5 分钟） | `TravelCostEstimate.in_transit_min` |

---

## 2. 字段映射矩阵（FMCG 列 $\rightarrow$ v0.3 本体对象）

```
[IDENTITY 层]
• 主数据_门店编码      → Customer.id
• 主数据_门店名称      → Customer.name
• 门店级别            → Customer.tier (Key→STRATEGIC, A→CORE, B/C/D→STANDARD)
• 经度 / 纬度         → Customer.location.lon / lat
• 主数据_KA名称       → Customer.ka_name
• 主数据_详细地址      → Customer.address
• 门店负责人          → Resource.rep_id (7位代表: 静/欣/许强/晓敏/仁军/超/佳佳)
• 大区 / 区域         → Resource.region / sub_region

[POLICY 层]
• 主数据_覆盖类型      → OwnershipPolicy.assignment_source
• 主数据_KA渠道        → OwnershipPolicy.channel_type

[EVENT 层]
• 拜访日期            → VisitEvent.date
• 进店时间 / 离店时间  → VisitEvent.arrival / departure
• 在店总时间(分钟)     → VisitEvent.service_duration
• 路程时间(分钟)       → VisitEvent.transit_duration
• 拜访类型            → VisitEvent.visit_type (线内/线外/取消)
• 拜访模式            → VisitEvent.visit_status (正常/取消/GPS偏差大)
• 星期几              → PlannedVisit.weekday
• 拜访顺序            → PlannedVisit.sequence_idx
• 拜访频率            → PlannedVisit.frequency_per_period
• 第几周              → PlannedVisit.week_of_period
```

---

## 3. 防升格与合规自检

- ✅ **零 SOP 字段引入**：GAP-6 永久关闭规则严格执行，无 `SOPPolicy` / `CustomerSOPBinding` 对象。
- ✅ **零算法概念泄漏**：无 `ColumnGen` / `LNS` / `Tabu` / `Simplex` 关键字。
- ✅ **零渠道层级升格**：`主数据_KA渠道` 仅作为属性值保留，不创建 `ChannelHierarchy` 本体对象。
- ✅ **零销售激励字段**：无 `Incentive` / `Quota` 字段引入。
- ✅ **可逆性保证**：每一行投影均保留 `source_row_ref` 指针，原始 53 列数据未被修改（只读摄入）。

---

## 4. 全仓测试回归总数

- `prism-ontology/tests/`: **108 个测试**（新增 21 个真实数据摄入、7 代表验证、字段映射覆盖与防升格测试）
- `svde/tests/`: **37 个测试**
- `svde-bench/`: **121 个测试**
- **全工作区总计**: **266/266 测试 100% 真实通过**（16.14s）。
