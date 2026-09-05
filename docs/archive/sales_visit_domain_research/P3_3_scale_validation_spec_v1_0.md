# Phase 3.3 — Scale Semantic Compilation Validation：Executable Spec v1.0
## 修订 r1（2026-08-22 评审批准）：术语升级 DSVL + Frozen Assumption Registry（KB-GOV-013/014）——Spec 主体不变
## GT-Small 规模扩展 × MathOpt 真实接口 × KBC-05 仲裁 × Constraint Type System / Semantic Validation Layer

> **文档标识**：`P33-SCALE-VALIDATION-EXESPEC-V1.0`  
> **执行日期**：2026-08-22  
> **上游**：Phase 3.2 关闭记录（KB-GOV-012）+ 评审指令（目标调整 + 四 AC + 措辞纪律）  
> **三问验证目标（评审原文）**：Q1 规模扩大后语义是否保持（GT-Small）· Q2 真实数学接口接入后是否保持（MathOpt）· Q3 复杂业务证据加入后是否保持（KBC-05）· 外加 Q4 两个新模块（Type System / Validation Layer）  
> **纪律**：0 DCR 预期；Guard 1/2/3 生效；runtime 非指标；对外表述按 KB-GOV-012 claim_scope

---

## 1. 实例规格：GT-Small v1.0

```
规模: 10 客户 × 1 业务员 × 4 周（20 工作日）——S-A §2.1 GT-Small 档位
Oracle: 独立 exact model（CP-SAT 独立实现，求到 OPTIMAL+bound；不做全枚举——S-A §2.10）
travel: 保留合成曼哈顿（KBC-05 仲裁在同一 travel 口径下进行——路网替换属 Phase 4 基准）
客户构成: KA×2 / A×4 / B×4；EXACT/RANGE 混合；cadence 边界收紧一档
```

## 2. 四 AC（评审指令原文——不加不减）

| AC | 检查 | 判定物 |
|---|---|---|
| **AC-1 Semantic Equivalence** | 保持 3.2 两档判据（语义层 L1/L2/L3 严格 + 代价层容差带）——F1/F2(MathOpt)/F3/Oracle 四方 | 元组比对表 |
| **AC-2 Zero Domain Contradiction** | 新增：业务语义冲突检查——编译产物的约束集经**语义验证层**扫描（HARD×HARD 冲突显式、Soft 不冒充 Hard、锁语义不互斥违背） | contradiction 扫描报告（0 起为过） |
| **AC-3 Constraint Type Safety** | 新增：约束全部经 **Typed Constraint** 通道生成（YAML: type/cardinality/entity/level/relaxable）——禁止裸字符串约束；cardinality 违例（AddExactlyOne@k=2 类）在**生成期**拦截 | Type System 拦截日志（7 类 3.2 失败的生成期等价物全部复现并拦截） |
| **AC-4 Runtime Trace Completeness** | 新增：Decision → Model → Solution → Outcome 四段 trace 全程可检索（机读 JSON，逐元素三元组） | trace 完整性断言 |

## 3. 新模块 A：Constraint Type System（KB-GOV-012 三模块之一落地）

```yaml
# Typed Constraint Schema（Decision IR → Type System → Math Model）
constraint:
  id: CT-001
  type: FREQUENCY_EXACT          # 枚举: FREQUENCY_EXACT|FREQUENCY_RANGE|MIN_GAP|MAX_GAP|
                                 #       DAY_CAPACITY|LOCK_DAY|LOCK_SEQUENCE|LOCK_COMPLETE|
                                 #       AVAILABILITY_WINDOW|DEFER_BUDGET
  entity: {kind: target, id: A}
  cardinality: {op: "==", value: 2}   # 生成期检查: AddExactlyOne 仅当 value==1
  level: HARD                     # HARD | SOFT_PREFERENCE | OBJECTIVE_PENALTY（Constraint Ontology）
  relaxable: false                # Case2 软化白名单外一律 false——min_gap 误软化类失败生成期拦截
  provenance: {domain_object: FrequencySpec(EXACT,2), requirement: REQ-GM-001}
```

**Compiler 生成期检查**（3.2 七失败的类型学等价）：
1. cardinality op/值与 API 语义匹配（ExactlyOne 仅 k=1）
2. level=HARD 且 relaxable=false 的约束在任何 soft 模式下不得进入罚项
3. 锁约束 (LOCK_*) 与 AVAILABILITY_WINDOW 冲突时显式报 Contradiction（AC-2）

