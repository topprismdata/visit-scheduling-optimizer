# -*- coding: utf-8 -*-
"""Algorithm base class and result types."""
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, Optional


@dataclass
class LineData:
    """Data for one sales line (线路)."""
    line_id: str          # e.g. "09"
    line_name: str        # e.g. "海珠荔湾09"
    codes: list[str]       # 客户编码, 索引=store_idx
    lon: list[float]       # 经度, 与 codes 对齐
    lat: list[float]       # 纬度, 与 codes 对齐
    dates: list[date]      # 所有工作日
    days_orig: dict[date, list[int]]  # 每日原始顺序 (store_idx 列表)
    freq: dict[str, int]   # 每店月总次数 {编码: 次数}
    stores: int             # 店数
    visits: int             # 总拜访次数
    min_daily_capacity: int = 0  # 单日门店数硬下限: min(|S_t^orig|) 防闲置/出工不出力
    max_daily_capacity: int = 0  # 单日门店数硬上限: max(|S_t^orig|) 防过劳/物理不可行

    def __post_init__(self):
        if self.days_orig:
            lens = [len(v) for v in self.days_orig.values()]
            if self.min_daily_capacity <= 0:
                self.min_daily_capacity = min(lens)
            if self.max_daily_capacity <= 0:
                self.max_daily_capacity = max(lens)
@dataclass
class AlgoResult:
    """One algorithm's output."""
    name: str                                   # 算法标识
    days: dict[date, list[int]]                 # 每日分配 {date: [store_idx]}
    km: float = 0.0                             # 总路网里程 (km)
    moves: int = 0                              # 跨日移动次数
    count_ok: bool = True                       # 每店总次数校验
    capacity_ok: bool = True                    # 单日容量上限校验 (len <= max_daily_capacity)
    elapsed: float = 0.0                        # 耗时 (秒)
    metadata: dict = field(default_factory=dict)  # 算法特有信息


class Algorithm:
    """Base class for all optimization algorithms.
    
    Subclass MUST set `name` and implement `solve()`.
    """
    name = ""  # override in subclass

    def solve(self, data: LineData, D: list[list[float]]) -> AlgoResult:
        """Return store assignment per day after optimization.
        
        Args:
            data: line data from loader
            D: n×n road distance matrix (km, n=len(data.codes))
        
        Returns:
            AlgoResult with days dict and metrics
        """
        raise NotImplementedError