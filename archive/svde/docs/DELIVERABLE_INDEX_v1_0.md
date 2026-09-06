# TopPrism SVDE 销售拜访决策引擎 — 整体实施文档与交付物汇总

**实施技术规格书已成功落盘于指定路径：**  
📁 `/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/svde/docs/SVDE_WORLD_MODEL_ONTOLOGY_PLANNING_ENGINE_INTEGRATION_IMPLEMENTATION_SPEC_v1_0.md`

---

## 核心交付文档索引与架构全景

```
========================================================================================================
                                     TopPrism SVDE 核心技术文档体系
========================================================================================================
[1. 总体集成技术规格书 (Implementation Spec)]
  • svde/docs/SVDE_WORLD_MODEL_ONTOLOGY_PLANNING_ENGINE_INTEGRATION_IMPLEMENTATION_SPEC_v1_0.md
    - 定义世界模型 v2.0、语义编译器、运筹求解引擎与双重机器验证门禁的端到端集成技术规格

[2. 领域本体与世界模型演进 (Ontology Layer v2.0 DCR)]
  • svde/docs/SVDE_WORLD_MODEL_EVOLUTION_v2_0.md
    - AccountHierarchy / ProductLineScope / SupplyNodeLink / MerchandisingCompliance / InStoreAction

[3. 抽象数学建模规范 (Mathematical Layer v2.0)]
  • svde/docs/SVDE_ABSTRACT_STRICT_PERIODIC_MATH_SPEC_v2_0.md
    - 严格同周几周期性 VRP 模型（严格 7天/14天/28天 模式空间 P_i，单日 <= 6 家，崇川中心 Depot 闭环）

[4. 业务审计与真实排班参考方案 (Diagnostic & Schedule)]
  • svde/docs/RENJUN_CADENCE_COMPLIANCE_AUDIT_v2_0.md (仁军 6 月频次履约失控穿透与脱访暴露)
  • svde/docs/RENJUN_STRICT_PERIODIC_SCHEDULE_FINAL_v2_0.md (4 周 18 天 100% 严格同周几参考排班日历)
  • svde/docs/HISTORICAL_MODEL_COMPARISON_AUDIT_v2_0.md (四代模型演进与历史基线深度对比)

[5. 核心诊断与机器验证算子 (Engine Operators & Tests)]
  • svde/ontology/src/prism_ontology/diagnostics/cadence_auditor.py (全量客户底表履约审计算子)
  • svde/ontology/src/prism_ontology/diagnostics/schedule_verifier.py (排班结果机器验证引擎)
  • svde/ontology/tests/test_cadence_auditor.py (履约审计算子自动化测试套件)

[6. 阶段性综合证据总结报告 (Evidence Draft)]
  • svde/docs/SVDE_COMPREHENSIVE_DELIVERABLE_REPORT_v2_0.md (阶段性总结草案与证据库溯源)
========================================================================================================
```
