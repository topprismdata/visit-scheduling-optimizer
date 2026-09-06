# SVDE Knowledge Base — Assembly Phase A Report v1.0
## Phase A1–A5 执行报告（Ontology Authority / Governance / Backend Reference / Evidence Link / Decision Model Candidates）

> **文档标识**：`SVDE-KB-ASSEMBLY-PHASEA-V1.0`  
> **执行日期**：2026-08-22  
> **依据**：Phase 0.5 Review（APPROVED WITH CONDITIONS 五条件）+ RECON Assembly Plan  
> **执行纪律**：全程未修改任何 FROZEN 资产一字；未新增 Domain Concept；零数学。  
> **产出位置**：`knowledge_base/svde_v0_1/`（五层文件，版本号均在文件名）

---

## 一、五条件落实总表（Phase 0.5 Review → 执行结果）

| # | 条件 | 落实 | 载体 |
|---|---|---|---|
| 1 | 增加 provenance 字段 | ✅ 47/47 概念六子字段（origin_asset/source_version/migration_method/review_history/approved_date/change_reference）；4 条含 DCR-SA-001-R 完整链 | `ontology_authority_v0_1.yaml` |
| 2 | Frozen/Candidate/Reference 三态严格隔离 | ✅ Ontology 全 Frozen（1 Candidate 独立段）；Backend 全层降为 Reference（layer_status_convention 显式声明"solver 更替不触发知识变更"）；Decision Model 全 Candidate | 全部五层 |
| 3 | Backend 维持 Reference | ✅ 8 引擎+1 路网基础设施，每条含 known_limits/maturity_caveat；selection_authority 归 SolverStrategySelector+实验 | `backend_reference_v0_1.yaml` |
| 4 | Decision Model 不直接 Approved | ✅ 10/10 Candidate；7 个 mapping-complete（概念+证据+场景三挂接）仅是**分类标签**，转 Approved 须 E/B 后经 Gate 复审 | `decision_model_candidates_v0_1.yaml` |
| 5 | 不新增 Domain Concept | ✅ 净 47↔47（A03 对象数严格相等）；执行中**发现并移除 1 处自身迁移错误**（见 §四迁移审计） | `ontology_authority_v0_1.yaml` |

## 二、五层产出清单

| 层 | 文件（版本固化） | 规模 | 状态构成 |
|---|---|---|---|
| **A1 Ontology Authority** | `ontology_authority_v0_1.yaml` | 36 KB | 47 Frozen + 1 Candidate(Outcome) + 10 包概念强制展开表 |
| **A2 Governance** | `governance_layer_v0_1.yaml` | 5.0 KB | 5 治理案例（DCR-SA-001-R 完整链 / 冻结纪律 / Phase Gate / CRR 纪律 / 三场景验证记录） |
| **A3 Backend Reference** | `backend_reference_v0_1.yaml` | 4.5 KB | 8 引擎 + 1 路网 + Build-vs-Reuse 六门禁（全层 Reference 态） |
| **A4 Evidence Link** | `evidence_layer_v0_1.yaml` | 11 KB | 23 条显式 Evidence（含 claim/supports/confidence 回填）+ 1 条 R6 占位（12 源待回填） |
| **A5 Decision Model Candidates** | `decision_model_candidates_v0_1.yaml` | 5.0 KB | 10 Candidate：7 mapping-complete / 3 awaiting-scenario / **0 Approved** |

## 三、各层关键设计

### A1 Ontology（核心层）
- **权威源唯一**：47/47 origin_asset 指向 `03_A03_domain_ontology_v1_0_1.md`——包内精简卡零引用（R2 缓解落地）
- **verbatim 迁移**：47/47 migration_method=verbatim；八字段（definition/business_meaning/not_this/relations/evidence/decision_models/scenario_mapping/status）+ provenance 全齐
- **包概念强制展开**（R1 缓解）：10 包内概念→精确对象表；Visit→五对象（四态+ExecutionVisit）零歧义
- **provenance 可回答"为什么存在"**：如 DeferralPolicy 完整链 `A03 v1.0.1 ← DCR-SA-001-R(MRE-1 证伪 a/b→裁定 c) ← KB migration ← Frozen`
- **not_this 全量回填**：DVR Glossary 10 条 + 各概念排他定义（如 FulfillmentClass 非 RequirementStrength）

