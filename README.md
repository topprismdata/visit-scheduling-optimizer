<p align="center">
  <img src="https://raw.githubusercontent.com/topprismdata/.github/main/assets/brand/topprism-repo-header.png" alt="TopPrism dual-prism visual" width="100%" />
</p>

# Visit Scheduling Optimizer

> **Language / 语言:** English primary · 中文概览如下。
>
> ### 中文概览
> 面向快消行业周期性外勤拜访与实时动态插单的**智能体决策引擎 (Agentic Decision Engine)**：
> 1. **静态月度规划**：在频次、工作日锁定、路线里程与每日工作量均衡约束下求解最优拜访计划；
> 2. **MO-ALNS v4 三目标帕累托前沿**：以 v3 月度结果为基准，回答"愿意用多少里程换每天工作量均衡"，并量化"改日期"本身的价值（09 线 +63.4 km / 19.4%）；
> 3. **Agent 动态实时调度副驾**：针对现场实际走访中高达 27.4%（全办）的突发临时插单需求，基于近 3 年学术顶刊（2024 Transportation Science 亚马逊冠军方案）的**沿街走廊一维投影与顺路拼接算法**，实测单次决策 **75–330 微秒**；全办 10 线 23 工作日总账（全矩阵道路实测口径）：人类实际 **13,417.7 km → Agent 5,632.0 km（−58.0%，净省 7,785.7 km）**！

**A data-calibrated decision engine for recurring field-sales visit
planning.**

`CUSTOMER DECISION` · `APPLIED` · `ANONYMIZED OPERATIONAL DATA` · `MIT`

> **Decision question:** Who should visit which customers, on which
> days, under recurring-frequency, spacing, routing, and workload
> constraints?

Part of **TopPrism Decision Intelligence**. This repository focuses on
the optimization layer behind periodic field-sales planning. It contains
no customer-level raw data or real coordinates.

------------------------------------------------------------------------

## Why this exists

Recurring field-sales planning is not a one-route TSP problem.

A representative may need to visit dozens of outlets over a monthly
cycle. Different outlets require different visit frequencies, repeated
visits must be separated in time, daily workload is capped, service time
varies, and the final plan must remain executable on a road network.

The real decision is therefore:

> **How should recurring customer visits be distributed across days and
> sequenced within each day so that service requirements are satisfied
> with less travel and workload?**

This repository turns that decision into a reproducible optimization
problem.

------------------------------------------------------------------------

## What this engine decides

``` text
Customers + visit frequency + service time
                  +
Historical travel observations + depot
                  ↓
          Time calibration
                  ↓
 Feasible recurring day-group generation
                  ↓
Restricted set-partitioning master problem
                  ↓
 Dual-guided heuristic column generation
                  ↓
     Final CP-SAT selection
                  ↓
      Within-day route ordering
                  ↓
Day-by-day executable visit plan
```

### Inputs

-   customer locations
-   required recurring visit frequencies
-   inter-visit spacing rules
-   service / dwell time
-   depot location
-   daily work-hour capacity
-   optional historical travel observations for calibration

### Outputs

-   customers assigned to each working day
-   recurring-visit compliance
-   estimated daily work time
-   route ordering within each day
-   aggregate travel / workload metrics
-   comparison against baseline planning approaches

------------------------------------------------------------------------

## Evidence

The repository includes an **anonymized industry study covering 7
representatives and 235 customers**. Only aggregate results are
published.

  ------------------------------------------------------------------------
  Metric             Business actual          Framework    Observed change
  --------------- ------------------ ------------------ ------------------
  Active working                 139                117               -16%
  days, 20-day                                          
  horizon                                               

  In-day work                  768 h              569 h               -26%
  hours                                                 

  OSRM route               10,056 km           6,345 km               -37%
  distance                                              

  Frequency                 92--100%               100%    hard constraint
  compliance                                                     satisfied

  Daily                  12% of days                 0%    hard constraint
  work-hour-cap                                                  satisfied
  violations                                            
  ------------------------------------------------------------------------

