---
**Status:** EXPERIMENTAL DRAFT — NOT SIGNED, NOT EFFECTIVE
**Date:** 2026-08-25

> 本文件是**实验性草案**，**不是**业务规则。内容基于行业通用知识填充，**未获得**业务方签署。  
> MVP 正式基线**不**加载此规则。BIZ 框架在业务方签署前不得进入默认运行路径。  
> 待业务方覆盖 7 字段 (业务问题/选定规则/适用范围/生效时间/责任人/例外条件/违反处理) 后, 解除此 EXPERIMENTAL 标记。

---

# BIZ-01~09 业务签署接收 Workflow

**Document ID:** TOPPRISM-BIZ-SIGNING-WORKFLOW-v1.0
**Date:** 2026-08-25
**Status:** **DRAFT (Ready for BIZ-01 first item)**

---

## 1. 目的

BIZ-01~09 是销售拜访域**业务规则**（频次、Deferral、Key 店零脱访、GPS 阈值、工时红线、归属冲突、多产品线、审批层级等），需业务方**逐项**书面签署确认。

MVP 在规则到货前默认不应用任何业务规则；规则到货后，MVP 仅做**约束检查开关**——在 audit 阶段叠加到 `MVPResult.constraint_violations`，**不修改主流程**。

---

## 2. 接收流程

每项 BIZ 业务方需填写以下 7 字段 schema：

| # | 字段 | 含义 |
|---|---|---|
| 1 | 业务问题 (business_question) | 该规则要解决的业务问题（一句话） |
| 2 | 选定规则 (rule) | 规则的精确表述（如"1A 类大店每月 4 次，误差 ±2 天"） |
| 3 | 适用范围 (scope) | 该规则适用哪些对象（店类型 / 时间 / 区域） |
| 4 | 生效时间 (effective_time) | 该规则何时开始生效 |
| 5 | 责任人 (owner) | 该规则的业务责任人 |
| 6 | 例外条件 (exceptions) | 该规则不适用的场景（如"春节当月"） |
| 7 | 违反处理 (violation_handling) | 违反规则时如何处理（CRITICAL_INCIDENT / WARNING / IGNORE） |

**当前 BIZ-01~09 内容**：先用公开资料/通用实践填充（见 `BIZ_01..09_*.md`），明确标注 `[来源: 公开资料/通用实践，非贵司实际业务]`。业务方签署时直接覆盖文本。

---

## 3. 应用流程

```
业务方返回 1 份 BIZ-XX 签署
  ↓
我方 (本项目) 落盘 BIZ-XX 决策文档
  ↓
MVP 加载 BIZSigningRegistry (仅在 MVP 进程内有效)
  ↓
MVP 在 audit 阶段叠加 BIZ 规则校验
  ↓
MVPResult.constraint_violations 增加 BIZ 校验条目
  ↓
跑 9+ 个 MVP 测试 + 全量回归
  ↓
不创建新状态报告版本
```

**严格红线**：
- ❌ 不实现 BIZ 规则的**实际业务执行**（仅做"接收 + 加载 + 校验"框架）
- ❌ 不修改 MVP 主流程主链路
- ❌ 不创建新状态报告版本
- ❌ 不等 9 项全部到货才动；签一项就动一项

---

## 4. BIZ 列表

| ID | 主题 | 文档 |
|---|---|---|
| BIZ-01 | CADENCE 频次语义（1A/2A/3A/B/C/D 各级别节奏与误差窗口） | `BIZ_01_CADENCE.md` |
| BIZ-02 | 3 次/月频次具体语义 | `BIZ_02_3_PER_MONTH.md` |
| BIZ-03 | Deferral 配额与延期窗口 | `BIZ_03_DEFERRAL.md` |
| BIZ-04 | Key/A 店零脱访刚性 | `BIZ_04_KEY_STORE.md` |
| BIZ-05 | GPS 偏差阈值与降级策略 | `BIZ_05_GPS.md` |
| BIZ-06 | 工时双重红线 | `BIZ_06_WORKLOAD.md` |
| BIZ-07 | 归属冲突优先级 | `BIZ_07_OWNERSHIP.md` |
| BIZ-08 | 多产品线拜访策略 | `BIZ_08_MULTI_PRODUCT.md` |
| BIZ-09 | 决策审批层级 | `BIZ_09_APPROVAL.md` |
