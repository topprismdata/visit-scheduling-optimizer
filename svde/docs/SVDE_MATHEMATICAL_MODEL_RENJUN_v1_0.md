# SVDE 销售拜访决策引擎 — 第二级：数学建模形式化规范
**模型编号:** SVDE-MATH-MODEL-RENJUN-JUNE-v1.0
**层级定位:** 第二级：数学建模层 (Mathematical Formulation Layer)
**前置输入:** 第一级《销售业务拜访政策与决策契约》(Business Policy Contract)
**铁律规范:** 严禁出现任何求解器名称 (Solvers) 与启发式算法 (Heuristics) 术语，纯数学形式化表达。

---

## 1. 集合与索引 (Sets and Indices)

- $I = \{1, 2, \dots, N\}$: 在册管辖门店集合（仁军场景 $N = 36$）。
  - $I_{\text{REQUIRED}} \subset I$: 硬履约保障门店集合（Key 级及核心 A 级大店，共 14 家）。
  - $I_{\text{STANDARD}} \subset I$: 常规门店集合（$I = I_{\text{REQUIRED}} \cup I_{\text{STANDARD}}$）。
- $D = \{\text{如皋}, \text{崇川}, \text{海安}, \text{如东}, \text{通州}\}$: 行政区县/地理片区集合。
  - $I_d \subset I$: 位于区县 $d \in D$ 的门店子集。
- $T = \{1, 2, \dots, M\}$: 规划期内有效工作日集合（仁军 6 月份 $M = 18$ 天）。
  - $T = T_1 \cup T_2 \cup T_3 \cup T_4 \cup T_5$: 按周划分的工作日子集（第 1 周至第 5 周）。
- $V = I \cup \{0\}$: 包含虚拟起点/大本营（Depot 0）的全部节点集合。

---

## 2. 参数定义 (Parameters)

### 2.1 频次与节奏参数 (Frequency & Cadence)
- $F_i \in \mathbb{Z}^+$: 门店 $i$ 在规划期内的目标拜访频次（主数据规定，如 $F_i \in \{1, 2, 3, 4\}$）。
- $L_i^{\min} \in \mathbb{Z}^+$: 门店 $i$ 相邻两次拜访之间的**最小日期间隔**（Min Gap）。
- $L_i^{\max} \in \mathbb{Z}^+$: 门店 $i$ 相邻两次拜访之间的**最大日期间隔**（Max Gap）。

### 2.2 时间与空间参数 (Time & Space)
- $S_i \ge 0$: 门店 $i$ 的在店标准服务时长（基于动作分类学合成，单位：分钟）。
- $C_{ij} \ge 0$: 从节点 $i$ 到节点 $j$ 的在途交通时间矩阵（单位：分钟，$i, j \in V$）。
- $W_{\max} \in \mathbb{R}^+$: 单日最大允许总工时预算（在店时长 + 在途时间上限，如 480 分钟 / 8 小时）。
- $K_{\min}, K_{\max} \in \mathbb{Z}^+$: 单日拜访门店数量下限与上限（如 $K_{\min} = 3, K_{\max} = 6$）。

### 2.3 惩罚权重与字典序优先级 (Lexicographic Priority Weights)
- $P_{\text{MISSED}}$: 核心门店未履约最高级罚项（Level 1: $P_{\text{MISSED}} \gg 10^6$）。
- $P_{\text{CADENCE}}$: 拜访间隔超出 $[L_i^{\min}, L_i^{\max}]$ 的节奏违规罚项（Level 2）。
- $P_{\text{CROSS}}$: 单日跨越多个不相邻区县的离散度罚项（Level 3）。

---

## 3. 决策变量 (Decision Variables)

### 3.1 核心决策变量 (Core Binary Variables)
- $x_{it} \in \{0, 1\}, \quad \forall i \in I, \forall t \in T$:
  - $x_{it} = 1$ 表示代表在工作日 $t$ 拜访门店 $i$；否则为 0。
- $y_{ijt} \in \{0, 1\}, \quad \forall i, j \in V, i \ne j, \forall t \in T$:
  - $y_{ijt} = 1$ 表示在工作日 $t$，代表拜访完节点 $i$ 后紧接着拜访节点 $j$；否则为 0。
- $z_{dt} \in \{0, 1\}, \quad \forall d \in D, \forall t \in T$:
  - $z_{dt} = 1$ 表示在工作日 $t$，代表涉足了片区 $d$（即当天在片区 $d$ 至少拜访了 1 家门店）；否则为 0。

### 3.2 辅助变量 (Auxiliary Variables)
- $u_{it} \ge 0, \quad \forall i \in I, \forall t \in T$: 单日内的拜访次序变量（用于消除子回路与时间窗连续性）。
- $\delta_i \ge 0, \quad \forall i \in I$: 门店 $i$ 的实际拜访频次与目标频次的负偏差量（欠访缺口）。

---

## 4. 约束条件体系 (Constraints Formulation)

### 4.1 频次与契约履约约束 (Frequency & Fulfillment Constraints)

1. **总拜访频次精确平衡约束**:
   $$\sum_{t \in T} x_{it} + \delta_i = F_i, \quad \forall i \in I$$
2. **`REQUIRED` 核心大店零脱访硬约束**:
   $$\delta_i = 0 \iff \sum_{t \in T} x_{it} = F_i, \quad \forall i \in I_{\text{REQUIRED}}$$
3. **超频过度拜访硬性禁止约束**:
   $$\sum_{t \in T} x_{it} \le F_i, \quad \forall i \in I$$

