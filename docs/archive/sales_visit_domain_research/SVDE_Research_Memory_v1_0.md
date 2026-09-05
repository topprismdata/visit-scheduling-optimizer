# SVDE Research Memory & Frozen Assumption Snapshot v1.0
## 科学研究记忆沉淀 · 假设生命周期状态机 · 失败分类学库

> **文档标识**：`SVDE-RESEARCH-MEMORY-V1.0`  
> **冻结日期**：2026-08-22  
> **性质**：不可变研究档案（Immutable Research Record）——杜绝“单次成功后无边界外推”，固化可证伪的假设状态与失败知识。

---

## 1. 假设生命周期状态表（The Five Frozen Assumptions）

状态机流转规则：`ACTIVE`（冻结中） $\to$ `VALIDATED`（实证通过） / `INVALIDATED`（实证证伪） / `SUPERSEDED`（被更优假设替代）。

| 假设 ID | 核心陈述 | 适用范围 | 判定状态 | 实证依据与测试工件 | 失效条件（何时必须重新验证） |
|---|---|---|---|---|---|
| **A001** | 行程表达可由 KBC-05（VRPSolverEasy exact BPC）仲裁，区隔 Data 与 Semantic 变异 | Phase 3.3 | **VALIDATED** ✅ | `Phase 3.3-⑤`：成功识别绕行与非对称拓扑为 Data Variation（成本偏差 $<1.5\%$，锁 100% 保持） | KBC-05 无法求解或外部路网出现结构性阻断（Unavailable Path）导致日容量溢出 |
| **A002** | Constraint Type System 十类约束枚举（C01–C10）覆盖当前全部业务约束 | Phase 3.3 | **VALIDATED** ✅ | `Phase 3.3-②`：GT-Small 10 客户全部约束 100% 映射入 C01–C10，无第 11 类缺口 | 出现新的业务语义（如多资源协同组队、实时抢单），必须经 DCR 评定是新类型还是现有组合 |
| **A003** | 字典序分层标量化求解在 GT-Small 规模可稳定收敛至各层全局最优 | Phase 3.3 | **VALIDATED** ✅ | `Phase 3.3-④`：MathOpt+HiGHS 求得 status=OPTIMAL，bound=36006340.0，gap=0 | 出现多目标权重尺度交叠（Scale Interleaving），导致低层目标反噬高层目标 |
| **A004** | 合成曼哈顿行程与真实路网行程在决策语义层等价（满足三角不等式时） | Phase 3.3 | **VALIDATED** ✅ | `Phase 3.3-⑤`：KBC-05 真实绕行系数介入后，$L1/L2/L3$ 结构 100% 免疫 | 引入动态拥堵时变路网（Time-dependent travel），导致时窗穿越或可行性翻转 |
| **A005** | 代表解策略配合共享 refine 收口的 $L4/L5$ 容差带在 GT-Small 尺度保持收敛 | Phase 3.3 | **VALIDATED** ✅ | `Phase 3.3-⑤`：四方代价偏差 $\Delta \le 40\text{min}$，远低于 120min 容差上限 | 规模扩展至 GT-Medium/Real 时，四方代表解的日组合差异过大导致行程偏离超容差带 |

---

## 2. 失败分类学案例沉淀库（The Failure Memory Dossier）

| 缺陷案例 | 现象 | 根因分类 | 架构级启示与防护机制 |
|---|---|---|---|
| **tc006 容量误判** | 容量上限（480min）被频次可达性检查器判定为“可用日 20 < 频次 480”报错 | **Class C: Checker Scope Error** | 验证器本身必须具有严格的语义类型边界。`tc006` 仅允许作用于 `Equality / Cardinality` 类别。 |
| **C03 实例重复误判** | B 类客户 4 个 C03（价值最大化）实例被断言判定为“非唯一”报错 | **Class C: Identity Granularity Error** | 明确 **Type Identity ≠ Instance Identity**。类型定义唯一，业务实例多重，禁止在实例级进行不合理的集合去重。 |
| **DSVL-T002 断链** | `SEQUENCE_LOCKED` 在词表比对中因大小写问题未能匹配 `Lock` 报错 | **Class C: Vocabulary Mapping Error** | 语义验证层必须建立大小写免疫且基于受控词表（Controlled Vocabulary）的双向追溯比对器。 |
| **AddExactlyOne 误用** | EXACT(4) 频次被错误翻译为 `AddExactlyOne` 导致模型假不可行（Phase 3.2） | **Class C: Semantic Type Misalignment** | 催生 **Constraint Type System**：约束生成必须由强类型卡片驱动（Cardinality op: `==` 且 `value==1` 才允许绑定 `ExactlyOne`）。 |
| **min_gap 错误软化** | 最小间隔在容量短缺 Case 中被错误放入目标罚项（Phase 3.2） | **Class C: Semantic Priority Inversion** | 催生 **Constraint Ontology**：约束分为 `HARD / SOFT_PREFERENCE / OBJECTIVE_PENALTY`，`relaxable: false` 属性禁止被任何下游优化器修改。 |

---

## 3. 全局证据链路全景图（End-to-End Evidence Trace Matrix）

```
[Level-A/B 商业专著 & 论文] 
      │ (BE-001..BE-026, Zoltners, Sethi, Rothenbächer)
      ▼
[Phase 0–1: 领域契约与治理] ─── (A03 v1.0.1 47 Frozen 概念, 零破坏性 DCR)
      │
      ▼
[Phase 2: 场景级业务验证] ───── (S-A, S-C, S-D, S-E, S-B 五场景, 88 测试全过)
      │
      ▼
[Phase 3.0–3.1: 编译映射规范] ─ (P3.1 符号字典, S-A §2.5 五级字典序规范目标)
      │
      ▼
[Phase 3.2: 微型语义等价] ───── (GT-Micro 4/4 Case 四方严格等价, 命题 A 确立)
      │
      ▼
[Phase 3.3: 决策编译器定型] ─── (GT-Small 规模扩展 + MathOpt + KBC-05 仲裁, AC-1..4 全过)
      │
      ▼
[SVDE Architecture v1.0 架构成立] ── 编译器前端 (Contract/Type/DSVL) + 后端 (MathOpt/CP-SAT/KBC-05) 闭环
```
