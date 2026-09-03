# Decision Memory Ontology & Governance Specification v1.0 — Phase 5.1-0
## 决策记忆本体与治理规范 · 从执行凭证到可复用企业知识 · 记忆晋升流水线

> **文档标识**：`P51-0-MEMORY-GOVERNANCE-SPEC-V1.0`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Phase 5.1-0 —— 决策记忆本体与治理设计（Decision Memory Ontology & Governance Design）  
> **核心命题**：**决策记忆不是日志库、不是向量数据库、不是历史方案的简单复制**。决策记忆是**带上下文的可复用决策知识（Contextualized Decision Knowledge）**。本规范形式化定义三级演进层级（Trace $\to$ Episode $\to$ Memory）、四类记忆资产、记忆晋升闸门（Memory Promotion Pipeline）与防退化治理纪律。

---

## 1. 三级记忆演化阶梯（The Three-Level Memory Hierarchy）

```
     ┌────────────────────────────────────────────────────────────────────────┐
     │ Level 1: Decision Trace (决策追踪凭证 · 单次计算事实)                   │
     │  • 记录单次决策如何产生：Intent → Contract → Model → Solution         │
     │  • 属于执行期硬证据（如 CH-TRACE-001, DD-TRACE-SEQUENCE-001）          │
     └───────────────────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼ [Outcome 评估与因果闭环]
     ┌────────────────────────────────────────────────────────────────────────┐
     │ Level 2: Decision Episode (决策片段 · 单次完整决策与反馈闭环)           │
     │  • 记录决策上下文 + 执行前方案 + 现实扰动 + 决策因果 + 实际 Outcome 反馈 │
     │  • 提炼局部决策经验（如：车辆突发故障时优先保留锁定订单）              │
     └───────────────────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼ [Memory Promotion Gate 晋升与泛化]
     ┌────────────────────────────────────────────────────────────────────────┐
     │ Level 3: Decision Memory (决策记忆 · 跨周期可复用企业知识资产)          │
     │  • 跨场景沉淀的上下文约束规则、假设生命周期与策略泛化模板              │
     │  • 反哺下一次 Decision Compilation，指导未来决策而非死板复制历史解      │
     └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 决策记忆四大核心资产（The Four Memory Asset Classes）

| 记忆资产类别 | 形式化模式 | 解决的核心企业认知问题 | 典型实例 |
|---|---|---|---|
| **1. Decision Episode Memory**<br>（决策片段记忆） | $\langle \text{Context}, \text{Intent}, \text{ContractSnapshot}, \text{Solution}, \text{Outcome}, \text{Rationale} \rangle$ | **全景因果回溯**：记录过去在何种特定上下文与约束下做出了什么决策，实际成效如何 | Phase 4.3 车辆故障时转派 ORD_03 并 100% 保障承诺时窗的完整因果片段 |
| **2. Constraint Evolution Memory**<br>（约束演化记忆） | $\langle \text{ConstraintID}, \text{InitialLevel}, \text{EvolutionTrigger}, \text{FinalLevel}, \text{BusinessReason} \rangle$ | **规则生命周期**：记录业务约束如何从软偏好升级为硬红线（或反之），避免规则僵化 | 配送时间窗从“软偏好”经多次客户投诉后晋升为 `TIME_WINDOW_LOCKED` 刚性不变量 |
| **3. Decision Outcome Memory**<br>（决策成效记忆） | $\langle \text{DecisionID}, \text{PredictedObjective}, \text{RealizedOutcome}, \text{VarianceDelta}, \text{CalibrationFeedback} \rangle$ | **预期与实际偏差学习**：校准未来目标函数与现实环境参数，防止盲目乐观 | 渠道布局预测旗舰店收益 960k，实际 820k $\to$ 记录环境偏差并微调下次商业潜能系数 |
| **4. Assumption Memory**<br>（假设生命周期记忆） | $\langle \text{AssumptionID}, \text{Statement}, \text{Status(ACTIVE/VALIDATED/INVALIDATED)}, \text{EvidenceRef} \rangle$ | **科学研究记忆**：严密记录哪些假设成立、哪些被证伪，防止企业重复试错 | A001–A005 假设状态机；路网接入仅属 Data Variation 的验证结论 |

---

## 3. 记忆晋升流水线与安全闸门（Memory Promotion Pipeline & Gates）

为了彻底解决 **Q2: 如何区隔“经验复用”与“错误复制”**，任何历史 Episode 必须通过严格的六阶段晋升流水线，严禁未经验证的执行方案直接污染全局记忆库：

```
Decision Trace ──► Outcome Evaluation ──► Episode Construction ──► Memory Validation (MDVL) ──► Memory Promotion Gate ──► Reusable Knowledge
```

### 3.1 记忆决策语义验证层（Memory Decision Validation Layer — MDVL）
- **门限 MP-G1 (Outcome Threshold Gate)**：实际商业效果（Realized Outcome）必须达到预期基准或产生明确正向因果（严禁劣质方案晋升）。
- **门限 MP-G2 (Invariant Compliance Gate)**：整个执行与反馈周期中，所有 HARD 不变量（如安全隔离、锁定承诺、财政红线）**零违规**。
- **门限 MP-G3 (Contextual Boundary Gate)**：必须显式提取生效的适用边界（Contextual Preconditions，如适用预算区间、适用商圈层级），禁止无边界的裸知识晋升。
- **门限 MP-G4 (Non-Repetition Gate)**：检查该经验是否与现有知识库矛盾；若属于假设证伪，必须触发 Assumption 状态机的 `INVALIDATED` 或 `SUPERSEDED` 流转。

---

## 4. 记忆反哺决策编译器机制（Memory-to-Compiler Feedback Loop）

决策记忆如何影响下一次 Decision Compilation？（**回答 Q3 & Q4**）：

```
                                  Decision Memory Layer
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
            Contract Calibration    Type System Evolution    DSVL Invariant Patch
            (修正预期收益/参数)      (将经验固化为强类型)      (新增高危情景不变量)
                     │                      │                      │
                     └──────────────────────┬──────────────────────┘
                                            ▼
                              Next Decision Compilation Pipeline
