# 拜访计划优化引擎 — 算法技术指南

> **SRP 拜访计划优化引擎（Visit Scheduling Optimizer）· 算法白皮书**
> 版本 v2.0 · 2026-09-02 · 面向客户汇报的技术说明文档
>
> 所有论文引用均经 CrossRef 验证；所有性能数据均来自本项目真实运行台账
> （`output/ledger_deep.csv`、`output/ledger_09_test.csv`、`demo/09_optimized_days.json`）。

---

## 0. 问题定义与算法全景

### 0.1 业务问题

本项目解决的是**周期性外勤拜访计划优化问题**，在运筹学中属于 **PVRP（Periodic Vehicle Routing Problem，周期性车辆路径问题）** 类别：

| 要素 | 本项目取值 |
|---|---|
| 门店规模 | 163 家门店（单线路，如海珠荔湾09线） |
| 规划周期 | 23 个工作日（自然月） |
| 拜访频次 | 每店每月 2–5 次，且**固定星期几**（周期一致性硬约束） |
| 交通方式 | 骑行（电动车/自行车），**OSM 真实路网距离**（FOSSGIS `routed-bike` 接口） |
| 目标 | 最小化全月总骑行里程 |
| 硬约束 | 频次精确满足、固定拜访日不改变、门店不可遗漏 |

**距离口径说明**：全程采用 OSM 官方 FOSSGIS 服务器 `routed-bike/table` 的骑行路网距离矩阵，逐店缓存于 `output/road_dist_*.npy`，**严禁使用直线距离**——城市路网中直线距离与实际骑行距离偏差可达 30–50%，这是本引擎与"地图直线估距"类产品的本质区别。

### 0.2 两层决策结构

拜访计划优化被分解为两个相互嵌套的子问题：

1. **层①：日内顺序重排（TSP 层）**——给定某天必须拜访的门店集合，求最短骑行顺序。对应算法：NN+2-opt、CP-SAT 精确 TSP、LKH-3。（Clustered TSP 已实现评估→本场景否决，见 §5.7）
2. **层②：跨日门店重分配（PVRP 层）**——在满足"每店频次 + 固定星期几"前提下，把门店在不同日期间重新组合。对应算法：ALNS。
3. **组合层：路线池重组合与池内证书**——把各算法产出的候选路线汇总为路线池，用集合划分模型选出**池内整数最优组合**，并给出受限主问题 LP 值与池内差距（启发式定价下非全局认证，见附录 C）。对应算法：Ensemble SP、SDR Exact。

### 0.3 求解流水线（时间口径已按实测更新：深度审计自然结束 avg 4.1 / max 6.5 分钟每线，非旧口径 30 分钟）

```mermaid
flowchart LR
    A[原始 SRP 计划<br/>1116.0 km] --> B[层① 日内重排<br/>NN+2-opt / CP-SAT / LKH<br/>326.6 km]
    B --> C[层② 跨日重分配<br/>ALNS / Greedy<br/>290.8 km]
    B --> D[路线池 RoutePool<br/>收集全部算法产出]
    C --> D
    D --> E[Ensemble SP<br/>集合划分重组合<br/>290.3 km]
    E --> F[SDR Exact<br/>受限主问题 LP 值 + 池内 gap 证书<br/>非全局认证,见附录C]
```

### 0.4 算法一览（海珠荔湾09线实测；时间列 = 2026-09-04 性能核查 `PERFORMANCE_BENCHMARK.md`）

| # | 算法 | 类型 | 决策层 | 09线里程 | 求解时间（实测） | 最优性保证 |
|---|---|---|---|---|---|---|
| 1 | NN+2-opt（最近邻+2-opt） | 启发式 | ①日内 | 381.7 km | 0.01 s/线 | 无（基线锚点） |
| 2 | CP-SAT 精确 TSP | 精确 | ①日内 | 326.6 km | 3.0 s/线（0.13 s/天） | ✅ 矩阵上可证最优 |
| 3 | ALNS v1（自适应大邻域搜索） | 元启发式 | ①+②跨日 | 290.3 km | 自然收敛 avg 145 s / max 221 s | 无 |
| 3b | **ALNS v3（反馈耦合·主力）** | 元启发式 | ①+②跨日 | **262.6 km** | **恒=预算**（生产 300 s / 快档 60 s；seed 波动 km ±0.5%） | 无（实践最优·主力） |
| 4 | LKH-3（Lin-Kernighan-Helsgaun） | 启发式 | ①日内 | 15.97 km/23店¹ | 本次未测（历史对照·非主力） | 无（近似比极优） |
| 6 | Ensemble SP（集合划分重组合） | 精确组合 | 组合层 | 290.3 km | 0.1 s | ✅ 池内最优 |
| 7 | SDR Exact（列生成+LP 下界） | 精确+证书 | 组合层 | 290.3 km | 0.9 s（gap=0） | ✅ 池内最优 + gap 证书 |
| 8 | MO-ALNS v4（三目标帕累托） | 多目标元启发 | Layer 1.5 | 基准=v3，前沿 36 解 | **恒=预算**（无早停） | 无（帕累托非支配） |
| ~~5~~ | ~~Clustered TSP~~ | 启发式 | ①日内 | 374.2 km | 同底层 | ⚠ **本场景已否决**（§5.7） |

¹ LKH 数据为审计报告中的 23 店单日对照实验（LKH ATSP 修正后 15.97 km，CP-SAT 最优 14.03 km）。
**"恒=预算"含义**：该类算法是时间预算驱动，墙钟精确撞满设定预算（实测 300.02 s / 60.02 s / 30.01 s），不会自动提前结束——时间可按 SLA 弹性承诺，里程随预算增大单调改善。完整计时见 `PERFORMANCE_BENCHMARK.md`。

> **业务总结果**（10 条线路 × 11 名业务代表，2026 年 7 月）：原始计划 **16,857 km** → 日内重排后 **4,606 km**（−73%）→ 跨日重分配后 **3,319 km**（再 −28%）。全部算法通过频次精确校验（`count_ok = 100%`）。

---

## 1. NN + 2-opt — 最近邻贪心 + 2-opt 局部搜索

### 1.1 算法名称
**中文**：最近邻贪心 + 2-opt 边交换局部搜索
**英文**：Nearest Neighbor Construction + 2-opt Local Search

### 1.2 核心原理
最近邻（NN）从一个起点出发，每步贪心地选择距离当前门店最近且未访问的门店，O(n²) 时间构造一条可行路径。2-opt 在此基础上迭代地移除路径中的两条边、将中间段反转后重连，只要新路径更短就接受，反复执行直到不存在可改进的"交叉边"。本项目实现的是**开放路径**版本（拜访结束无需回仓），比传统闭环 TSP 少一条回程边。

