# 算法参考资料索引（Reference: Algorithms）

> **用途**：新接手项目的工程师/AI 从这里进入。每个在用算法一份说明文档：定位、输入输出、机制、复杂度、已知陷阱、引用论文。
> **阅读顺序建议**：先读 [概念文档](../concepts/)（集合划分 / 列生成 / R2′ 契约），再读本文，最后按接手模块挑算法文档。
> **协议背景**：算法研究对比协议见 `docs/design/MATRIX_PROTOCOL_V3_DESIGN_v0.3.md`（v0.3）；生产选型快筛见 `contract_matrix_cell/v2`。

## 概念文档（横切知识，所有算法文档都引用，先读）

| 文档 | 概念 |
|---|---|
| [../concepts/set-partitioning-final-gate.md](../concepts/set-partitioning-final-gate.md) | 集合划分（SP，Set Partitioning）与 Contract-SP 终闸：数学模型、终闸语义、血泪账 |
| [../concepts/column-generation.md](../concepts/column-generation.md) | 列生成（CG，Column Generation）：对偶→定价→回灌；rc 公式；能力边界 |
| [../concepts/r2-prime-contract.md](../concepts/r2-prime-contract.md) | R2′ 星期几一致契约：业务语义、形式定义、实现位置、W53 边界警告 |

## 算法文档清单

| 文档 | 算法/组件 | 类别 | 层 |
|---|---|---|---|
| [base.md](base.md) | base 构造式基准（原分配 + 精确排序） | 构造式 | 组合层（参照系） |
| [r2-alns.md](r2-alns.md) | R2′-ALNS（合同同构局部搜索） | 元启发式 | 日历层 |
| [alns-v3.md](alns-v3.md) | ALNS v3（反馈耦合自适应大邻域搜索） | 元启发式 | 日历+顺序 |
| [hgs-pvrp.md](hgs-pvrp.md) | HGS-PVRP（混合遗传搜索） | 元启发式（种群） | 日历+顺序 |
| [sp-cg.md](sp-cg.md) | 列生成算法行（对偶驱动供列） | 线性规划（LP）框架 | 组合层 |
| [alns-v4-pareto.md](alns-v4-pareto.md) | ALNS v4（稳定性权衡精修器；⚠ 双周相位缺陷修复排期中） | 元启发式（增量重优化） | 微调层 |
| [sdr-exact.md](sdr-exact.md) | SDR Exact（多起点采样+集合划分+线性规划下界） | 构造式+线性规划（LP） | 组合层（旧代） |
| [tsp-heuristics.md](tsp-heuristics.md) | 最近邻（NN）+2-opt、多起点采样 | 启发式 | 顺序层 |
| [tsp-cpsat.md](tsp-cpsat.md) | CP-SAT 开链精确旅行商（TSP） | 精确（约束规划） | 顺序层 |
| [tsp-lkh3.md](tsp-lkh3.md) | LKH-3 开放路径 | 启发式（大规模） | 顺序层 |
| [corridor-insertion.md](corridor-insertion.md) | 走廊投影动态插单工具 | 动态重优化 | 在途层 |
| [clustered-tsp.md](clustered-tsp.md) | 聚类旅行商（Clustered TSP，已评估→否决） | 构造式 | 顺序层 |

## 全局事实速记（写代码前必读）

1. **集合划分（SP，Set Partitioning）是终点站**：SP 是一种整数规划模型——从候选路线池里，每个工作日恰好选一条路线、每家店被访次数等于合同频次。所有算法的本质都是"给 Contract-SP 供候选列"，最终解由 `sp_solve_ip`（r2_prime+contract）统一选出。算法不决策。
2. **独立性是来源隔离**：引擎之间不允许隐式共享运行产物（日历/列/对偶/incumbent）；共享的是公共数学工具、估计器与原始数据。
3. **不同类型的算法，用不同的考核标准**：
   - 搜索型引擎（R2′-ALNS、ALNS v3、HGS）：考核**方案质量**——最终方案比原计划省多少公里、多次运行结果是否稳定；
   - 分支定价（bp）：考核**数学证明能力**——它给出的“当前解离理论最优还差多少”（gap，最优性间隙）下界有多紧、多大比例的搜索能证明完成；
   - 两者不可互换：不能拿公里数评判 bp（它的职责是给数学证明，不是改方案）；也不能要求搜索型引擎提供数学证明（机制上给不出）。
