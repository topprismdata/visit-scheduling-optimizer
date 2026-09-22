# PJP 第一代架构技术债地图（代码事实版）

> 代码来源：`~/UFS-demo/pjp-m-dev-month0924-drtm-business-drtm-planner.zip`（2026-09-21 导出，与交给 GPT 的是同一份）
> 清点对象：**300 个 `.java` 文件**，包 `com.topprismcloud.planner`，求解器 `org.optaplanner`，分数类型 `HardMediumSoftLongScore`
> 口径：所有数字由 `grep`/正则**实数统计**得出，命令与模式见文末「复现方式」。本页只报代码事实，不做架构评价。

## 0. 总览：业务知识分散在五层

```
业务需求 → Planning Entity → Constraint → Score → Solver → Planning Result
              ↑4 类              ↑12 个 Provider      ↑3 级分数        ↑16 个搜索层类
              └──────────────── Service 层 86 个文件 / 1239 个 if( ─────────────┘
```

| 层 | 代码事实 | 债务证据 |
|---|---|---|
| Planning Entity | **4 个** `@PlanningEntity`、**4 个** `@PlanningSolution`、**9 个** `@PlanningVariable` | 一个对象承担 4 个生命周期（见 §1） |
| Constraint | **12 个** `ConstraintProvider`、**118 次**具名评分调用、**40 个**去重约束名 | **40 条约束被注释停用**；同一规则最多重复 **10 次**（见 §2） |
| Score | `ONE_HARD` 49 / `ONE_MEDIUM` 24 / `ONE_SOFT` 43 | 三类知识全部压进 hard/medium/soft，无类型系统（见 §3） |
| Move / Filter | **16 个**搜索层类 | 业务资格判断写在 Filter 里（见 §4） |
| Service | **86 个** service 文件、**1239 个** `if (`、34 处注释含"不能/禁止/必须"、56 处 TODO/FIXME | 业务规则散落在流程代码与注释里（见 §5） |
| **经验 / 学习** | **0 个** | 全仓无 Experience/Learning/Bayes/Posterior/Dirichlet/Probab 类或字段（见 §6） |

## 1. Entity 层：一个对象，四个生命周期（代码命中）

`@PlanningEntity` 四个：`Customer`、`Visit`、`AreaDayCustomer`、`CustomerAssignment`。
`@PlanningSolution` 四个：`EqualValueSplitSolution`、`SalesRoutingSolution`、`AreaDaySolution`、`CustomerDateSolution`。

最典型的是 `CustomerAssignment`（`split2606/domain/CustomerAssignment.java`）：

| 生命周期 | 字段 | 性质 |
|---|---|---|
| 业务事实 | `customer`、`areaCode`、`location`、`customerId` | 客户是谁、在哪 |
| 规划变量 | `assignedDate`（`@PlanningVariable(valueRangeProviderRefs = "dateBinRange")`） | 排到哪一天 |
| 执行状态 | `visitIndex`（拜访序号，从 0 开始） | 跑的时候第几家 |
| 评分影响 | `priority`（0=核心攻坚 `serviceFrequency=0.5`、1=AB 类 0.25、2=CDNA） | 直接进分数 |

→ 业务需求/规划变量/执行结果/评分权重**同一个对象**。要新增「销售星期习惯」「执行反馈」这类概念时，代码里没有自然落点，只能再塞一个字段或再写一个 Constraint。

## 2. Constraint 层：规则重复 + 大面积停用

**12 个 Provider / 118 次具名评分调用 / 40 个不同约束名**：

| Provider | 约束数 | | Provider | 约束数 |
|---|---|---|---|---|
| SplitDateConstraintProvider | 12 | | SplitDayConstraintProvider | 10 |
| DivideWeekConstraintProvider | 12 | | AreaDayIntervalConstraintProvider | 10 |
| SplitWeekConstraintProvider | 11 | | MonthSplitConstraintProvider | 9 |
| SalesRoutingConstraintProvider | 11 | | WeekSplitConstraintProvider | 9 |
| EqualValueSplitConstraintProvider | 10 | | EstimateSplitWeekConstraintProvider | 9 |
| EstimateSplitDayConstraintProvider | 10 | | CustomerDateConstraintProvider | 5 |