## 4. 新模块 B：Decision Semantic Validation Layer — **DSVL**（正式术语，KB-GOV-013——避免与普通数据校验混淆）

**前置+后置**执行（评审裁定：parse-time check × runtime check——非仅末尾）。前置=编译后求解前；后置=解产出后 trace 前。类比编译器 semantic checking：
- **不变式扫描**：模型约束集 ⊇ 装配件全部 HARD 语义（无遗漏）；无冗余冒充（SOFT 项不在 HARD 集）
- **锁语义验证**：每个承诺锁在模型中存在对应执法元素（3.2 锁丢失类失败的生成期防护）
- **双射抽查**：Typed Constraint ↔ 数学元素 ↔ Domain 对象 三链闭合（KG 图谱在数学层的投影）

## 5. KBC-05 仲裁机制（Q3）

GT-Small 解的**行程腿**（每选中日子集的 route 顺序与 cost）提交 KBC-05（VRPSolverEasy exact BPC）独立求值：
- 三形态 route cost 与 KBC-05 精确值差 ≤ 1e-6（同一 HK 口径下）
- 仲裁不一致时：**裁决语义**（是否某形态的 travel 表达漂移）而非性能——Class B/C 归因框架适用
- KBC-05 定位不变：R&D oracle，仅验证不生产（KBC-005 known_limits）

## 6. F2 → MathOpt 真实接口（Q2）

F2 从 CP-SAT 语义实现切换为 **`ortools.math_opt`（python）建模 + HiGHS/SCIP 求解**（KBC-02 绑定）：
- date-index 0-1 变量 + 线性约束（S-A §2.8 F2 定义——无 λ）
- 字典序：分层求解序列（L1 可行 → L2 固定 → L3 → L5；每层加最优割约束）
- CP-SAT 实现保留为 F3（原生 interval 族）——F2/F3 从此真异构后端

## 7. 执行计划

| # | 步骤 | 产出 |
|---|---|---|
| 1 | GT-Small 装配件 | `gt_small_instance_v1_0.yaml` |
| 2 | Constraint Type System（生成+检查） | `constraint_type_system.py` + 拦截日志 |
| 3 | Semantic Validation Layer | `semantic_validation_layer.py` + 不变式扫描报告 |
| 4 | F2→MathOpt 重写 + F1/F3 保留 + Oracle exact | `gt_small_oracle.py` |
| 5 | KBC-05 仲裁接入 | route 仲裁段 |
| 6 | 四 AC 判定 + 四段 trace | `phase3_3_scale_validation_report_v1_0.md` |

## 8. 失败处理（Guard 3 预登记）

Type System/Validation Layer 拦截的违例 = **Class C（生成期捕获——模块按设计工作）**；MathOpt/HiGHS 数值问题 = Class C；KBC-05 仲裁不一致 = 先查三形态 travel 表达（Class B 候选）；仅当装配件语义无法用冻结对象表达 → Class A → DCR。

## 9. 措辞纪律（KB-GOV-012 claim_scope 绑定）

本阶段结论无论 PASS 与否，对外表述限定："验证 SVDE Decision Compiler 在 GT-Small 规模/真实接口/仲裁机制下的语义一致性"——不使用"已证明 Agent 能自动建模"。


## 10. Frozen Assumption Registry（评审 r1 新增——KB-GOV-014 全文引用）

本 Benchmark 阶段冻结五假设（A001-A005）。任何失败先判 **Assumption Fail**（假设失效——修订假设并重申范围）vs **Implementation Fail**（实现缺陷——Class C/B 处理），才允许进入 Domain 层讨论：

| ID | 假设 | 失效条件 |
|---|---|---|
| A001 | Travel 表达可由 KBC-05 仲裁 | KBC-05 无法求解 GT-Small 尺寸/接口不可用 |
| A002 | Type System 十类覆盖全部约束 | 出现第 11 类 |
| A003 | 字典序分层求解 GT-Small 可达各层最优 | 超时/层间割失效 |
| A004 | 合成 travel ≡ 路网 travel（语义层） | Phase 4 漂移超 ε_couple |
| A005 | L4/L5 容差带在 GT-Small 成立 | 四方差 >120min |

## 11. 架构升级声明（评审裁定）

Compiler Pipeline 正式化（KB-GOV-013）：`Decision Compiler → Decision IR → Constraint Type System → DSVL(前置) → Math Model Generation → Solver → DSVL(后置) → Runtime Trace`——SVDE 定位为**编译器架构**而非 Agent Workflow。执行顺序严格 ①→⑥ 串行，不并行；PI Agent 继续暂缓。
