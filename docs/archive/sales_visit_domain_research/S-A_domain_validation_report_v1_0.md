# Scenario A — Domain Executable Validation Report v1.0
## Phase 2 · Executable Validation（解释层执行结果，非 Solver Spike）

> **文档标识**：`SA-DOMAIN-EXECUTABLE-VALIDATION-V1.0`  
> **执行日期**：2026-08-22  
> **验证对象**：A03 `Domain-Contract-v1.0.1 FROZEN` 能否完整表达 Scenario A（S-A v1.1.1 规格）  
> **执行纪律**（RMAP Phase 2）：✅ 全程零数学——未创建任何决策变量、约束、目标系数、求解器调用或后端比较。  
> **执行载体**：`validation/phase2/domain_contract.py`（契约忠实转写）+ `validation/phase2/run_scenario_a_validation.py`（验证套件）  
> **结果**：**18/18 PASS · 0 FAIL · 0 DCR**

---

## 1. Instance Assembly（装配验证）

三类实例从冻结契约对象装配成功，未新增任何 Domain Entity：

| 实例 | 规模 | 说明 |
|---|---|---|
| `S-A-STD` | 32 客户（2KA/8A/16B/6C）× 20 工作日 | 对齐 §2.3 预期表；含 2 家 B 类周分化时窗、1 家 C 漏访史、1 条 DAY_LOCKED 承诺 |
| `S-A-MICRO` | 6 客户 × 10 工作日 | GT-Micro 规格（穷举 oracle 属 Phase 3，本阶段仅装配） |
| 变体 ×5 | POL/GAP/RES/CAP/INF/HIST | 各测试专用，改动面受控（见 §3） |

**Requirement Binding 回归（DCR-SA-001-R）**：
- `REQ-A-008 (COMPANY_POLICY) → exception_handling_policy_ref="DP-STD"` ✅ 可解析
- `REQ-A-009 (CONTRACT) → "DP-SLA"` ✅ 可解析
- 不可解析引用（`DP-NOPE`）→ **显式 KeyError**，无静默跳过 ✅

## 2. Demand / Occurrence Generation 验证（§2.3 逐行命中）

| 段 | 预期（S-A v1.1.1 §2.3） | 实际 | 判定 |
|---|---|---|---|
| KA×2, EXACT(4) | 8 REQUIRED | 8 | ✅ |
| A×8, EXACT(2) | 16 REQUIRED | 16 | ✅ |
| B×16, RANGE(1..2) | 16 REQUIRED（底线）+ 16 OPTIONAL（stretch，PROOF-E1 分层法） | 16+16 | ✅ |
| C×6, EXACT(1) | 6 COMMITTED | 6 | ✅ |
| **合计** | **40 REQUIRED / 16 OPTIONAL / 6 COMMITTED（62 occurrence）** | **40 REQUIRED / 16 OPTIONAL / 6 COMMITTED（62）** | ✅ |
| Micro | 1KA×4+2A×2+2B×(1+1)+1C = 13 | 13 | ✅ |
| `policy_ref` 溯源指针 | 全部指向 P1–P4（G-07a：仅溯源，不参与决策） | ✅ | ✅ |

## 3. 八类 TA-* 解释层测试（3/8 涉及修复后重跑）

| ID | 测试 | 只改动的对象 | 实测结果 | 判定 |
|---|---|---|---|---|
| TA-BASE | 基线 occurrence 表 | — | 40/16/6 全命中 | ✅ |
| TA-POL | 28d/2→3（A 类） | 仅 P2.FrequencySpec | A demands 16→**24**；VisitTargets 逐一相等（域对象零改动） | ✅ |
| TA-GAP | min_gap 10→12 | 仅 P2.CadenceSpec | A EXACT(2) 结构仍可行（枚举验证，非求解） | ✅ |
| TA-RES | 请假 1 天 | 仅 ResourceAvailability.date_profiles | 缺勤日 `is_absent=True, capacity=0`；次日正常 480 | ✅ |
| TA-CAP | 容量压力 | 仅资源声明容量（70min/日，service-time 口径，**未叠加 stop_time**） | admitted=1280 / cap=1400 → **deferred=280（OPTIONAL stretch）+ 四段异常链 R3→DP-STD→defer≤7d→capacity_shortage**；无 INFEASIBLE | ✅ |
| TA-INF | 真结构不可行 | TargetAvailability(仅周二)+P1.CadenceSpec(10) | 4 个周二彼此隔 7d<10 → **PROVEN structurally infeasible**（非静默延期） | ✅ |
| TA-HIST | 历史抵扣 | 仅 ExecutionHistory（上次访问 5 天前） | T002 需求 2→**1**（REQ-A-007 抵扣） | ✅ |
| TA-LOCK | 锁定承诺 | ExistingCommitment 已在 STD 装配 | DAY_LOCKED、日期在 horizon 内 | ✅ |

## 4. 失败用例与治理行为（FC-*）

| ID | 结果 | 治理意义 |
|---|---|---|
| FC-3 缺失参数 | 显式 KeyError（`missing registered parameter`） | 禁止静默默认值 ✅ |
| FC-4 scope 未知属性 | 匹配为零 → 配置错误在装配期暴露 | 禁止隐式吞掉 ✅ |
| 不可解析 exception ref | 显式 KeyError | DCR-SA-001-R 引用完整性 ✅ |

## 5. DecisionTrace Skeleton（已机读落盘）

`validation/phase2/decision_trace_skeleton.json`：
```
requirement_bindings: REQ-A-008→DP-STD (COMPANY_POLICY) · REQ-A-009→DP-SLA (CONTRACT)
occurrence_summary  : {total: 62, required: 40, optional: 16, committed: 6}
exception_audit_trace: [REQ-A-008 → DP-STD → defer≤7d → resource capacity shortage]  ← 四段链 ✅
```

## 6. 执行期发现与处置（诚实记录）

| 发现 | 处置 |
|---|---|
| 首跑 3 项 FAIL（P4 未按规格设 COMMITTED / TA-CAP 容量口径未由资源声明承载 / TA-INF 误用 P1 默认 cadence 5d） | **均为验证套件自身缺陷，非 Domain 缺口**——修正套件后 18/18；契约对象未动一行 |
| 容量评估基于 service-time（travel 属 Phase 3 路由耦合，已按 §2.8 声明） | 与 §2.1 口径一致；stop_time 未叠加（AC-8 守卫逻辑确认） |
| Domain Change Log | **EMPTY**（无任何 Failure Evidence 指向契约缺口） |

## 7. Gate 判定

```
Gate A1 Domain Gate        : PASS（维持；本次执行零 DCR 再确认）
Gate A2 Trace Gate         : PASS（Requirement→Exception Policy→Action→Reason 链机读落盘）
Phase 2 Scenario A         : DOMAIN EXECUTABLE VALIDATION ✅ COMPLETE
下一动作                    : Phase 2 续 — Scenario C spec 复制（A→C→D→E→B）；数学/GT-Micro 仍锁定于 Phase 3
```