**同一个业务规则被反复实现（出现次数）**：`visitInterval` **10**、`validateShape` 8、`noBlockGroup` 8、`blockValueTotalM` 8、`totalDistance` 8、`optimizeShape` 8、`calcDistanceByCenter` 8、`silhouetteScore` 8、`lonePoint` 7、`unplannedBlocks` 3、`firstVisitInterval` 3。

→ 改一次「拜访间隔」语义要在最多 10 个文件里同步改，且这 10 处实现**各自带自己的权重常量**。

**被注释停用的约束：40 条**（占全部评分的三分之一）。典型：
```
SplitDateConstraintProvider:    // silhouetteScore(factory)
AreaDayIntervalConstraintProvider: // dailyCapacity(factory)  // areaIsolation(factory)  // workloadBalance(factory)
DivideWeekConstraintProvider:   // emptyVehicle(factory)  // unplannedVisits(factory)
                                // distanceFromLastCustomerToDepot(factory)  // firstVisitInterval(factory)
SalesRoutingConstraintProvider: // emptyVehicle(factory)  // unplannedVisits(factory)
                                // distanceFromLastCustomerToDepot(factory)  // unplannedCustomVisits(factory)
```
注释里的 34 处「不能/禁止/必须」进一步说明：业务规则的真实形态常被写在注释里（`ChangeBlockFilter` 4 处、`SplitMonthChangeBlockFilter` 4 处、`VisitRoutingSplitByAreaServiceImpl` 8 处）。

## 3. Score 层：三类知识压进三级分数

- 分数级别用量：`ONE_HARD` **49**、`ONE_MEDIUM` **24**、`ONE_SOFT` **43**。
- 事实约束（合同频次/必须拜访/同日重复）与优化目标（距离/均衡/形状）**都在同一套 hard/medium/soft 里**，靠人工选级别 + 手调系数区分。
- 权重是手写表达式，例如 `DivideWeekConstraintProvider.vehicleCapacity`：
  `penalizeLong("must visit avg balanceValue", HardMediumSoftLongScore.ONE_HARD, … (sum - avg)² × 200)` —— 硬约束 + 平方惩罚 + 魔法数 200。
- 约束命名没有统一语义体系，三种风格混用：
  - 驼峰英文：`visitInterval`、`noBlockGroup`
  - 伪英文短语：`total avg`、`must visit avg balanceValue`、`visit per week`
  - 中文：`同一个客户不能在同一天安排多次拜访`、`超出每日最大拜访数`、`地理位置聚集`、`工作量不均衡`、`拜访间隔不满足要求`

→ 代码里**没有「这是事实约束 / 这是优化目标 / 这是经验偏好」的显式表达**；新增需求的第一反应永远是「加个 Constraint，给它一个分数和权重」。

## 4. Move / Filter 层：业务资格混入搜索层

**16 个**搜索层类（Filter / Move / Selector / Comparator / WeightFactory / VariableListener）。其中承担业务资格判断的：

| 类 | 它挡掉的业务条件 |
|---|---|
| `ChangeBlockFilter` | 同一 `Customer.code` 在目标车次已有 → 拒绝；**「访问频率大于 1 的店，不能安排在同一天」**；同文件另有 4 处注释掉的硬约束（凸包/跨组/就近） |
| `SplitMonthChangeBlockFilter` | `accept()` **直接 `return true`**；原来的就近约束整段被注释 |
| `ChangeOutletsFilter` | 同一 `outlets.code` 不能排在同一周；`isMustVisit()` 时按 `limits` 内车次计数并放行 |
| `ChangeOutletsNewFilter` | 与上者核心规则重复（排重 + `isMustVisit` 计数 + 上限） |
| `BlockMoveFilter` | `return false` —— SwapMove 被整体关闭 |

→ 「谁能服务谁、哪些不能动」这些业务资格，写在**求解器的 Move/Filter**里。

## 5. Service 层：业务规则散落在流程代码

- **86 个** service 文件（接口 + Impl）。
- **`if (` 精确 1239 处**，最集中：

| 文件 | if 数 |
|---|---|
| `product/service/impl/RegionalCustomersHandlerServiceImpl.java` | **260** |
| `product/service/impl/ArrangeWorkPlanServiceImpl.java` | **174** |
| `split2606/service/impl/VisitRoutingSplitByAreaServiceImpl.java` | **133** |
| `visit/service/impl/VisitTaskV1ServiceImpl.java` | 79 |
| `visit/service/impl/VisitTaskV2ServiceImpl.java` | 77 |
| `visit/service/impl/VisitTaskServiceImpl.java` | 70 |

