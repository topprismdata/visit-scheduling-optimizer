# SRP 4.1 · Experience Layer 与双工作台设计
## 从"算出计划"到"计划作为运行状态"

> **Document Status**: Draft v0.3 (2026-09-21)
> **基座**: THREE_LAYER_ARCHITECTURE_v0.2.md — L1/L2/L3 定义不变，本文在其上加层
> **来源**: GPT 交叉研究(Salesforce/ClickSoftware US20200210936A1 · Microsoft US11734066/US11218558B2 · Oracle Activity-Duration + WO2024081106A1，老板已裁定采纳) + 2026-09-21 全国 547 线 H3 格级实证(模板定律 r=0.82)
> **一句话**: 月度计划算得再好，价值在"下发→执行"之间漏光了——本文补上 Planning 与 Operations 之间缺失的产品层和数据层。

---

## 1. Why：实证依据(2026-08 全国)

| 事实 | 数字 |
|---|---|
| 同日执行率中位(计划日=实际日) | **42%** —— 计划过半不被按日执行 |
| 星期几×片区模板一致度 → 同日执行 | **r=0.82**(一致≥75%→执行 94%，<40%→29%) |
| 模板强度(业代自建 星期几→res7格 分布 HHI) | 中位 0.65(区县口径 0.86 是尺子错觉) |
| 超载型线(片区≥12 且 ≥15% 店整片被弃) | 64 线 / 4,229 家店(地盘直径最大 267km) |
| 停工型线 | 12 线 / 1,225 店访压在身后 |
| 有打卡无计划的线 | **424 条**(占实际出勤线 43%) |

结论：**计划系统缺的不是优化器(L2/L3 已把计划排到习惯结构内近最优)，缺的是"读懂执行、解释决策、承接修改"的产品层。**

---

## 2. 架构位置：Experience Layer

```
L1 Semantic Compiler      业务不变量 · 审批链 · 零例外闸     ← BUSINESS_INVARIANT
L2 Mathematical Compiler  VisitPlanningInstance · SourceMap · MathValidator
L3 Solver Backend         MathProblem → Solution(只报数学事实)
──────────────────────────────────────────────────────────
Experience Layer  (新)    预测 · 偏好 · 风险 · 排序 · 建议    ← LEARNED_PREFERENCE(软)
──────────────────────────────────────────────────────────
Orchestrator / Decision Kernel   建议呈现 · 升级裁决(Escalation) · 留账
Execution              ExecutionState + Event Stream(非静态表)
Decision Memory        DecisionEpisode + OverrideEvent + planned-vs-actual
          ↺ Experience Learning(升格机制 §3)
```

**架构红线**：Experience Layer 只影响预测/偏好/排序/建议，**不得修改 Hard Feasibility、不得自行生成约束**。任何"经验"要变成硬规则，必须走 L1 授权通道(ExceptionGrant/Policy 审批)。这是 v0.2 中心命题"L3 无权决定 17 能不能变 16"的镜像：**经验无权决定什么是可行**。

接口约定：Experience Layer 的输入 = DecisionEpisode + OverrideEvent + 执行事件流；输出 = 带 confidence 的建议分，经 Orchestrator 呈现给人，人决定采纳(采纳本身又是 OverrideEvent)。

---

## 3. 四级经验升格机制

```
LEVEL 0  Observation        观察事实(打卡、改单、planned-vs-actual 差异)
LEVEL 1  Hypothesis         经验假设("周五下午城北效率低")
LEVEL 2  Learned Preference 统计支持(support=312, Fri-PM North 51% vs 其他 83%, conf=HIGH)
LEVEL 3  Approved Policy    业务确认原因后 → soft preference / guarded policy
                            ("周五下午批发市场在进货"→ Avoid North wholesale Fri 14-17)
```

类型定义(visit_math_api 扩展)：

```python
@dataclass(frozen=True)
class LearnedPreference:
    pref_id: str
    scope: str                    # "rep|city|channel×area|global"
    subject_id: str               # 如 sales_line_code
    statement: str                # "wd3→cell_G1371 (support 78%)"
    support: int                  # 样本数
    confidence: float             # [0,1]
    status: str                   # OBSERVED|HYPOTHESIS|LEARNED|APPROVED_SOFT|APPROVED_HARD
    evidence_refs: tuple          # DecisionEpisode / OverrideEvent ids
    drift_watch: bool
```

