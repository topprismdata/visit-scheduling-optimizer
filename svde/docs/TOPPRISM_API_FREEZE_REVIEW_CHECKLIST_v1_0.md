---
**Status:** HISTORICAL SNAPSHOT — NOT THE CURRENT CANONICAL STRUCTURE
**MIGRATED-TO:** `svde/docs/TOPPRISM_CANONICAL_ENTERPRISE_ARCHITECTURE_BASELINE_v1_0.md`
**Reason:** 本文档采用 L0-L6（6 层）或 Pre-L0-L7 编号；当前提议中的 Canonical 分层已扩展为 L0-L7（7 层）。
**Date:** 2026-08-25

> 本状态为 **PROPOSED CANONICAL / PARTIALLY ALIGNED**；待 Phase 0 完成全仓 4 类分类文档迁移。

---

# TopPrism L0-L6 Canonical World Model API 冻结评审核对清单 (Freeze Review Checklist)

**Document ID:** TOPPRISM-API-FREEZE-CHECKLIST-v1.0  
**Version:** v1.0-draft.5.2  
**Date:** 2026-08-24  
**待评审规范:** `TOPPRISM_L0_L6_CANONICAL_WORLD_MODEL_API_SPEC_v1_0.md` (v1.0-draft.5.2)  
**评审性质:** 契约冻结正式签署前的终极逐项核对清单 (Pre-Freeze Final Checklist)

---

## 一、技术与契约完整性核对表 (技术架构团队签署)

| 检查项编号 | 审查维度与具体标准 | 规范对齐位置 | 自检状态 | 技术签署状态 |
| :--- | :--- | :--- | :--- | :--- |
| **TECH-01** | **深度不可变算法**: `deep_freeze()` 采用路径栈消除循环误判，清晰分离 `datetime`/`date`/`time`，拒绝 `-0.0`/`NaN`/`Inf`，**拒绝** `bytearray`（raise TypeError，不做隐式 bytes 转换），禁止 `complex`，递归重建 frozen dataclass | 主规范 §3.0 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-02** | **RFC 8785 指纹矩阵**: 完整给出 16 类数据类型的规范化转换规则，明确 float、datetime UTC、Decimal、键名按 RFC 8785 UTF-16 code unit 排序 | 主规范 §2.2 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-03** | **授权四状态生命周期**: 明确 `AVAILABLE → RESERVED → CONSUMED / ROLLED_BACK` 唯一状态机，明确 `ROLLED_BACK` 为废弃终态 (不可复用) | 主规范 §4.1 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-04** | **Storage CAS 信任模型**: 明确服务端 `compile_planner_projection()` 绝不信任客户端传入的 `status`，以 Storage CAS 为准 | 主规范 §4.2 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-05** | **跨文档签名全量一致**: `compile_planner_projection(context, snapshot_id, intent, partial_auth)` 在全仓文档中无任何旧版本残留 | 全仓扫描 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-06** | **异常类体系标准构造**: 统一 `default_code` 属性与 `super().__init__(message, context)`，修正 `self.context = ...` | 主规范 §6.0 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-07** | **集中上下文强制携带**: 所有 API 通过 `ApiRequestContext` 集中传递 `api_version`, `request_id`, `timezone` (拒绝 naive) | 主规范 §2.1 | 已自检对齐 | [ ] 待技术架构签署确认 |
| **TECH-08** | **WorkflowContext / RequestFingerprint 类型定义完整性**: 主规范 §5.2.1 已按 Registry 权威字段登记补全 `WorkflowContext` (expected_snapshot_version / idempotency_key / fingerprint) 与 `RequestFingerprint` (server-computed 防伪) frozen 定义；此前两者均为悬空引用 (仅有 API 签名无类型定义) | 主规范 §5.2.1 | 已自检对齐 | [ ] 待技术架构签署确认 |

---

## 二、业务语义签署核对表 (业务主管团队签署)

*(依据 `BUSINESS_SIGNOFF_REQUIREMENTS.md` 8 项业务语义)*

| 业务项编号 | 核心业务语义问题 | 业务方确认选项 / 签署结论 | 签署状态 |
| :--- | :--- | :--- | :--- |
| **BIZ-01** | **3 次/月频次语义**: A(同周几选3周) / B(每9-10天) / C(大仓排定) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待业务签署 |
| **BIZ-02** | **DeferralPolicy 规则**: A(单月最多1次/7天内) / B(单月最多2次/经理批) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待业务签署 |
| **BIZ-03** | **Key/A 级零脱访刚性**: A(绝对零脱访/代班) / B(允许1周内补访) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待业务签署 |
| **BIZ-04** | **GPS 偏差阈值**: A(500m) / B(1km) / C(200m) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待业务签署 |
| **BIZ-05** | **工时双重红线**: A(近郊480/长途660批准) / B(统一600) / C(按距离弹性) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待业务签署 |
| **BIZ-06** | **客户归属冲突优先级**: A(打卡最多) / B(区域优先) / C(经理指派) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待签署 |
| **BIZ-07** | **多产品线拜访策略**: A(合并一次拜访) / B(分别拜访) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待签署 |
| **BIZ-08** | **决策引擎审批层级**: A(仅主管) / B(主管+总监双签) / C(Key店总监批) | 待业务方勾选: [ ] A  [ ] B  [ ] C | ⏳ 待签署 |

---

## 三、冻结签署结论 (Final Sign-off)

- **技术架构签署**:  
  `[ ] 确认上述 8 项技术规范，同意冻结 L0-L6 Canonical World Model API 规范 (v1.0-draft.5.2 -> v1.0-FROZEN)`  
  签署人: ____________________ 日期: ______________

- **业务主管签署**:  
  `[ ] 确认上述 8 项业务语义，同意作为后续决策引擎与状态转移的执行依据`  
  签署人: ____________________ 日期: ______________

---
*(注：在双方未全部完成签署前，本 API 规范保持草案状态，严禁进入代码实现)*