4. **确定性红线**（元启发式引擎：r2_alns/v3/v4）：搜索期零求解器调用（seeded RNG）；终局精排只接受已证最优（PROVEN OPTIMAL）的重排。例外：bp 的树内 CP-SAT 定价、矩阵 runner 的终局重排是算法/协议内禀行为，受状态字段诚实记录约束而非此红线。
5. **诚实口径**：km 分原始（raw）/取整（rounded）、池列成本/重算成本；状态三档 已证最优（PROVEN_OPTIMAL）/ 启发式界限（BOUND_HEURISTIC）/ 达限（TIME_LIMIT）；三闸（count/capacity/contract）由调用方独立复验。

## 缩写与术语速查（新人必读；正文首次出现均为"中文（缩写，英文全称）"格式）

| 术语 | 含义 |
|---|---|
| 集合划分（SP，Set Partitioning） | 整数规划模型，从候选路线池中"每个工作日恰选一条路线 + 每店次数=合同频次"。全系统的最终决策点 |
| 列生成（CG，Column Generation） | 反复用 LP 对偶发现"值得加入的列"并回灌的技术 |
| 线性规划（LP，Linear Programming）/ 整数规划（IP，Integer Programming） | 连续松弛 vs 0/1 整数解 |
| 受限主问题（RMP，Restricted Master Problem） | 只含当前已生成列的 SP（LP 或 IP） |
| 约简成本（rc，Reduced Cost，检验数） | 定价子问题的目标，rc<0 表示该列值得加入当前池 |
| 分支定价（B&P / bp，Branch-and-Price） | 分支树 × 每节点列生成的精确求解框架 |
| 自适应大邻域搜索（ALNS，Adaptive Large Neighborhood Search） | destroy–repair 邻域搜索 |
| 混合遗传搜索（HGS / UHGS，(Unified) Hybrid Genetic Search） | 种群 + 局部搜索混合体制 |
| 随机局部搜索（SLS，Stochastic Local Search） | 单解轨迹邻域搜索 |
| 模拟退火（SA，Simulated Annealing） | 以概率接受劣解的接受准则 |
| 车辆路径问题（VRP，Vehicle Routing Problem）/ 周期性车辆路径问题（PVRP，Periodic VRP） | PVRP：多日、每店有拜访频次合同 |
| 旅行商问题（TSP，Traveling Salesman Problem）/ 非对称（ATSP，Asymmetric TSP） | 本项目指"单日开放路径排序"：不回起点 |
| R2′ | 本项目自定义契约（非文献缩写）：门店可整月换星期几，但换后全月一致；禁止同店跨星期几分裂。详见 [../concepts/r2-prime-contract.md](../concepts/r2-prime-contract.md) |
| 约束规划求解器（CP-SAT） | Google OR-Tools 的约束规划求解器（本系统的日内精确 TSP 引擎） |
| 线性规划求解器（GLOP） | Google OR-Tools 的线性规划求解器（供对偶与下界） |
| LKH-3 | Helsgaun 的 Lin-Kernighan 大规模 TSP 启发式求解器（外部二进制） |
| 基本最短路问题（ESPPRC，Elementary Shortest Path Problem with Resource Constraints） | 精确定价子问题的标准形态，bp 的路线图目标 |
| [ESF] | Paradiso et al. 2020 论文在本项目的引用代号（精确定价能力边界） |
| 下界（LB，Lower Bound）/ 上界（UB，Upper Bound）/ 最优性间隙（gap） | `gap = 100×(UB−LB)/|UB|`，衡量"当前解离已知下界还有多远" |
| 走廊 | 每日门店数的硬区间 `[min_daily, max_daily]`（由原计划派生的负荷代理约束） |
| 当前最好解（incumbent） | 搜索过程中保留的最优可行解，用作剪枝基准与输出候选 |
| 三闸 | 频次（count）、容量（capacity）、合同（contract）三项由调用方独立复验的验收闸 |

> **覆盖注记**：旧代基线与杂项算法（`algos/impl.py`：baseline / nn2opt / greedy_crossday / cpsat_route / alns / ensemble_sp）未单独立档——研究矩阵不使用，接手时以文件头注与 `ALGORITHM_GUIDE.md` 附录 C 的历史口径警示为准。

## 引用论文总表（按主题）