### A2 Governance（治理范例知识）
- **KB-GOV-001 DCR-SA-001-R 全案**：trigger（PROOF-E2 四通道穷举）/ decision_path（001→INVESTIGATION→MRE-1→c 裁定→sign-off）/ naming_ruling（exception_handling 非 deferral 专属）/ conflict_resolution_ruling（Scenario 级配置不写死）/ audit_requirement（四段链）
- **KB-GOV-002 冻结纪律**：含三无效理由 + OBS≠DCR 判据 + 失败二分类（Domain vs Compiler）+ 8 次首跑失败全归因套件的先例
- **KB-GOV-003 Phase Gate**：P0–P6 全状态 + 三铁律
- **KB-GOV-004 CRR**：CR-COMPILER-C-001 登记（Domain impact=None）
- **KB-GOV-005 验证记录**：三场景 58 测试 / 0 DCR 违规 / 1 合规 DCR / 1 编译规则

### A3 Backend Reference（降级层）
- **layer_status_convention** 显式：Backend 能力随版本变化，不作为稳定业务知识；随 A04 复审（2026-11-22）同步
- **known_limits 保留**：MathOpt 缺 interval 原语（#5144）/ PyVRP PVRP open（#441）/ VRPSolverEasy R&D 原型 / Timefold Python 归档
- **Build-vs-Reuse 六门禁 + TopPrism 自研清单**（含 Pricing 的 CONDITIONAL 定位）

### A4 Evidence（证据链层）
- **schema 对齐包规范**：每条含 metadata + claim + supports(concepts/decision_models) + confidence + review_status
- **fact/inference 铁律内置**：A02 的 [PRODUCT FACT] vs [MODELING HYPOTHESIS] 区分写入 convention
- **23 条显式 + 1 条 R6 占位**：厂商 16 + 学术 3 + 内部实证 1 + 场景证明 4（PROOF-E1/DOV-MRE1/D-FOURCONCEPT/C-TIMEWINDOW）——场景执行产物作为 evidence 类型进入（Phase 0.5 建议 2 的对称落实：Decision 也由 Evidence 支撑）
- **R6 规则执行**：仅填可从原文直接引述的 claim；12 源无把握者统一占位标 unverified

### A5 Decision Model Candidates
- **三挂接齐备才可 Approved**（registry_convention 显式）
- **7 mapping-complete**：DM-001–007（Coverage/Prioritization/ReqGen/Alloc/Assignment/VisitPlan/Exception）——每条列出 ontology_concepts + evidence + scenario_validation 三链
- **3 awaiting-scenario**：DM-008 Execution Monitoring（等 E/B）、DM-009 Capacity Planning（TA-CAP 仅战术级，战略级未验证——**已标注可能降级合并入 DM-004**）、DM-010 Replanning（等 E+B 核心）
- **0 Approved**——全部保持 Candidate

## 四、迁移审计记录

### 4.1 执行期发现并纠正的迁移错误（1 起）
| 发现 | 处置 |
|---|---|
| 首版 Ontology 误含 `VisitOverheadCost`（v6.1 前旧名，A03 v1.0.1 中零出现——已被 v6.1.1 拆分为 RouteMetrics+ObservedStopTime 取代） | **当场移除**；净结果回到 47↔47 严格相等。属我迁移时带入历史词汇，非 Domain 缺口；审计链保留于此 |

### 4.2 全量审计通过项
```
A03 47 对象 ↔ KB 47 Frozen     全覆盖·零缺失·零多出     ✅
权威源唯一 47/47                origin→03_A03_v1_0_1     ✅
verbatim 47/47                                          ✅
Candidate 隔离                  Outcome 唯一·三无        ✅
DCR 溯源 4 条                   BR/DP/RequirementRegistry/Scenario ✅
Visit 四态展开                  package_index_expansion  ✅
三态隔离                        Frozen/Candidate/Reference ✅
Decision Model 0 Approved       10 Candidate             ✅
FROZEN 资产零修改               A03/A05/DCR 等一字未动    ✅
```

## 五、遗留项与下一步

| 项 | 状态 | 时机 |
|---|---|---|
| Evidence 12 源 claim 回填（R6 占位） | 待做（不阻塞） | 按需逐条，仅填可直引者 |
| DM-008/009/010 场景验证 | awaiting Scenario E/B | Phase 2 续 |
| 7 个 mapping-complete 转 Approved | 冻结中 | E/B 过 + Phase 2 Gate 复审 |
| Outcome 概念 | Candidate 三无 | 需 Failure Evidence |
| Scenario 层（A/C/D spec→19 项统一模板实例） | RECON Phase B 范围 | 下一装配批次 |

**Phase A 完成判定：五条件全落实 · 五层全产出 · 审计全过 · 纪律零违例。**
SVDE_Knowledge_Base_v0.1 骨架已就绪（Ontology 权威层 + Governance + Backend Reference + Evidence + DM Candidates），可进入 Phase B（Scenario 层迁移）或按指令优先推进 Scenario E 验证。
