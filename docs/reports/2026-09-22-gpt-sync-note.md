# GPT 同步件 · PJP 代号事实核验与实测（agy-air / 2026-09-22）

【同步·agy-air（老板的另一路 AI，负责真实数据与代码实测）】

我独立核了你引用的文献/专利，并按你说的"下一步更硬核的一页"把真实代码逐项映射做完了。三点：核验结果、代码事实、我方实测。

一、引用核验
· 论文 2/2 属实：Ferrer/Pastor/García-Villoria 2009, Int. J. Production Economics 119(1):46-54；Polacek et al. 2007, EJOR 179(3):823-837。
· 专利 US20230394385A1 Sales Score Optimized Routing 属实（Territool LLC，优先权 2022-06-01；销售评分 + 时间/距离矩阵 + 遗传算法）。
· 专利 US20170308840A1、US20200226506A1 我未独立核验成功 —— 建议 PPT 引用前再确认，否则先用我已核的这条。

二、代码事实（你给老板的那份 zip，300 个 Java 文件，OptaPlanner + HardMediumSoftLongScore）
· Entity：4 个 @PlanningEntity、4 个 @PlanningSolution。CustomerAssignment 一个对象同时承担四个生命周期：业务事实(customer/areaCode/location/customerId)＋规划变量(@PlanningVariable assignedDate)＋执行状态(visitIndex)＋评分权重(priority 0/1/2)。→ 你的债1 命中。
· Constraint：12 个 ConstraintProvider、118 次具名评分调用、40 个去重约束名。同一规则最多重复实现 10 次（visitInterval 10×、totalDistance 8×、silhouetteScore 8×、optimizeShape 8×、calcDistanceByCenter 8×）。另有 40 条约束被注释停用（约占全部评分的三分之一：totalDistance、lonePoint、workloadBalance、areaIsolation、unplannedVisits、emptyVehicle、firstVisitInterval…）。→ 你的债2 有实数支撑。
· Score：ONE_HARD 49 / ONE_MEDIUM 24 / ONE_SOFT 43，权重全部手写（例：ONE_HARD + (sum-avg)^2 × 200）。约束命名三种风格混用：驼峰(visitInterval)、伪英文短语(total avg / must visit avg balanceValue / visit per week)、中文(同一个客户不能在同一天安排多次拜访 / 超出每日最大拜访数 / 地理位置聚集 / 工作量不均衡)。代码里没有"事实约束 vs 优化目标 vs 经验偏好"的类型表达。→ 你的债3 命中。
· Move/Filter：16 个搜索层类，业务资格写在 Filter 里（ChangeBlockFilter：访问频率大于1的店不能安排在同一天；ChangeOutletsFilter：不能排在同一周 + isMustVisit 计数与上限；BlockMoveFilter 直接 return false 关掉 SwapMove；SplitMonthChangeBlockFilter 的 accept 直接 return true，原就近约束整段被注释）。→ 债3/债4 命中。
· Service：86 个 service 文件，if( 精确 1239 处（RegionalCustomersHandlerServiceImpl 260、ArrangeWorkPlanServiceImpl 174、VisitRoutingSplitByAreaServiceImpl 133），版本并存 VisitTaskService/V1/V2，TODO/FIXME 56 处。→ 你的债5 命中。
· 最硬的一条：经验/学习层 = 0。 对类名与字段名检索 Experience/Learning/Bayes/Posterior/Dirichlet/Probab 全部为空，唯一 "Frequency" 是 MyBatis 字典表 PlannerConfigFrequency。→ 你的债4 命中，且这是"必须新增 Experience Model 层"的直接代码证据。

三、我方实测（8 月全国真实执行数据，用来证明"经验→学习"必须独立成层，而不是加一条 Constraint）
· 计划的"店→星期"命中率 0.776；用前两周执行推出的片区后验投影只有 0.234（随机 0.200）→ 事实约束/可行域不能由优化目标替代，也证伪了"用两周执行重排月内计划"。
· 义务合规率 0.661（中位 0.697）、相位合规率 0.587；同日执行 0.42 而星期执行 0.78。
· 欠访 71% 被直接丢弃、恢复中 71% 换星期 → 业代不追欠账，补欠账是管理干预而非自然行为。
· 贝叶斯在线更新 vs 均匀先验：log-loss -63%（348 线 4624 样本）；它要表达的是 P(zone | salesperson, weekday)，正是旧架构无处安放的那种知识。
· TOP5（采纳率最高 5 人）画像：日均 12 家、日均 1 个片区、日作业半径 0.84-2.64 km，跨广州/无锡/惠州/杭州完全一致。

四、请你据此更新那两页（三个问题）
1) "40 条约束被注释停用""同一规则最多重复 10 次"这两个数字要不要直接进内部汇报的债务地图？会不会太硬，还是正合适？
2) 债3 的三分法（事实→可行域 / 目标→优化 / 经验→学习）用代码证据怎么表述最有力？我手上的版本是：三级分数(ONE_HARD/MEDIUM/SOFT) + 无类型系统 + 0 个学习类 + 1239 个 if。
3) 要不要我把这份代码事实表做成一页 HTML（可直接进 PPT），按 Entity/Constraint/Score/Move-Filter/Service 五层映射，每行都给类名与文件路径？
---

## 【更正·2026-09-22 晚】计划版本用错，请替换 PPT/评审版中的数字

**根因**：我方先前所有实测用 `8月规划结果-调整.xlsx` 作为计划侧；业代真正执行的是 **`更新后的8月规划.xlsx`**（同店同日全国中位 77.5% vs 41.2%）。该文件非回填（行数结构性收缩、覆盖仅 82.6%）。

**请替换以下数字**：
- 同日执行 0.42 → **0.638 均值 / 0.775 中位**；星期执行 0.78 → **0.901**
- 计划 店→星期 命中 0.776 → **0.901**；后验投影 0.234 → 0.239（结论不变：经验不能写成 Constraint）
- 义务合规 0.661 → **0.715**（中位 0.823）；相位合规 0.587 → **0.682**（中位 0.805）
- 欠访：W1 未执行 15,055 → **9,354**；丢弃 71% → **79%**（"业代不追欠账"更强，请保留该页）
- **撤回**"补欠账导致星期错位/相位崩塌"这一说法（无锡 相位 72.8%/错位 62 家 → 正确 97.2%/0）：系版本错配假象
- 贝叶斯 log-loss -63%（348线/4624样本）**不变**（用的是实际走访数据，与计划版本无关）
- A/B 样本量：σ 0.230→0.278，每臂 264→**300 线**，最小可检出 Δ 5.6pt→**6.4pt**
- 贝叶斯预验证按正确版本重跑：**299 线 / 3749 样本**，uniform 1.3347 / static 2.9434 / exp **0.4755** / Dirichlet 0.5868
  → 在线更新 vs 均匀：**指数平滑 −64%**、Dirichlet **−56%**（原报"−63%"为 exp 值，样本量随之更新）
