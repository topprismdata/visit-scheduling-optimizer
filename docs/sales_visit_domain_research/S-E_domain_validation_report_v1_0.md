# Scenario E — Domain Executable Validation Report v1.0
## Phase B3 · Rolling Replanning + Commitment/Lock + Execution History（解释层）

> **文档标识**：`SE-DOMAIN-EXECUTABLE-VALIDATION-V1.0`  
> **执行日期**：2026-08-22  
> **验证目标（评审指令对齐）**：验证 SVDE KB 能否表达动态决策——**非新增概念、非扩展 Domain**  
> **执行纪律**：零数学；A03 v1.0.1 未动；DM-010 保持 Candidate  
> **载体**：`validation/phase2/run_scenario_e_validation.py` + `decision_trace_e.json`  
> **结果**：**17/17 PASS · 0 DCR · 0 Class-A Failure**

---

## 1. Gate E 判定

| Gate | 结果 | 证据 |
|---|---|---|
| **E1 Immutability** | ✅ | TE-IRREV：重排输出零改动已执行记录；week-1 只入 History |
| **E2 Commitment Survival** | ✅ | TE-COMMIT/TE-LOCK-SEQ/TE-INF-COMMIT：DAY_LOCKED 存活于请假扰动；SEQUENCE_LOCKED 三连零移（即使落在请假日）；COMPLETELY_LOCKED×absence → kept + 结构冲突显式归因 |
| **E3 Rolling History** | ✅ | TE-HIST-CARRY：wk1/wk2 完成的 eligible 滚动后移单调；TE-HIST-MISSED：regen eligible = max(horizon, missed+gap)——cadence 保持 |
| **E4 Injection** | ✅ | TE-INJECT：Z-缺货 OPTIONAL 注入，REQUIRED 零挤占 |
| **E5 Ratio/Freeze Governance** | ✅ | TE-RATIO：50% 需求 vs 30% 预算 → moved=2/shortfall=6 **显式报告**（非静默违反） |
| **E6 DM-010 Adjudication** | ✅ | **H2 判定（建议合并入 DM-006+007）**——详见 §2 |
| **E7 Scenario Pass** | ✅ | 17/17 + Classification 全登记 + Change Log EMPTY |

## 2. DM-010 裁定实验结果（本场景核心交付）

**评审问题**：Replanning 需要独立 DM-010，还是 DM-006+007 已足够？

**判定：H2——建议降级合并**。证据链：

| 重排语义 | 承载（全部冻结对象） | 归属 DM |
|---|---|---|
| freeze 窗口 / 移动比例预算 | `PlanningPolicy.freeze_days_count / max_reassignment_ratio`（KB-ONT-080） | DM-006 输入 |
| 扰动未满足处理 | `DeferralPolicy` 链（KB-ONT-053，R3→DP-STD→defer→absence 回归通过） | DM-007 |
| 漏访补访重生成 | `ExecutionHistory`（KB-ONT-078）+ OccurrenceGenerator | DM-003 |
| 重排差异审计（moved/kept/regen） | **trace 维度输出**——非 Domain 对象 | DM-006 输出扩展 |

**无任何"重排特有的、006/007 无法承载的决策输入"出现 → 无 Failure Evidence → 不满足独立 DM 门槛。**

按评审建议的三态模型：DM-010 维持 **Validated Candidate**（E 已验其语义可表达），**建议状态：merge-candidate**（最终降级/保留由 E+B 双场景后 Gate 复审裁定——B 可能暴露日内修复的差异语义）。

## 3. Failure Classification 全登记（评审 §四.4 要求）

| 高风险点 | 预判 | 实际 | 证据 |
|---|---|---|---|
| freeze 窗口语义 | B(Compiler) | **B** ✅ | PlanningPolicy 字段已有，缺的是解释规则（随 Phase 3 Compiler 规范） |
| 重排差异审计无对象 | B | **B** ✅ | moved/kept/regen 为 trace 维度，未新增 Domain 对象 |
| 运行期新增 commitment | 无风险 | **无风险** ✅ | ExistingCommitment list 追加即表达 |
| DM-010 独立性 | 待判 | **H2(合并)** ✅ | 全部语义由冻结对象承载 |

**Class-A（Domain 缺失）：0 起。**

## 4. 测试明细（17 项）

| 组 | 测试 | 关键实测 |
|---|---|---|
| 基线 | TE-BASE ×6 | 承诺 THU 存活/请假日 visit 移动/week-1 不可逆/missed regen/注入/预算 1/2 |
| 承诺 | TE-COMMIT + TE-LOCK-SEQ | executor 不变；三连 SEQUENCE_LOCKED 零移（lock 优先于 absence → 冲突显式而非静默移动） |
| 历史 | TE-HIST-CARRY + TE-HIST-MISSED | eligible 单调后移；regen=max(horizon, missed+10d) |
| 注入 | TE-INJECT | OPTIONAL 类、REQUIRED 零挤占 |
| 治理 | TE-IRREV + TE-RATIO + TE-INF-COMMIT | 只读守卫；超预算 shortfall=6 显式；lock×absence→PROVEN_INFEASIBLE 归因 REQ-E-002×availability |
| 裁定 | TE-DM010 ×2 | H2 判定 + Class-A 零发生 |

## 5. Domain Change Log

**EMPTY**（0 DCR；全部失败风险点判为 Class-B/无风险，登记于 Classification）。

## 6. 对 A/C/D 的增量证明

| 维度 | 前序已证 | E 增量 |
|---|---|---|
| PlanningPolicy | 值为 0/1.0（未约束） | **freeze/ratio 首次非零生效**——重排范围受控 + 超限显式 |
| CommitmentLock | DAY_LOCKED 存在性 | **SEQUENCE/COMPLETELY_LOCKED 首次使用** + 扰动下存活性 + **运行期追加** |
| ExecutionHistory | 单次抵扣/漏访 | **多轮滚动累积**——决策输入地位确立（DM-008 主验素材） |
| LifecycleState | 至 PLANNED | **IN_PROGRESS→COMPLETED/MISSED 流转素材生成**（DM-008 awaiting→E 已供证据，B 终验） |
| 重排审计 | 无 | **diff-audit 四类（moved/kept/injected/regen）作为 trace 维度**——非 Domain 对象 |

## 7. RMAP / KB 状态推进

```
Phase 2/B3: A✅ C✅ D✅ E✅ → B(最后)
DM-010: Validated Candidate / merge-candidate（B 后终裁）
DM-008: 证据已供（E）→ B 终验后可审 Approved
Change Log: EMPTY · 累计四场景 75 测试 / 0 DCR 违规
```
