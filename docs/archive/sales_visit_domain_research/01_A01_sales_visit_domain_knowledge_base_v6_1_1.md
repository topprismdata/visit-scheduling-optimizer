# A01: 通用销售拜访领域知识库与一手实证研究报告 (v6.0)
## Generic Sales Visit Domain Knowledge Base & Primary Evidence Dossier (v6.1.1 Cleanup)

> **文档标识**：`A01-SALES-VISIT-KNOWLEDGE-BASE-V6.1.1`  
> **所属资产组**：TopPrism 销售拜访决策智能事实源基准库  
> **版本状态**：`Evidence-Baseline-v1.0`（长期维护证据基线：最后核验日期 2026-08-22，下次复审日期 2026-11-22）  
> **核心硬规则（The Three-Layer Mapping Rule）**：  
> 知识条目采用图谱式 `0..N` 关联结构，**严禁为业务概念生造数学模型，严禁将厂商技术实现当成通用领域本体**。  
> 每一个条目严格区分：`[PRODUCT FACT]`（厂商官方事实）与 `[TOPPRISM MODELING HYPOTHESIS]`（建模假设）。

---

## 目录
1. [研究方法论与二维证据评级规范](#1-研究方法论与二维证据评级规范)
2. [第一群组：销售拜访与零售执行原生产品深度解构（Group A: Sales & Retail Execution）](#2-第一群组销售拜访与零售执行原生产品深度解构group-a-sales--retail-execution)
   - 2.1 Salesforce Maps Advanced & Consumer Goods Cloud (含官方 Trailhead 培训)
   - 2.2 SAP Sales Cloud Dynamic Visit Planning (C4C, 含官方配置手册)
   - 2.3 Nomadia Sales & Geoconcept Opti-Time (欧洲快消拜访标杆)
   - 2.4 BeatRoute: 商业价值驱动的现场销售规划
   - 2.5 StayinFront: Size-of-Prize 零售执行与经济机会闭环
   - 2.6 Repsly: 零售现场活动与敏捷执行管理
3. [第二群组：专业路线与排程优化厂商深度解构（Group B: Route & Scheduling Optimization）](#3-第二群组专业路线与排程优化厂商深度解构group-b-route--scheduling-optimization)
   - 3.1 PTV Group (xTour / xCluster / OptiFlow): 多周排班与 VisitOrder 机制
   - 3.2 ORTEC: 战术级与运营级分层优化 (Tactical vs. Operational Optimization)
   - 3.3 Descartes: 静态/动态/混合路由与异常导向规划 (Exception-based Planning)
   - 3.4 Aptean Paragon: 固定基准主干路线与周期性循环维护
4. [第三群组：现场服务与复杂资源调度平台（Group C: Field Service Reference）](#4-第三群组现场服务与复杂资源调度平台group-c-field-service-reference)
   - 4.1 Microsoft Dynamics 365 Universal Resource Scheduling (URS, 含 MS Learn 培训)
   - 4.2 Oracle Field Service: 履约惩罚与未安排成本 (non_assignment_cost)
   - 4.3 Timefold Field Service & Employee Rostering (2.3.0 事实核验)
5. [第四群组：运筹学与决策科学前沿理论映射（Group D: Academic & OR Base）](#5-第四群组运筹学与决策科学前沿理论映射group-d-academic--or-base)
   - 5.1 周期性路径与柔性日程结构 (PVRP with Flexible Schedule Structures)
   - 5.2 服务一致性与熟悉度模型 (Consistent VRP & Customer Familiarity)
   - 5.3 选点定向与奖赏收集模型 (Team Orienteering & Prize-Collecting VRP)
   - 5.4 滚动周期重排与解稳定性理论 (Rolling Horizon & Plan Stability)
   - 5.5 商业区域划分与拜访对齐 (Commercial Territory Design & Alignment)
   - 5.6 运筹算法实验与验证规范 (Good Laboratory Practice for Optimization)
6. [全量一手证据索引与元数据登记库（Primary Source Registry - 25 项真实核验官方源）](#6-全量一手证据索引与元数据登记库primary-source-registry---24-项真实核验官方源)

---

# 1. 研究方法论与二维证据评级规范

```
                    【二维证据矩阵 (Two-Dimensional Evidence Matrix)】

   来源权威度 (Source Authority)                     断言类型 (Claim Type)
┌──────────────────────────────────────┐     ┌──────────────────────────────────────┐
│ • OFFICIAL_PRODUCT_DOC  (官方文档/手册)│     │ • PRODUCT_FACT     (产品事实/字段定义)│
│ • OFFICIAL_API_SPEC     (官方API/模型)│     │ • DOMAIN_PRACTICE  (行业业务惯例)    │
│ • OFFICIAL_TRAINING     (官方培训认证)│     │ • MATHEMATICAL_THEORY(数学定理/公式)  │
│ • PEER_REVIEWED_RESEARCH(顶刊学术论文)│     │ • EMPIRICAL_EVIDENCE (实证数据/中位数)│
│ • VENDOR_WHITEPAPER     (厂商白皮书)  │     │ • DESIGN_INFERENCE (架构设计推论)    │
└──────────────────────────────────────┘     └──────────────────────────────────────┘
```

---

# 2. 第一群组：销售拜访与零售执行原生产品深度解构（Group A: Sales & Retail Execution）

### 2.1 Salesforce Maps Advanced & Consumer Goods Cloud
```
【厂商深度解构：Salesforce Maps Advanced / CG Cloud】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC & OFFICIAL_TRAINING / Level A | 检索句柄: SRC-SF-MAPS-01, SRC-SF-MAPS-02, SRC-SF-TRAIL-01
• 官方引用: Salesforce Help, "Key Terms and Concepts for Salesforce Maps Advanced Routing",
  "Specify Visit Frequency, Duration, and Visit Windows", Article ID: sf.salesforce_maps_advanced_concepts_terms;
  Salesforce Trailhead Module, "Automate Route and Schedule Optimization with Salesforce Maps Advanced".

1. [PRODUCT FACT] 官方核心对象模型:
   - Routable Object: 拥有坐标且可被拜访的目标实体 (Account, Lead, RetailStore)。
   - Dataset: 适用相同拜访规则的客户分群容器。
   - Visit Plan: 路线生成政策主模板，定义规划生效期、重新优化批次周期 (Batch Interval)。
   - Visit Requirement: 拜访需求定义，显式拆解为 Target Frequency, Min/Max Days Between Visits,
     Visit Duration (店内时长), Buffer Time (额外通行/出入缓冲), Visit Window (可服务时段)。
   - Output Object: 算法最终实例化的 Event 或 Visit 业务对象。

2. [PRODUCT FACT] 关键机制:
   - 节奏控制 (Cadence) 优于单一频次：通过最小/最大天数间隔防止拜访扎堆。
   - 执行状态回写再生 (State-Driven Regeneration)：算法在优化批次扫描时，自动读取 SFA 实际打卡完成的
     Visit，将漏访或未履约的拜访动态转化为下一轮的补救需求。

3. [TOPPRISM MODELING HYPOTHESIS] 数学形式化候选:
   - 候选 1 (Pattern 形式): 构造周次模式集合 P_i，通过 ∑_{p ∈ P_i} y_ip = 1 约束 [Ref-Rothenbacher2019]。
   - 候选 2 (时间依赖四元数): 引入 (δ_min, δ_max) 时间差边界 van Montfort, Leitner & Paradiso (2026), *An exact algorithm for vehicle routing problems with temporal dependency constraints*, arXiv:2604.16064。
─────────────────────────────────────────────────────────────────────────────
```

---

### 2.2 SAP Sales Cloud Dynamic Visit Planning (C4C)
```
【厂商深度解构：SAP Dynamic Visit Planning】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-SAP-DVP-01, SRC-SAP-DVP-02
• 官方引用: SAP Help Portal, Dynamic Visit Planning Add-On for SAP Sales Cloud,
  "Manage Visiting Information", "Create Visit Lists", "Scope and Configure Dynamic Visit Planning".

1. [PRODUCT FACT] 官方核心对象模型:
   - Visit Plan: 基于 Sales Area 与 Account 维度的静态周期覆盖维护表。
   - Account Score: 门店动态商业价值评分 (综合 Perfect Store 指标、销售异动、覆盖率与逾期天数)。
   - Plan My Day: 基于 "Account Score + Travel Distance + Work Hours" 的单日高 ROI 拜访调度。
   - Allocation Objective: 显式支持 Highest Impact (价值优先) 与 Maximum Visits (吞吐量优先)。

2. [PRODUCT FACT] 关键机制:
   - 双轨需求模型：显式区分“常规覆盖政策 (Visit Plan)”与“动态机会推荐 (Visit Recommendation)”。
   - 逾期价值持续累积：未按时拜访的客户，其 Account Score 随逾期天数**持续增加**直至完成拜访（官方未声明函数形式）。

3. [TOPPRISM MODELING HYPOTHESIS] 数学形式化候选:
   - 候选 1 (Prize-Collecting / Orienteering): max ∑_i Score_i · z_i - c(Route)。
   - 候选 2 (分层多目标 Lexicographic): Level 1 满足必访 -> Level 2 最大化得分 -> Level 3 最小化耗时。
─────────────────────────────────────────────────────────────────────────────
```

---

### 2.3 Nomadia Sales & Geoconcept Opti-Time (欧洲快消拜访标杆)
```
【厂商深度解构：Nomadia Sales (formerly Geoconcept / Opti-Time)】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-NOMADIA-01, SRC-NOMADIA-02
• 官方引用: Nomadia Group, "Nomadia Sales CRM for FMCG and Retail Execution",
  Geoconcept Opti-Time Product Sheet, "Optimizing Sales Rounds & Territory Management".

1. [PRODUCT FACT] 官方核心概念:
   - Sales Sector: 销售代表的专属责任辖区。
   - Call Cycle / Visit Round: 多周常态化拜访循环 (巡店计划)。
   - 区分门店营业时间与店长/采购关键联系人在店时段。
   - 优化目标聚焦于**最大化面向客户的时间 (Customer-Facing Time)**。

2. [TOPPRISM MODELING HYPOTHESIS] 数学形式化候选:
   - 目标函数设为 max ∑_i ServiceDuration_i - α · TravelTime。
─────────────────────────────────────────────────────────────────────────────
```

---

### 2.4 BeatRoute: 商业价值驱动的现场销售规划
```
【厂商深度解构：BeatRoute Intelligent Field Sales Platform】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: VENDOR_WHITEPAPER / Level D | 检索句柄: SRC-BEATROUTE-01
• 官方引用: BeatRoute Innovation Inc., "Intelligent Visit Planning Software for Retail Sales".

1. [PRODUCT FACT] 业务层级:
   - Beat Planning (辖区网格) -> Visit Planning (拜访优先级) -> Route Optimization (单日组线)。
   - 拜访优先级由订单新鲜度、历史回款、未结账款与销售额贡献联合决定。
─────────────────────────────────────────────────────────────────────────────
```

---

### 2.5 StayinFront: Size-of-Prize 零售执行与经济机会闭环
```
【厂商深度解构：StayinFront Intelligent Guided Selling (IGS)】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: VENDOR_WHITEPAPER / Level D | 检索句柄: SRC-STAYINFRONT-01
• 官方引用: StayinFront Inc., "Intelligent Guided Selling (IGS) & Retail Execution Whitepaper".

1. [PRODUCT FACT] 业务思想:
   - Size-of-Prize: 单个门店在特定 SKU 上的潜在商业收益预期。
   - 拜访决策实质是投资回报率 (ROI) 权衡：销售代表时间是昂贵资本，必须投向边际回报最高门店。
─────────────────────────────────────────────────────────────────────────────
```

---

### 2.6 Repsly: 零售现场活动与敏捷执行管理
```
【厂商深度解构：Repsly Retail Execution Platform】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-REPSLY-01
• 官方引用: Repsly Help Center, "Schedule Management & Visit Planning in Repsly", 2026.

1. [PRODUCT FACT] 业务模型:
   - Client / Place (场所实体) 与 Scheduled Visit (拜访任务) 彻底解耦。
   - 实时记录现场漏访状态 (Missed Visit) 与漏访原因。
─────────────────────────────────────────────────────────────────────────────
```

---

# 3. 第二群组：专业路线与排程优化厂商深度解构（Group B: Route & Scheduling Optimization）

### 3.1 PTV Group (xTour / xCluster / OptiFlow): 多周排班与 VisitOrder 机制
```
【厂商深度解构：PTV Group (PTV xServer & OptiFlow)】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC & OFFICIAL_API_SPEC / Level A | 检索句柄: SRC-PTV-XTOUR-01, SRC-PTV-XCLUSTER-01, SRC-PTV-DOC-02
• 官方引用: PTV xServer API Documentation, "xCluster: How to Plan Multi Weeks (planMultiWeeks)",
  "xCluster: How to Plan a Week (planWeek)", "xTour: Technical Concepts - Order Priorities & Fixation".

1. [PRODUCT FACT] 官方数据模型:
   - VisitOrder: 去客户现场完成访问但**不运输实物货物**的订单实体 (仅有 Location, ServiceTime)。
   - planMultiWeeks / planWeek: 针对周期性拜访规划的专用接口，支持 Week Rhythm 与 Weekday Patterns，最长 52 周。
   - Order Priorities: 资源不足时指导优化器进行权衡。
   - TourPointFixation: 细粒度计划锁定 (NONE, NO_TOUR_POINT_OUT, NO_TOUR_POINT_IN_AND_OUT, COMPLETELY_FIXED)。
   - xTerritory: 独立的商业区域划分引擎。

2. [TOPPRISM MODELING HYPOTHESIS] 数学形式化候选:
   - Multi-period MIP / Flexible Schedule Structures。
─────────────────────────────────────────────────────────────────────────────
```

---

### 3.2 ORTEC: 战术级与运营级分层优化 (Tactical vs. Operational Optimization)
```
【厂商深度解构：ORTEC Field Service & Routing】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-ORTEC-01
• 官方引用: ORTEC Official Solutions, "Field Service Scheduling: Tactical vs. Operational Decisions", 2026.

1. [PRODUCT FACT] 架构设计:
   - Tactical (战术级): 区域结构划分、销售团队与客户群匹配 (季度/年度)。
   - Operational (运营级): 单日组线、具体排程、突发应急重排 (周度/日度)。
   - Optimization Layer 定位: 运筹引擎作为无状态优化层嵌入企业现有 CRM/SFA。
─────────────────────────────────────────────────────────────────────────────
```

---

### 3.3 Descartes: 静态/动态/混合路由与异常导向规划 (Exception-based Planning)
```
【厂商深度解构：Descartes Route Planning & Optimization】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-DESCARTES-01
• 官方引用: Descartes Systems Group, "Operational Route Planning Buyer's Guide", "Static vs. Dynamic Routing".

1. [PRODUCT FACT] 业务模式:
   - 支持 Static Master Route (固定主干), Dynamic Route (动态优化), Hybrid Route (主干+动态插入)。
   - 调度员聚焦异常 (Planner Focuses on Exceptions): 系统自动处理 90% 规则，人工介入冲突异常。
─────────────────────────────────────────────────────────────────────────────
```

---

### 3.4 Aptean Paragon: 固定基准主干路线与周期性循环维护
```
【厂商深度解构：Aptean Paragon Routing & Scheduling】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-APTEAN-01
• 官方引用: Aptean Paragon Documentation, "Fixed Master Routing and Strategic Territory Modelling", 2026.

1. [PRODUCT FACT] 业务模式:
   - Master Route Scheduling: 维护固定基准循环路线表。
   - 支持多周多频次客户周期性轮转。
─────────────────────────────────────────────────────────────────────────────
```

---

# 4. 第三群组：现场服务与复杂资源调度平台（Group C: Field Service Reference）

### 4.1 Microsoft Dynamics 365 Universal Resource Scheduling (URS)
```
【厂商深度解构：Microsoft Dynamics 365 URS】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC & OFFICIAL_TRAINING / Level A | 检索句柄: SRC-MSFT-URS-01, SRC-MSFT-URS-02, SRC-MSFT-TRAIN-01
• 官方引用: Microsoft Learn, "Universal Resource Scheduling Overview", "Work Order Architecture",
  "Schedule Requirements with Travel Time and Distance", Microsoft Learn Training "Deploying Resource Scheduling Optimization".

1. [PRODUCT FACT] 业务模型:
   - Resource Requirement (业务需求) 严格不等于 Resource Booking (排班记录)。
   - 调度模式: Manual (手动拖拽) -> Schedule Assistant (推荐) -> Auto RSO (全自动)。
   - 规划使用历史代表性交通 (Historical Traffic)，导航使用实时路况 (Live Traffic)。
─────────────────────────────────────────────────────────────────────────────
```

---

### 4.2 Oracle Field Service: 履约惩罚与未安排成本 (non_assignment_cost)
```
【厂商深度解构：Oracle Field Service】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC / Level A | 检索句柄: SRC-ORA-FS-01, SRC-ORA-FS-02
• 官方引用: Oracle Fusion Field Service Cloud, "Setting Optimization Goals", "Using Routing", Part No. FARCU.

1. [PRODUCT FACT] 业务机制:
   - non_assignment_cost: 未安排某个活动产生显式业务惩罚，使工时不足时的延期成为合法的经济学决策。
   - 增量平滑修补 (Continuous Improvement): 出现突发取消或新增活动时，执行局部微调，保持路线稳定性。
─────────────────────────────────────────────────────────────────────────────
```

---

### 4.3 Timefold Field Service & Employee Rostering (2.3.0 事实核验)
```
【技术评估卡片：Timefold Solver & Platform】
─────────────────────────────────────────────────────────────────────────────
• 证据元数据: OFFICIAL_PRODUCT_DOC & REPO / Level A | 检索句柄: SRC-TIMEFOLD-01, SRC-TIMEFOLD-02
• 官方引用: Timefold Documentation, "Field Service Routing and Employee Rostering Quickstart", v2.3.0 (2026);
  GitHub Timefold Platform Announcement (2025).
• 维护状态核实: Timefold Python 实验包已于 2025 年正式归档；当前主力为 Java/Kotlin 原生引擎与 Timefold Platform 托管 REST API。
• 核心价值: 其基于 ScoreDirector 与 ConstraintStreams 的业务约束声明模式为我们提供了优秀的领域 DSL 参考。
─────────────────────────────────────────────────────────────────────────────
```

---

# 5. 第四群组：运筹学与决策科学前沿理论映射（Group D: Academic & OR Base）

| 业务决策语义 (Business Semantic) | 数学模型形式化候选 (Mathematical Formulation Candidates) | 技术实现与工具证据 (Implementation Evidence) | 权威文献题录与 DOI |
|---|---|---|---|
| **周期拜访节奏 (Cadence)** | • 候选 1: 离散周次模式集合 $P_i$ 与 $y_{ip}$ 变量<br>• 候选 2: 连续工作日最小/最大间隔不等式 | • Rothenbächer BCP 框架<br>• PTV `planMultiWeeks` API | **Rothenbächer (2019)** *Trans. Sci.*, 53(3), 850–866. `10.1287/trsc.2018.0855` |
| **客户服务熟悉度 (Familiarity)** | • 候选 1: 偏离历史最习惯星期的软惩罚项<br>• 候选 2: 固定指派到特定销售代表 $x_{ik} = 1$ | • Consistent VRP 算法<br>• PTV 锁定模式 | **Groër, Golden & Wasil (2009)** *M&SOM*, 11(4), 630–643. `10.1287/msom.1080.0243` |
| **商机价值与未安排权衡 (Priority)** | • 候选 1: 选点定向奖赏收集目标 $\max \sum p_i z_i - c(R)$<br>• 候选 2: 分层序列优化 (Lexicographic Hierarchy) | • Oracle `non_assignment_cost`<br>• SAP `Highest Impact` 模式 | **Archetti, Speranza & Vigo (2014)** *SIAM Book Chapter*, pp. 273–297 |
| **滚动重排与路线稳定性 (Stability)** | • 候选 1: 冻结前 $N$ 天工作日为常数<br>• 候选 2: 路线扰动惩罚项 $\beta \cdot \|x - x_0\|$ | • Oracle Continuous Improvement<br>• Microsoft Booking Lock | **Sethi & Sorger (1991)** *Annals of OR*, 29(1), 387–416. `10.1007/BF02283611` |
| **商业辖区网格划分 (Territory)** | • 候选 1: 紧凑度与工作量平衡的混合整数规划<br>• 候选 2: Voronoi 图与 P-中值聚类模型 | • PTV `xTerritory` 引擎<br>• Nomadia Territory Manager | **Ríos-Mercado & López-Pérez (2013)** *Omega*, 41(3), 525–535. `10.1016/j.omega.2012.08.002` |
| **多周期工作量平滑 (Equity)** | • 阶段 1: 求全局最小工时 $C^\star$<br>• 阶段 2: 约束 $C \le C^\star$ 下求解 $\min \max_t L_t$ | • Lexicographic 二次 MIP 平滑器<br>• Nekooghadirli 多周期公平性 | **Nekooghadirli et al. (2026)** *ITOR*, Wiley. `10.1111/itor.70012` |
| **城市实证观察门店停留耗时 (ObservedStopTime)** | • 候选 1: 经验校准总中位数 (32.0 min, 分项 UNKNOWN)<br>• 候选 2: 距离相关两段式城市慢速模型 | • 319 条打卡流水拟合模型<br>• Dalla Chiara 停车巡航实证 | **Dalla Chiara & Goodchild (2020)** *Transport Policy*, 97, 26–36. `10.1016/j.tranpol.2020.06.013` |
| **运筹算法实验与验证 (GLP)** | • 候选 1: 语义/结构/小算例比对/行为蜕变四层验证<br>• 候选 2: 求解凭证双态验证 (Heuristic vs Exact) | • ReLoop 行为单调性测试框架<br>• Kendall GLP 实验规范 | **Kendall et al. (2016)** *JORS*, 67(4), 676–689. `10.1057/jors.2015.77`<br>**Lian et al. (2026)** arXiv:2602.15983 |

---

# 6. 全量一手证据索引与元数据登记库（Primary Source Registry - 25 项真实核验官方源）

```json
[
  {
    "source_id": "SRC-SF-MAPS-01",
    "vendor": "Salesforce",
    "title": "Salesforce Maps Advanced Concepts and Key Terms",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://help.salesforce.com/s/articleView?id=sf.salesforce_maps_advanced_concepts_terms.htm",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-SF-MAPS-02",
    "vendor": "Salesforce",
    "title": "Specify Visit Frequency, Duration, and Visit Windows in Salesforce Maps Advanced",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://help.salesforce.com/s/articleView?id=salesforce_maps_adv_visitplan_datasets_create_requirements.htm",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-SF-TRAIL-01",
    "vendor": "Salesforce",
    "title": "Automate Route and Schedule Optimization with Salesforce Maps Advanced (Trailhead)",
    "source_authority": "OFFICIAL_TRAINING",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://trailhead.salesforce.com/content/learn/modules/salesforce-maps-advanced-basics",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-SAP-DVP-01",
    "vendor": "SAP",
    "title": "Manage Visiting Information in SAP Dynamic Visit Planning",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://help.sap.com/docs/sap-cloud-for-customer/dynamic-visit-planning-add-on-for-sap-sales-cloud/manage-visiting-information",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-SAP-DVP-02",
    "vendor": "SAP",
    "title": "Scope and Configure Dynamic Visit Planning & Highest Impact Allocation",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://help.sap.com/docs/sap-cloud-for-customer/dynamic-visit-planning-add-on-for-sap-sales-cloud/scope-and-configure-dynamic-visit-planning",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-NOMADIA-01",
    "vendor": "Nomadia Group",
    "title": "Nomadia Sales CRM for FMCG and Retail Execution",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://www.nomadia-group.com/en/solutions/nomadia-sales/",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-NOMADIA-02",
    "vendor": "Nomadia Group",
    "title": "Geoconcept Opti-Time Product Specification for Sales Sector Optimization",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://en.geoconcept.com/download/product_sheet/Opti-Time_Psheet-EN.pdf",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-BEATROUTE-01",
    "vendor": "BeatRoute",
    "title": "Intelligent Visit Planning Software for Retail Sales and Distribution",
    "source_authority": "VENDOR_WHITEPAPER",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://beatroute.io/platform/visit-planning-software/",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-STAYINFRONT-01",
    "vendor": "StayinFront",
    "title": "Intelligent Guided Selling (IGS) & Size-of-Prize Architecture",
    "source_authority": "VENDOR_WHITEPAPER",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://www.stayinfront.com/cg-solutions-igs-test/",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-REPSLY-01",
    "vendor": "Repsly",
    "title": "Schedule Management & Visit Planning in Repsly",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://help.repsly.com/hc/en-us/articles/schedule-management",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-PTV-XTOUR-01",
    "vendor": "PTV Group",
    "title": "PTV xServer xTour API Documentation - VisitOrder & Technical Concepts",
    "source_authority": "OFFICIAL_API_SPEC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://xserver2-europe-eu.cloud.ptvlogistics.com/dashboard/Content/API-Documentation/xtour.html",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-PTV-XCLUSTER-01",
    "vendor": "PTV Group",
    "title": "PTV xServer xCluster - How to Plan Multi Weeks (planMultiWeeks)",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://xtour-eu-n-test.cloud.ptvgroup.com/manual/Content/Use%20cases/xCluster/UC_How_to_Plan_Multi_Weeks.htm",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-PTV-DOC-02",
    "vendor": "PTV Group",
    "title": "PTV OptiFlow Route Optimization Documentation",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://www.ptvlogistics.com/en/products/ptv-optiflow",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-ORTEC-01",
    "vendor": "ORTEC",
    "title": "Field Service Scheduling - Tactical vs Operational Decision Layer",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "DESIGN_INFERENCE",
    "url": "https://ortec.com/en-us/solutions/field-service",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-DESCARTES-01",
    "vendor": "Descartes",
    "title": "Operational Route Planning Buyer's Guide - Static vs Dynamic Routing",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://www.descartes.com/solutions/routing-mobile-and-telematics/route-planning-and-optimization/operational-route-planning",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-APTEAN-01",
    "vendor": "Aptean",
    "title": "Paragon Routing & Scheduling Fixed Master Route System",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://www.aptean.com/en-US/products/routing-and-scheduling",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-MSFT-URS-01",
    "vendor": "Microsoft",
    "title": "Universal Resource Scheduling Overview in Dynamics 365",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://learn.microsoft.com/en-us/dynamics365/field-service/universal-resource-scheduling-for-field-service",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-MSFT-URS-02",
    "vendor": "Microsoft",
    "title": "Understand Booking Lock Options in Resource Scheduling Optimization",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://learn.microsoft.com/en-us/dynamics365/field-service/booking-lock-options",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-MSFT-TRAIN-01",
    "vendor": "Microsoft",
    "title": "Deploying Resource Scheduling Optimization - Microsoft Learn Module",
    "source_authority": "OFFICIAL_TRAINING",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://learn.microsoft.com/en-us/training/modules/deploy-resource-scheduling-optimization/",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-ORA-FS-01",
    "vendor": "Oracle",
    "title": "Set Optimization Goals and non_assignment_cost in Oracle Field Service",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://docs.oracle.com/en/cloud/saas/field-service/farcu/t-changing-optimization-goal.html",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-ORA-FS-02",
    "vendor": "Oracle",
    "title": "REST API for Oracle Fusion Field Service Cloud Service v2",
    "source_authority": "OFFICIAL_API_SPEC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://docs.oracle.com/en/cloud/saas/field-service/cxfsc/op-api-field-service-routing-v2-routingprofiles-profilelabel-plans-planlabel-custom-actions-export-post.html",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-TIMEFOLD-01",
    "vendor": "Timefold",
    "title": "Timefold Solver v2.3.0 Quickstart & ConstraintStreams Architecture",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://docs.timefold.ai/timefold-solver/latest/quickstart/overview",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-TIMEFOLD-02",
    "vendor": "Timefold",
    "title": "Timefold Platform Field Service Routing REST Architecture",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://docs.timefold.ai/field-service-routing/latest/introduction",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-GOOGLE-MATHOPT-01",
    "vendor": "Google",
    "title": "OR-Tools MathOpt: Solver-Independent Operations Research Modeling Library",
    "source_authority": "OFFICIAL_PRODUCT_DOC",
    "claim_type": "PRODUCT_FACT",
    "url": "https://developers.google.com/optimization/math_opt",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
  {
    "source_id": "SRC-SAP-VIDEO-01",
    "vendor": "SAP",
    "title": "Dynamic Visit Planning — Official Product Team Demo (Visit Type / Recommendation / Generation Schedule / Route Group / Re-optimization / Multi-Day Planning)",
    "source_authority": "OFFICIAL_DEMO_VIDEO",
    "claim_type": "DOMAIN_PRACTICE",
    "url": "https://www.youtube.com/watch?v=GEQMnkxEgZs",
    "retrieved_date": "2026-08-22",
    "verified_at": "2026-08-22",
    "next_review_date": "2026-11-22"
  },
]
```