These figures are **study results, not a universal performance
guarantee**. Improvement depends on customer geography, frequency
policy, depot location, workload rules, and the quality of travel-time
calibration.

### What the evidence supports

-   recurring visit constraints can be modeled explicitly rather than
    handled only by spreadsheet heuristics;
-   data-calibrated travel and dwell assumptions materially affect
    executability;
-   the framework produced lower aggregate workload and route distance
    on the anonymized study;
-   hard frequency and daily-capacity rules can be enforced in the
    optimization model.

### What the evidence does not support

-   a claim that every deployment will achieve the same percentage
    improvement;
-   a claim of full PVRP global optimality;
-   a claim that the published aggregate study reproduces a live
    production deployment.

------------------------------------------------------------------------

## Optimization status --- important

This implementation uses **dual-guided heuristic column generation**.

The pricing step greedily constructs promising columns from seed
customers; it is **not an exact RCSP / ESPPRC pricing oracle**.
Therefore:

-   the LP objective is a lower bound for the **restricted master over
    the generated column pool**;
-   stopping because the heuristic finds no negative-reduced-cost column
    does **not** certify that no improving column exists in the full
    PVRP;
-   the final CP-SAT solution can be reported as optimal **within the
    generated column pool** when CP-SAT proves that restricted problem
    optimal;
-   full global PVRP optimality would require exact pricing /
    branch-and-price or another valid global-certification mechanism.

This distinction is intentional and should be preserved in papers,
demos, and downstream product claims.

------------------------------------------------------------------------

## Architecture

``` text
┌─────────────────────────────────────────────────────┐
│ BUSINESS STATE                                      │
│ customer · frequency · service · depot · capacity   │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 1. TIME CALIBRATION                                 │
│ historical segments → travel + dwell assumptions    │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 2. DAY-GROUP / COLUMN CONSTRUCTION                  │
│ feasible customer groups + exact/heuristic routing  │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 3. RESTRICTED SET-PARTITIONING MASTER               │
│ LP duals → heuristic pricing → expanded column pool │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ 4. FINAL CP-SAT SELECTION                           │
│ coverage · spacing · daily capacity · workload      │
└──────────────────────────┬──────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│ DECISION                                            │
│ day assignment · route order · workload metrics     │
└─────────────────────────────────────────────────────┘
```

------------------------------------------------------------------------

## Agentic Dynamic Dispatch & Ad-hoc Store Insertion (动态调度智能体与沿街走廊插单)

### 1. 业务痛点：实际走访与静态计划的严重脱节
对广州海珠荔湾片区真实的 9,760 条打卡流水分析表明：**一线业代的实际拜访与静态计划存在巨大鸿沟**。
以 09 线路（梁健满）为例：全月实际打卡 1,063 次中，**临时新增拜访高达 368 次（占比 34.6%）**。由于缺乏实时智能指引，业代在面对临时加店时依靠个人记忆折返跑、重复绕路严重，单日骑行甚至突破 80~100 公里。

### 2. 核心对比三指标与实测成效（全月 23 个法定工作日）
| 评估维度 | 全月实测总里程 | 单日响应耗时 | 业务场景与评价 |
|---|:---:|:---:|---|
| **对比 1：人类业代实际走法（现状）** | **13,417.7 km**（09 线 1,240.4） | — | 人类凭直觉边走边加，折返跑、逆行绕路极其严重 |
| **对比 2：事后理论全局最优（静态上限，09 线口径）** | **578.4 km** | 20~35 ms | 事后全量已知的理论极限下界 |
| **对比 3：Agent 动态在途规划（实时副驾）** | **5,632.0 km**（09 线 557.7） | **75–330 μs 实测** | **全办净省 7,785.7 km（−58.0%）；09 线 −55.0%** |

