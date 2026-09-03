# SVDE Architecture Specification v1.5
## 决策运行时编译器架构 · 动态运行时层正式化 · 四领域全景证据 · 决策记忆演进规范

> **文档标识**：`SVDE-ARCH-SPEC-V1.5`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Phase 5.0 架构升级复盘（Architecture v1.5 Freeze）——完成 Phase 4 全线闭环后的重大架构定型  
> **架构跃迁**：从静态编译（v1.0: $\text{Decision} = f(\text{State})$）正式演进为 **动态决策运行时编译器（v1.5: $\text{Decision}(t+1) = f(\text{Intent}, \text{Contract}, \text{State}(t), \text{Event})$）**。  
> **非外推边界定型**：SVDE 已在四类具有明确约束、目标和可验证性的企业决策范式中完成通用化验证，证明统一 Decision Compiler Kernel 在测试范围内具备跨领域表达、编译与验证能力；不向无约束直觉决策或全自主 AGI 外推。

---

## 1. 架构升级：五层决策运行时编译器拓扑（The 5-Layer Decision Architecture）

```
                         Decision Interface Layer
                         (Human / Agent / API)
                                    │
                                    ▼
                          Semantic Layer (语义层)
       ┌────────────────────────────────────────────────────────────┐
       │  1. Semantic Contract       (业务契约与不变量规范)          │
       │  2. Constraint Type System  (强类型系统与生成期安全检查)    │
       │  3. Decision Semantic Validation (DSVL 决策语义安全闸门)   │
       └────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                      Decision Compiler Layer (编译层)
       ┌────────────────────────────────────────────────────────────┐
       │  1. Math Compiler           (MIP / CP / Flow 多模式投影)   │
       │  2. Solver Adapters         (MathOpt / HiGHS / CP-SAT 等)  │
       │  3. Independent Oracle      (异构隔离仲裁与数学等价基准)   │
       └────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                     Decision Runtime Layer ⭐新增 (运行时层)
       ┌────────────────────────────────────────────────────────────┐
       │  1. Runtime State Model     (物理状态机与历史不可逆性守卫) │
       │  2. Event Classification    (Data vs. Semantic 变异分诊)   │
       │  3. Incremental Recompile   (最小破坏增量编译与承诺保持)   │
       │  4. Post-Event DSVL         (事件后动态决策可行性秒级验证) │
       └────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    Decision Memory Layer (决策记忆层)
       ┌────────────────────────────────────────────────────────────┐
       │  1. Decision Episode        (单次静态决策因果快照)         │
       │  2. Decision Evolution Episode (动态时序决策演化追踪)      │
       │  3. Assumption & Failure Memory (假设状态机与缺陷知识库)   │
       └────────────────────────────────────────────────────────────┘
```

---

## 2. 核心架构升级：Decision Runtime Layer（运行时决策层）正式化

Phase 4.3 证实动态现实接入需要编译器不仅具备单次生成能力，更必须具备**运行时自适应能力（Runtime Adaptation）**。本层形式化确立四大核心子模块：

### 2.1 运行时状态模型（Runtime State Model）
- **动态三要素输入方程**：
  $$\text{Decision}(t+1) = \mathcal{F}\Big(\text{Business Intent}, \ \text{Semantic Contract}, \ \text{Runtime State}(t), \ \text{Event Stream}(t)\Big)$$
- **历史不可逆性铁律（Past Reality Immutability Principle）**：
  $$\text{Past Executed Fact} \ne \text{Optimization Variable}$$
  处于已执行终态的物理事实（如 `DELIVERED`、已排产工单）自动沉淀为确定性常数，严禁被任何重规划优化器重新拉回变量池。

### 2.2 事件分诊机制（Event Classification: Data vs. Semantic Variation）
- **Data Variation（数据级微调）**：行车轻微拥堵（ETA $+5\%$）、拣选耗时微调 $\implies$ **仅平滑更新显示与状态估算，零重新编译，保障计划稳定性**。
- **Semantic Variation（语义级变异）**：车辆故障、冷链断电、急件插入、锁定冲突 $\implies$ **触发增量决策重编译（Incremental Semantic Recompile），调用 DSVL 重新裁定可行性**。
- **回答核心 AI 哲学问题**：*AI 决策系统何时应当重新思考？*——仅当事件破坏决策语义假设时，才介入重新编译。

