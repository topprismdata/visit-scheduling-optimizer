# Clustered TSP（已评估 → 本场景否决）

> 类别：构造式（约束 TSP 变体） | 实现：`algos/clustered_tsp.py` | 状态：**否决留档**（方法论完整，业务场景不适配）

## 它解决什么（曾想解决什么）

Amazon Last-Mile 冠军方法（Cook/Held/Helsgaun）的移植尝试：**跨区块边加大常数 M**（10×max(D)）把"同区块店必须连续拜访"的聚类约束编译进 TSP 目标——求解器自动把同区块排连续，区块间顺序仍由全局最优决定。动机：业代跨区穿行成本高（路网/管理原因），希望按行政区块聚类拜访。

```
D2[i][j] = D[stores[i]][stores[j]] + (M if zone(i) != zone(j) else 0)
整体求解 TSP（封装内 nn2opt）→ 同区块自然连续
```

- 区块来源：`core/zone_graph.py` 按广州市四级路网 geojson（含海岸线边界）把门店指派到区县；`zone_of` 也可外部注入。

## 为什么否决（2026-09 评估结论）

1. **KM 恶化**：聚类约束在真实路网上增加的绕行，超过跨区穿行节省——本场景门店分布下净负收益。
2. 论文 Table 3 的"仅 +3.5%"是 Amazon 密集城市场景；我们的门店密度与区块形态不同，**不能外推**。
3. 与 R2′ 走廊语义冲突风险：区块连续化会挤压每日店数走廊。

**裁定**：实现保留（正确性有注释与出处），矩阵与生产不启用；若未来出现"强区块绑定"客户场景可重新评估。

## 引用论文

- Cook, W., Held, M., Helsgaun, K. (2024). *Constrained local search for last-mile routing*. Transportation Science 58(1).（§4.2：Clustered TSP → ATSP 的大常数变换；Table 3：+3.5%）

## 相关文件与测试

- `algos/clustered_tsp.py`；`core/zone_graph.py`（ZoneGraph，注意其中有一处 `/Users/ghb/Downloads` 路网硬编码——关联 issue #5 的可移植性清理）