**禁令**：L0/L1 直接写进 ALNS 约束。GPT 点名的模仿陷阱——主管 85% 删远店，可能是"知道老板下午不在"，也可能是嫌懒/坐标错/KPI 歪。**HumanChoice 必须与 Outcome 双证据**才允许升 L2。(活例：342 业代整片弃守芜湖县 39 店——选择是事实，结果丢了覆盖，模仿即学错。)

---

## 4. 起步四模型(不做 RL)

| 模型 | 回答 | 数据 | 师承 |
|---|---|---|---|
| **A. Preference** | 专家通常怎么选? | OverrideEvent 流 | ClickSoftware US20200210936A1(Historical Assignment DB) |
| **B. Execution** | 实际会发生什么? E[时长]/P[成功]/E[路程] | 打卡事件+主数据坐标 | Oracle 个人/公司双层 duration + **层级回退**(店×销售→片区×渠道→全国→默认，shrinkage) |
| **C. Consequence** | 这么改，后面发生什么? | 计划+事件流 | Oracle WO2024081106A1(下游影响预测，非"谁适合"而是"连锁后果") |
| **D. Drift/Confidence** | 这条经验还可靠吗? | 滚动窗口评估 | Microsoft US11734066(online/offline evaluator + retrain 触发) |

数据治理前置(§9)不满足的字段，模型宁可不上：打卡时间/GPS 当前不可信 → Execution 模型 v0 只用 **日期×店集合 + 主数据坐标**。

---

## 5. OverrideEvent：人工修改是一级事件

每次人改计划，不止存 before/after，存完整决策现场：

```python
@dataclass(frozen=True)
class OverrideEvent:
    event_id: str
    ts: str
    actor: str                       # 主管/业代/系统管理员
    decision_context: dict           # line, date, candidate_set, 当时系统方案指纹
    system_choice: str
    human_choice: str
    changed: dict                    # {customer?, date?, sequence?, rep?}
    reason_code: str                 # customer_preference|local_knowledge|relationship|
                                     # traffic|store_closed|manager_request|personal_preference|
                                     # data_suspect|other   ← 可不填
    free_text: str = ""
    execution_outcome: str = ""      # 事后回填(该改动最终执行了吗/效果)
```

- reason **不强制**(强制会烦死业务)，但高价值 override(如动 A 级店)系统追问一句："为什么调整？以后遇到类似情况可以帮你自动处理。"——这是 Agent 最该出现的位置。
- 存量第一批真实数据已就位：芜湖三线手工版 = 系统版的 OverrideEvent(删 2 店 + 17 家"核心攻坚"降级为 C/B/D)——**reason 大概率是 local_knowledge 或 data_suspect，值得回访**。
- **planned-vs-actual 是自动 Observation 入口**：地图同画计划(虚线)与实际(实线)，"连续三次把 B/C 顺序反过来"自动成为 L0 观察(support=17)，进升格流水线。

---

## 6. Experience Memory 五分层(可信度显式化)

```
Fact                事实(这家店 8-14 被访问过)
Observed Pattern    观察规律(该销售周三从不去无为)
Learned Preference  统计偏好(support/confidence)
Prediction          预测(周五下午去无为成功率 51%)
Business Policy     已批准规则(soft/hard 分级)
```

UI 与 API 必须带上这一层标签——与 SSI 的 "Detection ≠ Repair ≠ Truth" 同一哲学：**Observed Behavior ≠ Good Practice ≠ Business Rule**。

---

## 7. 双工作台产品架构

### Planning Workspace —"下个月应该怎么排?"
月历 · Territory · Pareto 前沿 · ALNS/CG/CP-SAT · 出厂质检(§8 模板一致度)

### Operations Workspace —"今天现实变了，现在怎么办?"(当日调度台)

