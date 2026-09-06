---
**Status:** EXPERIMENTAL DRAFT — NOT SIGNED, NOT EFFECTIVE
**Date:** 2026-08-25

> 本文件是**实验性草案**，**不是**业务规则。内容基于行业通用知识填充，**未获得**业务方签署。  
> MVP 正式基线**不**加载此规则。BIZ 框架在业务方签署前不得进入默认运行路径。  
> 待业务方覆盖 7 字段 (业务问题/选定规则/适用范围/生效时间/责任人/例外条件/违反处理) 后, 解除此 EXPERIMENTAL 标记。

---

# BIZ-05 GPS 偏差阈值与降级策略

**Document ID:** TOPPRISM-BIZ-05-GPS-v1.0
**Date:** 2026-08-25
**Status:** **DRAFT — 待业务方签署覆盖 (内容基于行业通用知识，无外部网络验证)**
**来源标注:** `[来源: 行业通用知识，无外部网络验证]`

---

## 1. 业务问题

代表 GPS 偏离门店多少米算"实际到店"？超过如何处理？影响拜访有效性判定吗？

## 2. 选定规则 (rule)

| 项 | 规则 |
|---|---|
| 默认 GPS 偏差上限 | 500 米 |
| 偏差 > 500m | 拜访打卡无效（视为未到店） |
| 偏差 > 1000m | CRITICAL_INCIDENT（疑似假打卡） |
| 偏差 200-500m | WARNING（需补 GPS 截图） |

## 3. 适用范围 (scope)

所有 SFA/CRM 现场打卡记录（含 CheckIn / CheckOut / MISSED_FLAG 三种事件）。

## 4. 生效时间 (effective_time)

2026-09-01 生效。

## 5. 责任人 (owner)

业务方: 销售运营经理 + IT 团队。

## 6. 例外条件 (exceptions)

- 室内/地下店（GPS 信号弱）: 允许 WiFi/蓝牙信标作为辅助证据
- 客户门店新搬迁（坐标未更新）: 7 天宽限

## 7. 违反处理 (violation_handling)

- 偏差 200-500m: WARNING（需后续补 GPS 截图或门店坐标）
- 偏差 > 500m: 拜访视为未到店（自动标记为 MISSED）
- 偏差 > 1000m: CRITICAL_INCIDENT（疑似假打卡，需人工复核）
