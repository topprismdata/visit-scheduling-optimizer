# 需要修改的规范清单 (Required Specification Updates)

**Document ID:** TOPPRISM-SPEC-UPDATES-v1.0  
**Date:** 2026-08-24  
**Status:** **MANDATORY SPECIFICATION UPDATE CHECKLIST**

---

## 一、必须修改的现有规范

### 1. `SVDE_WORLD_MODEL_FOUNDATIONAL_ARCHITECTURE_SPEC_v1.0.md`
- **修改 1**: 在文档开头增加 `TOPPRISM_ENTERPRISE_DECISION_WORLD_MODEL_PRODUCT_AND_COMMUNICATION_SPEC_v1_0.md` 上位约束的引用；
- **修改 2**: 明确说明 L0-L7 中 L5（情景仿真）和 L7（决策引擎）的设计仍在草案阶段；
- **修改 3**: 将 "SVDE = 整个系统" 的旧表述全部替换为 "TopPrism Prism Enterprise Decision Intelligence Product Family"。

### 2. `SVDE_WORLD_MODEL_METAMODEL_SPEC_v1.0.md`
- **修改 1**: 在导言明确 "此规范属于 TopPrism Prism Enterprise World Model 的 L1 通用元模型层，SVDE 仅是消费此底座的领域之一"；
- **修改 2**: 删除或澄清所有可能被误读为 "SVDE 独有" 的语句。

### 3. `SVDE_STATE_TRANSITION_ENGINE_SPEC_v1.0.md`
- **修改 1**: 在标题与导言明确 "本规范属于 TopPrism Prism Enterprise World Model 的 L3 状态转移引擎层"；
- **修改 2**: 强调守卫是从业务主管策略中提取，而非 SVDE 业务独有；
- **修改 3**: 删除任何将 SVDE 描述为整个系统的语句。

### 4. `SVDE_PLANNER_PROJECTION_CONTRACT_v1.0.md`
- **修改 1**: 明确 "L6 Planner Projection 是 World Model 向 Decision Engine 暴露的接口契约"；
- **修改 2**: 强调 `PlannerStateProjection` 是 **领域无关** 的纯数学载荷。

### 5. `SVDE_SALES_VISIT_DOMAIN_ONTOLOGY_SPEC_v2.0.md`
- **修改 1**: 在文档开头明确 "本规范是 TopPrism Prism Enterprise World Model 在 FMCG 销售拜访领域的 L2 领域特化"；
- **修改 2**: 强调业务政策（如 Key 级 REQUIRED）是领域特征，需通过 L3 状态转移引擎与 L7 决策引擎协同执行。

### 6. `SVDE_OPERATIONAL_DECISION_WORLD_MODEL_SPEC_v1.0.md`
- **修改 1**: 重新对照 World Model 子系统，明确 L5 与 L7 的边界；
- **修改 2**: 文档应明确本规范定义的是 L4 WorldState，L7 Decision Engine 属于另一份规范（待编写）。

---

## 二、必须新增的规范

| 新增规范文档 | 优先级 |
| :--- | :--- |
| `TOPPRISM_L7_ENTERPRISE_DECISION_ENGINE_SPEC_v1.0.md` | **P0** |
| `TOPPRISM_L5_SCENARIO_SIMULATION_ENGINE_SPEC_v1.0.md` | P1 |
| `TOPPRISM_MATURITY_MODEL_ASSESSMENT_v1.0.md` (五级成熟度评级模板) | P2 |

---

## 三、必须新增的代码层物理重构 (待业务方确认后启动)

| 物理重构项 | 优先级 |
| :--- | :--- |
| 将 `diagnostics/plan_auditor.py` 移至 `l7_decision_engine/audit/` | P0 |
| 将 `engine/decision_pipeline.py` 移至 `l7_decision_engine/pipeline/` | P0 |
| 降级 `engine/periodic_pvrp_solver.py` 至 `svde/domain_solver/` | P1 |
| 新增 `l5_scenario_engine/` 子包 | P1 |
| 新增 `l7_decision_engine/` 子包 | P0 |

---

## 四、报告口径整改

### 必须对所有未来报告落实：
1. 区分 5 级成熟度（设计 / 代码 / 测试 / 业务验证 / 生产能力）；
2. 严禁出现 "完成"、"生产级"、"已闭环" 等笼统宣称，除非有明确证据达到 5 级；
3. 必须明确标注 "World Model" 与 "Decision Engine" 的职责边界。
