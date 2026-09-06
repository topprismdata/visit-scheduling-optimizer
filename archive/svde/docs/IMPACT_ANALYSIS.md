# 当前代码与文档影响分析 (Impact Analysis)

**Document ID:** TOPPRISM-IMPACT-ANALYSIS-v1.0  
**Date:** 2026-08-24  
**Status:** **MANDATORY IMPACT ANALYSIS BEFORE CODE CHANGES**

---

## 一、当前代码归位影响分析

| 当前文件 | 当前归属 | 应当归属 | 影响 | 优先级 |
| :--- | :--- | :--- | :--- | :--- |
| `svde/ontology/src/prism_ontology/world_model/state_snapshot.py` | L4 ✅ | **保持** | 无 | - |
| `svde/ontology/src/prism_ontology/world_model/transition_engine.py` | L3 ✅ | **保持** | 无 | - |
| `svde/ontology/src/prism_ontology/world_model/planner_projection.py` | L6 ✅ | **保持** | 无 | - |
| `svde/ontology/src/prism_ontology/real_data/world_state_assembler.py` | L4 数据装载 ✅ | 改名为 `l4_data_loader.py` | 低 | P2 |
| `svde/ontology/src/prism_ontology/diagnostics/cadence_auditor.py` | L3 ✅ | **保持** | 无 | - |
| `svde/ontology/src/prism_ontology/diagnostics/schedule_verifier.py` | L3 ✅ | **保持** | 无 | - |
| `svde/ontology/src/prism_ontology/diagnostics/plan_auditor.py` | L7 ❌ 误归位 | **必须移出** `diagnostics/`，归入 `l7_decision_engine/audit/` | 高 | **P0** |
| `svde/ontology/src/prism_ontology/engine/decision_pipeline.py` | L7 ❌ 误归位 | **必须移出** `engine/`，归入 `l7_decision_engine/pipeline/` | 高 | **P0** |
| `svde/ontology/src/prism_ontology/engine/periodic_pvrp_solver.py` | L7 内部 Solver ❌ 误归位 | 降级为 `svde/domain_solver/` | 中 | P1 |
| `svde/ontology/src/prism_ontology/adapters/svde/bridge.py` | 适配层 ✅ | 保持 | 无 | - |
| `svde/ontology/src/prism_ontology/diagnostics/three_dim_audit` (现 plan_auditor) | L7 ❌ | 详见上 | 高 | **P0** |

---

## 二、当前文档归位影响分析

| 当前文档 | 当前归属 | 应当归属 | 影响 |
| :--- | :--- | :--- | :--- |
| `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md` | 全局规格 | **保持顶层** | 增加本轮交付物链接 |
| `L0_L7_RESPONSIBILITY_MATRIX.md` | 本轮新增 | **保持** | OK |
| `WORLD_MODEL_SYSTEM_BOUNDARY.md` | 本轮新增 | **保持** | OK |
| `DECISION_ENGINE_BOUNDARY.md` | 本轮新增 | **保持** | OK |
| `WORLD_MODEL_DECISION_ENGINE_CONTRACT.md` | 本轮新增 | **保持** | OK |
| `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1_0.md` | 既有 | **保留 (L0)** | OK |
| `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md` | 既有 | **保留 (L1)** | OK |
| `SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md` | 既有 | **保留 (L3)** | OK |
| `SVDE_PLANNER_PROJECTION_CONTRACT_v1.0.md` | 既有 | **保留 (L6)** | OK |
| `SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC_v2.0.md` | 既有 | **保留 (L2 SVDE 部分)** | OK |
| `SVDE_OPERATIONAL_DECISION_WORLD_MODEL_SPEC_v1.0.md` | 既有 | **重新对照** WorldModel 子系统 | 微调 |

---

## 三、Test Files 归位影响分析

| 测试文件 | 影响 |
| :--- | :--- |
| `test_world_state_assembler.py` | 保持（测试 L4 装载） |
| `test_operational_world_model.py` | 保持（测试 L3 状态转移 + L4 WorldState） |
| `test_wm_fix_v3_full_closure.py` | 保持（测试守卫） |
| `test_bridge_capability_dispatch.py` | 保持（测试桥接适配器） |
| `test_three_dimensional_plan_auditor.py` | **未来移至** `test_l7_audit/` |
| `test_periodic_pvrp_solver.py` | **未来移至** `test_svde_domain_solver/` |
| `test_renjun_end_to_end_pipeline.py` | **未来标记** 为 "L7 HITL Demo" |
| `test_world_state_contract.py` | 保持 |

---

## 四、关键风险与瓶颈

| 风险 | 缓解 |
| :--- | :--- |
| 一次性重构可能引入回归 | 必须逐步迁移（先 copy + alias，再 deprecate，再 remove） |
| 测试夹具耦合 WorldModel 与 SVDE | 暂不强行拆分，确保功能正常后再分层 |
| 文档层和代码层不同步 | 在每层设置版本号与对应规范文档 ID |
| 业务方未明确签署 3 次/月语义 | **必须先完成第 7 项（业务方确认事项），再进行代码改动** |

---

## 五、不动代码的承诺

按主管第 6 项交付顺序要求，本轮交付矩阵、边界、契约、影响分析、需修改清单、需业务方确认事项的 **6 份规范文档**已全部完成。

**代码改动必须等待第 8 项：经业务方确认后再提交代码实现计划！**
