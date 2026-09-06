# TopPrism 规范验证 vs 实现验证矩阵 (Spec Check vs Implementation Check Matrix)

**Document ID:** TOPPRISM-SPEC-VS-IMPL-MATRIX  
**Version:** v1.0  
**Date:** 2026-08-24  

---

## 核心原则

本矩阵严格区分以下两种验证状态：

- **SPECIFICATION CHECK: PASS** — 规范文档中的设计描述已通过多轮文本审查，但尚未在代码中运行验证
- **IMPLEMENTATION CHECK: NOT RUN** — 对应的代码实现尚未启动（因冻结前不写代码的红线约束）

---

## 验证矩阵

| 检查项 | 规范层 | 代码层 | 说明 |
| :--- | :--- | :--- | :--- |
| **deep_freeze() date 分支** | SPEC: PASS | IMPL: NOT RUN | date 不查 tzinfo，直接 return |
| **deep_freeze() -0.0 拒绝** | SPEC: PASS | IMPL: NOT RUN | math.copysign(1.0, obj) < 0.0 |
| **deep_freeze() complex 禁止** | SPEC: PASS | IMPL: NOT RUN | raise TypeError |
| **deep_freeze() bytearray 拒绝** | SPEC: PASS | IMPL: NOT RUN | raise TypeError; 不做隐式 bytes 转换 |
| **deep_freeze() frozen dataclass 递归重建** | SPEC: PASS | IMPL: NOT RUN | type(obj)(**frozen_kwargs) |
| **RFC 8785 跨语言序列化** | SPEC: PASS | IMPL: NOT RUN | Python RFC 8785 库尚未选定 |
| **FrozenValue 类型封闭** | SPEC: PASS | IMPL: NOT RUN | 递归联合类型定义完成，代码验证未启动 |
| **L3 Guard A~E 守卫** | SPEC: PASS | IMPL: NOT RUN | 5 守卫形式化判定逻辑已写入规范 |
| **L3 审计哈希 RFC 8785** | SPEC: PASS | IMPL: NOT RUN | rfc8785_canonical_json 算法已定义 |
| **L5 simulation_time 统一** | SPEC: PASS | IMPL: NOT RUN | 5 个文档签名一致 |
| **L5 容量公式单位** | SPEC: PASS | IMPL: NOT RUN | 分钟/天数/工时量纲已明确 |
| **L7 2PC/Saga 事务** | SPEC: PASS | IMPL: NOT RUN | 幂等键/超时/补偿/审计已定义 |
| **L7 PlanningIntent 定义** | SPEC: PASS | IMPL: NOT RUN | 完整 dataclass 在 L7 §4.1 |
| **L7 PlanAuditReport 定义** | SPEC: PASS | IMPL: NOT RUN | 完整 dataclass 在 L7 §4.2 |
| **Canonical Types Spec §1-§38** | SPEC: PASS | IMPL: NOT RUN | 38 个章节号（§17/§18 为类型别名，§30 为非权威交叉引用；2026-08-26 增补 §37 PolicyAmendment / §38 OwnershipAssignment，代码迁移待签署）|
| **Registry 路径完整性** | SPEC: PASS | IMPL: NOT RUN | 领域类型全部指向 CANONICAL_TYPES_SPEC；API-INFRA 类型（6 个）指向主 API |
| **API simulation_time 签名** | SPEC: PASS | IMPL: NOT RUN | 全仓 5 文档一致 |
| **request_body Any 隔离** | SPEC: PASS | IMPL: NOT RUN | 已标注 INTERNAL + FrozenValue |
| **3 个历史文档标记** | DONE | N/A | HISTORICAL SNAPSHOT header 已添加 |

---


| **Dataclass 构造合法性** | SPEC: PASS | IMPL: NOT RUN | 必填字段在可选字段之前 |
| **深度不可变字段扫描** | SPEC: BLOCKED | IMPL: NOT RUN | Mapping 接口不等于深度不可变；需通过 deep_freeze() 构造边界保证 |
| **Any/Dict/List 逃逸检查** | SPEC: PASS (字面 Any) | IMPL: NOT RUN | 公共类型中 Tuple[Any,...] 已替换为命名类型；但 Mapping 构造边界未形式化 |
| **Registry 精确锚点** | SPEC: PASS | IMPL: NOT RUN | 每类型对应唯一章节号 |


| **类型引用闭合 (§35 支撑类型)** | SPEC: PASS | IMPL: NOT RUN | 9 个未定义引用已全部闭合（枚举/StatusTransitionEntry/SourceManifest/PolicyRegistry 等） |
| **弱类型字段参数化** | SPEC: PASS | IMPL: NOT RUN | 5 处裸 tuple 已改为 Tuple[str,...] / Tuple[time,time] |
| **类型加载顺序契约 (§36)** | SPEC: PASS | CI HOOK: NOT DEPLOYED | 规范性契约已固化；三步冒烟门禁为设计要求，工作区尚无 workflow/script |
| **双层权威 (Tier 1/Tier 2)** | SPEC: PASS | IMPL: NOT RUN | 领域类型权威=本规范；API-INFRA 6 类型权威=主 API，Registry 已标注 |

---

## 测试基线双命令澄清 (Test Baseline Clarification)

既有测试的两种可复现口径（均只证明既有代码无回归，不证明新规范成立）：

| 口径 | 精确命令 | 结果 |
| :--- | :--- | :--- |
| **A: 全量（含 tools 测试）** | `PYTHONPATH=svde/ontology/src python -m pytest svde/ontology/tests -q` + `python -m pytest svde/tests -q` + `cd svde-bench && python -m pytest -q` | 172 + 37 + **121** = **330 passed**（2026-08-26 刷新; 另有 shadow 包 75 passed 未计入）|
| **B: 仅 tests/ 目录** | `PYTHONPATH=svde/ontology/src python -m pytest svde/ontology/tests svde/tests svde-bench/tests -q`（从仓库根目录） | 历史 156 + 37 + **62** = **255 passed**（B 口径未刷新, A 口径为准）|

差异根因：`svde-bench` 从其目录内部运行 `pytest` 时会额外收集 `tools/*/tests/`（21 个文件、59 个测试）；从仓库根目录指定 `svde-bench/tests` 时仅收集 `tests/`（14 个文件、62 个测试）。两口径均已实测复现。

## 铁律

1. **SPEC: PASS 不等于 IMPL: PASS**；
2. **IMPL: NOT RUN 是当前所有新 API 规范的真实状态**（因冻结前不写代码红线）；
3. **代码实现必须在业务方完成 8 项签署 + API 冻结后才能启动**。
