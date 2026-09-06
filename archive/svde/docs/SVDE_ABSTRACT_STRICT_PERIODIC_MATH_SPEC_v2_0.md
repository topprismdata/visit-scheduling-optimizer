# SVDE 严格周期销售拜访决策通用数学模型规范 v2.0
**模型名称:** 严格同周几周期性拜访决策模型 (Strict Cyclic PVRP with Fixed-Weekday Cadence)
**模型编号:** SVDE-MATH-ABSTRACT-SPEC-v2.0
**层级定位:** 第二级：通用抽象数学建模层 (Mathematical Formulation Layer)
**特性:** 通用参数化抽象（与具体算例解耦）、严格 7 天同周几周期锁定、崇川中心 Depot 闭环、字典序多目标分级。

---

## 1. 集合、周期与拓扑结构 (Sets & Structure)

- $I = \{1, 2, \dots, N\}$: 在册管辖门店全集（客户集合）。
  - $I_{1\text{w}} \subset I$: 规定频次为 **1次/周** 的门店子集（全月需拜访 4 次，每周固定 1 次）。
  - $I_{2\text{w}} \subset I$: 规定频次为 **1次/2周** 的门店子集（全月需拜访 2 次，隔周固定 1 次）。
  - $I_{4\text{w}} \subset I$: 规定频次为 **1次/4周** 的门店子集（全月需拜访 1 次，全月特定周 1 次）。
  - $I = I_{1\text{w}} \cup I_{2\text{w}} \cup I_{4\text{w}}$（互斥且完备）。
- $W = \{1, 2, 3, 4\}$: 规划周期内的周集合（标准 4 周周期）。
- $K = \{1, 2, 3, 4, 5\}$: 每周内的工作日索引（$k = 1$ 为周一，$\dots$，$k = 5$ 为周五）。
- $T = W \times K = \{(w, k) \mid w \in W, k \in K\}$: 全月有效工作日全集（共 20 个标准工作日，或输入日历中有效的工作日对）。
- $V = I \cup \{0\}$: 包含起点与终点（Depot 0，崇川市中心）的全部空间节点集合。

---

## 2. 严格周期访问模式集合 (Strict Cyclic Patterns)

对于任意门店 $i \in I$，其合法的“工作日访问模式”必须严格遵循同周几（Same Weekday $k \in K$）规则：

### 2.1 模式定义 (Pattern Definitions)
- 对于 $i \in I_{1\text{w}}$ (1次/周):
  - 只有 5 种合法模式 $R_i = \{p_1, \dots, p_5\}$，模式 $p_k$ 表示在**所有 4 周的周 $k$** 拜访：
    $$\text{Pattern } p_k = \{(1, k), (2, k), (3, k), (4, k)\}, \quad k \in K$$
- 对于 $i \in I_{2\text{w}}$ (1次/2周):
  - 只有 10 种合法模式（选择周几 $k \in K$，以及选择第 1/3 周或第 2/4 周）：
    $$\text{Pattern } p_{k, \text{奇}} = \{(1, k), (3, k)\}, \quad k \in K$$
    $$\text{Pattern } p_{k, \text{偶}} = \{(2, k), (4, k)\}, \quad k \in K$$
- 对于 $i \in I_{4\text{w}}$ (1次/4周):
  - 共有 20 种合法模式（选择第 $w$ 周的周 $k$）：
    $$\text{Pattern } p_{w, k} = \{(w, k)\}, \quad w \in W, k \in K$$

- 记 $\mathcal{P}_i$ 为门店 $i$ 的**合法候选模式集合**。
- 引入指示参数 $a_{i, p}^{(w, k)} \in \{0, 1\}$：表示若门店 $i$ 选择了模式 $p \in \mathcal{P}_i$，在工作日 $(w, k)$ 是否必须拜访（是为 1，否为 0）。

---

## 3. 参数定义 (Parameters)

- $S_i \ge 0$: 门店 $i \in I$ 的标准在店服务时长（分钟）。
- $C_{ij} \ge 0$: 节点 $i$ 到节点 $j$ 的在途通勤时间（分钟，$i, j \in V$）。其中 $C_{0i}$ 表示从崇川中心出发到门店 $i$ 的耗时，$C_{i0}$ 表示从门店 $i$ 返回崇川中心的耗时。
- $K_{\max} = 6$: 单日允许拜访的最大门店数量上限（硬约束）。
- $W_{\max} = 480$: 单日允许的最大工作总工时（分钟，8小时红线）。

---

## 4. 决策变量 (Decision Variables)

1. **模式选择变量 (Pattern Selection Variables)**:
   $$\lambda_{ip} \in \{0, 1\}, \quad \forall i \in I, \forall p \in \mathcal{P}_i$$
   - $\lambda_{ip} = 1$ 表示门店 $i$ 选择了严格同周几的访问模式 $p$；否则为 0。

