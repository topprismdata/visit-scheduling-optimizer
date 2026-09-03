# SVDE Knowledge Graph Integrity Review v0.1
## Phase 3 前置 · 全库语义关联网络审计（程序化建图——非重建，只审计）

> **文档标识**：`KG-INTEGRITY-REVIEW-V1.0`  
> **执行日期**：2026-08-22  
> **方法**：脚本从 9 个 Registry 程序化抽节点/边（零手工计数）；EV 内联 supports 格式二次修正解析  
> **审计动因**（评审指令）：表结构检查 ≠ 图检查——"每个节点单独看都正确，但节点之间的关系可能错误"；Phase 3 一旦开始，错误的 Decision-Pattern-Backend 链会被放大为错误数学模型  
> **执行顺序调整确认**：Knowledge Expansion ✅ → **本审计 ◀** → Contract（已冻结 v0.1，先于此审计完成但内容经本审计回验无冲突）→ Phase 3（暂停中——P3.1 映射未落盘）

---

## 1. Node Statistics（程序化统计）

| 节点类型 | 数量 | 构成 |
|---|---|---|
| Evidence | **52** | EV ×26（evidence_layer，含 1 占位）+ BE ×26（business_knowledge 17 + book_batch_A1 9） |
| Concept | **51** | KB-ONT Frozen ×47 + KB-CAND-001 Outcome + CC-01/02/03 |
| Decision | **21** | DM ×10（001-008 活跃 + 009/010 merged 历史）+ BDC ×8 + NDC ×3 |
| Pattern | **9** | MP-01..09 |
| Backend | **17** | KBC ×8（能力卡）+ KB-BE ×9（v0_1 事实层，含 KB-BE-010 路网基础设施） |
| Scenario | **5** | S-A/C/D/E/B |

## 2. Edge Statistics

| 关系 | 数量 | 覆盖率 |
|---|---|---|
| Evidence → Concept（id 锚定） | 30 | — |
| Evidence → Decision | 82（BE→D 67 + EV→D 15） | — |
| Concept → Decision（CC/CAND 路由） | 4/4 | **100%**（CC-01→BDC-05 · CC-02→NDC-01 · CC-03→NDC-03 · KB-CAND-001→BDC-02 经 BE-007） |
| **Evidence 去向覆盖** | 51/52 | **98.1%**（唯一例外=EV-PLACEHOLDER，见 §3） |
| Decision → Pattern allowed | 20 条边 / 11 契约 | 8/11 决策有 allowed；3 空=**sanctioned**（BDC-03 generation / BDC-07 policy / BDC-08 monitoring——nature 门控） |
| Decision → Pattern forbidden | 7 条边 | 覆盖全部禁项场景（含 NDC-01 禁 MP-05） |
| Pattern → Backend | 20 条 KBC→P | **9/9 Pattern 全有承载面；uncovered=[]** |
| Scenario → Decision (DM) | 23 条 S→DM | **DM-001..008 8/8 全有场景**（closure 复核通过） |
| Backend → Pattern/Decision（反向） | **0** | Guard 1 图上无违例 |

## 3. Orphan Detection

### 孤立 Evidence（1 起——sanctioned）
| 节点 | 状态 | 处置 |
|---|---|---|
| `EV-PLACEHOLDER-REMAINDER` | supports={} · claim=null | **已知 R6 占位**（12 源待回填）——Level-D 定级已标注"不可支撑 DM 晋升"；非断链，属登记在案的未完成回填 |

其余核查：`EV-A03-GENERIC`（concepts=[全部 47 Frozen]——伞形证据，全对象引用）；`EV-INTAKE-001`（supports→**Governance 面**——契约 Part 4 支持面枚举含 Governance，合法）；`BE-014`（concept→ParameterRegistry 按名引用 + decision 显式 null-by-design 证据型知识——挂 BDC-08 calibration_note，非断链）。

### 孤立 Concept：0
47 Frozen 概念经 Phase B2 closure 100% 挂 DM；KB-CAND-001 + CC-01/02/03 全部路由至 Decision。

### 孤立 Decision：0（但 3 个 validation_pending——诚实标注，不假装已验证）
| 节点 | 状态 | 依据 |
|---|---|---|
| NDC-01 TerritoryAlignment | **validation_pending** | G-4/P6 战略层锁定 |
| NDC-02 SalesCapacity | **validation_pending** | G-4 同上 |
| NDC-03 WorkloadBalance | **validation_pending** | G-5 公平口径未定 |
| CC-01/02/03 | scenario_gap 保留 | G-3/G-4/G-5 |

