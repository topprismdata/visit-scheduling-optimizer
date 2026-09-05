# SVDE-Bench Sprint 3D — Memory Evaluator Task 入册报告 v1.0
## 记忆治理评估器任务书入册 · 评价智能第四维度 · 四维评价体系闭环 · 治理层登记

> **文档标识**：`SVDE-BENCH-SPRINT-3D-TASK-V1.0`  
> **执行日期**：2026-08-22  
> **入册对象**：`SVDE-Bench Sprint 3D — Memory Evaluator Implementation Task v1.0`  
> **核心命题**：**实现 SVDE-Bench 第四类核心评价器：`MemoryEvaluator`（记忆治理评估器），冻结 `MemoryEvaluationResult` 模型，回答 SVDE-Bench 最后一个核心问题——“一个决策经验是否值得被未来系统长期继承？”**。  
> **核心架构原则**：① 纯评价不执行（Promotion 是评价结论而非直接写库）✅ ② 自动化实现 `MDVL MP-G1..G5` 五大门限规则与虚假记忆检测（False Memory Detection）✅ ③ 坚决杜绝 Vector DB、Embedding、Search/Retrieval 算法混入 ✅  
> **治理层与证据更新**：`EV-INTAKE-012` 证据入册，治理层记录 `KB-GOV-042`，路线图标记 Sprint 3D 实施启动。

---

## 1. 任务规范核心要素逐项裁定与映射表

| # | 任务书核心要求 | SVDE-Bench 体系对齐与实施方案 | 裁定结论 |
|---|---|---|---|
| **1** | **统一结果继承模型：`MemoryEvaluationResult`**<br>继承 `BaseEvaluationResult`，扩展 `promotion_status`, `lifecycle_validation`, `evidence_sufficiency`, `context_boundary_check`, `contradiction_check`, `false_memory_probability` | 位于 `svdebench.evaluator.models`，使 Semantic / Feasibility / Runtime / Memory 4 大结果模型全部归一 | **架构标准化** |
| **2** | **评价器定位：Memory Evaluator**<br>评价决策经验的证据充分性、上下文边界完整性、生命周期合法性与防错误泛化 | 对应 SVDE 架构核心：`Memory Governance Layer` 与 `MDVL` 自动化判定 | **确立为第四核心评价器** |
| **3** | **五大核心记忆评估规则（Rules 1–5）**：<br>- Rule 1: Evidence Sufficiency（必含 Trace + Case + Outcome）<br>- Rule 2: Context Boundary Validation（No Context, No Memory）<br>- Rule 3: Lifecycle Validation（Candidate/Validated/Promoted 门限）<br>- Rule 4: Contradiction Detection（历史经验冲突检测）<br>- Rule 5: False Memory Detection（过度泛化/无 Outcome 阻断） | 纯确定性逻辑，严格杜绝无边界 RAG 或黑盒打分 | **确定性算法规则实现** |
| **4** | **MDVL MP-G1..G5 自动化门限实现**：<br>- MP-G1 Evidence Gate / MP-G2 Context Gate / MP-G3 Outcome Gate / MP-G4 Contradiction Gate / MP-G5 Promotion Gate | 自动化扫描并输出 `PROMOTED` / `VALIDATED` / `REJECTED` | **门限规则引擎落地** |
| **5** | **Golden Case 001 记忆判定实证**：<br>- Valid Memory (上下文明确 + Trace + Outcome): 判定 `PROMOTED`<br>- False Memory (过度泛化为“所有故障优先 VIP”): 判定 `REJECTED` | 确立识别“劣质/过度泛化经验”的能力 | **Golden Case 严格对账** |
| **6** | **四大架构门限（Architecture Gates 1–4）**：<br>1. 仅评价不生成 / 2. 零 Retrieval 访问 / 3. 不改动内部生命周期 / 4. Promotion 仅为评价结论 | 100% 保持独立性 | **自动化测试验证** |

---

## 2. 治理层与证据库更新

### 2.1 `EV-INTAKE-012` 证据入册
- **来源**：`SVDE-Bench Sprint 3D — Memory Evaluator Implementation Task v1.0`
- **评级**：`Level-A (官方 Sprint 3D 执行任务书)`
- **支持面**：支持 `MemoryEvaluationResult` 模型、`MemoryEvaluator` 架构、MDVL MP-G1..G5 门限与虚假记忆阻断。

### 2.2 治理层记录 `KB-GOV-042`
- 正式登记 `SVDE-Bench Sprint 3D Memory Evaluator Acceptance`。
- 确认进入 **Sprint 3D（Memory Evaluator Implementation）** 执行。

---

## 3. 下一步执行指引

```
Sprint 3C: Runtime Evaluator Implementation ✅ (DoD 达成)
           │
           ▼
Sprint 3D: Memory Evaluator Implementation ◀ 立即执行
  • 更新 svdebench/evaluator/models.py (新增 MemoryEvaluationResult)
  • 编写 svdebench/evaluator/memory.py (实现 MemoryEvaluator, MP-G1..G5 门限, 虚假记忆检测)
  • 更新 svdebench/evaluator/__init__.py 导出四大评估器完整套件
  • 编写 tests/test_memory_evaluator.py (包含 5 组全覆盖单元测试)
  • 执行 pytest 全量自检与架构门禁复核
```
