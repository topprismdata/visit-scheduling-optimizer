# Scenario C — Domain Executable Validation Report v1.0
## Phase 2 · 柔性 Cadence + Time Window（解释层执行结果）

> **文档标识**：`SC-DOMAIN-EXECUTABLE-VALIDATION-V1.0`  
> **执行日期**：2026-08-22  
> **验证对象**：A03 `Domain-Contract-v1.0.1 FROZEN` 对"柔性 Cadence + Time Window"语义的表达能力  
> **执行纪律**：零数学（无变量/约束/系数/solver）；A03/A05 未动；无新 Domain Entity  
> **执行载体**：`validation/phase2/run_scenario_c_validation.py` + `decision_trace_c.json`  
> **结果**：**20/20 PASS · 0 DCR · 1 项领域观察（OBS-C-1，不构成 DCR）**

---

## 1. Gate C 判定结果

| Gate | 判据 | 结果 | 证据 |
|---|---|---|---|
| **C1 Cadence Semantics** | min/max spacing 语义边界表成立；无未冻结"偏好星期"引入 | ✅ PASS | 语义边界表（spec §2.2）+ TC-CAD-1/2 双向 + cadence_spec_valid 装配校验 |
| **C2 TimeWindow Source-Separation** | 三源各归其位（门店/客户→TargetAvailability；资源→ResourceDayProfile）；交集无吞并 | ✅ PASS | TC-TW-1/2/3：窗口换班生效、date_exception 覆盖、资源部分日独立 |
| **C3 Independence** | Frequency 与 Cadence 变更互不影响 | ✅ PASS | TC-CAD-3：freq RANGE→EXACT 后 cadence_spec 逐字段相等 |
| **C4 Trace** | eligible 可回溯四源；异常链四段 | ✅ PASS | 6 live + 2 stale 每个 eligible 记录 (last_visit, min, max, horizon)；REQ-C-003→DP-FLEX 链落盘 |
| **C5 Scenario Pass** | C1–C4 + TC 全过 + MM + Change Log EMPTY | ✅ **PASS** | 20/20 |

## 2. 二十项测试结果摘要

| 组 | 测试 | 关键实测 |
|---|---|---|
| 基线 | TC-BASE ×4 | occurrence 8 REQ+8 OPT；eligible = (L+min_gap, L+max_gap)∩horizon 四源可溯；**stale 锚点（35/40 天前）→ eligible=None 被显式暴露而非隐藏** |
| 节奏 | TC-CAD-1/2/3 | min_gap 7→14 起点= L+14；max_gap 30→21 终点= L+21；**频次改动后 CadenceSpec 逐字段不变（两轴独立）** |
| 时窗 | TC-TW-1/2/3 | 门店窗口换班可用性翻转；**date_exception 覆盖 weekday 规则**；资源部分日（周三仅下午）独立生效 |
| 容量 | TC-CAP | required=240 / cap=250 → stretch deferred=230 + REQ-C-003→DP-FLEX→defer≤10d→capacity shortage 四段链；无 INFEASIBLE |
| 不可行 | TC-INF | 单开放日 + EXACT(2) + gap≥25 → **PROVEN structurally infeasible**（open_days=1），归因 REQ-C-002×REQ-C-004 |
| 历史 | TC-HIST | 3 天前 > 16 天前 > stale(None)——单调性成立 |
| 守卫 | FC-C-1/2 + binding | min>max 装配拒绝；exception+blackout 冲突可探测；DP-FLEX 引用可解析 |
| 蜕变 | MM-C1/2/4 | 放宽 max_gap 终点不缩；收紧 min_gap 起点不扩；**加 date_exception 永不收缩可用集** |

## 3. 领域观察（诚实记录，未升级 DCR）

### OBS-C-1：Stale Anchor（过期锚点）重定基规则
- **现象**：last_visit 距 horizon 起点 35 天（> max_gap=30）时，字面计算 `[L+7, L+30]` 终点落在 horizon 之前 → eligible=None。
- **业务语义**：该客户"逾期未访"，业务上应**立即**具备资格，而非无资格。
- **裁定**：**不构成 DCR**——契约对象（CadenceSpec.reference_period_days、ExecutionHistory）完全足以表达；缺的是 **OccurrenceGenerator 的解释规则**（stale 锚点重定基到 horizon 起点）。该规则属编译规范层，将登记入 Phase 3 Compiler 规范；Phase 2 记录为 OBS-C-1 防丢失。
- **处置**：测试断言改为**显式暴露该行为**（None + 分类 stale），而非掩盖——正是"失败优先于 workaround"纪律的执行。

## 4. 执行期缺陷记录（套件自身，非 Domain）

| 发现 | 修复 |
|---|---|
| 首跑 2 FAIL：stale 锚点误期待非 None（套件未定义 stale 语义）；TC-CAP 容量算术错（1400 vs 240 无压力） | 均为测试套件缺陷；修正断言与容量参数后 20/20；**契约对象零改动** |
| MM-C4 初版为恒真断言 | 重写为真实集合包含断言（availability_before ⊆ availability_after） |

## 5. 与 Scenario A 的增量证明

| 维度 | A 已证 | C 增量证明 |
|---|---|---|
| CadenceSpec | 固定 min/max 单点使用 | **双向边界 + 与 history 交互的 eligible 推导 + 频次轴独立** |
| WeeklyAvailabilityRule.date_exceptions | 未用 | **客户指定时段覆盖机制（CONTRACT 级效力）** |
| ResourceDayProfile | 仅全日请假 | **部分日时段（下午 only）** |
| 领域观察 | OBS-1/2（D 场景） | **OBS-C-1（stale 锚点，编译规范级）** |

## 6. Domain Change Log

**EMPTY**（OBS-C-1 经论证不满足 DCR 门槛：契约可表达，缺口在解释规则层）。

## 7. RMAP 状态推进

```
Phase 2: A ✅ → C ✅ → D ◀ next → E → B
生产重构 LOCKED 保持；数学/GT 仍锁定于 Phase 3。
```