```
┌──────────────┬──────────────────────────┬─────────┐
│ 待处理任务池  │   当日时间轴 (FMCG 化)     │  地图    │
│ ⚠急单 C018   │ 张三 27店/32上限 6.8h 68km │ 计划虚线 │
│ □ C126       │ [A]─5km→[B]─1km→[C]⚠42min │ 实际实线 │
│ 未排3 风险2   │      →[D🔒]→[E]           │ 状态着色 │
├──────────────┴──────────────────────────┴─────────
│ Decision Assistant: 张三14:10后迟到27min          │
│ 建议: E移李四16:00, -18km, 不违反合同与承诺          │
│ [为什么?] [替代方案] [接受] [保持原计划]             │
└────────────────────────────────────────────────────┘
```

六条从 Salesforce 继承并 FMCG 化的设计律：
1. **三视图 = 同一 Decision State 的三个投影**(Time/Task/Space)，绝不做三份数据
2. **拖动 = 一次决策请求**：过 L1 校验链(Eligibility/Contract/Rhythm/Capacity/Commitment)→ PASS/FAIL 带原因，不是改数据库字段
3. **Commitment 分级可视**：`A`普通 / `A🔗`今日必须但时间可调 / `A🕐`时间已确认 / `A👤`人已确认 / `A🔒`全冻结 / `A▶`已出发 / `A✓`完成 —— 背后是 `(assignment/date/time/sequence/droppable)_mutable` 五元组
4. **异常长在时间轴上**(⚠+影响+可行动作+系统建议)，不做独立"异常报表"
5. **拜访块 + 行驶线段**：两店之间那条线本身就是规划质量；capacity 用 店数/工时/公里 三元组，不照抄 utilization%
6. **ExecutionState + Event Stream**：计划是随事件演进的状态(完成/取消/延迟/急单)，不是 09:00 算完的静态表

**超越 Salesforce 的差异点**：ConstraintTrace"为什么"做到店级——"为什么今天/为什么周三/为什么张三/为什么14:10/什么不能改/还有什么方案"六问全可答(第二道棱镜的产品表达)。

---

## 8. ZoneDayPolicy：第一个生产级 Learned Preference

- **定义**：每销售的 星期几→H3 res7 格 分布(从实际打卡学，粒度已数据校准：res8 太碎 HHI 0.15，区县太粗产生 0.86 错觉，res7=0.65 是真实模板尺度)
- **证据**(2026-09-21, 547 线)：一致≥75%→同日执行 94% / 一致<40%→29%；r=0.82；一致→覆盖 r=0.55
- **三用途**：① 计划出厂质检(预测执行率) ② L3 软偏好(change_count 按模板距离加权) ③ 诊断基线(超载/停工分型)
- **一禁**：不得作为硬约束下发(除非该线业务确认升格)

---

## 9. 数据治理前置(GeoGov 依赖声明)

1. 打卡**时间/顺序/GPS 不可作证据**(342 教训：68%"坐标错位"实为 GPS 噪声；规划坐标与主数据一致)——duration/travel 模型待可靠采集后启用
2. 当前可用证据 = 日期×店集合 + 客户主数据坐标
3. 424 条无计划线身份核查(新人/非规划岗/计划版本差)——决定全国合规率分母，也决定 Preference 模型样本边界
4. 官方"是否在规划内"flag 与计划文件矛盾(芜湖三线 0% vs 手算 23-24%)——flag 参照版本必须查明，否则 KPI 系统性高估

---

## 10. 落地路线

| 步 | 内容 | 依赖 |
|---|---|---|
| S1 | ZoneDayPolicy 学习管线 + 模板一致度质检器(全国 547 线数据现成) → `orchestration/experience/` | 无 |
| S2 | OverrideEvent schema + Decision Memory 落账(扩展 DecisionEpisode) + 全国诊断例行(超载/停工/无计划线三名单) | S1 |
| S3 | Operations Workspace 原型(芜湖三线素材；342 planned-vs-actual 为演示高潮) | S2 |
| S4 | Preference/Execution 模型 v0(层级 shrinkage)；Drift 监控上线 | S2 |
| S5 | Consequence 模型(需时长/轨迹数据可靠采集) | §9-1 |

## 11. 开放问题(待拍板)

1. 经验升格为 Policy 的确认权限在哪级(区域经理 vs 总部)——与 v0.2 §11 授权矩阵同源
2. 17 家"核心攻坚"被手工降级：是业务真知还是消解考核？回访后决定该 OverrideEvent 的 reason 归档
3. 424 无计划线的处置：补计划 or 承认"计划外常态"并设拓客容量科目
