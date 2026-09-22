# Recurring Sales Visit Decision Engine · 架构 v0.4
## 周期销售拜访决策引擎 — 把"月"放回系统中心

> **Document Status**: Draft v0.4 (2026-09-22) — 老板纠偏 + GPT 复核后的收敛版
> **取代**: EXPERIENCE_LAYER_v0.3.md 的产品层(双工作台/Gantt 中心);其 Experience Layer 红线、四级升格、OverrideEvent 定义**继续有效**
> **一句话**: Salesforce Field Service 给我们的启发是"如何治理约束、承诺、人工调整与解释";但产品中心不是日内派单,是**月度周期拜访计划**。周是节奏结构,日是诊断下钻,执行数据服务于下月学习。

---

## 1. 主链(取代 v0.3 的 Task→Gantt→Execution 链)

```
Customer / Contract / Territory
            ↓
        Visit Demand            ← 本月应该拜访什么 (合同→周期拜访义务)
            ↓
    Rhythm / Phase Model        ← Week / Weekday / Interval (合同-节拍-相位)
            ↓
    Monthly Feasible Set        ← Territory Ownership × Calendar Workdays × Capacity Corridor
            ↓
        Commitment              ← 月节奏级锁定 (见 §4)
            ↓
    Optimization Scope          ← 五种 Scope (见 §5)
            ↓
════════ DECISION KERNEL (L1→L2→L3, v0.2 不变) ════════
            ↓
        Monthly Plan
      ┌─────┼─────┐
  Month View  Week View  Rep-Day(诊断单位,非顶层对象)
            ↓
        Execute → Actual Visit Behavior
            ↓
    Experience Learning (月循环, §6)
            ↓
      Decision Memory → Next Month
```

**Event-triggered Reoptimization 降级**为 Rep-Day 层的局部异常能力;核心是
Recurring Demand + Rhythm + Monthly Structure + Experience Learning。

## 2. 核心对象 = VisitDemand(不是 Appointment)

```
VD01: C001 · Week 1 · 合法星期 {Wed}
VD02: C001 · Week 3 · 合法星期 {Wed}
```
优化器解的是"**Week 1 周三跟哪些店一起跑**",不是"9月22日14:00 派单"。
合同-节拍-相位语义由此真正成为系统骨架(coverage_v2 的 σ 锁 = weekday_fixed 承诺的实例)。

## 3. 产品四层(主管心智分配)

| 层 | 回答 | 心智占比 | 已建 |
|---|---|---|---|
| **Monthly Plan** | 这个月整体合理吗?(拜访次数/覆盖工作日/总里程/日均/频次履约/4周节奏/异常日/territory 结构) | **70%** | 全国诊断 66 超载/7 停工/424 无计划 + ZoneDayPolicy 质检 |
| **Weekly Pattern** | 月计划的结构(W1-W4 × Mon-Fri 稳定性) | 15% | 本次新增(月矩阵原型) |
| **Rep-Day** | 为什么 9/17 异常?(诊断单位) | 10% | v0.3 当日调度台 → 降级为 Day Inspector |
| **Optimization/What-if** | 调整能改善多少?(原计划 vs 优化: 里程/异常日/负荷/改动量/星期稳定性/频次履约) | 5% | 帕累托前沿(σ 预算) |

**工作台四件套**: Month Calendar + Team + Map + Insight。Gantt 属 Day Inspector,不是 Supervisor Home。

## 4. Commitment 重解释:月节奏级锁定

```
C001: rep_fixed=T, week_fixed=T, weekday_fixed=T, exact_date_fixed=F, sequence_fixed=F
C002: rep_fixed=T, week_fixed=F, weekday_fixed=F
```
五元 mutability 旗标(assignment/week/weekday/exact_date/sequence)取代单一"时间锁"。
v0.3 的 🔗🕐👤▶✓ 图标映射到这五元。

## 5. OptimizationScope 五档(正式架构)

`MONTH | REP_MONTH | REP_WEEK | REP_DAY | CUSTOMER_CYCLE`
主管日常不重排整月:"张三第三周异常→只重排张三第三周";"某双周客户节奏错→重算该客户后续周期"。

## 6. Experience Layer 月循环(数据已就位)

```
① Optimized Plan ─┐
② Human-adjusted ─┼─→ 三份比较 → 为什么主管总改这里? 为什么销售又不按主管版执行?
③ Actual Behavior ┘                哪些人工调整被证明有效? 哪些只是习惯?
                                            ↓
                        September → Experience Memory → October
```
**现状**: ① vs ② = 45,415 条 OverrideEvent(2026-08 全国计划版本差异,已收割待归因);
② vs  = planned-vs-actual(547 线同日执行率/模板一致度/整片跳过)。月循环的两个比较面**数据已落盘**,缺的只是归因闭环(Agent 追问队列 = awaiting_reason)。

