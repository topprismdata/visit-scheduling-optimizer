# A02: 跨厂商概念横向映射与三层解耦对齐表 (v6.0)
## Cross-Vendor Concept Crosswalk & Three-Layer Decoupled Normalization Matrix (v6.1.1 Cleanup)

> **文档标识**：`A02-VENDOR-CONCEPT-CROSSWALK-V6.1.1`  
> **所属资产组**：TopPrism 销售拜访决策智能事实源基准库  
> **版本状态**：`Evidence-Baseline-v1.0`（长期维护证据基线：最后核验日期 2026-08-22，下次复审日期 2026-11-22）  
> **分表硬规则（Three Separate Crosswalks）**：  
> **严禁在一张大表中混合业务实体、排程工作流与底层求解技术！**  
> 拆分为三大独立矩阵：**表 1 业务本体对齐**、**表 2 规划工作流对齐**、**表 3 技术能力对齐**。每一个条目均附带 `source_id` 一手来源句柄与权威原厂词条。

---

## 目录
1. [表 1：业务本体横向对齐表（Business Ontology Crosswalk）](#1-表-1业务本体横向对齐表business-ontology-crosswalk)
2. [表 2：规划工作流与运营策略横向对齐表（Planning Workflow Crosswalk）](#2-表-2规划工作流与运营策略横向对齐表planning-workflow-crosswalk)
3. [表 3：技术与优化能力横向对齐表（Technical Capability Crosswalk）](#3-表-3技术与优化能力横向对齐表technical-capability-crosswalk)

---

# 1. 表 1：业务本体横向对齐表（Business Ontology Crosswalk）

回答：“现实商业世界中存在哪些核心业务对象与规则？”（纯业务语义，零数学公式与求解器名）

| TopPrism 归一化业务概念 | **Salesforce** (Maps/CG) | **SAP** (Dynamic Visit Planning) | **Microsoft** (Dynamics 365 URS) | **PTV Group** (xTour/xCluster) | **Nomadia / BeatRoute** | 晋升依据与一手证据句柄 |
|---|---|---|---|---|---|---|
| **`VisitTarget`**<br>(被访门店/物理终端) | `Routable Object`<br>(Account/Store) | `Account` / `Customer`<br>(门店主数据) | `Service Location`<br>(服务地点) | `Location`<br>(VisitOrder 物理发生点) | `Retail Outlet` / `Place`<br>(终端门店) | `SRC-SF-MAPS-01`<br>`SRC-PTV-XTOUR-01`<br>(全厂商支持实体) |
| **`SalesResource`**<br>(销售人员/执行主体) | `Assigned User`<br>(业务员/跟线员) | `Sales Representative`<br>(区域销售代表) | `Bookable Resource`<br>(可预订业务人员) | `Vehicle / Field Rep`<br>(外勤执行资源) | `Field Rep` / `Agent`<br>(巡店销售员) | `SRC-MSFT-URS-01`<br>`SRC-SAP-DVP-01`<br>(全厂商支持实体) |
| **`StartEndPolicy`**<br>(起终点策略: 车场/住址) | `Start/End Location`<br>(Office or Home) | `Base Location`<br>(车场/代表驻地) | `Start/End Location`<br>(Resource Address/Org) | `Depot / Home Location`<br>(支持员工住家出发) | `Base Depot / Home`<br>(车场或住家起止) | `SRC-PTV-XTOUR-01`<br>`SRC-MSFT-URS-01`<br>(多厂商支持) |
| **`VisitPolicy`**<br>(常态渠道覆盖政策模板) | `Visit Plan`<br>(Data Sets 模板) | `Visit Plan`<br>(基于 Sales Area 维护) | `Recurrence Pattern`<br>(常态复发规则) | `Multi-Week Template`<br>(多周巡回模板) | `Beat Schedule`<br>(周期巡店基准表) | `SRC-SF-MAPS-01`<br>`SRC-SAP-DVP-01`<br>`SRC-PTV-XCLUSTER-01` |
| **`VisitDemand`**<br>(拜访需求: 包含动因与履约级别) | `Visit Requirement`<br>(包含频次与时间窗口) | `Visit Plan Item / Recommendation`<br>(覆盖项或商机推荐项) | `Resource Requirement`<br>(业务硬性需求) | `Required VisitOrder`<br>(服务订单需求) | `Beat Visit / Opportunity`<br>(巡店或机会需求) | `SRC-SF-MAPS-02`<br>`SRC-SAP-DVP-01`<br>`SRC-PTV-XTOUR-01` |
| **`FrequencySpec`**<br>(周期频次与参考时段) | `Target Frequency`<br>(周期规定频次) | `Frequency Cycle`<br>(周期循环定义) | `Recurrence Rule`<br>(复发规则) | `Visits per Order`<br>(订单规定拜访数) | `Call Frequency`<br>(拜访频次) | `SRC-SF-MAPS-02`<br>`SRC-SAP-DVP-01`<br>`SRC-PTV-XCLUSTER-01` |
| **`CadenceSpec`**<br>(周期节奏与间隔跨度) | `Min/Max Days Between`<br>(最小/最大间隔天数) | `Visits per Frequency Cycle`<br>(周期内发生周次) | `Recurrence Interval`<br>(复发间隔天数) | `Week Rhythm / Patterns`<br>(周次节奏与星期组合) | `Visit Spacing`<br>(拜访间隔控制) | `SRC-SF-MAPS-02`<br>`SRC-PTV-XCLUSTER-01`<br>(Rothenbächer 2019) |
| **`TargetAvailability`**<br>(门店营业与可服务时段) | `Visit Window`<br>(可拜访时段) | `Visiting Days / Slots`<br>(可服务星期与时段) | `Time Window Start/End`<br>(客户时间窗口) | `Operating Hours / Slots`<br>(门店开放时段) | `Store Open Window`<br>(店长在店时段) | `SRC-SF-MAPS-02`<br>`SRC-NOMADIA-01`<br>`SRC-MSFT-URS-01` |
| **`Territory`**<br>(销售辖区/商业网格) | `Enterprise Territory`<br>(企业辖区) | `Sales Area`<br>(销售片区) | `Service Territory`<br>(服务区域) | `xTerritory`<br>(上游独立区域规划) | `Beat / Sector`<br>(销售网格) | `SRC-PTV-XTOUR-01`<br>`SRC-NOMADIA-02`<br>(Ríos-Mercado 2013) |

---

# 2. 表 2：规划工作流与运营策略横向对齐表（Planning Workflow Crosswalk）

回答：“业务调度员与系统如何交互？生命周期如何流转？”

| TopPrism 归一化工作流概念 | **Salesforce** (Maps/CG) | **SAP** (Dynamic Visit Planning) | **Microsoft** (Dynamics 365 URS) | **Oracle** (Field Service) | **PTV Group** (xTour) | 晋升依据与一手证据句柄 |
|---|---|---|---|---|---|---|
| **`PlanningMode`**<br>(多级人机协同调度模式) | `Batch Optimization`<br>(批量自动优化) | `Plan My Day / Cockpit`<br>(单日推荐 / 多日规划) | `Manual / Assistant / RSO`<br>(手动 / 助理推荐 / 自动) | `Manual Move / Auto Routing`<br>(手动微调 / 自动组线) | `Interactive / Batch Opt`<br>(交互甘特 / 批量优化) | `SRC-MSFT-URS-01`<br>`SRC-SAP-DVP-02`<br>(多厂商一致支持) |
| **`LifecycleState`**<br>(业务状态机生命周期) | `Generated / Completed / Missed`<br>(生成 / 完成 / 漏访) | `Scheduled / Fixed / Done`<br>(已排 / 锁定 / 完成) | `Proposed / Committed / Done`<br>(建议 / 确认 / 执行完) | `Tentative / Scheduled / Done`<br>(待定 / 已排 / 结束) | `Open / Planned / Executed`<br>(开放 / 计划 / 执行) | `SRC-MSFT-URS-01`<br>`SRC-REPSLY-01`<br>`SRC-SF-MAPS-01` |
| **`CommitmentLock`**<br>(既有计划锁定约束) | `Restart Lock`<br>(重新规划时锁定已有) | `Fixed Visit Marker`<br>(固定拜访标记) | `Booking Lock Options`<br>(Time Range, Resource, Time, Resource and Time) | `Activity Lock`<br>(锁定活动不可移动) | `TourPointFixation`<br>(NONE, NO_TOUR_POINT_OUT, NO_TOUR_POINT_IN_AND_OUT, COMPLETELY_FIXED) | `SRC-MSFT-URS-02`<br>`SRC-PTV-XTOUR-01`<br>(多厂商一致支持) |
| **`PlanningHorizonMode`**<br>(多时间尺度运营策略) | `Batch Period (Monthly)`<br>(按月度批次重排) | `Multi-Day vs Plan My Day`<br>(多日规划 vs 当日出车) | `Tactical vs Daily Schedule`<br>(战术排班 vs 当日派工) | `Strategic / Daily / Intraday`<br>(战略 / 日常 / 日内应急) | `planMultiWeeks / planWeek`<br>(多周规划 / 单周规划) | `SRC-PTV-XCLUSTER-01`<br>`SRC-ORA-FS-01`<br>`SRC-ORTEC-01` |
| **`PlanStability`**<br>(滚动重排路线平滑度) | `Regenerate Threshold`<br>(重排门槛控制) | `Recalculate Remaining`<br>(仅重排未执行日期) | `Freeze Window`<br>(冻结窗口不可变) | `Continuous Improvement`<br>(增量平滑微调) | `Keep Tour Structure`<br>(保持原有路线结构) | `SRC-ORA-FS-01`<br>`SRC-MSFT-URS-02`<br>(Sethi 1991 理论) |

---

# 3. 表 3：技术与优化能力横向对齐表（Technical Capability Crosswalk）

回答：“由什么成熟算法、预言机与求解器执行数学形式化？”

| 技术能力维度 | **数学形式化表达候选 [TOPPRISM HYPOTHESIS]** | **商业厂商实现证据** | **开源与底层算力基准** | 权威理论文献与 DOI |
|---|---|---|---|---|
| **未安排决策与履约成本** | • 候选 A: Prize-Collecting $\max \sum p_i z_i - c(R)$<br>• 候选 B: Slack 惩罚项 $\sum \text{Penalty}_i (1-z_i)$ | • Oracle: `non_assignment_cost`<br>• PTV: `Order Priorities` | • Google MathOpt 目标项<br>• SCIP 软约束松弛 | **Archetti et al. (2014)**<br>*SIAM Book Chapter*, pp. 273–297 |
| **周期模式到日路线映射** | • 候选 A: $\sum_{t \in D_w} x_{it} = \sum_p B_{ipw} y_{ip}$<br>• 候选 B: 连续工作日 Min/Max Gap 不等式 | • PTV: `planMultiWeeks` 算法<br>• Salesforce: Cadence Engine | • CP-SAT 线性映射约束<br>• Rothenbächer BCP 框架 | **Rothenbächer (2019)**<br>*Trans. Sci.*, `10.1287/trsc.2018.0855` |
| **单日路径顺序求值 (ATSP)** | • 候选 A: 状态压缩动态规划 $O(2^k k^2)$<br>• 候选 B: 2-Opt / Lin-Kernighan 局部搜索 | • PTV: Sequence Optimizer<br>• Nomadia: TourSolver | • Held-Karp 精确 DP ($k \le 9$)<br>• PyVRP / OSRM 快速近似 | **Held & Karp (1962)**<br>*SIAM*, `10.1137/0110015` |
| **单日富路径元启发式基线** | • 候选 A: 迭代局部搜索 (Iterated Local Search, ILS)<br>• 候选 B: 自适应大邻域搜索 (ALNS) | • PTV: OptiFlow 启发式内核<br>• Descartes: 混合路由引擎 | • **PyVRP (MIT, Wouda 2024 ILS)**<br>• Røpke (2006) ALNS | **Wouda, Lan & Kool (2024)**<br>*INFORMS J. Comput.*, `10.1287/ijoc.2023.0055` |
| **周期路径专用遗传基线** | • 候选 A: 周期混合遗传搜索 (PVRP-HGS) | • PTV: xCluster 遗传算法 | • **Vidal et al. (2012) PVRP-HGS** | **Vidal et al. (2012)**<br>*Operations Research*, `10.1287/opre.1120.1048` |
| **精确分支定价割平面 (BCP)** | • 候选 A: 限制主问题 RMP + ESPPRC 标号法<br>• 候选 B: Subset-Row 割平面强化 | • GCG / Coluna.jl 分解框架<br>• VRPSolver (研究原型) | • **VRPSolverEasy (R&D 工具)**<br>• SCIP/GCG 自动分解 | **Pessoa et al. (2020)**<br>*Computers & OR*, `10.1016/j.cor.2020.105036` |
| **跨天工作量平滑** | • 阶段 1: 求最小总工时 $C^\star = \min \sum c_r \lambda_{rt}$<br>• 阶段 2: 约束 $\sum L_t = C^\star$ 下求解 $\min \max_t L_t$ | • Lexicographic 二次 MIP 平滑<br>• Nekooghadirli 多周期公平性 | • CP-SAT 二次快速求解<br>• HiGHS 整数规划 | **Nekooghadirli et al. (2026)**<br>*ITOR*, `10.1111/itor.70012` |
| **多级旅行时间证据链** | • L1: OSRM/高德真实路网矩阵<br>• L2: 区县中位数打卡两段式校准 + ObservedStopTime (median 32.0 min, 分项 UNKNOWN)<br>• L3: Haversine 球面兜底 | • Microsoft: Historical Traffic<br>• PTV: Time-dependent Network | • OSRM API 适配器<br>• 内部 319 条实证数据拟合 | **Dalla Chiara & Goodchild (2020)**<br>*Transport Policy*, `10.1016/j.tranpol.2020.06.013` |
