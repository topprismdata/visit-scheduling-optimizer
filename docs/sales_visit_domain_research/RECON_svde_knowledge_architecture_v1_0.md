# SVDE Knowledge Architecture Reconciliation Report v1.0
## Phase 0.5 · 五输入包 × 既有治理资产 对账报告

> **文档标识**：`RECON-SVDE-KNOWLEDGE-ARCH-V1.0`  
> **阶段**：Phase 0.5（Understanding Gate 已过；本报告是 Knowledge Base 装配前置条件）  
> **目标**（按指令严格限定）：**不是扩充知识**——保证既有治理资产（A01–A06 / S-A / S-C / S-D 及其验证体系）能够**安全进入**新的 Knowledge Architecture。  
> **对账范围**：五包 26 文件 × 既有 17 资产 + validation/phase2 可执行套件。

---

## 目录
1. [五包内容盘点与结构判定](#1-五包内容盘点)
2. [五包 ↔ 既有资产逐项映射](#2-映射)
3. [四类知识分类：冻结/可迁移/待验证/历史参考](#3-四类知识分类)
4. [迁移风险登记](#4-迁移风险)
5. [Knowledge Base Assembly Plan](#5-assembly-plan)

---

# 1. 五包内容盘点

| 包 | 文件数 | 性质判定 |
|---|---|---|
| **Domain Contract Reference v1.0** | 8 | **治理规范层**——A01–A06 的"精炼引用版"（每份 ≤50 行 Agent 规则卡，非完整契约正文） |
| **Knowledge Base Agent Package v0.1** | 5 | **知识库结构规范**——Ontology/Decision-Model YAML（骨架级）+ 知识工程流程 + Agent 指令 |
| **Scenario Executable Reference v1.0** | 4 | **验证规范层**——14 节场景模板 + Scenario A 参考卡 + 失败分类规则 |
| **Evidence Knowledge Package v1.0** | 5 | **证据工程规范**——Registry schema/template + 抽取 prompt + 研究优先级（Tier 1/2/3） |
| **Research Source List v1.0** | 4 | **研究路线图**——三层主题目录 + 来源评审模板 |

**关键结构判定**：五包是**规范/模板/骨架**（how to organize），不是知识内容本身（what is known）。Ontology YAML 仅列 10 个 approved_concepts 名称，无 definition/not_this/relations 字段——**知识内容恰恰在既有资产里**。

# 2. 五包 ↔ 既有资产逐项映射

| 包内组件 | 既有对应物 | 对齐度 | 判定 |
|---|---|---|---|
| DC-A01 Domain Research Baseline | `01_A01_..._v6_1_1.md`（14 厂商 25 源） | 规则一致（外部资料≠Domain）；**包内是摘要，内容在既有 A01** | 内容以既有为准 |
| DC-A02 Business Evidence Baseline | `02_A02_..._v6_1_1.md`（三表分立） | 包内 "Source Fact / Expert Interpretation / Design Decision" 三分 ≈ 既有 "[PRODUCT FACT] vs [MODELING HYPOTHESIS]" | 既有更细（多了 EMPIRICAL） |
| **DC-A03 Domain Contract** | `03_A03_..._v1_0_1.md` | 包内仅含 Agent 规则+核心原则（"Requirement Fulfillment 是核心对象"）——**与 A03 v1.0.1 §2.9 注释逐字一致**（DCR-SA-001-R 设计原则已同步） | ✅ 无冲突 |
| DC-A04 External Reference Mapping | A02 三表 + A01 图谱式映射 | 包内规则（External→Evidence→Generic，禁 Product Object→Entity）= 既有纪律 | ✅ 一致 |
| DC-A05 Scenario Contract | S-A/S-C/S-D specs（16 项模板） | 包内 Required Elements（6 项）⊂ 既有 16 项模板 | 既有超集 |
| DC-A06 Validation Gate | Gate A1–A5（S-A）+ Gate C1–C5 + Gate D1–D5 | 包内 Gate 模型（A1–A5）与 S-A Gate **同名同义** | ✅ 同源 |
| **KB Ontology v0.1（10 concepts）** | A03 31 对象 + DVR Glossary 10 条 | **关键映射表见 §2.1** | 需逐条对齐 |
| **KB Decision Models v0.1（10 models）** | 散在 A05 架构 + specs（未显式建模） | **既有缺此层显式清单** → 可迁移缺口（见 §3） | 主要迁移工作 |
| Scenario Template（14 节） | S-A 16 项模板 | 14 ⊂ 16（多出 Business Context/Question/Actors 三节 ≈ 既有散布）；缺 Domain Coverage/Change Log | 模板合并不难 |
| Scenario A Reference | `S-A_..._v1_1_1.md` + 18/18 验证 | 包内是简化卡（无 occurrence 表/TA 测试）；**"VRP 只解决访问顺序"推理示例与 S-A §1 精神一致** | 既有是执行版 |
| Evidence Registry Schema | A01 Primary Source Registry（JSON 25 条） | 包内字段（id/title/author/year/type/claim/supports/confidence/review_status）**比既有多 claim/supports/confidence 三字段** | 既有需按 schema 扩展（可迁移） |
| Research Priority（3 Tier） | A01 四群组（A/B/C/D） | Tier1 业务 ≈ 群组A；Tier2 OR ≈ 群组D；Tier3 AI ≈ **新增维度**（既有未覆盖 Knowledge Graph/Agent Architecture 类研究） | 部分新增 |

## §2.1 Ontology 10 概念 ↔ A03 对象映射（核心对账）

| 包内概念 | A03 v1.0.1 对应 | 判定 |
|---|---|---|
| Customer | `VisitTarget` | ✅ 名称差（Customer→Target 更通用），语义同 |
| Territory | `territory_id` 字段 + 上游域声明 | ✅ |
| **Requirement** | `BusinessRequirement` + **核心原则同句** | ✅ 完全同源 |
| Resource | `SalesResource` | ✅ |
| Ownership | `OwnershipPolicy`（三轴之一） | ✅ 既有更细 |
| Visit | **四态**：VisitDemand/Occurrence/Candidate/PlannedVisit + ExecutionVisit | ⚠️ 包内单数 "Visit" **粗于冻结四态**——映射时必须展开，禁止回退 |
| Execution | `ExecutionHistory` | ✅ |
| Outcome | **无直接对应** | ⚠️ 唯一新概念（见 §4 风险 R4） |
| Policy | `VisitPolicy` | ✅ |
| Exception Handling Policy | `DeferralPolicy` + `exception_handling_policy_ref` | ✅ 即 DCR-SA-001-R，包内命名更通用（非 deferral 专属）——**与裁定一致** |

# 3. 四类知识分类

## 3.1 已冻结知识（Frozen — 直接作为 KB 权威层，零改动进入）

| 资产 | 状态 | 进入 KB 的角色 |
|---|---|---|
| A03 v1.0.1（31 对象 + Glossary） | FROZEN | **Ontology 权威层**（包内 10 概念展开自它） |
| A05 v1.0（四层参考架构） | FROZEN | Layer Boundary 规范 |
| DCR-SA-001-R（含 DOV 验证链） | APPROVED | Governance 知识（Change Request 范例） |
| Glossary 10 条（含 not_this） | FROZEN（DVR） | Ontology not_this 字段直接来源 |
| Visit 四态切分 | FROZEN | "Visit" 概念的强制展开规则 |

## 3.2 可迁移知识（Migratable — 结构转换后进入）

| 既有资产 | 迁移动作 | 目标结构 |
|---|---|---|
| A01 Primary Source Registry（25 条 JSON） | 扩展 claim/supports/confidence 三字段 | Evidence Registry（包 schema） |
| A02 三表（业务/工作流/技术） | 每行 → 1 条 Evidence 映射 | Evidence.supports 字段 |
| S-A/S-C/S-D 16 项 spec | 合并包模板 3 个新节（Business Context/Question/Actors）→ **19 项统一模板** | Scenario 层 |
| Gate A/C/D 判定 + 18/18+20/20+20/20 结果 | → Validation Record | scenario_mapping 字段 |
| CRR CR-COMPILER-C-001 | → Mathematical Pattern 层条目（Domain impact=None 标注） | 编译规则知识 |
| A04 八引擎事实卡 | → Backend Knowledge 层 | Backend 层 |

## 3.3 待验证知识（Candidate — 进队列，不直接 Approved）

| 知识项 | 来源 | 待验证内容 |
|---|---|---|
| **10 个 Decision Models**（包 YAML 清单） | KB Package v0.1 | 每个需：挂 Ontology 概念 + 挂 Scenario + 挂 Evidence（Step 4/5 缺一不可）；现有场景直接覆盖 7 个，Capacity Planning/Execution Monitoring/Replanning 三个**尚无对应场景验证**（E/B 待做） |
| **Outcome 概念** | 包 Ontology | 无 A03 对应、无 evidence、无场景——**三无，纯 Candidate** |
| Tier 3 AI Decision Engineering 研究方向 | Evidence 包 | 既有未研究；作为研究缺口登记，不阻塞装配 |
| 19 项统一 Scenario 模板本身 | 合并产物 | 需 S-E/S-B 使用后回检（模板过 A/C/D 三场景实measuring） |

## 3.4 历史参考知识（Reference-Only — 归档不进 KB 活层）

| 资产 | 处置 |
|---|---|
| `architecture_v5*`（4 版演进） | 归档：V4 失败模式 → 教训知识（Failure Pattern 层可选收录） |
| `sales_visit_decision_domain_knowledge_v1_0.md` | 归档：被 A01–A06 套件取代 |
| V5.4 组件审查结论（A06 表） | 归档：迁移时参考 KEEP/REMOVE 分类 |

# 4. 迁移风险登记

| ID | 风险 | 等级 | 缓解 |
|---|---|---|---|
| **R1 概念降维** | 包内 "Visit" 单数粗于冻结四态；装配时若按包内 10 概念直建，**四态切分被回退**——正是 DVR Glossary 防的坑 | 🔴 高 | 装配规则：包内概念仅为**索引名**，每个必须展开至 A03 精确对象；四态强制映射写入 Assembly Plan 步骤 2 |
| **R2 双权威源** | 包 DC-A03 与既有 A03 v1.0.1 并存；若 Agent 读包内精简版作权威，丢失 31 对象细节与 DCR 补丁 | 🔴 高 | 声明：**包 = 使用规则，既有 = 契约正文**；KB 的 ontology 层数据源唯一指向既有 A03 v1.0.1 |
| **R3 Decision Model 层真空** | 既有资产从未显式建过 "Decision Model" 层（散在架构图）；包要求 10 个——直接照抄会违反"无验证不入稳定库" | 🟡 中 | 10 个模型全部进 **Candidate 队列**；其中 7 个可由 A/C/D 结果追溯补验，3 个等 E/B |
| **R4 Outcome 新概念** | 包内唯一无对应概念；若顺手创建= 违反"无 Failure 不新增" | 🟡 中 | 维持 Candidate；登记触发条件（哪个 Scenario 失败会需要它） |
| **R5 模板合并漂移** | 16 项 vs 14 项模板合并时遗漏 Change Log/Domain Coverage 两个治理关键节 | 🟡 中 | 合并清单显式列出两节保留；19 项模板先在 S-E 试运行 |
| **R6 证据字段回填成本** | 25 条 Registry 补 claim/supports/confidence = 手工回填，可能引入推断 | 🟢 低 | 只填可从原文直接引述的 claim；无把握则 review_status=unverified |

# 5. Knowledge Base Assembly Plan

**目标重申**：安全迁移既有治理资产，不是扩充。

```
Phase A  权威层直载（零转换）
  A1  Ontology 层 ← A03 v1.0.1（31 对象 YAML 化，逐条含 definition/business_meaning/
      not_this/relations/evidence/decision_models/scenario_mapping/status 八字段）
      —— not_this ← DVR Glossary；evidence ← A01/A02 句柄；status=Frozen
  A2  Governance 层 ← DCR-SA-001-R + DOV + CRR + RMAP（作为治理范例知识）
  A3  Backend 层 ← A04 八引擎卡（事实+Build-vs-Reuse 结论）

Phase B  结构转换迁移
  B1  Evidence 层 ← A01 Registry 25 条按包 schema 扩展（三新字段，R6 缓解规则）
  B2  Scenario 层 ← A/C/D 三 spec+report 合并为 19 项统一模板实例（R5 规则），
      validation 结果写入 scenario_mapping
  B3  Layer Boundary ← A05 + 包 README 四层定义（互证一致后取并集表述）

Phase C  Candidate 队列（不 Approved）
  C1  Decision Models ×10 —— 7 个标 mapping-complete（可由 A/C/D 追溯），
      3 个标 awaiting-scenario（E/B）
  C2  Outcome 概念 —— awaiting-failure-evidence
  C3  Tier3 AI 研究方向 —— research-gap 登记

Phase D  验证关闸
  D1  映射完整性审计：包内 10 概念 100% 展开至 A03 对象（R1）
  D2  单一权威源审计：所有 Frozen 条目 evidence 指向链无断（R2）
  D3  纪律审计：Candidate 队列无一项直接 Approved
  → 通过后输出 SVDE_Knowledge_Base_v0.1（首个可运行知识库版本）
```

**装配期冻结承诺**：全过程不修改 A03 v1.0.1 / A05 / 任何 FROZEN 资产一字；发现矛盾 → 登记 Reconciliation Issue（非 DCR）→ 人工裁定。