### 2.3 增量重编译与承诺保持（Incremental Recompile & Commitment Survival）
- 动态重排的本质**不是 Re-Optimization（全局重新求解），而是 Re-Compilation（受控增量重编译）**：
  1. 锁定已有客户承诺（`TIME_WINDOW_LOCKED` / `DAY_LOCKED`）零移动；
  2. 保持冷链等物理不变量刚性；
  3. 约束未受扰动运单的改派上限（$\Delta_{\text{reroute}} \le \rho$）。

### 2.4 事件后动态安全闸门（Post-Event DSVL）
- 确立 **Pre-Compile DSVL（编译前静态语法/语义检查）+ Post-Event DSVL（动态事件后运行时安全复验）** 的双重防御机制，确保即使在极端突发事件下下发的应急指令依然满足工时安全、物理容量与法律底线。

---

## 3. 内核边界规范（Kernel vs. Domain Adapter v1.2）

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                SVDE Kernel (不可变通用内核 v1.2)                            │
│                                                                                           │
│  1. Semantic Pipeline Core: Intent → Contract → Type → DSVL → Math → Runtime → Trace      │
│  2. Constraint Type System Engine: Shift Left 静态类型检查与错误拦截 (TC-001/002/003/004) │
│  3. Dual-Stage DSVL Scanner: Pre-Compile Invariant 扫描 + Post-Event 运行时可行性复验     │
│  4. Heterogeneous Math Engine: MathOpt / HiGHS / CP-SAT 统一抽象与多目标字典序求解器       │
│  5. Sequence Oracle Engine: 静态 Single Oracle + 动态 Sequence Oracle 分步仲裁引擎        │
│  6. Runtime State & Immutability Manager: 状态机单向流转守卫与历史事实冻结器              │
│  7. Event Triage & Recompile Controller: Data vs. Semantic 变异分诊与增量编译控制器       │
└───────────────────────────────────────────────────────────────────────────────────────────┘
                                              ▲
                                              │ 标准 6 大工件挂载协议 (Onboarding Protocol)
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                               Domain Adapter (领域专用插件层)                             │
│                                                                                           │
│  Artifact 1: <domain>_semantic_contract_v1_0.yaml   (实体、C1..Cn 规则、I1..Im 不变量)    │
│  Artifact 2: <domain>_constraint_type_registry_v1_0 (领域强类型定义、生成期规则)          │
│  Artifact 3: <domain>_dsvl_rules_v1_0.yaml          (领域不变量判定逻辑、特化白名单)        │
│  Artifact 4: <domain>_oracle_definition_v1_0.md     (领域隔离 Oracle 实现与参数设置)        │
│  Artifact 5: <domain>_trace_schema_v1_0.json        (决策因果解释与变异审计模式)            │
│  Artifact 6: <domain>_runtime_state_schema_v1_0.json(动态领域专用: 状态切片与事件流模式)    │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 四大领域全景证据矩阵（Four-Domain Evidence Map）

SVDE 已在四类截然不同的决策范式中完成完整工程闭环，各领域均满足 **Gate O1–O8** 且 **MathOpt == 独立 Oracle 100% 语义等价**：

