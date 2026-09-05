# Phase 5.2 — Decision Memory Reliability & Evolution Stress Test Spec v1.0
## 决策记忆可靠性与演化压力测试规范 · 逆向记忆测试 · 五大压力测试矩阵

> **文档标识**：`P52-MEMORY-STRESS-SPEC-V1.0`  
> **冻结日期**：2026-08-22  
> **阶段定位**：Phase 5.2 —— 决策记忆可靠性与演化压力测试（Memory Reliability & Evolution Test）  
> **核心命题**：**“如果 AI 学错了，它是否知道自己学错了？”** 验证决策记忆系统面对劣质经验、环境漂移、记忆冲突、跨域错配与记忆过载时的免疫与自我修复能力，杜绝“错误经验固化”与“过约束可行域窒息”。

---

## 1. 记忆分类学升级：Memory Taxonomy v1.1（引入反事实记忆）

在原有四类记忆资产基础上，正式确立第五类一等记忆资产：

| 类别 | 符号 | 定义与核心结构 | 核心企业认知价值 |
|---|---|---|---|
| 1. Episode Memory | `DMEM-EPISODE` | $\langle \text{Context}, \text{Intent}, \text{Solution}, \text{Outcome}, \text{Rationale} \rangle$ | 记录“做了什么与成效如何”的因果事实 |
| 2. Constraint Evolution | `DMEM-CONST` | $\langle \text{ConstraintID}, \text{LevelEvolution}, \text{Trigger}, \text{Reason} \rangle$ | 记录业务规则如何从偏好收敛为硬不变量 |
| 3. Outcome Memory | `DMEM-OUTCOME` | $\langle \text{DecisionID}, \text{Predicted}, \text{Realized}, \text{VarianceDelta} \rangle$ | 记录预期与实际偏差，校准环境潜能参数 |
| 4. Assumption Memory | `DMEM-ASSUME` | $\langle \text{AssumptionID}, \text{Status(ACTIVE/VALID/INVALID)}, \text{Evidence} \rangle$ | 严密记录科学假设的验证与证伪历程 |
| **5. Counterfactual Memory ⭐**<br>（反事实记忆） | `DMEM-COUNTER` | $\langle \text{Context}, \text{AlternativeAction}, \text{PredictedRisk/Loss}, \text{AvoidanceReason} \rangle$ | **记录“为什么没有这么做”以及未选方案的潜在损失评估**（如：若不保护 ORD_03 锁定时窗，预计将引发客户索赔与关系破裂风险） |

---

## 2. 记忆治理层（Memory Governance Layer）架构升级

在五层决策运行时架构顶部，正式确立 **Memory Governance Layer**，形成闭环治理拓扑：

```
                           Memory Governance Layer ⭐
                    (MDVL 验证器 / 冲突裁决 / 淘汰老化 / 审计)
                                      │
                                      ▼
                            Decision Memory Layer
                (Episode / Evolution / Outcome / Assumption / Counterfactual)
                                      │
                                      ▼
                            Decision Runtime Layer
                 (State Model / Event Triage / Incremental Recompile)
                                      │
                                      ▼
                            Decision Compiler Layer
                     (Math Compiler / Solver Adapters / Oracles)
                                      │
                                      ▼
                                Semantic Layer
                 (Semantic Contract / Type System / DSVL)
                                      │
                                      ▼
                            Decision Interface Layer
```

---

## 3. 五大记忆压力测试矩阵（The 5-Stress Test Suite）

```
                                  Phase 5.2 Stress Test Matrix
 ─────────────────────────────────────────────────────────────────────────────────────────────
  Test 1: Bad Memory Injection       ──► 故意注入劣质亏损经验，验证 MDVL 阻断率 (100% 拒绝)
  Test 2: Negative Memory Harm       ──► 模拟环境漂移导致记忆过约束，验证记忆老化与可行域保护
  Test 3: Memory Conflict Resolution ──► 注入相互矛盾的经验规则，验证冲突裁决机制与置信度仲裁
  Test 4: Cross-Domain Transfer      ──► 强行跨域注入领域特化参数，验证 MP-G5 边界阻断
  Test 5: Memory Accumulation        ──► 批量注入 50+ 记忆条目，验证编译器性能与抗过约束退化
```

### Test 1: Bad Memory Injection（劣质记忆注入测试）
- **注入用例**：构造一条负向收益（$\Delta_{\text{outcome}} = -25\%$）或诱导违背安全不变量（如建议将危化品与食品同置以节约库位）的伪经验。
- **预期断言**：`MDVL (MP-G1 / MP-G2)` 必须 100% 触发阻断，状态强制标记为 `REJECTED`，严禁入库。

### Test 2: Negative Memory Harm / Environment Drift（逆向记忆危害与环境漂移测试）
- **测试场景**：客户已正式发函取消周三拜访偏好（环境漂移），但历史记忆 `DMEM-CONST-001` 仍试图强制锁定周三。
- **预期断言**：系统触发 `invalidation_conditions` 检查，自动将过时记忆流转为 `SUPERSEDED` / `DEPRECATED`，解除对可行域的不当压迫（防止 Opportunity Loss）。

### Test 3: Memory Conflict Resolution（记忆冲突仲裁测试）
- **注入用例**：
  - Memory A: “T1 商圈必须开设旗舰店（置信度 0.90）”；
  - Memory B: “预算紧缺时 T1 商圈允许开设专卖店替代旗舰店（置信度 0.95）”。
- **预期断言**：Memory Governance 引擎依据上下文特异性（Specificity）与置信度评分自动裁决，避免编译器陷入约束互斥无解。

### Test 4: Cross-Domain Semantic Transfer（跨领域语义迁移门禁测试）
- **注入用例**：尝试将渠道领域的 `DMEM-OUTCOME-001`（潜能转化系数 0.85）注入仓储库位或配送调度系统。
- **预期断言**：`MP-G5 (Cross-Domain Transfer Gate)` 判定语义范式不兼容，100% 阻断跨域注入。

### Test 5: Memory Accumulation & Scalability（记忆过载与规模演化测试）
- **测试场景**：连续沉淀 50 条合法记忆片段，输入 Decision Compiler。
- **预期断言**：Compiler 成功合并同类项约束，求解时间与决策质量保持稳定，未发生“约束爆炸导致求解不可行”。

---

## 4. 实验与验收标准（Acceptance Criteria）

- **AC-M1 (Bad Memory Immunity)**: 劣质/违规记忆注入拦截率 **100%**。
- **AC-M2 (No Memory Harm)**: 环境漂移下过时记忆自动失效，Feasibility 与 Objective 优于僵化记忆模式。
- **AC-M3 (Deterministic Conflict Resolution)**: 记忆冲突时输出唯一确定性裁决，零编译器崩溃。
- **AC-M4 (Semantic Transfer Isolation)**: 跨领域非法迁移拦截率 **100%**。
- **AC-M5 (Memory Scalability)**: 规模累积下决策质量单调非减，无约束爆炸。