### 3. 近 3 年顶刊学术理论支撑 (2023–2026)
- **《Transportation Science》2024 顶刊**：Cook, Held, Helsgaun (2024). *Constrained Local Search for Last-Mile Routing*. 58(1): 12–26 (Amazon 冠军方案) —— 人类优秀司机的本质是沿街道走廊（Street Corridor）分解，速度提升 2~3 个数量级且消除反直觉折返。
- **《Transportation Research》2025**：*Vehicle Routing Problem with En-Route Delivery* —— 在途通行弧段投影与一维单调微链拼接（En-route Chain Splicing）。
- **《EJOR》2023–2024**：Pillac et al. *Batch Dynamic Vehicle Routing* —— 走廊投影+接缝抛光范式。

### 4. 交互式可视化对比看板
运行本地服务即可体验完整的动态调度交互大盘：
- **实际走访 vs Agent 动态插单看板**：`http://localhost:8899/actual_vs_agent_comparison.html`
  - **高德地图风格主要途经走廊卡片**：直观展示主要途经道路流向、跨街折返警告标签与单向清扫走廊；
  - **全真道路网连线**：提取自 OpenStreetMap 真实骑行路网（单日 300~2,000+ 道路拐点）；
  - **行进方向小箭头**：直观展现人类轨迹的混乱折返与 Agent 路线的单向平滑推进；
  - **左右独立滑动条与动态单步播放器**：支持双屏同步推进或单手独立调节对比任意两站；
  - **花瓣微偏移算法 (Spider-Jitter)**：彻底解决同一市场/大楼内连续打卡导致的序号重叠遮挡问题；
  - **23 工作日全量下钻**：支持点选全月任意一天并查看 Agent 自然语言副驾调度指引。
- **计划优化主大盘**：`http://localhost:8899/index.html`
- **详细技术文档**：参见 `docs/AGENTIC_DYNAMIC_DISPATCH_GUIDE.md`。
------------------------------------------------------------------------


### 5. MO-ALNS v4 三目标帕累托前沿（基准 = v3 计划优化结果）

以 **v3 月度优化结果为基准**（计划数据），NSGA-II + ALNS 在三维目标上搜索帕累托前沿：

| 维度 | 定义 | 业务含义 |
|---|---|---|
| f₁ 总里程 | Σ day_km | "省多少油钱" |
| f₂ 再改动量 | 相对 v3 被挪的店数 | "已定日程还要再改几家" |
| f₃ 均衡度 | 每日拜访量变异系数 CV | "有没有哪天特别累" |

（原第四目标"跨区率 f₄"随 Clustered TSP 场景否决一并废弃）

**关键发现**：CP-SAT 精确解（锁死日期只排顺序）= 326.6 km；v3（允许改日期）= 263.2 km。**差值 63.4 km（−19.4%）即"改日期"本身的数学价值**；且 v3 双维度支配 CP-SAT，成为前沿"0 改动=里程最优"的重合端点。

09 线实测（2587 代，36 个非支配解）：

| 方案 | 里程 (km) | 相对 v3 再改动 | CV 均衡度 |
|---|:---:|:---:|:---:|
| 🔒 保守型 = v3 基准 | **263.2** | **0 店** | 0.320 |
| ⭐ 推荐型(膝点) | 359.2 | 35 店 (21.5%) | 0.224 |
| ⚖️ 均衡型 | 447.0 | 83 店 (50.9%) | **0.013** |

交互页面：`http://localhost:8899/v4_pareto.html`

### 6. 项目文档索引