| 领域维度 | Domain 1: 拜访排班 (Phase 3.3 ✅) | Domain 2: 仓储库位 (Phase 4.1 ✅) | Domain 3: 渠道布局 (Phase 4.2 ✅) | Domain 4: 动态配送 (Phase 4.3 ✅) |
|---|---|---|---|---|
| **决策分类** | **Temporal Operational**（时间周期调度） | **Spatial Physical**（物理空间存取） | **Strategic Allocation**（战略商业配置） | **Dynamic Runtime**（动态运行时自适应） |
| **一等对象** | 销售员 $\times$ 拜访需求 | 货位 $\times$ SKU 存储分配 | 商圈网格 $\times$ 渠道业态组合 | 运力车队 $\times$ 动态运单流 |
| **时空维度** | 静态周期（2–4 周） | 准实时/波次（小时/班次） | 宏观战略规划（季度/年度） | 动态实时（分钟级事件流） |
| **核心不变量** | 拜访承诺锁（DAY/SEQ/COMPLETE） | 危化品隔离（$\ge 15\text{m}$）、冷链不穿越 | 财政预算红线、品牌等级不降级 | 历史不可逆、承诺时窗必达、疲劳红线 |
| **数学后端** | MathOpt(HiGHS) == CP-SAT Oracle | MathOpt(HiGHS) == CP-SAT Oracle | MathOpt(HiGHS) == CP-SAT Oracle | MathOpt(HiGHS) == Sequence Oracle |
| **等价最优值** | `36006340.0` (4/4 Case 严格一致) | `['FEASIBLE', 8, 6135]` (100% 吻合) | `['FEASIBLE', 340, 2255]` (100% 吻合) | `['FEASIBLE', 10, 0/3]` (全时序一致) |
| **外部现实变异** | KBC-05 绕行扰动 $\to$ Data Var | 动线距离扰动 $\to$ Data Var | 潜能指数扰动 $\to$ Data Var | 拥堵 $\to$ Data Var；故障 $\to$ Semantic Var |

---

## 5. 决策记忆演进规范（Decision Trace $\to$ Decision Memory Specification）

在进入 Phase 5 之前，正式确立从“单次追踪”向“企业级决策记忆”的演进标准：

```
   [Phase 3/4 现状: 决策追踪]                         [Phase 5 目标: 决策记忆资产化]
┌───────────────────────────────┐                  ┌─────────────────────────────────────────┐
│        Decision Trace         │                  │             Decision Memory             │
│                               │                  │                                         │
│ • 记录单次决策如何产生        │                  │ • 长期沉淀: 决策 → 行动 → 结果 → 学习   │
│ • Intent → Model → Solution   │ ──── 资产化 ───► │ • Decision Evolution Episode (跨周期演化│
│ • 静态因果解释 (Why A, not B) │                  │ • 假设证伪知识库 (Research Memory)      │
│ • 属于执行期凭证              │                  │ • 属于企业战略级知识资产                │
└───────────────────────────────┘                  └─────────────────────────────────────────┘
```

### 5.1 决策片段（Decision Episode）的两大标准结构
1. **静态决策片段（Static Decision Episode）**：
   - 适用于静态计划型场景（拜访、仓储、渠道）；
   - 结构：$\langle \text{Intent}, \ \text{ContractSnapshot}, \ \text{TypedConstraints}, \ \text{Solution}, \ \text{CausalExplanation} \rangle$。
2. **动态演化片段（Decision Evolution Episode）**：
   - 适用于动态自适应场景（配送调度、实时重排）；
   - 结构：$\langle \text{InitialPlan}, \ \text{EventSequence}, \ \text{StateSnapshots}(t), \ \text{RecompilationTriggers}, \ \text{AdaptationDelta}, \ \text{Outcome} \rangle$。

---

## 6. 科学边界与非外推声明（Scope Boundaries & Non-Extrapolation）

1. **确立的科学事实（Proven Facts）**：
   - SVDE 架构成功证明：在具有明确业务契约、强类型约束与可验证不变量的企业决策场景下，统一的 Decision Compiler Kernel 能够在异构求解器与外部现实扰动下保持决策语义零漂移，并实现微观调度、物理空间、战略配置与动态运行时的四维跨越。
2. **严格禁止外推的领域（Non-Extrapolation Boundaries）**：
   - 尚未证明对完全无约束、依赖人类直觉模糊感知的艺术创作或纯商业谈判的自动决策能力；
   - 尚未证明自然语言意图到正式契约的 100% 全自动零误差抽取（仍需人类专家在 Contract Freeze 环节把关）；
   - 尚未证明超大规模千万级节点实时微秒级高频撮合性能（该指标属于高并发工程而非编译器语义正确性范畴）。