- 版本并存：`VisitTaskService` / `VisitTaskV1Service` / `VisitTaskV2Service`；`SplitWeekService`（split）与 `VisitRoutingSplitWeekService`（split2512）同期存在。
- 全仓 `TODO/FIXME/XXX` **56 处**（`RegionalCustomersHandlerServiceImpl` 12 处最多）。

→ 没有任何一处能回答「PJP 认为一次合理拜访是什么」；这个定义分散在 1239 个分支里。

## 6. 经验 / 学习层：不存在（关键一页）

检索类名与字段名中的 `Experience` / `Learning` / `Bayes` / `Posterior` / `Dirichlet` / `Probab` / `Frequency`：

**结果：0 个**。唯一命中 `Frequency` 的是 `PlannerConfigFrequency`（MyBatis-Plus 字典表 `@ApiModel("已覆盖客户类型拜访频次数据表")`），是**配置**，不是模型；`Probability` 只出现在 `KMeansPlusPlusClusterer` 的注释里。

→ 「销售在星期几跑哪片」这类知识，代码里只能表达成一个约束 + 一个 `+100` 之类的分数，无法表达 $P(\text{zone} \mid \text{salesperson}, \text{weekday})$，也没有 9 月经验 → 10 月先验的机制。

## 7. 与实测数据的交叉印证（我方独立证据）

| 债务 | 代码事实 | 8 月实测证据 |
|---|---|---|
| 债3 三类知识混层 | 事实/目标/偏好全在 hard/medium/soft | 计划的「店→星期」结构命中率 **0.776**，属事实约束/可行域；两周执行推出的片区后验只有 **0.234** → 事实约束不能由优化目标替代 |
| 债3 缺经验层 | 0 个学习/概率类 | 义务合规率 **0.661**、相位合规率 **0.587**；欠访 **71% 直接丢弃**、恢复中 **71% 换星期** → 经验是概率性的，必须单独建模 |
| 债4 无法动态适应 | 无 Experience Model | 贝叶斯在线更新 vs 均匀：log-loss **-63%**（348 线 4624 样本） |
| 债2 规则维护 | 同一规则重复最多 10 次 + 40 条被注释 | 规则一多就靠人工权衡；我们的合规 KPI 可替代「权重调参」做验收 |

## 8. 复现方式

```bash
# 解包
unzip -q ~/UFS-demo/pjp-m-dev-month0924-drtm-business-drtm-planner.zip -d /tmp/pjpsrc
# 关键统计（在 /tmp/pjpsrc 下）
find . -name "*.java" | wc -l                                  # 300
grep -rl "ConstraintProvider" --include=*.java . | wc -l        # 12
grep -rhoE '(penalize|reward)[A-Za-z]*\(\s*"[^"]{0,60}"' --include=*.java . | wc -l   # 118
grep -rhoE '//\s*\w+\(factory\)' --include=*.java . | wc -l     # 40 被注释停用
grep -rc "if (" --include=*ServiceImpl.java . | awk -F: '{s+=$2} END{print s}'      # 1239 (service 层)
grep -rlE "@PlanningEntity|@PlanningSolution" --include=*.java . | wc -l            # 8
```
---

## ⚠️ §7 数字更正（2026-09-22 晚）

§7 表格中的实测数字基于错误计划版本（调整版），正确版本为《更新后的8月规划》：

| 指标 | 错误值(调整版) | **正确值(更新后)** |
|---|---|---|
| 计划 店→星期 命中率 | 0.776 | **0.901** |
| 两周后验投影 命中率 | 0.234 | 0.239（不变） |
| 义务合规率 均值/中位 | 0.661 / 0.697 | **0.715 / 0.823** |
| 相位合规率 均值/中位 | 0.587 / 0.599 | **0.682 / 0.805** |
| 严格同日执行 中位 | 46.7% | **77.5%** |
| 门店覆盖 中位 | 69.7% | **82.6%** |
| W1 未执行店 / 月内丢弃 | 15,055 / 71% | **9,354 / 79%** |

债务结论**不变且更强**：事实约束（可行域）不能由优化目标替代（0.901 vs 0.239）；经验层缺失（0 个类）；业代不追欠账（79%）。
