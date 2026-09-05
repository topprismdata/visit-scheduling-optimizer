# Decision Memory Schema & Promotion Protocol v1.0 — Phase 5.1-0.5
## 决策记忆对象模式 · 记忆生命周期状态机 · MDVL 晋升协议 · 语义层消费协议

> **文档标识**：`P51-05-MEMORY-SCHEMA-PROTOCOL-V1.0`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Phase 5.1-0.5 —— 决策记忆模式与晋升协议冻结（Decision Memory Schema & Promotion Protocol Freeze）  
> **核心命题**：**决策记忆影响语义层（Semantic Layer），不影响求解器变量（Solver Layer）**。本规范形式化冻结 Memory 对象统一 Schema、MDVL 晋升五大门限（含跨域迁移门限 MP-G5）、七态生命周期状态机以及标准消费协议，彻底杜绝无边界向量存储或劣质经验直接复制。

---

## 1. 记忆对象统一数据模式（Decision Memory Object Schema）

任何决策经验在晋升为 Level 3 决策记忆资产时，必须严格符合以下标准化数据结构：

```yaml
# Decision Memory Object Schema v1.0
memory_id: "DMEM-DOM4-001"                         # 记忆唯一标识符: DMEM-<domain_id>-<seq>
memory_class: "EPISODE"                            # 枚举: EPISODE | CONSTRAINT_EVOLUTION | OUTCOME | ASSUMPTION
decision_domain: "Dynamic Fleet Route Logistics"   # 所属决策范式/领域
version: "1.0"
created_at: "2026-08-22"

# 1. 上下文前提（Contextual Boundary —— No Context, No Memory 铁律）
context:
  applicable_scope: ["Dynamic Rerouting", "Vehicle Mechanical Breakdown", "Fleet Disruption"]
  preconditions:
    fleet_size: ">= 2"
    has_locked_commitments: true
    load_headroom: ">= 20%"
  invalidation_conditions: "单车队全灭或无备用车辆可接单"

# 2. 触发与因果动因（Trigger & Mechanism）
trigger:
  event_type: "VEHICLE_MECHANICAL_BREAKDOWN"
  variation_classification: "SEMANTIC_VARIATION"

# 3. 决策原则与语义指导（Decision Heuristic —— Reuse Meaning, Not Exact Plan）
semantic_recommendation:
  target_layer: "Constraint Type System & Semantic Contract"  # 消费目标层
  guideline: "当发生车辆故障导致运力归零时，首要保障锁定订单（TIME_WINDOW_LOCKED）优先转派至可用运力，非锁定订单承担改派扰动，严禁放弃锁定承诺。"
  suggested_constraint_patch:
    type: "CommitmentPriorityOverride"
    hardness: "HARD"
    relaxable: false

# 4. 商业成效与置信度（Outcome & Evaluation）
outcome_evaluation:
  realized_benchmark: "ORD_03 锁定时窗 100% 保持，冷链不变量 0 破损，改派扰动控制在 3 单"
  predicted_vs_actual_variance: "0.0% (完全达成履约)"
  confidence_score: 0.98

# 5. 溯源与生命周期（Provenance & Lifecycle）
source_evidence:
  source_episode_id: "DD-EPISODE-001"
  source_trace_id: "DD-TRACE-SEQUENCE-001"
  verified_by: "MDVL Validation Engine v1.0"
lifecycle:
  status: "PROMOTED"                              # 状态机当前状态
  expiration_date: "2027-08-22"                   # 有效期（Memory Aging 机制）
  superseded_by: null                             # 替代记忆 ID
```

---

## 2. 记忆生命周期状态机（Memory Lifecycle State Machine）

任何决策记忆对象在系统中遵循严格的 **七态生命周期状态机（The 7-State Lifecycle）**：

```
                           [Episode Completed]
                                    │
                                    ▼
                                Candidate (候选记忆)
                                    │
                                    ▼ [MDVL 评估中]
                               Evaluating (评估中)
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
              [通过 MP-G1..G4]              [未达标]
                  Validated                 Rejected (拒绝入库)
                         │
                         ▼ [通过 MP-G5 跨域验证]
                     Promoted (正式发布/企业级资产)
                         │
        ┌────────────────┴────────────────┐
        ▼ [达到有效期/环境漂移]           ▼ [发现更优经验]
    Deprecated (已过时/降级)           Superseded (被替代/保留追溯链)
```

| 状态名称 | 规范定义 | 是否允许被编译器消费 |
|---|---|---|
| `Candidate` | 初步提炼的记忆候选，尚未完成因果与成效评估 | 否 |
| `Evaluating` | 正处于 MDVL 五大门限（MP-G1..G5）自动化扫描与人工复核中 | 否 |
| `Validated` | 已通过本领域的四道门限检验，证实具备本域复用价值 | 仅限本领域推荐 |
| `Promoted` | **正式企业级决策记忆**，通过跨域泛化门限，进入全局消费目录 | **是（全局允许）** |
| `Deprecated` | 超过有效期限（Aging）或商业环境发生剧烈漂移，已丧失推荐有效性 | 否（仅归档可查） |
| `Superseded` | 被更强假设或更优经验替代（显式包含 `superseded_by` 溯源指针） | 否（保留科学研究记忆） |
| `Rejected` | 未通过成效门限或违反不变量，被判定为“劣质经验”阻断入库 | 否 |

