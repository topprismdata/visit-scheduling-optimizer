# TopPrism SVDE 基础世界模型 WM-FIX 核心整改闭环报告 (World Model Foundation Fixes)
**Document ID:** SVDE-WM-FIX-REMEDIATION-CLOSURE-REPORT-v1.0  
**Date:** 2026-08-24  
**审查触发:** `SVDE_CROSS_INDUSTRY_WORLD_MODEL_RESEARCH_BASELINE_v1_0.md`  
**执行路径:** WM-FIX-1 / WM-FIX-2 / WM-FIX-3 / WM-FIX-4 / WM-FIX-5  
**最终状态:** **304 / 304 tests PASS (prism-ontology: 146, SVDE Core: 37, SVDE Bench: 121)**

---

## 一、整改落地清单

### 1. WM-FIX-1: 唯一化 L1 通用元模型 (`SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md`)
- 严格收紧 11 类元类型为 **8 个基础元类型** + **3 个衍生操作元类型** 的正交体系；
- 显式定义 `MetaEntity` 子类（AgentEntity / TargetEntity / FacilityEntity / HierarchicalOrgEntity）；
- 明确 `MetaObservation` 与 `MetaDerivedEstimate` 的边界；
- 统一 `MetaCommitment` 锁定级别：`FREE / RESOURCE_LOCKED / DAY_LOCKED / SEQUENCE_LOCKED / COMPLETELY_LOCKED`；
- 厘清 `MetaAction`（Agent 离散作业任务）vs `MetaEvent`（时空状态改变事实）的边界。

### 2. WM-FIX-2: 唯一化 L4/L5 规范世界状态 (`OperationalDecisionWorldState`)
- `world_model.state_snapshot.OperationalDecisionWorldState` 成为**唯一 Canonical WorldState**；
- 旧 `contracts/world_state.WorldState` 改造为 **DTO 兼容适配层**，从唯一规范导入所有数据类，杜绝双轨并行；
- 完整实例化：13 个 `AccountHierarchyEntity`，3 个 `ProductLineScopeEntity`，18 个 `SupplyNodeEntity`，**包含双时态 `BitemporalPeriod` 与 `SourceManifest` SHA-256 溯源**。

### 3. WM-FIX-3 + WM-FIX-4: 全要素状态转移引擎 (`StateTransitionEngine`)
- `transition_visit_status(base_state, visit_id, target_status, event_payload, approver_id, timestamp)`：
  - 执行完整生命周期守卫（PLANNED → COMMITTED 必须有 approver_id）；
  - IN_PROGRESS → COMPLETED 必须满足最短在店 10 min；
  - 非法跃迁阻断抛出异常；
- `rollout_reallocation_scenario()`：
  - 显式**校验 from_rep_id 当前是否拥有该门店**；
  - 同时演化双方 `ResourceEntity.assigned_store_codes`；
  - 重新计算双方的 `DerivedDepotEstimate` 几何质心；
  - 更新 `PolicyRegistry.ownership_map`；
  - 迁移转移生效期后的所有 `OperationalVisitLifecycleRecord`；
  - 基于 SHA-256 生成确定性分支哈希。

### 4. WM-FIX-5: 严密化 L6 规划器投影编译器 (`PlannerStateProjectionCompiler`)
- 真实动作合成时长（Key/A 级 55 min, NATURA 50 min, 默认 45 min）；
- 真实嵌入 `locked_commitments_mask: Dict[Tuple[int, int], List[int]]`；
- 严格坐标质量门禁（UNMAPPED 节点阻断并返回警告 `is_projection_clean = False`）；
- 返回包含 `unplannable_nodes_excluded` 的诊断字段。

---

## 二、全工作区真实测试回归最终总表

| 架构层级 | 模块/测试套件 | 测试数量 | 耗时 | 验证结果 |
| :--- | :--- | :--- | :--- | :--- |
| **领域与世界模型层 (Domain & World Model)** | `prism-ontology/tests/` | **146 个** | 10.72s | **✅ 100% PASS** |
| **决策编译层 (SVDE Core)** | `svde/tests/` | **37 个** | 1.17s | **✅ 100% PASS** |
| **基准与求解层 (SVDE Bench)** | `svde-bench/` | **121 个** | 8.50s | **✅ 100% PASS** |
| **全工作区总计** | | **304 个** | | **✅ 100% PASS** |

---

## 三、整改前后严格对比

| 关键架构问题 (审查指出) | 整改前 | 整改后 |
| :--- | :--- | :--- |
| L1 元模型 11 类不一致 | 11 类混乱 | 严格 8+3 类正交元类型 |
| L4/L5 双 WorldState 并行 | `WorldState` 与 `OperationalDecisionWorldState` 并存 | 唯一 Canonical + DTO 适配层 |
| L3 状态转移无守卫 | 仅枚举切换 | 全参数 + 审批/时长/GPS 守卫 |
| 反事实推演浅复制 | 仅改 `assigned_store_codes` | 多维同步 (Depot/Ownership/Policy/Lifecycle) |
| 哈希不稳定 | Python `hash()` | SHA-256 确定性摘要 |
| 规划投影使用默认 50 min | 硬编码 | 客户级别与品牌组合驱动的真实动作合成 |
| 锁定承诺未嵌入 | 缺失 | `locked_commitments_mask` 强制传递 |