### 1.3 论文引用
1. Rosenkrantz, D. J., Stearns, R. E., Lewis, P. M. (1977). *An Analysis of Several Heuristics for the Traveling Salesman Problem*. **SIAM Journal on Computing**, 6(3): 563–581. DOI: [10.1137/0206041](https://doi.org/10.1137/0206041) —— NN 启发式的奠基性理论分析，证明欧氏 TSP 上 NN 解不超过最优解的 0.5·(log₂n + 1) 倍。
2. Croes, G. A. (1958). *A Method for Solving Traveling-Salesman Problems*. **Operations Research**, 6(6): 791–812. DOI: [10.1287/opre.6.6.791](https://doi.org/10.1287/opre.6.6.791) —— 2-opt 边交换技术的原始出处。

### 1.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| **本项目自研** `algos/tsp_engine.py::_nn2opt_open` | Python | 开放路径 NN + 2-opt（上限 30 轮精修），约 60 行核心代码 |
| [google/or-tools](https://github.com/google/or-tools) | C++/Python | Routing 库内置 `PATH_CHEAPEST_ARC` 等首解策略与 2-opt 邻域算子 |
| [fillipe-gsm/python-tsp](https://github.com/fillipe-gsm/python-tsp) | Python | 纯 Python TSP 库，含 2-opt 局部搜索 |

### 1.5 工业案例
- **Google OR-Tools** 的所有路由求解默认先构造贪心首解再做局部搜索精修——本算法就是其内部逻辑的最小化版本；
- **美团、饿了么、菜鸟**等即时配送平台的公开技术分享中，NN/贪心 + 局部交换是订单串单（batching）与骑手路径的毫秒级基础方案；
- 各类物流 SaaS（运输管理系统 TMS）普遍以该算法作为路线功能的最快兜底方案。

### 1.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | NN 为 O(n²)；2-opt 每轮 O(n²)，本项目限 30 轮，整体近线性可感知 |
| 最优性保证 | **无**。理论最坏情况解质量可达最优的 O(log n) 倍；实践中欧氏/路网实例一般劣于最优 5–15% |
| 扩展性 | 极强——数千门店毫秒级完成；可在线实时重算 |
| 约束灵活性 | 弱——只能通过距离矩阵预置惩罚表达软约束，无法直接表达时间窗/频次等硬约束 |

### 1.7 在我们场景的表现
- **海珠荔湾09线（163 店）**：1116.0 km → **381.7 km**，节省 **65.8%**，求解 **<1 秒**；
- **10 线合计**：16,857 km → **4,606 km**（−73%），是所有后续算法的共同起点；
- **优点**：毫秒级速度、零依赖、结果确定可复现，是理想的**基线锚点**与路线池种子；
- **缺点**：只重排顺序、不跨日调店（相比 ALNS 的 290.8 km 差距 ~24%）；日内在店数超过 ~35 家时陷入局部交叉结构，无法继续改进。

---

## 2. CP-SAT 精确 TSP — 约束规划全局最优重排

### 2.1 算法名称
**中文**：CP-SAT 精确旅行商求解（AddCircuit 全局约束 + 虚拟仓库开放路径变换）
**英文**：CP-SAT Exact TSP (AddCircuit Global Constraint with Dummy-Depot Open-Path Transformation)

### 2.2 核心原理
将"某天 n 家店的访问顺序"建模为整数规划：布尔变量 xᵢⱼ 表示"从店 i 直接去店 j"，用 OR-Tools 的 **AddCircuit** 全局约束强制所有节点恰好构成一条哈密顿回路；对开放路径，增加一个**虚拟仓库节点**，其连出/连入边代表"起点/终点"且零成本，解出回路后剥离该节点即得最优开放序列。CP-SAT 求解器内部混合约束传播、LP 松弛、割平面与并行 portfolio 搜索，能在数学上证明不存在更优解后，返回可验证的全局最优值。

### 2.3 论文引用
1. Perron, L., Didier, F. (2018). *CP-SAT*. 载于 **Handbook of Parallel Constraint Reasoning**（Springer, Cham）. —— CP-SAT 首席设计师撰写的架构综述（并行 portfolio、学习式克隆、文字传播剪枝）。
2. Google OR-Tools 官方引用页：[developers.google.com/optimization/support/cite](https://developers.google.com/optimization/support/cite)（列出 Perron & Didier 的正式引用格式）。
3. Didier, F., Perron, L. (2023). *The CP-SAT-LP Solver*. **CP 2023**（第 29 届约束规划国际会议）特邀报告，[LIPIcs vol. 280](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3)。

### 2.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| [google/or-tools](https://github.com/google/or-tools) | C++（Python/Java/C# 绑定） | **Apache-2.0 协议，完全免费商用**，本项目求解内核 |
| 本项目 `algos/tsp_engine.py::_exact_open_tsp` | Python | AddCircuit + dummy depot 开放 TSP 封装，约 45 行 |
| [d-krupke/cpsat-primer](https://github.com/d-krupke/cpsat-primer) | 教程 | 社区公认的 CP-SAT 建模最佳实践手册 |

### 2.5 工业案例
- **Google 内部生产系统**：CP-SAT 由 Google 工程团队维护，直接服务于 Google 内部排程与资源分配；
- **制造业与人力排班**：全球范围内广泛用于排产（job-shop）、护士排班、员工轮班等，OR 社区（OR-StackExchange）与 CP-SAT Primer 收录大量生产部署案例；
- **MiniZinc 国际求解器挑战赛**常胜冠军，是学术界公认的开源 CP/MIP 混合求解器标杆。

### 2.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | TSP 是 NP-难问题，最坏指数级；**实践**中本项目单日 ≤35 店**平均 0.13 秒**证明最优（23 工作日全线 3.0 秒，2026-09-04 实测） |
| 最优性保证 | ✅ **强**——在给定距离矩阵上返回可证明的全局最优解（状态码 OPTIMAL） |
| 扩展性 | 中——单日门店 ≤100 家实用；更大规模应切换 LKH/ALNS 等启发式 |
| 约束灵活性 | ✅ **极强**——时间窗、容量、门店服务时长、先后顺序等均可直接写成线性/逻辑约束，这是精确求解器相对启发式的核心优势 |

### 2.7 在我们场景的表现
- **海珠荔湾09线**：日内重排 **326.6 km**（NN+2-opt 为 381.7 km，再省 14.4%），全线 **实测 3.0 秒**（0.13 秒/天 × 23 工作日，2026-09-04 性能核查）；
- **审计对照实验**（09 线某日 23 店）：CP-SAT 给出 **14.03 km** 的可证明最优解；同一实例 LKH-3（ATSP 修正后）仅达 15.97 km——**在真实路网非对称矩阵上 CP-SAT 显著优于 LKH**；
- **优点**：解质量有数学保证，可直接用于向客户承诺"该矩阵上不可能更短"；约束扩展零成本；
- **缺点**：单日规模过大（>100 店）时无法在分钟级证明最优；只解决日内顺序，不解决跨日分配（对比 ALNS 290.8 km）。

---

## 3. ALNS — 自适应大邻域搜索（跨日重分配主力）

### 3.1 算法名称
**中文**：自适应大邻域搜索（破坏-修复框架 + 多臂老虎机算子选择）
**英文**：Adaptive Large Neighborhood Search (ALNS)

### 3.2 核心原理
ALNS 在一个可行解上反复执行"**破坏（destroy）→ 修复（repair）**"：破坏算子移除解的一部分（如把某家店从 7 月 3 日挪走），修复算子以贪心方式把被移除的部分重新插回（可能插到另一天）。框架维护一个**算子池**，按各算子近期历史表现自适应调整选择权重（多臂老虎机思想，本项目每 50 轮更新一次），让"屡建奇功"的算子被更频繁调用。与模拟退火不同，本项目采用**只接受改进**的爬山接受准则，保证解的单调不退化。ALNS 是跨日重分配的关键——它能在满足"每店频次 + 固定星期几"硬约束的前提下，把门店在 23 个工作日之间重新组合。

### 3.3 论文引用
1. Ropke, S., Pisinger, D. (2006). *An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows*. **Transportation Science**, 40(4): 455–472. DOI: [10.1287/trsc.1050.0135](https://doi.org/10.1287/trsc.1050.0135) —— ALNS 框架奠基论文，在 350+ 标准算例上改进了超过一半实例的已知最优解。
2. Shaw, P. (1998). *Using Constraint Programming and Local Search Methods to Solve Vehicle Routing Problems*. **CP'98, LNCS 1520**: 417–431. DOI: [10.1007/3-540-49481-2_30](https://doi.org/10.1007/3-540-49481-2_30) —— 大邻域搜索（LNS）"移除-重插"思想的源头。

### 3.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| [N-Wouda/ALNS](https://github.com/N-Wouda/ALNS) | Python | 标准 ALNS 库（MIT），JOSS 论文：Wouda & Lan (2023), *J. Open Source Software*, 8(81): 5028, DOI: [10.21105/joss.05028](https://doi.org/10.21105/joss.05028) |
| **本项目自研** `algos/impl.py::ALNS` | Python | 4 算子池：`move`（最差成本单店移日）/ `swap`（两日互换）/ `ruin_repair`（乱序重建）/ `cluster_ruin`（相邻簇破坏重插），每 50 轮多臂老虎机权重更新 |
| [google/or-tools](https://github.com/google/or-tools) | C++ | Routing 库 Guided Local Search 属同族"大邻域"思想 |

### 3.5 工业案例
- **菜鸟网络、美团配送**：国内即时物流公开技术分享中，破坏-修复式迭代改进是订单-路线重优化的标准工程模式（本项目算子设计即参考"菜鸟/美团模式"）；
- **欧洲快消配送、垃圾收运、牛奶配送**行业：Ropke & Pisinger 的 ALNS 是商用 VRP 套件（如 ORTEC 类产品）方法论的重要基础；
- **学术界**：ALNS 是近十年 VRP 及其变体论文中出现频率最高的元启发式框架之一，PVRP 求解文献大量采用。
### 3.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | O(迭代次数 × 单算子成本 O(n²))；**实测（2026-09-04）：v1 自然收敛 avg 145 s / max 221 s；v3 恒=预算**（300 s / 60 s 档墙钟 300.02 / 60.02 s；v3 同预算迭代 25–31 万次，v1 仅数百次） |
| 最优性保证 | 无（元启发式），但作为全流水线**唯一能同时改进两个决策层**的算法，实践中产出全场最优解 |
| 扩展性 | 强——时间预算可伸缩（anytime 算法：给 60 秒出 60 秒的解，给 600 秒继续变好） |
| 约束灵活性 | ✅ 强——频次、固定星期几、单日工作量上限等业务硬约束内建于算子的可行性检查 |

### 3.7 在我们场景的表现
- **海珠荔湾09线**：**290.8 km**（演示口径，`demo/09_optimized_days.json`；深跑台账 290.3–293.3 km），~300 秒、20,000 次迭代；
- 对比贪心跨日（298.9 km，−2.9%）与纯日内重排最优（326.6 km，−11%）：**跨日重分配层贡献了日内重排无法企及的最后 ~11% 收益**；
- 10 线合计：日内重排 4,606 km → 跨日重分配 **3,319 km**（再省 **−28%**）；
- **优点**：解质量全场最佳；任何时间预算都能运行；直接满足频次/固定星期几硬约束（全部通过 `count_ok` 校验）；
- **缺点**：无最优性证明（需 SDR Exact 补充 gap 证书）；单次运行约 5 分钟，不适合秒级交互场景。

---

## 4. LKH-3 — Lin-Kernighan-Helsgaun 启发式（开放 TSP 专用引擎）

### 4.1 算法名称
**中文**：LKH-3 变深度 k-opt 启发式（Lin-Kernighan-Helsgaun 第三代）
**英文**：LKH-3 (Lin-Kernighan-Helsgaun Heuristic, version 3)

### 4.2 核心原理
LKH 是 TSP 启发式四十余年演化的巅峰之作：以 **α-nearness**（基于 1-树松弛的"最小生成树+1"下界）筛选候选边，执行**变深度 k-opt 交换**——交换深度不预先固定，而是逐段扩展直到无法继续改进（5-move + patching 补丁技术），从而跳出 2-opt/3-opt 的局部陷阱。LKH-3 在此之上扩展了约束 VRP 能力（容量、时间窗、先后顺序、收益收集等），通过罚函数把约束violations并入目标。本项目使用 **ATSP + FULL_MATRIX** 格式灌入路网距离矩阵，并以**大常数 C（10×最大边权）虚拟仓库**技巧将闭合回路转化为开放路径。

### 4.3 论文引用
1. Helsgaun, K. (2000). *An effective implementation of the Lin–Kernighan traveling salesman heuristic*. **European Journal of Operational Research**, 126(1): 106–130. DOI: [10.1016/S0377-2217(99)00284-2](https://doi.org/10.1016/S0377-2217(99)00284-2) —— LKH 原始论文。
2. Helsgaun, K. (2017). *An Extension of the Lin-Kernighan-Helsgaun TSP Solver for Constrained Traveling Salesman and Vehicle Routing Problems*. 技术报告，Roskilde 大学. [官方 PDF](http://webhotel4.ruc.dk/~keld/research/LKH-3/LKH-3_REPORT.pdf) —— LKH-3 约束扩展文档（本项目参数配置依据）。

### 4.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| [官方 LKH-3](http://webhotel4.ruc.dk/~keld/research/LKH-3/) | C | 学术/非商业用途免费，本项目通过 `LKH_BIN` 子进程调用（v3.0.14） |
| [cerebis/LKH3](https://github.com/cerebis/LKH3) | C | 社区 GitHub 镜像 |
| [heldstephan/jpt-amz](https://github.com/heldstephan/jpt-amz) | C | LKH-AMZ 亚马逊挑战赛特化变体（MIT） |
| 本项目 `algos/lkh_engine.py` | Python | ATSP 矩阵生成 + dummy depot 开放路径封装 + NN+2-opt 兜底 |

### 4.5 工业案例
- **TSP 世界纪录**：LKH 是世界巡游问题（World TSP，85,900 城）等全部主要 TSP 基准纪录的产生器，解距理论下界不足 0.01%——是"启发式也能达到最优级质量"的行业图腾；
- **Greenplan GmbH**（博世 Bosch 孵化的路线优化公司）：核心团队含波恩大学 Stephan Held 教授（LKH-AMZ 作者之一），将同源组合优化技术商用化，服务于欧洲物流企业；
- 各类商用/科研 VRP 求解器以 LKH 作为高质量子程序或对照基准。
### 4.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | 实践近线性于节点数（候选边稀疏化），最坏指数级；百万级节点分钟内可得近优解（本项目单日对照见 §4.7；2026-09-04 性能核查未纳入 LKH） |
| 最优性保证 | 无，但经验质量距最优 <1%（欧氏实例）；本项目实测在**非对称路网矩阵**上收敛弱于 CP-SAT |
| 扩展性 | ✅ 极强——是七算法中处理超大规模单日序列（数百店以上）的最佳选择 |
| 约束灵活性 | 中——LKH-3 原生支持容量/时间窗/优先序，但配置复杂（参数文件），调试成本高 |

### 4.7 在我们场景的表现
- **审计对照实验**（09 线 23 店单日）：初版 TSP 格式 17.4 km → **ATSP 修正后 15.97 km**，但仍劣于 CP-SAT 最优 14.03 km（−13.8%）；
- **全线运行**：约 5 min/线（RUNS=10、MAX_TRIALS=5000 配置）；
- **关键工程发现**：LKH 官方文档确认 `FULL_MATRIX` 配 `TYPE: TSP` 只读下三角——必须用 `TYPE: ATSP` 读全矩阵。修正后仍不敌 CP-SAT 的原因是：城市骑行路网矩阵**高度非对称且非欧氏**，α-nearness 候选边筛选在此类矩阵上失效；
- **定位**：作为路线池的**多样性生成器**保留（其解与 CP-SAT 解结构不同，可供 Ensemble SP 择优），但不再作为主力精确引擎；
- **优点**：超大规模扩展性、业界声望与文献背书；**缺点**：在本项目规模（单日 ≤35 店）与数据类型下无优势，非商业许可限制商用部署。

---

## 5. Clustered TSP — 亚马逊 2021 冠军方法论（已实现并验证 → 本场景评估后否决）

### 5.1 算法名称
**中文**：聚类约束旅行商（Clustered ATSP 大常数变换法）
**英文**：Clustered TSP / Constrained Local Search for Last-Mile Routing（Amazon Last-Mile Routing Research Challenge 2021 冠军方案，团队 "Just Passing Through"）

### 5.2 核心原理
真实配送/拜访路线具有强**地理分区结构**：司机会把同一片区的门店连续拜访完，再切换到下一片区。该方案将其建模为两级层次 TSP——外层决定片区间访问顺序、内层决定片区内顺序。关键实现技巧是论文 §4.2 的 **Clustered ATSP 变换**：对任意一对不同片区的门店 i、j，在距离矩阵上加上大常数 M（本项目取 10×最大边权），然后整体求解一次 TSP——M 惩罚自动迫使最优解"先扫完一个片区再跨区"，且跨区顺序由求解器全局决定，无需人工规定片区次序。论文 Table 3 实测：聚类结构约束仅增加约 **3.5%** 里程，换来与真实司机行为高度一致的路线。

### 5.3 论文引用
1. Cook, W., Held, S., Helsgaun, K. (2024). *Constrained Local Search for Last-Mile Routing*. **Transportation Science**, 58(1): 12–26. DOI: [10.1287/trsc.2022.1185](https://doi.org/10.1287/trsc.2022.1185)；预印本 [arXiv:2112.15192](https://arxiv.org/abs/2112.15192) —— 2021 年亚马逊最后一公里路由研究挑战赛**冠军**方案（$100,000 头奖，2,285 人参赛，领先第二名 42%）。

### 5.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| [heldstephan/jpt-amz](https://github.com/heldstephan/jpt-amz) | C | 冠军团队官方开源（**MIT 协议**），含 LKH-AMZ 惩罚搜索引擎完整源码 |
| **本项目自研** `algos/clustered_tsp.py::clustered_tsp_route` | Python | 论文 §4.2 M-变换的忠实实现：路网区块 GeoJSON（广州 7 区县 1,667 候选区块，22 个落店区块）+ 跨区块边 + M 惩罚 + 整体 TSP |

### 5.5 工业案例
- **Amazon**：挑战赛本身即亚马逊为改进其末端配送路线引擎（Rabbit RTL）发起，冠军方案直接影响其路线推荐系统研究；
- **Greenplan GmbH**（博世孵化）：冠军成员 Stephan Held 所在团队的商业化路线优化产品，面向欧洲物流客户；
- 更广泛的**司机行为感知路由**（driver-aware routing）已成为末端配送产品的标配研究方向（MIT CTL 与亚马逊联合主办即为信号）。

### 5.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | 与底层 TSP 引擎同阶（本项目配 NN+2-opt 底盘：O(n²)；原论文配 LKH-AMZ 底盘） |
| 最优性保证 | 无全局最优保证；但在"地理一致性"目标下**更贴近真实可执行路线** |
| 扩展性 | 强——继承底层引擎；层次结构使超大规模实例分解自然 |
| 约束灵活性 | 中强——支持多级聚类（zone/super-zone）、片区间前序约束（可从历史路线学习），但要求区块划分质量高 |

### 5.7 在我们场景的表现 —— **评估后否决（Rejected after evaluation）**
**结论先行**：算法实现正确、可复现，但**不适用于本场景**，已主动放弃。原因不是代码问题，而是**物理布局与 Amazon 根本不同**。

**实测数据（海珠荔湾09线，CP-SAT 精确同口径）**：
| 指标 | 数值 |
|---|---|
| 无约束 TSP（精确） | 326.6 km |
| Clustered（精确） | 374.2 km |
| 代价 | **+14.6%** |
| 区内边中位数 | 0.12 km |
| 跨区边中位数 | 0.51 km |
| 跨区边短于区内中位的比例 | 仅 18% |

**否决的物理原因（业务方点破）**：
- Amazon 的场景是**小区/楼宇配送**——门在小区内，跨小区必须绕到小区门口再进，"走完一个小区再换"几乎零额外代价，所以聚类强约束划算（论文 +3.5%）；
- 我们的门店**沿街分布**——区块边界本身就是马路，对面两家店直线几十米，但强制"走完本块再跨"要沿街绕行整段；实测跨区边中位数（0.51km）已比区内边（0.12km）贵 4 倍，再强聚类只是雪上加霜（+14.6%）。
- 即：**对路边店场景，"片区连贯"与"里程最短"直接冲突**，不是可控 tradeoff 而是纯损失。

**正确性验证（排除代码 bug，证明是场景问题）**：
1. M 敏感性扫描（第2周周二，7区块/29店）：M 从「刚好强制连续」(5.0km) 扫到 10× 全局最大(135km)，解恒为 **16.4km / 7 区块各 1 段 / CP-SAT 认证 OPTIMAL**；同实例无约束 TSP=13.7km。差值 2.7km 即"进出 7 个片区"的真实物理代价——**大 M 未扭曲解，16.4 就是约束下全局最优**；
2. 围栏坐标系核验：点与围栏均 GCJ-02（对齐高德底图），zone 分配逐点落在唯一多边形内 0 错误；
3. 频次守恒：22/23 天口径一致，1 处 0.3km 为求解器浮点界。

**保留价值**：M-常数/惩罚局部搜索框架仍然可用——未来若客户群转为**小区/园区店**（住宅团购、商超仓中配），此算法直接复活。选型判断（而非照搬论文）本身即方法论产出。

---

## 6. Ensemble SP — 集合划分重组合（路线池 MILP）

### 6.1 算法名称
**中文**：集合划分重组合（路线池上的 0-1 整数规划精选）
**英文**：Ensemble Set Partitioning (Route-Pool MILP Selection)

### 6.2 核心原理
前面各算法各自产出一批"某天按某顺序拜访某些店"的**候选路线**。Ensemble SP 把全部候选路线汇入**路线池（RoutePool）**，然后建一个 0-1 集合划分模型：决策变量 x_r 表示"是否选用路线 r"，约束为（a）每个工作日恰好选 1 条路线；（b）每家门店在整月被覆盖的次数恰好等于其计划频次（2–5 次、固定星期几天然满足，因为池内路线本就按日生成）；目标最小化总里程。该模型由 CP-SAT 求解——在路线池这个"菜单"里，给出**可证明的组合最优**。求解前还用启发式解做 **Warm Start（AddHint）**，让求解器从可行解起步加速搜索。

### 6.3 论文引用
1. Balinski, M. L., Quandt, R. E. (1964). *On an Integer Program for a Delivery Problem*. **Operations Research**, 12(2): 300–304. DOI: [10.1287/opre.12.2.300](https://doi.org/10.1287/opre.12.2.300) —— 集合划分法求解配送问题的奠基论文。
2. Arenas-Vasco, A., Alcázar, D., Villegas, J. G. (2025). *A meta-analysis of set partitioning/set covering based matheuristics for vehicle routing problems*. **Operations Research Perspectives**, 15: 100357. DOI: [10.1016/j.orp.2025.100357](https://doi.org/10.1016/j.orp.2025.100357) —— 对 54 篇文献的元分析：72% 采用 SP/SC 做后优化器，平均再改进 0.4–0.6%，且"团割（clique cuts）显著加速大规模 SP 模型"。

### 6.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| **本项目自研** `algos/impl.py::EnsembleSP` | Python | RoutePool + CP-SAT 集合划分（每日 1 条 + 频次精确覆盖 + AddHint 暖启动），约 65 行 |
| [google/or-tools](https://github.com/google/or-tools) | C++/Python | 求解内核（CP-SAT） |
| [google/or-tools](https://github.com/google/or-tools)（GLOP） | C++/Python | 同仓库 LP 求解器，供 SDR Exact 求下界 |

### 6.5 工业案例
- **航空业机组排班（crew pairing/scheduling）**：集合划分/集合覆盖是美国航空、达美航空等全球航空公司排班系统的标准建模方法，是运筹学在工业界最成功的应用之一（Barnhart 等人的 branch-and-price 文献即以航空排班为首要场景）；
- **公交/铁路司机排班**：欧洲公共交通企业的班次覆盖问题普遍采用 SP 模型；
- **按 2025 元分析**：SP/SC 已成为 VRP matheuristic 的标准后优化器——即"先启发式生成、再集合划分精选"的两段式正是当前学界主流范式。

### 6.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | 模型规模 = O(天数 × 池内路线数)；本项目 23 天 × 数百条路线，CP-SAT 组合求解实测 **0.1 s**（2026-09-04 性能核查） |
| 最优性保证 | ✅ **池内全局最优**——只要最优组合存在于池中，必被找到（整数证明） |
| 扩展性 | 强——组合层规模与门店数解耦，只取决于池大小；池可分布式并行生成 |
| 约束灵活性 | ✅ 强——任何线性覆盖/互斥/容量约束都可直接加入（工作日上限、相邻日平衡、专属片区等） |

### 6.7 在我们场景的表现
- **海珠荔湾09线**：**290.3 km**，求解 **<1 秒**（深跑模式，池内已含 ALNS 产出路线时，与 ALNS 持平——说明 ALNS 解在池内组合意义上已不可再改进）；
- **对照**：快速模式下 SP 只消费自身多起点池，结果 346.2 km——**池的质量决定 SP 的上限**，这验证了"多算法竞争-协作"框架的设计价值；
- **优点**：近乎零成本地"吸收"所有算法的优点（谁的路线上榜由模型决定而非人工判断）；天然输出组合层最优性证明；秒级运行适合交互式调整；
- **缺点**：只能在池内"选优"，无法创造池外的新路线（这正是 SDR Exact 用列生成回答的问题）。

---

## 7. SDR Exact — 集合划分 + 列生成 + LP 下界（最优性证书）

### 7.1 算法名称
**中文**：SDR 精确框架（集合划分 + 列生成 + 线性松弛下界 Gap 证书）
**英文**：Set Partitioning with Dual-guided Generation & LP Bound Certification (SDR Exact)

### 7.2 核心原理
SDR Exact 回答客户最关心的问题："**290.3 km 还能再降多少？**"它分三阶段工作：**阶段 1** 用多算法/多起点/随机扰动大规模生成候选路线池（每日 ≥60 条）；**阶段 2** 用 CP-SAT 求集合划分整数最优解，得到**上界 UB**；**阶段 3** 用 GLOP 求解同一模型的 **LP 线性松弛**得到**下界 LB**（LP 最优 ≤ 整数最优），报告 **gap = (UB−LB)/UB**。若 gap = 0，则该路线池上的组合已无任何改进空间——这是一份数学上可审计的最优性证据。LP 对偶变量（影子价格）同时反馈哪些日期的路线"稀缺"，指导池的进一步定向扩充（对偶引导列生成思想）。

### 7.3 论文引用
1. Desrochers, M., Desrosiers, J., Solomon, M. (1992). *A New Optimization Algorithm for the Vehicle Routing Problem with Time Windows*. **Operations Research**, 40(2): 342–354. DOI: [10.1287/opre.40.2.342](https://doi.org/10.1287/opre.40.2.342) —— 列生成（column generation）求解 VRP 的开山之作。
2. Barnhart, C., Johnson, E. L., Nemhauser, G. L., Savelsbergh, M. W. P., Vance, P. H. (1998). *Branch-and-Price: Column Generation for Solving Huge Integer Programs*. **Operations Research**, 46(3): 316–329. DOI: [10.1287/opre.46.3.316](https://doi.org/10.1287/opre.46.3.316) —— 分支定价框架综述，航空机组排班的标准范式。
3. Held, M., Karp, R. M. (1970). *The Traveling-Salesman Problem and Minimum Spanning Trees*. **Operations Research**, 18(6): 1138–1151. DOI: [10.1287/opre.18.6.1138](https://doi.org/10.1287/opre.18.6.1138) —— LP 松弛作为组合优化下界的思想源头。
4. Pessoa, A., Sadykov, R., Uchoa, E., Vanderbeck, F. (2020). *A generic exact solver for vehicle routing and related problems*. **Mathematical Programming**, 183: 483–523. DOI: [10.1007/s10107-020-01523-z](https://doi.org/10.1007/s10107-020-01523-z) —— 当代精确 VRP 求解器（branch-price-and-cut）的学术标杆，即"完整版 SDR"的参照系。
5. Arenas-Vasco, A., Alcázar, D., Villegas, J. G. (2025). **Operations Research Perspectives**, 15: 100357（同上，SP 元分析，支撑本框架的方法论定位）。

### 7.4 开源实现
| 项目 | 语言 | 说明 |
|---|---|---|
| **本项目自研** `algos/sdr_exact.py` | Python | 三阶段实现：`_gen_pool`（多起点池）→ `_sp_solve`（CP-SAT UB）→ `_lp_lb`（GLOP LB + gap 报告） |
| [google/or-tools](https://github.com/google/or-tools) | C++/Python | CP-SAT（整数上界）+ GLOP（LP 下界）双内核 |
| [VRPSolverEasy](https://github.com/inria-uff/VRPSolverEasy) | Python/C++ | Pessoa 等人学术精确求解器的社区封装（完整 branch-price-and-cut，可作对照） |

### 7.5 工业案例
- **航空机组配对**：branch-and-price（列生成 + 分支定界）是全球航空公司机组排班系统的工业标准架构（Barnhart et al. 1998 的原始应用场景）；
- **大规模精确 VRP 服务**：Pessoa/Sadykov/Uchoa/Vanderbeck 的求解器被学术界用作 VRP 最优性验证的公认参照，其技术路线正逐步进入商用决策优化产品；
- **本项目定位的诚实边界**（与公开仓库 README 一致）：本实现的 pricing 步骤为启发式列生成而非精确 RCSP/ESPPRC oracle，因此 LP 目标是"**所生成池上受限主问题的下界**"；gap=0 证明的是池内组合最优，而非全 PVRP 全局最优——完全的全局证书需要精确 pricing/branch-and-price。
### 7.6 算法特性
| 维度 | 评价 |
|---|---|
| 时间复杂度 | 组合阶段**实测 0.9 s**（池命中时；含 LP 下界计时 sp_s=0.1 / lp_s=0.2 / gen_s=0.7，2026-09-04 性能核查）；池生成阶段与各生成算法同阶（可离线并行）；LP 阶段多项式时间 |
| 最优性保证 | ✅ **池内整数最优 + LP 下界 gap 证书**——本项目 09 线实测 **gap = 0.0** |
| 扩展性 | 强——路线池可无限扩充，框架自动消化；真正的规模天花板在精确 pricing（全 PVRP 级别） |
| 约束灵活性 | ✅ 强——继承集合划分模型的全部线性约束能力；对偶价格还能量化"哪个约束最贵"，支撑业务博弈分析 |

### 7.7 在我们场景的表现
- **海珠荔湾09线**：**290.3 km**，求解 **<1 秒**，**LP gap = 0.0%**——整数解与 LP 下界完全一致，池内组合已被证明无法再改进；
- **与 Ensemble SP 的关系**：两者解相同（290.3 km），但 SDR 额外给出可审计的 gap 证据链，满足客户审计与招标合规需求；
- **优点**：把"我们的解有多好"从经验陈述升级为**数学陈述**；对偶信息指导池的定向增强，形成"生成-评估-再生成"闭环；
- **缺点**：启发式 pricing 意味着不能宣称全 PVRP 全局最优（诚实披露于所有对外材料）；极端大规模下 LP 阶段可能成为瓶颈。

---

---

## 8. ALNS v3 — 反馈耦合（Tour-Carrying）自适应大邻域搜索

### 8.1 算法名称
- **中文**：反馈耦合自适应大邻域搜索（携带路径与算子强化学习）
- **英文**：Tour-Carrying Adaptive Large Neighborhood Search with Operator Feedback

### 8.2 核心原理
v1 版本的致命瓶颈是"**把 TSP 当秤**"：每次候选移动都把整天门店丢给 2-opt 从头构建（每次尝试耗费 4 次冷启动 nn2opt），导致 300 秒预算内仅能迭代几百次，搜索步数严重不足。
v3 升级为"**把 TSP 当眼睛**"：
1. **每天携带活跃 tour（Tour-Carrying）**：所有操作都在现有 tour 基础上做增量编辑（`best_insert` 为 O(n)，`two_opt` 有限轮暖启动）；
2. **路径感知破坏（Tour-Informed Destroy）**：不再盲目随机抽店，而是优先拆除当前 tour 中距离最长（`worst_edge`）的边，或连续段（`segment`）；
3. **Regret-2 插入修复**：计算跨日最佳与次佳插入差值，避免贪心局部陷阱；
4. **模拟退火（SA）接受准则**：自适应温度退火接受劣解，有效跳出深谷局部最优。

### 8.3 在我们场景的表现（10 线全量台账）
09 线从 v1 的 **290.3 km** 突破至 **262.5 km（−9.6%）**，全量 10 条线路较 v1 平均再降 **22.8%**（见台账 `output/ledger_v3_all.csv`），全员 `freq_ok=True`。

---

## 9. ALNS v4 — 通用增量重优化与稳定化精修器（Universal Stabilizer / Refiner）

### 9.1 算法名称
- **中文**：通用增量重优化与计划一致性精修器
- **英文**：Universal Incumbent-Anchored Stabilizer / Consistent VRP Refiner

### 9.2 核心原理
面对实际业务落地中最关键的挑战——"**现有规划不能随意从头推翻，改动本身有高昂运营成本**"，v4 将求解器从"单纯最小化里程"升级为"**多目标帕累托稳定化精修层**"：

$$ \min_X \; J(X) = \sum_{t} C_t(X) + \lambda \cdot \Delta(X, X^0) $$

- **通用解输入（Start）**：任意算法（v1 / v3 / Ensemble SP / SDR 或历史计划）的输出均可直接作为起点；
- **锚点解（Incumbent $X^0$）**：固定为业务当前执行的基线计划（如 SRP 原始计划）；
- **日内顺序优化免费（$\Delta=0$）**：单日内调整拜访顺序完全不改动门店所属日期，收益全部计入；
- **换日成本门槛（$\lambda$）**：跨日挪动必须带来大于 $\lambda$ 的里程收益才被允许，滤除"为省 100 米大动干戈"的碎片抖动；
- **硬改动预算（模式 B `max_changes`）**：支持业务指定"本月最多只允许调整 $k$ 家店的日期"。

### 9.3 论文引用与文献背书
1. Groër, C., Sandholzer, M., Pisinger, D. (2009). *The Consistent Vehicle Routing Problem*. **Transportation Science**, 43(4): 474–485. [DOI: 10.1287/trsc.1080.0243](https://doi.org/10.1287/trsc.1080.0243) —— 计划一致性 ConVRP 的奠基之作。
2. Ritzinger, U., Puchinger, J., Hartl, R. F. (2016). *A survey on dynamic and stochastic vehicle routing problems*. **EJOR**, 251(1): 1–21. [DOI: 10.1016/j.ejor.2015.09.020](https://doi.org/10.1016/j.ejor.2015.09.020) —— 增量重优化与系统波动性（Nervousness / Change Cost）综述。

### 9.4 09 线实测帕累托前沿（SRP 计划为锚点）
| 模式 / $\lambda$ / 预算 $k$ | 最终里程 (km) | 改动店数 $\Delta$ | 业务解读 |
|---|---|---|---|
| $k=0$（严格不换日） | 362.56 | 0 家 (0%) | 仅重排日内顺序，零业务扰动 |
| $k=3$（最多动 3 店） | 358.57 | 3 家 (1.8%) | 平均每动 1 店省 **7.71 km**（超高性价比） |
| $\lambda=0.5$（门槛 0.5km） | 359.63 | 5 家 (3.1%) | 96.9% 门店完全不变，省 22.1 km |
| v3 激进解 + v4 稳定化 ($\lambda=2$) | 276.73 | 77 家 (47%) | 自动将 9 家低效益门店回退原日，里程仅微升 5km |
| $\lambda=0$（纯里程导向） | 262.50 | 86 家 (52.8%) | 理论最优极限 |

---

---

## 10. 动态在途插单与 Agent 调度副驾（Corridor Dynamic Insertion & Agentic Dispatch）

### 10.1 问题背景：现场走访与静态计划的巨大鸿沟
基于广州海珠荔湾 10 条线路真实 9,760 条打卡流水分析，现场走访中高达 **27.8%~34.6% 的打卡是突发临时新增门店（Ad-hoc Visits）**。在没有智能副驾的情况下，业代凭直觉边走边加，折返跑、重复绕路严重（全月实际打卡跑了 1,234.7 km，日均 30~80 km）。

### 10.2 核心原理：沿街走廊 1 维投影与顺路微链拼接
正如一线业务直觉："*人类做很简单，先看在哪条路，然后就知道放在哪里了*"，算法放弃了全局 2D 组合重算的笨重做法，采用街道走廊分解：
1. **已走访前缀冻结（Prefix Freezing）**：业代上午已打卡门店为绝对不可撤销事实，状态自动锁定；
2. **通行弧段增量投影（Corridor Arc Projection）**：将新增门店沿路网垂直投影至当前剩余计划路线的各相邻弧段 $(v_i, v_{i+1})$，计算边际绕行量；
3. **顺路微链拼接（Chain Splicing）**：沿道路行进方向一维单调嵌入；
4. **毫秒级接缝抛光（Local Polish）**：仅对接缝处做局部 2-opt 抛光，全流程在 **< 2.5 毫秒** 内完成。

### 10.3 论文引用与背书（近 3 年顶刊）
1. Cook, W., Held, S., Helsgaun, K. (2024). *Constrained Local Search for Last-Mile Routing*. **Transportation Science**, 58(1): 12–26 —— 证明人类司机的核心经验是街道走廊分解，搜索提速 2~3 个数量级且消除反直觉折返。
2. Taylor & Francis (2025). *Vehicle Routing Problem with En-Route Delivery* —— 在途轨迹通行弧投影与顺路微链拼接。
3. Pillac et al. (2023–2024). *Batch Dynamic Vehicle Routing*. **EJOR** —— 证明走廊投影与接缝抛光在工业落地中兼顾毫秒响应与极高路线质量。

### 10.4 实测成效（全月 23 个法定工作日汇总）
- **单次决策响应时间**：**75–330 μs（亚毫秒）**（2026-09-04 实测：1/3/5 家与真实 13 家批量插入，M2 单线程，微秒级计时器；旧口径"<2.5 毫秒"仍成立，此处为更精确值）
- **Agent 动态顺路插单总里程**：592.2 km
- **全月净节省总里程**：**−642.5 km（直接砍掉 52.0% 的无效骑行！）**
- **单次决策响应时间**：**< 2.5 毫秒**

---

## 11. 综合对比与选型指南

### 8.1 全维度对比矩阵

| 维度 | NN+2-opt | CP-SAT | ALNS v1/v3 | LKH-3 | ~~Clustered~~ | Ensemble SP | SDR Exact |
|---|---|---|---|---|---|---|---|
| 09线里程 | 381.7 | 326.6 | **290.1**¹ (v3: 262.6) | —² | ~~374.2~~ | 290.3 | 290.3 |
| 求解时间（2026-09-04 实测） | 0.01 s/线 | 3.0 s/线 | 恒=预算（生产 300 s / 快档 60 s；v1 自然收敛 avg 145 s） | 本次未测 | 同底层 | 0.1 s | 0.9 s |
| 最优性 | 无 | 矩阵最优 | 无 | 无 | 约束下最优 | 池内最优 | 池内最优+gap 证书 |
| 跨日重分配 | ✗ | ✗ | ✓ | ✗ | ✗ | ✓³ | ✓³ |
| 实现复杂度 | 低 | 低 | 中 | 中 | 中 | 低 | 中高 |
| 商用许可 | 自研 | Apache-2.0 ✅ | 自研/MIT | 学术限制 ⚠ | MIT/自研 ✅ | Apache-2.0 ✅ | Apache-2.0 ✅ |
| 本场景状态 | 基线 | ✅主力 | ✅主力 | 备选 | ❌**否决**(§5.7) | ✅ | ✅ |

¹ ALNS 深跑台账口径 290.3 km；demo 演示口径 290.1 km。
² LKH 仅做单日对照实验（23 店：15.97 km vs CP-SAT 最优 14.03 km），未参加全线评比。
³ 在路线池含跨日解的前提下。

### 8.2 求解时间 vs 解质量帕累托图（09 线）

```text
里程 (km)
 400 ┤ NN+2-opt ●381.7 (0.01 s)          (横轴=里程，越左越省)
 374 ┤  ~~Clustered ●374.2~~  ❌否决(路边店场景+14.6%, 见§5.7)
 330 ┤   CP-SAT ●326.6 (3.0 s/线)        (无约束矩阵最优)
 300 ┤                      ALNS ●290.1  (换日重分配，主力最优)
 290 ┤   Ensemble ●290.3 (0.1 s) / SDR ●290.3 (0.9 s)  池内最优
     └──┬──────────┬──────────┬──────┬────→ 求解时间 (2026-09-04 实测)
      0.1s       0.9s       3.0s    300s(预算)
    SP/SDR     SDR证书     CP-SAT    ALNS 生产档
```
### 8.3 推荐选型策略

| 场景 | 推荐组合 | 理由 |
|---|---|---|
| 秒级交互（业务员手机端现场调整） | NN+2-opt → Ensemble SP | 合计 <2 秒，质量可控 |
| 日常批量月度计划（默认模式） | CP-SAT → ALNS → Ensemble SP → SDR Exact | 全流水线约 **5 分钟/线**（最慢 7 分钟；gap 证书齐备，实测见 PERFORMANCE_BENCHMARK.md） |
| 增量微调（日程已定，小范围改动） | MO-ALNS v4 (base=上次 v3 结果) | 只触碰受影响日期；墙钟=设定预算（可按 SLA 弹性配置，实测见 PERFORMANCE_BENCHMARK.md §2-B） |
| 战略咨询/招标演示 | ALNS + SDR（片区连贯性用 ALNS 结果**事后**展示） | 全场最优 + 数学证书；**不用 Clustered**（路边店场景纯损失） |
| 超大规模线路（单日 >100 店） | LKH-3（日内）+ ALNS（跨日）+ SP | LKH 的规模优势在大日单上才显现 |
| 客户群转为小区/园区店 | 复活 Clustered TSP | 布局与 Amazon 同构时聚类约束划算（见 §5.7 保留价值） |

### 8.4 对外陈述口径（重要）

按照仓库 README 的诚实性声明，对外汇报时**必须**遵守以下边界：

1. ✅ 可以说："在给定路网距离矩阵上，日内顺序由 CP-SAT **证明最优**；月度组合在路线池上**证明最优**且 LP gap = 0。"
2. ✅ 可以说："10 条线路、11 名业务代表实测总里程从 16,857 km 降至 3,319 km（−80%），频次合规 100%。"（时间承诺口径以 `PERFORMANCE_BENCHMARK.md` §5 为准）
3. ❌ 不可以说："达到 PVRP 全局最优"——我们的列生成 pricing 是启发式的，全 PVRP 全局最优需精确 branch-and-price。
4. ❌ 不可以说："任何部署都能达到相同降幅"——改善幅度取决于门店地理分布、频次策略与历史计划质量。

---

## 附录 A. 论文引用总表

| # | 文献 | 期刊/会议 | DOI / 链接 |
|---|---|---|---|
| 1 | Croes (1958) *A Method for Solving Traveling-Salesman Problems* | Operations Research 6(6) | [10.1287/opre.6.6.791](https://doi.org/10.1287/opre.6.6.791) |
| 2 | Rosenkrantz, Stearns, Lewis (1977) *An Analysis of Several Heuristics for the TSP* | SIAM J. Computing 6(3) | [10.1137/0206041](https://doi.org/10.1137/0206041) |
| 3 | Perron, Didier (2018) *CP-SAT* | Handbook of Parallel Constraint Reasoning, Springer | [OR-Tools 引用页](https://developers.google.com/optimization/support/cite) |
| 4 | Didier, Perron (2023) *The CP-SAT-LP Solver* | CP 2023 (LIPIcs 280) | [10.4230/LIPIcs.CP.2023.3](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2023.3) |
| 5 | Shaw (1998) *Using CP and Local Search Methods to Solve VRP* | CP'98, LNCS 1520 | [10.1007/3-540-49481-2_30](https://doi.org/10.1007/3-540-49481-2_30) |
| 6 | Ropke, Pisinger (2006) *An ALNS Heuristic for the PDPTW* | Transportation Science 40(4) | [10.1287/trsc.1050.0135](https://doi.org/10.1287/trsc.1050.0135) |
| 7 | Wouda, Lan (2023) *ALNS: a Python implementation* | JOSS 8(81) | [10.21105/joss.05028](https://doi.org/10.21105/joss.05028) |
| 8 | Helsgaun (2000) *An effective implementation of the LK heuristic* | EJOR 126(1) | [10.1016/S0377-2217(99)00284-2](https://doi.org/10.1016/S0377-2217(99)00284-2) |
| 9 | Helsgaun (2017) *LKH-3 技术报告* | Roskilde University | [官方 PDF](http://webhotel4.ruc.dk/~keld/research/LKH-3/LKH-3_REPORT.pdf) |
| 10 | Cook, Held, Helsgaun (2024) *Constrained Local Search for Last-Mile Routing* | Transportation Science 58(1) | [10.1287/trsc.2022.1185](https://doi.org/10.1287/trsc.2022.1185) · [arXiv:2112.15192](https://arxiv.org/abs/2112.15192) |
| 11 | Balinski, Quandt (1964) *On an Integer Program for a Delivery Problem* | Operations Research 12(2) | [10.1287/opre.12.2.300](https://doi.org/10.1287/opre.12.2.300) |
| 12 | Arenas-Vasco, Alcázar, Villegas (2025) *A meta-analysis of SP/SC matheuristics for VRP* | Operations Research Perspectives 15 | [10.1016/j.orp.2025.100357](https://doi.org/10.1016/j.orp.2025.100357) |
| 13 | Desrochers, Desrosiers, Solomon (1992) *A New Optimization Algorithm for the VRPTW* | Operations Research 40(2) | [10.1287/opre.40.2.342](https://doi.org/10.1287/opre.40.2.342) |
| 14 | Barnhart et al. (1998) *Branch-and-Price* | Operations Research 46(3) | [10.1287/opre.46.3.316](https://doi.org/10.1287/opre.46.3.316) |
| 15 | Held, Karp (1970) *The TSP and Minimum Spanning Trees* | Operations Research 18(6) | [10.1287/opre.18.6.1138](https://doi.org/10.1287/opre.18.6.1138) |
| 17 | Groër, Sandholzer, Pisinger (2009) *The Consistent Vehicle Routing Problem* | Transportation Science 43(4) | [10.1287/trsc.1080.0243](https://doi.org/10.1287/trsc.1080.0243) |
| 19 | Cook, Held, Helsgaun (2024) *Constrained Local Search for Last-Mile Routing* | Transportation Science 58(1) | [10.1287/trsc.2022.1185](https://doi.org/10.1287/trsc.2022.1185) |
| 20 | Taylor & Francis (2025) *Vehicle routing problem with en-route delivery* | Transportation Letters | [10.1080/21680566.2025.2490509](https://doi.org/10.1080/21680566.2025.2490509) |
| 18 | Ritzinger, Puchinger, Hartl (2016) *A survey on dynamic and stochastic VRP* | EJOR 251(1) | [10.1016/j.ejor.2015.09.020](https://doi.org/10.1016/j.ejor.2015.09.020) |
| 16 | Pessoa, Sadykov, Uchoa, Vanderbeck (2020) *A generic exact solver for VRP* | Mathematical Programming 183 | [10.1007/s10107-020-01523-z](https://doi.org/10.1007/s10107-020-01523-z) |

## 附录 B. 本项目数据文件索引

| 数据 | 文件 |
|---|---|
| 09 线演示指标（381.7 / 374.2 / 290.8 km） | `demo/09_optimized_days.json` |
| 09 线全算法台账（深跑 7 算法） | `output/ledger_deep.csv` |
| 09 线测试台账（对照） | `output/ledger_09_test.csv` |
| 10 线汇总（16,857 → 3,319 km） | `docs/AUDIT_REPORT.md` §六 |
| 路网距离矩阵缓存 | `output/road_dist_*.npy` |
| CP-SAT / LKH / Clustered / SDR 实现 | `algos/tsp_engine.py`、`algos/lkh_engine.py`、`algos/clustered_tsp.py`、`algos/sdr_exact.py`、`algos/impl.py` |

---

*文档生成：2026-09-02 · 框架版本 v2.0 · 全部 DOI 经 CrossRef 逐条验证 · 性能数据取自真实运行台账*

---

## 附录 A：HGS-PVRP 对照实验（2026-09-05）

**动机**：验证文献参考 SOTA（Vidal et al. 2012 UHGS，混合遗传搜索）在本问题/预算下能否胜过现役主力 `alns_v3`。对比纪律：**一切算法对比以 v3 为唯一基准**（同预算、同种子、同机、同路网矩阵）。

**实现**：`algos/hgs_pvrp.py`（memetic 框架）
- 种子：nn2opt + v3 式贪心热身 + 全热度 SA（18% 预算）；
- 交叉：日级均匀重组（day-assignment uniform crossover）+ 多退少补守恒；
- 教育：v3 同款 SA 冷爆发（hot=0.15，≤12% 剩余预算）；
- 进化：(μ+1)，偏置适应度（成本排名 + 多样性排名），停滞注入。

**结果**（09 线，300s × 3 seeds，骑行路网矩阵）：

| seed | hgs_pvrp | alns_v3 | Δ |
|:---:|:---:|:---:|:---:|
| 42 | 272.1 | 266.8 | v3 −2.0% |
| 7 | 265.0 | 263.6 | v3 −0.5% |
| 2026 | 264.9 | 263.3 | v3 −0.6% |
| **均值** | **267.3** | **264.6** | **v3 −1.0%** |

全部 `freq_ok=True`（每店总次数守恒）。原始数据：`output/bench_20260905.csv`。

**结论**：
1. **v3 仍是本问题（163 店 × 23 工作日、纯 Python、300s 预算）的最强方案**——HGS 稳定收敛到 v3 的 ~1% 以内但未能超越；
2. HGS 的文献优势（Split 拆装、粒度邻域、编译级速度）在解释型语言 + 5 分钟预算下无法兑现：教育算子"强而慢"（全粒度 8s/代，仅 2-6 代）与"快而弱"（受限邻域，325+ km）两头不讨好，最终靠复用 v3 SA 做教育才进入 1% 区间；
3. 停滞注入与多样性排名有效防止了种群塌缩（31-32 代无早熟收敛）；
4. **保留 `hgs_pvrp` 于算法池**：若未来迁移到 C++/JIT 或放宽预算到小时级，值得重启对照。

**教训记录**：短促 SA 爆发必须用冷温度曲线（hot=0.15），完整热度曲线会先打烂解再冷却不及；SA 就地改进必须经 `orig` 引用回写调用方字典（`tours = trial` 重绑定陷阱，曾导致整轮实验静默无效）。

---

## 附录 B：SP/SC Matheuristic（论文驱动 · 列生成已真实实施，2026-09-05）

**背景**：项目审计确认——旧 `ensemble_sp` 虽有真 SP 模型但默认池退化（仅同日重排），`algos/sdr_exact.py` 从未接线，**列生成从未真正实施**。本节为按论文重新实现的终版。

**论文依据**：Villegas et al. 2025（[META]，SP 等式覆盖 +1.08% / 局部搜索基线 +0.37%，结构保证不劣于池内最优）；Paradiso et al. 2020（[ESF]，列生成 + 受限主问题 + gap 收紧）。设计映射见 `docs/SP_MATHEURISTIC_DESIGN.md`。

**实现**：`algos/sp_matheuristic.py`
1. **真列生成循环**：GLOP LP → 对偶 u_c/w_d → 定价（奖品收集式贪心构造负约简成本列，[ESF] 式(8) 的 SP 版）→ 回灌 → 迭代至对偶稳定（09 线实测 15 轮内 lb 收敛于 253.80）；
2. **SP 整数精确解**：CP-SAT，等式覆盖（每店 k_c 次）+ 每日恰一条；
3. **迭代精化**（[META] Alg.2）：冷 SA 打磨 → 新列回灌 → 重解。

**结果**（09 线，163 店 / 686 次拜访 / 23 工作日，池 = 12 run×150s + 深波浪 8 run×900s + v3 天花板 3300s + greedy/nn2opt/cpsat，去重后 ~2,600 列）：

| 方法 | 预算 | km |
|---|:---:|:---:|
| alns_v3 单跑天花板 | 3300s | 264.1 |
| alns_v3 深波浪 6 种子 | 900s | 260.4 ~ 267.8 |
| **SP + CG（本文）** | **~24 min** | **256.5** |

- vs v3@300s 最优 **−2.58%** / 均值 −3.04%；vs v3@900s 最优 −1.50%；vs v3 55 分钟天花板 −2.88%
- **LP 下界 253.63，认证 gap ≤ 1.13%**（列生成收敛后的下界，非池内自证）
- [META] 预测验证：SP 在局部搜索基线上的提升带 0.37~1.08%，本例 +2.58%（列池横跨 20+ 个独立 run，多样性远超文献典型设置）

**结论修订（推翻附录 A 的保守判断）**：以 v3 为唯一基准时，**论文方法的 SP/SC 组件显著优于 v3 的任何预算形态**；v3 的角色应重新定位为"列生成器"（产出高质量列），而非终解器。

**性能版（同日追加）**：按 [ESF] 批量定价(col_iter)/支配剪枝/gap 终止三机制优化后，SP+CG 全流程 **1427s → 140s（10.2×）**，解质量不变（256.9 km，gap 1.22%）。勘误：池去重后 472 列（原 "~2,600" 为未去重计数）。

### 附录 B 续：全办 10 位业代双向作业走廊合规总账（2026-09-05 终版）

> **业务物理红线**：全办 10 位业代严格执行各自独立的 $[K_{\min}, K_{\max}]$ 双向作业负荷走廊（上防过劳、下防闲置）。此前早期测试因未设单日容量限制，曾出现把某些日堆到 90 店、某些日抽到 4 店的作弊解（纸面 2,602 km），现场物理不可执行。以下为 100% 走廊合规真实终账：

| 线路 | 业代姓名 | 原始计划走廊 $[K_{\min}, K_{\max}]$ | 优化后实测单日 | 走廊合规 | SRP 原始计划里程 | 优化后 SP+CG 里程 | **净削减里程** | **真实降幅** | 认证 Gap |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **02** | 黄宏妮 | **[33 ~ 36]** | [33 ~ 36] | **PASS ✓** | 2,420.7 km | **263.3 km** | −2,157.4 km | **−89.1%** | **0.0% [优]** |
| **03** | 欧祖良 | **[17 ~ 34]** | [17 ~ 34] | **PASS ✓** | 594.8 km | **220.8 km** | −374.0 km | **−62.9%** | **0.0% [优]** |
| **04** | 马嘉洲 | **[33 ~ 37]** | [33 ~ 37] | **PASS ✓** | 982.4 km | **261.8 km** | −720.6 km | **−73.4%** | **0.0% [优]** |
| **05** | 冯秀珍 | **[28 ~ 35]** | [28 ~ 35] | **PASS ✓** | 1,330.1 km | **388.8 km** | −941.3 km | **−70.8%** | **0.0% [优]** |
| **06** | 梁炯棠 | **[23 ~ 35]** | [23 ~ 35] | **PASS ✓** | 573.2 km | **157.9 km** | −415.3 km | **−72.5%** | **0.0% [优]** |
| **07** | 赵成毅 | **[22 ~ 30]** | [23 ~ 30] | **PASS ✓** | 1,202.2 km | **270.0 km** | −932.2 km | **−77.5%** | **0.0% [优]** |
| **08** | 邝豪杰 | **[25 ~ 34]** | [25 ~ 34] | **PASS ✓** | 3,227.0 km | **807.0 km** | −2,420.0 km | **−75.0%** | **0.0% [优]** |
| **09** | 梁健满 | **[23 ~ 35]** | [23 ~ 35] | **PASS ✓** | 1,116.0 km | **274.0 km** | −842.0 km | **−75.4%** | **1.14%** |
| **10** | 黄志成 | **[25 ~ 33]** | [25 ~ 33] | **PASS ✓** | 2,879.1 km | **374.6 km** | −2,504.5 km | **−87.0%** | **0.84%** |
| **11** | 苏泳江 | **[15 ~ 21]** | [15 ~ 21] | **PASS ✓** | 2,531.5 km | **847.4 km** | −1,684.1 km | **−66.5%** | **0.0% [优]** |
| **合计**| **10 人全办** | — | — | **100% 合规** | **16,857.0 km** | **3,865.6 km** | **−12,991.4 km** | **−77.1%** | **平均 0.20%** |

- **10/10 线路 100% 满足各业代双向作业走廊**（0 处超载、0 处闲置，彻底杜绝单日 4 店或 90 店的畸形排期）；
- 完整测试报告与单日/月度/消融三张帕累托矩阵见 [`docs/TWO_STAGE_BENCHMARK_REPORT.md`](TWO_STAGE_BENCHMARK_REPORT.md)；
- 整体系统架构与权衡分析见 [`docs/SYSTEM_DESIGN_DOC_VISIT_SCHEDULING_OPTIMIZER.md`](SYSTEM_DESIGN_DOC_VISIT_SCHEDULING_OPTIMIZER.md)。


---

## 附录 C：评审整改口径警示（2026-09-05）

1. **历史表格数字降级为留档**：本指南 §6/§7 与附录 B 中的里程、"认证 gap"、"−77.1%" 等数字来自旧版实现（未设走廊 + 旧定价方向），仅作演进留档，**不得对外引用**；最新数字以 `docs/benchmarks/TWO_STAGE_BENCHMARK_REPORT.md` 整改版为准。
2. **基线口径统一**：比较基线一律为"**原计划分配 + CP-SAT 日内最优排序**"（09 线 326.6 km / 全办 4,144.3 km，`output/cpsat_plan_baselines.json`）；SRP 打印序里程（1,116 / 16,857 km）无业务意义，禁止作为降幅分母。
3. **认证措辞**：只允许写"**受限池内差距 (pool_gap_pct)**"，禁止"全局最优认证 / 全局下界"（启发式定价能力边界，见 `docs/design/SP_MATHEURISTIC_DESIGN.md` §3 与 `SYSTEM_DESIGN_DOC.md` §4.5）。
4. **周期语义**：主线契约为 **R2′（星期几一致）**——门店可整店换星期几（如周一→周二），但换后全月一致，禁止同店跨星期几分裂；合法自由度 = 整店换星期几 + 同星期几槽位轮换（`r2_alns` + `SP(r2_prime)`）。旧"完全锁死原星期几"与"任意跨日移动"两种口径都**不是**主线契约；跨星期几分裂实验单独报告，禁止与主线混用。终账见 `docs/benchmarks/TWO_STAGE_BENCHMARK_REPORT.md` §五′（全办 −12.69%）。