---

### 4.2 柔性拜访节奏与间隔约束 (Cadence & Regularity Constraints)

对于任何两次实际发生的拜访日 $t_1, t_2 \in T$（满足 $t_1 < t_2$ 且期间无其他拜访）：
1. **最小间隔硬约束 (Min-Gap Guard)**:
   $$x_{it_1} + x_{it_2} \le 1, \quad \forall i \in I, \quad \forall t_1, t_2 \in T \text{ 满足 } 1 \le t_2 - t_1 < L_i^{\min}$$
2. **周度分散度约束 (Weekly Dispersion)**:
   对于规定 4 次/月的门店，每一周内最多拜访 1 次：
   $$\sum_{t \in T_w} x_{it} \le 1, \quad \forall i \in \{i \in I \mid F_i = 4\}, \quad \forall w \in \{1, 2, 3, 4, 5\}$$

---

### 4.3 片区专场与空间聚合约束 (Territory Dedicated Days Constraints)

1. **片区激活与门店拜访关联约束**:
   $$x_{it} \le z_{dt}, \quad \forall d \in D, \forall i \in I_d, \forall t \in T$$
2. **单日片区专注度硬约束 (Single-District / Tight-Cluster Exclusivity)**:
   单日内最多允许激活 1 个独立外围片区（如东、海安不能同日拼单；崇川与紧邻的通州允许联合激活）：
   $$z_{\text{如东}, t} + z_{\text{海安}, t} \le 1, \quad \forall t \in T$$
   $$z_{\text{如东}, t} + z_{\text{崇川}, t} \le 1, \quad \forall t \in T$$
   $$\sum_{d \in D} z_{dt} \le 2, \quad \forall t \in T$$

---

### 4.4 单日路线拓扑与时间容量约束 (Daily Tour & Time Budget Constraints)

1. **流守恒与出入度平衡 (Flow Conservation)**:
   $$\sum_{j \in V, j \ne i} y_{jit} = x_{it}, \quad \forall i \in I, \forall t \in T$$
   $$\sum_{j \in V, j \ne i} y_{ijt} = x_{it}, \quad \forall i \in I, \forall t \in T$$
   $$\sum_{j \in I} y_{0jt} = \mathbb{I}\left(\sum_{i \in I} x_{it} > 0\right), \quad \forall t \in T \quad (\text{从起点出发})$$
   $$\sum_{i \in I} y_{i0t} = \mathbb{I}\left(\sum_{i \in I} x_{it} > 0\right), \quad \forall t \in T \quad (\text{返回终点})$$
2. **子回路消除约束 (Subtour Elimination / MTZ)**:
   $$u_{it} - u_{jt} + N \cdot y_{ijt} \le N - 1, \quad \forall i, j \in I, i \ne j, \forall t \in T$$
3. **单日拜访门店数上下限约束 (Daily Stop Bounds)**:
   $$K_{\min} \cdot \mathbb{I}\left(\sum_{i \in I} x_{it} > 0\right) \le \sum_{i \in I} x_{it} \le K_{\max}, \quad \forall t \in T$$
4. **单日总工时容量预算约束 (Daily Time Capacity Budget)**:
   $$\sum_{i \in I} S_i \cdot x_{it} + \sum_{i \in V} \sum_{j \in V, j \ne i} C_{ij} \cdot y_{ijt} \le W_{\max}, \quad \forall t \in T$$

---

## 5. 字典序多目标函数体系 (Lexicographic Multi-Objective Objective)

按照 SVDE A03 领域契约与 S-A §2.5 冻结标准，目标函数定义为严格的**四级字典序最小化（Lexicographic Minimization）**：

$$\operatorname{LexMin} \quad \mathbf{Z} = \left( Z_1, Z_2, Z_3, Z_4 \right)$$

### Level 1: 核心客户脱访与契约违规惩罚 (Contract Compliance)
$$Z_1 = \sum_{i \in I_{\text{REQUIRED}}} P_{\text{MISSED}} \cdot \delta_i + \sum_{i \in I_{\text{STANDARD}}} 10^4 \cdot \delta_i$$
- **含义**: 第一优先级绝对保证核心大店 0 漏访，消除履约事故。

### Level 2: 拜访节奏与周度离散度偏离 (Cadence Smoothness)
$$Z_2 = \sum_{i \in I} \sum_{w=1}^4 \left( \sum_{t \in T_w} x_{it} - \frac{F_i}{4} \right)^2$$
- **含义**: 第二优先级确保拜访在全月 4 周中均匀平滑分布，杜绝月初扎堆、月末脱保。

### Level 3: 空间在途时间与跨区折返损耗 (Spatial Detour & Transit Loss)
$$Z_3 = \sum_{t \in T} \sum_{i \in V} \sum_{j \in V, j \ne i} C_{ij} \cdot y_{ijt} + \sum_{t \in T} \sum_{d \in D} P_{\text{CROSS}} \cdot z_{dt}$$
- **含义**: 第三优先级最小化全月总在途交通时间，惩罚单日多区县跳跃，把路程耗时降至理论极小。

### Level 4: 每日工作负荷均衡度 (Workload Balance)
$$Z_4 = \sum_{t \in T} \left( \sum_{i \in I} x_{it} - \frac{\sum_{i \in I} F_i}{M} \right)^2$$
- **含义**: 第四优先级实现 18 个工作日之间拜访负荷的高度均衡（单日 4~5 家）。
