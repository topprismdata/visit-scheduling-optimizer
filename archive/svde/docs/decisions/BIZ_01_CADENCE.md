---
**Status:** EXPERIMENTAL DRAFT — NOT SIGNED, NOT EFFECTIVE
**Date:** 2026-08-25

> 本文件是**实验性草案**，**不是**业务规则。内容基于行业通用知识填充，**未获得**业务方签署。  
> MVP 正式基线**不**加载此规则。BIZ 框架在业务方签署前不得进入默认运行路径。  
> 待业务方覆盖 7 字段 (业务问题/选定规则/适用范围/生效时间/责任人/例外条件/违反处理) 后, 解除此 EXPERIMENTAL 标记。

---

# BIZ-01 CADENCE 频次语义

**Document ID:** TOPPRISM-BIZ-01-CADENCE-v1.0
**Date:** 2026-08-25
**Status:** **DRAFT — 待业务方签署覆盖 (内容基于行业通用知识，无外部网络验证)**
**来源标注:** `[来源: 行业通用知识 + 项目内已有规划 (svde/docs/SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC_v2.0.md)，无外部网络验证]`

---

## 1. 业务问题

销售拜访系统中，每家门店每月应被拜访几次？允许多大时间误差？

## 2. 选定规则 (rule)

按门店级别 (tier) 设定月度拜访频次上限与下限，误差窗口按频次分档：

| 门店级别 (tier) | 月度频次 (times/month) | 误差窗口 (days) | 业务说明 |
|---|---|---|---|
| Key | 4 | ±2 | 关键大店，频次最高，误差最严 |
| A | 3-4 | ±3 | A 级主力店 |
| B | 2 | ±5 | B 级常规店 |
| C | 1 | ±7 | C 级维护店 |
| D | 0-1 | 不限 | D 级长尾 |

## 3. 适用范围 (scope)

所有 246 家门店（仁军代表的南通片区 + 其他 6 位代表管区）。

## 4. 生效时间 (effective_time)

2026-09-01 生效。

## 5. 责任人 (owner)

业务方: 销售运营经理。

## 6. 例外条件 (exceptions)

- 春节当月（农历正月）: 频次下限可放宽 50%（Key 仍需 ≥2 次）
- 国庆/618/双11 当月: 频次上限可放宽 30%
- 客户主动申请暂停拜访: 例外 1 个月

## 7. 违反处理 (violation_handling)

- **WARNING**: 实际频次低于下限 1 次
- **CRITICAL_INCIDENT**: Key 店频次为 0，或实际频次低于下限 ≥2 次

---

## MVP 集成方式

BIZ-01 加载到 `BIZSigningRegistry` 后，MVP 在 audit 阶段执行 `apply_biz_01_cadence(plan, world_state, biz_rule) → List[ConstraintViolation]`：

- 检查 `plan.daily_routes` 每家门店实际拜访次数 vs 规则下限/上限
- 误差窗口检查: 实际拜访日 vs `policy_version.effective_time` 起始日的天数差
- 返回违反清单进入 `MVPResult.constraint_violations`
- 不修改主流程主链路

## 业务方签署时

业务方仅需覆盖本文档的 7 字段文本即可（业务问题/选定规则/适用范围/生效时间/责任人/例外条件/违反处理）。MVP 校验框架**不变**。