| 文档 | 内容 |
|---|---|
| `docs/COMPARISON_REPORT_TSP_V1_V3.md` | 月度日程优化：TSP vs ALNS v1 vs v3（以 TSP 为诚实基线） |
| `docs/COMPARISON_REPORT_ACTUAL_VS_AGENT.md` | 实际走访 vs Agent 动态插单（全办 10 线，50.6% 提效） |
| `docs/COMPARISON_REPORT_V4_PARETO.md` | MO-ALNS v4 三目标帕累托（基准=v3；"改日期=63.4km"定价 + 花钱买均衡曲线） |
| `docs/MANUAL_10_DAYS_AUDIT_REPORT.md` | 10 天人工白盒抽查审计（可直接用于客户答辩） |
| `docs/AGENTIC_DYNAMIC_DISPATCH_GUIDE.md` | Agentic 动态调度技术专著 |
| `docs/ALGORITHM_GUIDE.md` | 全部 8+ 算法的技术指南（含 20 篇文献） |
| `docs/V4_DESIGN_V2_MULTIOBJECTIVE.md` | V4 多目标重设计文档（NSGA-II + ALNS） |


---

## Where it fits at TopPrism

``` text
Business World Model
        ↓
customer · geography · travel · service · policy
        ↓
Visit Scheduling Optimizer
        ↓
recurring visit decision
        ↓
field execution / SFA / route navigation
        ↓
actual travel + service feedback
```

This repository is a **Decision Engine**, not the entire DRTM product.

Related TopPrism capabilities can provide entity resolution, spatial
structure, opportunity scoring, execution interfaces, and feedback loops
around this optimization core.

------------------------------------------------------------------------

## Quick start

``` bash
git clone https://github.com/topprismdata/visit-scheduling-optimizer.git
cd visit-scheduling-optimizer

pip install ortools numpy pandas matplotlib

python examples/synthetic_pvrp_cg.py
```

The synthetic example contains no real customer data.

------------------------------------------------------------------------

## Core implementation

  -----------------------------------------------------------------------
  Component                           Role
  ----------------------------------- -----------------------------------
  `algos/pvrp_cg/travel.py`           route cost, Held--Karp TSP, NN +
                                      2-opt, Haversine

  `algos/pvrp_cg/calibration.py`      travel-time calibration

  `algos/pvrp_cg/solver.py`           restricted master, dual-guided
                                      column generation, CP-SAT

  `algos/pvrp_cg/baselines.py`        ALNS comparison baseline

  `examples/`                         synthetic reproducible examples

  `docs/algorithm.md`                 mathematical and algorithmic detail

  `docs/paper_draft.md`               methodology-oriented working paper
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Data and privacy

This public repository intentionally excludes:

-   customer raw data;
-   real customer coordinates;
-   proprietary business rules;
-   internal identifiers;
-   customer-specific configuration files.

The published industry study is anonymized and reported only in
aggregate.

------------------------------------------------------------------------

## Boundaries & limitations

Current limitations include:

1.  heuristic rather than exact pricing in column generation;
2.  deterministic planning assumptions for travel and service time after
    calibration;
3.  no stochastic service-duration model in the current public
    framework;
4.  no joint multi-representative optimization in the current public
    solver;
5.  aggregate study evidence is not equivalent to a production SLA.

Potential extensions include exact pricing, rolling-horizon re-planning,
stochastic service times, time windows, and multi-representative
coordination.

------------------------------------------------------------------------

## Repository structure

``` text
visit-scheduling-optimizer/
├── algos/pvrp_cg/
├── docs/
├── examples/
├── src/
├── README.md
└── LICENSE
```

Detailed method explanations live in `docs/`; the README stays the
public decision-and-evidence entry point.

------------------------------------------------------------------------

## TopPrism metadata

The `topprism.yaml` shipped with this repository declares:

``` yaml
topprism:
  purpose: customer-decision
  capability: visit_scheduling
  platform_layer: decision_engine
  maturity: applied
  evidence:
    type: anonymized-operational-data
    scope: "7 representatives, 235 customers; aggregate statistics only"
  customer_data_in_repo: false
  product_context:
    - drtm
    - field_sales
```

------------------------------------------------------------------------

## Citation

If you use the methodology in academic work, see the citation
information in the repository and `docs/paper_draft.md`.

## License

MIT.

## Contributing

Contributions are welcome, especially around exact pricing, stochastic
planning, time-window extensions, rolling-horizon planning, and
multi-representative optimization. Do not submit customer-identifiable
data.