## 7. 命名

Field Decision Engine → **Recurring Sales Visit Decision Engine**(产品名: Sales Visit Planning Intelligence)。Planning 是主语,不是 Dispatching。

## 8. 落地顺序(v0.4)

| 步 | 内容 | 状态 |
|---|---|---|
| V1 | 月工作台原型(Month 矩阵 + Team + Map + Insight;Rep-Day 作下钻) | 本次 |
| V2 | VisitDemand 对象进 L1(合同→周义务生成) | 待 |
| V3 | OptimizationScope 五档接线(先 REP_WEEK) | 待 |
| V4 | OverrideEvent 归因闭环(Agent 追问 → reason 回填 → Preference Model) | 待 |

---

## 9. Experience Bayesian Layer (v0.4 增补, 2026-09-22 老板命题验证)

**命题**(老板): "规划出来的日历没有意义, 只有了解业务实际才有意义。"
**验证结论**: 日历作为命令失效(同日执行中位 42%; 业务调整版被 TOP 销售忽略 1-4% same-day);
但日历作为义务载体不可省略(冷启动先验/合同相位/容量走廊学不出来)。
**形式化**: 日历 = 义务约束下对业代时空节奏的后验投影。系统主产品 = 信念模型, 日历是其投影。

### 形式化 (GPT 研究 + 8月 612 线 prequential 验证)
- 状态 θ_{r,d} = P(zone | rep, weekday); zone = H3 res7 连通块(邻居=同片地, 老板: 网格不严谨→概率表达)
- 更新 α_z ← λ·α_z + x_z; 先验 α0 = 城市级 zone 混合 × a (层次收缩, Oracle personal/company profile 同思想但非公开贝叶斯)
- 论文支撑: Gonzalez 2008 Nature (EPR), Song 2010 Science (visitation entropy), Eagle&Pentland 2006 (Reality Mining), Isaacman 2011 (important places), Liao 2007 (routine learning), Antoniak 1974 (DP); 产品侧 Oracle/Microsoft/ClickSoftware 均无公开贝叶斯 routine learning → 差异化机会
- 验证 (348 线 4624 样本, prequential log-loss): uniform 1.361 / static 3.152 / exp(λ=.7) 0.501 / Dirichlet(λ=.9,a=5) 0.625
  → 在线更新 vs uniform -63%, vs static -76% (强证据); 点预测 exp 最优, Dirichlet 价值 = posterior strength 置信门控
- 架构位置: Monthly Plan → **Experience Bayesian Layer** → Weekly Pattern → Rep-Day → What-if
- 脚本: experiments/validate_bayes_routine.py

---

## 10. 月内适应与跨月投影 — 证伪记录 (2026-09-22)

**命题**(老板 ML framing): "第一周、第二周是训练样本" → 用 W1-W2 拟合的习惯重排剩余周。
**裁决**: 机制对，数据量不足以复现计划。以下为 8月 499-510 线实测，脚本 `experiments/validate_projection.py`。

### 证伪证据
| 对照 | 结果 | 含义 |
|---|---|---|
| 原计划 店→星期 命中率 | **0.776** | 计划的店级星期映射是强信号 |
| W1-W2 片区后验投影 预测星期 | 0.234 | 两周执行无法重建计划的店级知识 |
| 随机 | 0.200 | 投影几乎无信息 |
| 实际访问落在片区 top2 星期 | 0.417 | 片区结构存在但弱 → 只配做战略信号 |
| W3-W4 槽位 Jaccard: 原计划 / 模型重排 / 欠账插入 | 0.475 / 0.233 / 0.223 | **任何月内重排都破坏计划价值** |
| 店级习惯槽位重复率 / 客户群稳定性 | 0.043 / 0.151 | 多数店月访一次 = 月访轮换，店级 routine 非目标 |
| 同日执行 42% vs 星期执行 77.6% | — | 业代跟计划的"星期"结构，差的是"日期/周" |

### 结论修正
- ✅ **最高价值资产 = 计划的店→星期映射 (0.776)**；月内重排必须以保持该结构为硬约束（σ锁/走廊已有），不得重排
- ✅ 执行数据的正确定位: (a) 依从性监控与质检 (b) 欠账/义务簿记 (c) 变点检测 + elicitation（隐约束: 周会日/郊区日） (d) 跨月作为下月计划的**特征与约束**输入
- ⚠️ (d) **未验证** — 需 9 月计划数据；禁止在汇报中主张已验证
- ❌ 不做: 用两周执行重排本月计划
- 教训: 计划的店→星期结构是系统历史 + 业务规则的沉淀；两周观测信息量不足以复现。适应 = 在其约束下移动**日期**，不是移动**店**