图上显式标记 `validation_pending`（契约 phase_gate 字段）——无任何 Candidate 伪装 Validated。

### 孤立 Pattern：0
MP-01..09 全部 decision_types 非空（BDC-03/08 的"空 Pattern"是 Decision 侧无 Pattern，非 Pattern 侧无 Decision）。

### 孤立 Backend：1 项注记
`KB-BE-010`（OSRM/高德）无 Pattern 映射——**路网基础设施（travel model / RoutingOracle 支撑件），非求解器**；属 MP-05 行程腿的下层依赖，不参与 Pattern→Backend 语义映射。注记 accepted。

## 4. Dangerous Shortcut Detection

| 捷径类型 | 扫描结果 |
|---|---|
| Evidence → Pattern（绕过 Decision） | MP 卡 evidence 字段引用业务证据 4 处：BE-013/019/023（MP-09）、BE-024（MP-08）——**全部有 Decision 中介上游**（NDC-03/NDC-02/BDC-06+07，均在其 supporting_evidence 中）→ **零未中介捷径**。数学证据（Hillier/DOI）为 Step 2 契约第 2 阶段 sanctioned 通道（验证 Pattern 存在性，非决定业务） |
| Evidence → Backend | **0** |
| Backend → Decision | **0**（正则全扫 KBC 文件无 KBC→BDC/NDC 语义边；KBC-05 "GT-Micro 第四方仲裁"为 Phase 3 验证基础设施注记，非知识边） |
| Backend → Pattern 创建 | **0**（`new_pattern_created: 0` + upstream_ref 全部指回 v0_1 事实层） |

## 5. Semantic Contradiction Detection

| 检查 | 结果 |
|---|---|
| MP.decision_types ∈ 契约 forbidden？ | **0 冲突**（逐 Pattern × 逐 Decision 交叉——如 MP-05 decision_types 仅 [BDC-06]，与 BDC-01/04/NDC-01 禁项无交集） |
| 同一 Decision 既 allowed 又 forbidden 同一 MP？ | **0** |
| "Territory ≠ VRP" 负知识 vs 图上 Territory→VRP 边？ | **不存在**——NDC-01 反查仅 [MP-01/06/03]；MP-05 not_suitable_for 显式含 Territory；三处一致（Pattern 卡/契约/反查表） |
| 负知识条目总量 | **28**（MP not_suitable_for ×9 + 契约 forbidden ×11 + KBC not_suitable_for ×8）——全部可检索 |
| 信息性不对称（非矛盾） | 契约 allowed ⊇ Registry decision_types（如 BDC-01 允 MP-06 但 MP-06 卡未回标 BDC-01）——方向安全（允而未用 ≠ 禁而用之）；**注记：Phase 3.1 映射时以契约为准，MP 卡 decision_types 字段可在 Gate 复审时补齐回标** |

## 6. 五类关系审计结论（对照评审指令）

| # | 评审要求 | 图上事实 |
|---|---|---|
| 1 | Evidence→Concept→Decision 无断链 | 51/52 Evidence 有去向（1 sanctioned 占位）；Concept→Decision 4/4；Decision→Evidence 反向 11/11（BDC+NDC supporting_evidence 全非空） |
| 2 | Decision→Pattern 有 allowed/forbidden/边界 | 11/11 有契约条目；forbidden 执法图上零违例；**反向污染 0** |
| 3 | Pattern→Backend 单向 | KBC→P 20 边、upstream 8 边全部指向上游；反向 0 |
| 4 | Scenario→Decision 覆盖 | DM 8/8 已验；NDC 3/3 显式 `validation_pending`（不伪装） |
| 5 | 负知识存在 | 28 条 "NOT" 边可检索；Territory 反例三处一致 |

## 7. 总裁定

```
PASS —— 知识图谱语义网络完整，可进入 Phase 3。
0 语义矛盾 · 0 反向污染 · 0 未中介捷径 · 0 伪装验证
1 sanctioned 占位（EV-PLACEHOLDER/R6 回填中）
1 信息性注记（契约 allowed ⊇ MP 回标——Phase 3.1 以契约为准）
3 validation_pending 诚实标注（NDC ×3，门控出）
```

**评审顺序调整落实**：本审计完成后 Phase 3.1 方可启动（Contract v0.1 已冻结且经本审计回验无冲突——审计非回溯豁免，而是双向验证）。