```

1. **反哺 Semantic Contract**：Outcome Memory 校准参数（如将历史实测通行时间回填入 `TravelModel`，将实测潜能回填入 `ChannelContract`）。
2. **反哺 Type System**：Constraint Evolution Memory 将反复验证的高频业务策略沉淀为新的 `TypedConstraint` 模板。
3. **反哺 DSVL**：将过去的重大事故或故障场景自动转化为新的 Invariant 检查规则（如将“某类型车辆易故障”转化为备用运力冗余规则）。

---

## 5. 治理纪律与防退化四铁律（Governance Discipline）

- **铁律 1: 上下文绑定铁律（No Context, No Memory）**：
  - 禁止存储脱离约束与环境的裸方案（如“CBD必须开旗舰店”为非法记忆；“当预算 $\ge 1500\text{k}$ 且处于 T1 商圈时开旗舰店”为合法记忆）。
- **铁律 2: 方案不可盲目复用铁律（Reuse Meaning, Not Exact Plan）**：
  - Memory 输出的是**决策指导意图（Decision Heuristic/Policy Constraint）**，而不是直接覆盖下游数学求解器的变量赋值。
- **铁律 3: 假设证伪可追溯铁律（Falsification Memory）**：
  - 证伪的假设与失败的案例同等具备最高知识价值，必须 100% 入库归档，禁止静默删除。
- **铁律 4: 记忆生命周期老化铁律（Memory Aging & Pruning）**：
  - 连续多个周期环境发生剧烈漂移（如城市商圈重新规划）导致适用前提失效的 Memory，必须标记为 `SUPERSEDED` 并降级。