### 集合划分与列生成
- Balinski, M. L., Quandt, R. E. (1964). *On an integer program for a delivery problem*. Operations Research 12(1).
- Desrochers, M., Desrosiers, J., Solomon, M. (1992). *A new optimization algorithm for the vehicle routing problem with time windows*. Operations Research 40(2):342–354.
- Barnhart, C., Johnson, E. L., Nemhauser, G. L., Savelsbergh, M. W. P., Vance, P. H. (1998). *Branch-and-price: Column generation for solving huge integer programs*. Operations Research 46(3):316–329.
- Lübbecke, M., Desrosiers, J. (2005). *Selected topics in column generation*. Operations Research 53(6):1007–1023.
- Pessoa, A., Sadykov, R., Uchoa, E., Vanderbeck, F. (2020). *A generic exact solver for vehicle routing and related problems*. Mathematical Programming 183:483–523.

### 分支定价与精确定价
- Ryan, D. M., Foster, B. A. (1981). *An integer programming approach to scheduling*. In Computer Scheduling of Public Transport.
- Feillet, D., Dejax, P., Gendreau, M., Gueguen, C. (2004). *An exact algorithm for the elementary shortest path problem with resource constraints*. Transportation Science 38(3):299–316.（ESPPRC）
- Paradiso, R. et al. (2020). Operations Research 68(1).（精确定价能力边界，[ESF]）

### 周期性 VRP 与一致性
- Cordeau, J.-F., Gendreau, M., Laporte, G. (1997). *A tabu search heuristic for periodic and multi-depot vehicle routing problems*. Networks 30(2).
- Christofides, N., Beasley, J. E. (1981). *The periodic routing problem*. Networks 11.
- Groër, C., Golden, B., Wasil, E. (2009). *The consistent vehicle routing problem*. Manufacturing & Service Operations Management 11(4).

### 元启发式
- Ropke, S., Pisinger, D. (2006). *An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows*. Transportation Science 40(4):455–472.
- Pisinger, D., Ropke, S. (2010). *A general heuristic for vehicle routing problems*. Computers & Operations Research 37(3):516–534.
- Shaw, P. (1998). *Using constraint programming and local search methods to solve vehicle routing problems*. CP'98, LNCS 1520.
- Vidal, T., Crainic, T. G., Gendreau, M., Lahrichi, N., Rei, W. (2012). *A hybrid genetic algorithm with adaptive diversity management for a large class of vehicle routing problems with time-windows*. Computers & Operations Research 40(1):137–150.
- Vidal, T. (2022). *Hybrid genetic search for the CVRP: An open-source implementation*. Transportation Science.
- Kirkpatrick, S., Gelatt, C. D., Vecchi, M. P. (1983). *Optimization by simulated annealing*. Science 220(4598):671–680.
- Ritzinger, U., Puchinger, J., Hartl, R. F. (2016). *A survey on dynamic and stochastic vehicle routing problems*. International Journal of Production Research 54(1).

### TSP 与路线
- Croes, G. A. (1958). *A method for solving traveling-salesman problems*. Operations Research 6(6):791–812.（2-opt）
- Rosenkrantz, D. J., Stearns, R. E., Lewis, P. M. (1977). *An analysis of several heuristics for the traveling salesman problem*. SIAM Journal on Computing 6(3).（NN 启发式）
- Helsgaun, K. (2000). *An effective implementation of the Lin–Kernighan traveling salesman heuristic*. European Journal of Operational Research 112(1):106–130.
- Helsgaun, K. (2017). *LKH-3 version 2.0*（技术报告，Roskilde University）。
- Cook, W., Held, M., Helsgaun, K. (2024). *Constrained local search for last-mile routing*. Transportation Science 58(1).（Amazon last-mile）
- Pillac, V., Gendreau, M., Guéret, C., Medaglia, A. L. (2013). *A review of dynamic vehicle routing problems*. European Journal of Operational Research 225(1):1–11.

### 软件
- Google OR-Tools（CP-SAT 求解器、AddCircuit 约束）：https://developers.google.com/optimization
- LKH-3：http://webhotel4.ruc.dk/~keld/research/LKH-3/

> 卷期页码以出版方页面为准；本表只列确证存在的文献。

## 引用规范（本项目惯例）

- 正文引用格式：`[作者 年份]`，如 `[BARN]`=Barnhart 1998、`[ESF]`=Paradiso 2020。
- 缩写表达规范：**中文（缩写，英文全称）**，如"集合划分（SP，Set Partitioning）"；同文档后续出现可用缩写。
- km 双口径：`raw`（内部计算）vs `rounded`（对外 3 位小数）；池列成本 vs 重算成本分开记录。
- 状态语义：`PROVEN_OPTIMAL` 仅在完整证书条件满足时签发（见 branch-and-price.md §状态）。
