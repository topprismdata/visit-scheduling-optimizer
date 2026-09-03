# -*- coding: utf-8 -*-
"""Clustered TSP — 亚马逊 2021 方法论 (Cook/Held/Helsgaun 2022).
正确实现: 跨区块边 + M (大常数) → 整体 TSP 求解。
M 迫使求解器将同区块店连续排列，区块间顺序由求解器全局最优决定。
参考: 论文 Section 4.2: "An instance of the clustered TSP can be transformed to
an ATSP by adding a large constant M to the travel time between any pair of
stops that do not have matching zone IDs."
论文 Table 3: 聚类约束仅增加 3.5% 里程 (vs 最优 ATSP)."""
import time
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km
from algos.registry import register
from algos.tsp_engine import _nn2opt_open


def clustered_tsp_route(seq, D, zone_of, M=None):
    """Clustered ATSP: 跨区块边加 M → 整体 TSP 求解.
    seq: 当日店索引列表 (任意顺序, 只取集合)
    D: 路网距离矩阵
    zone_of: {store_idx: zone_id}
    M: 跨区块惩罚 (默认 10×max(D), 论文建议 large constant)
    返回: 排序后的店索引 (同区块连续, 由求解器自动决定)
    """
    stores = sorted(set(seq))
    n = len(stores)
    if n <= 2: return list(seq)
    if M is None:
        M = max(max(row) for row in D) * 10.0
    # 构造带聚类约束的矩阵
    D2 = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j: continue
            D2[i][j] = D[stores[i]][stores[j]]
            if zone_of[stores[i]] != zone_of[stores[j]]:
                D2[i][j] += M  # 跨区块惩罚
    # 整体求解 TSP (NN+2opt)
    result = _nn2opt_open(list(range(n)), D2)
    return [stores[i] for i in result]


@register
class ClusteredTSP(Algorithm):
    """亚马逊 Clustered ATSP: 跨区块+M → 整体求解."""
    name = "clustered_tsp"

    def solve(self, data, D, time_budget=300, zone_of=None):
        if zone_of is None:
            from core.zone_graph import ZoneGraph
            zg = ZoneGraph('/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson',
                           keep_codes={'440103','440104','440105','440106','440111','440112','440113'})
            zone_of = {i: z for i, z in enumerate(zg.assign_stores(data.lon, data.lat))}
        days = {}
        for dd, seq in data.days_orig.items():
            days[dd] = clustered_tsp_route(seq, D, zone_of)
        return AlgoResult(name=self.name, days=days, km=total_km(days, D),
                          metadata={"zones": len(set(zone_of.values()))})