---

## 3. MDVL 记忆晋升协议（Memory Decision Validation Layer Protocol）

任何记忆从未定型候选（`Candidate`）晋升为正式企业资产（`Promoted`），必须严格 100% 通过 **五大晋升门限（Promotion Gates MP-G1..G5）**：

```
             ┌──────────────────────────────────────────────────┐
             │       MDVL Five Promotion Gates (五大晋升门限)    │
             │                                                  │
             │  MP-G1: Outcome Threshold Gate (成效达标门限)     │
             │  MP-G2: Invariant Compliance Gate (不变量零违规)  │
             │  MP-G3: Contextual Boundary Gate (适用边界完整)   │
             │  MP-G4: Non-Repetition Gate (无知识冲突与证伪)    │
             │  MP-G5: Cross-Domain Transfer Gate (跨域迁移验证) │
             └──────────────────────────────────────────────────┘
```

- **MP-G1 (Outcome Threshold Gate)**：实际成效指标必须达到正向收益阈值（$\Delta_{\text{outcome}} \ge 0$），杜绝将亏损或劣质决策沉淀为经验。
- **MP-G2 (Invariant Compliance Gate)**：整个生命周期内所有 HARD 不变量（如安全隔离、锁定承诺、财政红线）**零违规**。
- **MP-G3 (Contextual Boundary Gate)**：必须显式声明适用的前提条件（Preconditions）与失效边界，禁止无上下文的裸结论。
- **MP-G4 (Non-Repetition & Falsification Gate)**：检查是否与现有 Promoted 记忆冲突；若属于假设被证伪，强制要求流转为 `INVALIDATED / SUPERSEDED`。
- **MP-G5 (Cross-Domain Transfer Gate —— 评审新增核心门限)**：
  - **核心职责**：验证经验在跨范式迁移时的适用性。
  - **执行规则**：例如配送领域的“锁定优先”原则欲迁移至仓储时，必须由 MDVL 验证仓储领域是否存在等价的“高危库位锁定”语义；若语义不兼容，则限定该记忆仅能在本领域内生效（停留在 `Validated` 状态，禁止无条件全局 `Promoted`），**彻底阻断错误泛化**。

---

## 4. 记忆消费标准协议（Memory Consumption Protocol）

### 4.1 消费作用层级铁律（The Semantic Impact Law）
$$\text{Memory} \Longrightarrow \text{Semantic Layer} \quad (\text{Contract / Type / DSVL})$$
$$\text{Memory} \centernot\Longrightarrow \text{Solver Layer} \quad (\text{Variables / Coefficients / Solver Options})$$

- **严禁**：决策记忆直接向 MathOpt 输出变量赋值（如：禁止 Memory 输出 `x["ORD_03", "VEH_03"] = 1`）。
- **必须**：决策记忆向编译器的语义层输出**指导约束或参数校准（Semantic Recommendations）**（如：Memory 输出“将 ORD_03 标记为不可降级的 `CommitmentLock`”），随后由完整的编译器流水线重新完成数学建模。

### 4.2 记忆反哺编译器的三大标准接口（The 3-Interface Consumption Protocol）

```
                     Decision Memory (Promoted Asset)
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
[Interface 1: Contract]   [Interface 2: Type System]    [Interface 3: DSVL]
  • 参数偏差校准            • 提炼高频经验强类型模板      • 沉淀新增安全不变量
  • 修正预测潜能/耗时系数   • 固化组合策略规则            • 历史故障自动转化为新闸门
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    ▼
                    Next Decision Compilation Run
```

---

## 5. 治理纪律：防退化四铁律工程化校验（Verification Matrix）

| 铁律名称 | 编译器工程化拦截机制 | 违规后果与报错码 |
|---|---|---|
| **1. No Context, No Memory** | MDVL 扫描 `context.preconditions` 字段是否非空且可参数化判断 | 缺失上下文者立即拒入：`MEM-E001_NO_CONTEXT` |
| **2. Reuse Meaning, Not Plan** | 消费接口扫描器严禁包含具体解变量名（如 `x_*`, `f2_*`） | 包含解变量者阻断消费：`MEM-E002_SOLVER_POLLUTION` |
| **3. Falsification Memory** | 假设证伪事件必须同步触发 `KB-GOV-014` 假设状态机更新 | 丢失证伪记录者审计告警：`MEM-E003_LOST_FALSIFICATION` |
| **4. Memory Aging & Pruning** | 定期调度器扫描 `expiration_date`，超期自动流转至 `Deprecated` | 消费超期记忆者报错：`MEM-E004_EXPIRED_MEMORY` |