2. **日历拜访指派变量 (Daily Visit Assignment Variables)**:
   $$x_{i, w, k} \in \{0, 1\}, \quad \forall i \in I, \forall (w, k) \in T$$
   - $x_{i, w, k} = 1$ 表示在第 $w$ 周周 $k$ 拜访门店 $i$；否则为 0。
   - 由模式选择变量直接决定：$x_{i, w, k} = \sum_{p \in \mathcal{P}_i} a_{i, p}^{(w, k)} \cdot \lambda_{ip}$。

3. **单日路径连接变量 (Daily Routing Variables)**:
   $$y_{ij, w, k} \in \{0, 1\}, \quad \forall i, j \in V, i \ne j, \forall (w, k) \in T$$
   - $y_{ij, w, k} = 1$ 表示在第 $w$ 周周 $k$，代表从节点 $i$ 移动到节点 $j$；否则为 0。

4. **单日访问次序辅助变量 (MTZ Subtour Elimination Variables)**:
   $$u_{i, w, k} \ge 0, \quad \forall i \in I, \forall (w, k) \in T$$

---

## 5. 严格约束体系 (Constraints)

### 5.1 唯一模式选择与频次契约硬约束 (Exact Pattern & Cadence Compliance)
每个门店**必须且只能选择一种合法的严格同周几模式**：
$$\sum_{p \in \mathcal{P}_i} \lambda_{ip} = 1, \quad \forall i \in I$$
*(由于合法模式中天然内嵌了严格的 7天 / 14天 / 28天 同周几等距规则，该约束自动保证了 100% 零脱访、零欠访、零超频与零间隔偏离！)*

### 5.2 日历激活映射约束 (Assignment Projection)
$$x_{i, w, k} = \sum_{p \in \mathcal{P}_i} a_{i, p}^{(w, k)} \lambda_{ip}, \quad \forall i \in I, \forall (w, k) \in T$$

### 5.3 单日拜访上限硬约束 (Daily Stop Capacity $\le 6$)
$$\sum_{i \in I} x_{i, w, k} \le K_{\max}, \quad \forall (w, k) \in T \quad (K_{\max} = 6)$$

### 5.4 崇川中心起终点闭环与流平衡约束 (Chongchuan Depot Flow Balance)
1. **中间门店进出度平衡**:
   $$\sum_{j \in V, j \ne i} y_{ji, w, k} = x_{i, w, k}, \quad \forall i \in I, \forall (w, k) \in T$$
   $$\sum_{j \in V, j \ne i} y_{ij, w, k} = x_{i, w, k}, \quad \forall i \in I, \forall (w, k) \in T$$
2. **崇川中心 (Depot 0) 出发与返回**:
   $$\sum_{j \in I} y_{0j, w, k} = \mathbb{I}\left(\sum_{i \in I} x_{i, w, k} > 0\right), \quad \forall (w, k) \in T$$
   $$\sum_{i \in I} y_{i0, w, k} = \mathbb{I}\left(\sum_{i \in I} x_{i, w, k} > 0\right), \quad \forall (w, k) \in T$$

### 5.5 单日子回路消除约束 (Subtour Elimination)
$$u_{i, w, k} - u_{j, w, k} + N \cdot y_{ij, w, k} \le N - 1, \quad \forall i, j \in I, i \ne j, \forall (w, k) \in T$$

### 5.6 单日总工时红线约束 (Daily Time Budget $\le 480$ min)
$$\sum_{i \in I} S_i \cdot x_{i, w, k} + \sum_{i \in V} \sum_{j \in V, j \ne i} C_{ij} \cdot y_{ij, w, k} \le W_{\max}, \quad \forall (w, k) \in T$$

---

## 6. 字典序多目标优化体系 (Lexicographic Objectives)

根据主管裁决，目标函数体系遵循严格的分级优化原则，**以最小化在途时间为主导，不为追求过度均衡而牺牲空间紧凑性**：

$$\operatorname{LexMin} \quad \mathbf{Z} = \left( Z_1, Z_2 \right)$$

### Level 1: 频次与同周几节奏硬履约 (Feasibility Guaranteed by Design)
$$Z_1 = 0 \quad (\text{在模式空间 } \mathcal{P}_i \text{ 穷尽保证，违背即无可行解})$$

### Level 2: 最小化全月总通勤交通损耗 (Minimize Total Transit Time from/to Chongchuan Center)
$$Z_2 = \sum_{(w, k) \in T} \sum_{i \in V} \sum_{j \in V, j \ne i} C_{ij} \cdot y_{ij, w, k}$$
- **业务含义**: 
  - 核心目标。将离散在南通各区县的门店按照最优空间簇团聚类到特定的周几；
  - 彻底压缩从崇川市中心出发、在各店之间穿行、最终返回崇川市中心的全月总行驶耗时；
  - 允许偏远片区（如海安、如东）在特定工作日集中安排 6 家，而在近郊崇川安排 2~3 家轻量日，**绝不过度惩罚日间负荷波动**。
