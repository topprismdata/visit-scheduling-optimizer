"""
domain.entities
~~~~~~~~~~~~~~~~
Authoritative domain entities for the Periodic Field-Sales Visit Planning system.

Pure Python dataclasses representing real-world FMCG business entities and outputs.
Zero dependencies on mathematical solvers, OR-Tools, or execution engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Customer:
    """
    业务客户实体（门店 / 销售网点）

    Attributes:
        id: 内部连续索引 0..N-1 (用于矩阵与图算法映射)
        code: 业务唯一编码 (如 "S001")
        name: 门店显示名称
        latitude: WGS84 纬度
        longitude: WGS84 经度
        frequency: 4 周规划周期内规定拜访总频次 (e.g. 1, 2, 4)
        service_duration_min: 进店标准化在店服务耗时 (分钟)
        county: 所属行政区县/网格标识 (用于匹配路网速度与停靠模型)
        allowed_weekdays: 允许拜访的星期元组 (0=周一 .. 4=周五)
        historical_weekday_counts: 历史各星期实际走访次数分布 (长度为 5)
    """

    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    frequency: int
    service_duration_min: float
    county: str = "DEFAULT"
    allowed_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)
    historical_weekday_counts: tuple[int, ...] = (0, 0, 0, 0, 0)

    def is_weekday_allowed(self, weekday: int) -> bool:
        """检查该客户是否允许在指定星期拜访 (0=周一 .. 4=周五)"""
        return weekday in self.allowed_weekdays


@dataclass(frozen=True)
class Depot:
    """
    销售人员出发车场 / 驻地实体

    Attributes:
        id: 驻地编号
        name: 驻地名称 (如 "南通业务部")
        latitude: WGS84 纬度
        longitude: WGS84 经度
    """

    id: int
    name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class CostBreakdown:
    """
    单日拜访路线的白盒化耗时与物理指标细分

    遵循 Dalla Chiara & Goodchild (2020) 城市商用车耗时分解标准：
    Total Time = Driving Time + Service Time + Dwell Time

    Attributes:
        driving_time_min: 纯路网在途行驶耗时 (经过两段式速度模型校准)
        service_time_min: 进店店内标准化服务时长总和
        dwell_time_min: 寻找车位/进出商场/安检等固定停靠沉没耗时总和
        total_time_min: 当日总工作耗时 (driving + service + dwell)
        total_distance_km: 当日物理实际行驶总里程 (km)
        route_sequence: 最优访问顺序序列 (包含客户 ID 列表)
    """

    driving_time_min: float
    service_time_min: float
    dwell_time_min: float
    total_time_min: float
    total_distance_km: float
    route_sequence: tuple[int, ...]


@dataclass(frozen=True)
class DaySchedule:
    """
    单日最终排班结果实体

    Attributes:
        day_index: 周期内工作日索引 (0..T-1)
        weekday: 星期几 (0=周一 .. 4=周五)
        week_number: 第几周 (1..4)
        customers: 当日拜访的客户实体元组 (按最优访问顺序排列)
        cost_breakdown: 当日白盒化耗时与里程细分
    """

    day_index: int
    weekday: int
    week_number: int
    customers: tuple[Customer, ...]
    cost_breakdown: CostBreakdown

    @property
    def visit_count(self) -> int:
        return len(self.customers)

    @property
    def is_active(self) -> bool:
        return len(self.customers) > 0


@dataclass
class SchedulePlan:
    """
    全周期（4周20工作日）完整排班方案实体

    Attributes:
        scenario_id: 场景/算例标识
        horizon_days: 规划总工作日天数 (通常为 20)
        daily_schedules: 每日排班详情列表 (长度为 horizon_days)
        total_driving_min: 全周期累计在途行驶耗时 (分钟)
        total_service_min: 全周期累计店内服务耗时 (分钟)
        total_dwell_min: 全周期累计停靠寻路耗时 (分钟)
        total_time_min: 全周期累计总工作耗时 (分钟)
        total_distance_km: 全周期累计总行驶里程 (km)
        active_days_count: 实际出勤工作天数
        is_feasible: 是否满足所有业务硬约束
        solver_status: 求解器返回状态名称 (如 "OPTIMAL", "FEASIBLE", "INFEASIBLE")
        metadata: 决策血缘与调试元数据 (对齐 W3C PROV-O)
    """

    scenario_id: str
    horizon_days: int
    daily_schedules: list[DaySchedule]
    total_driving_min: float
    total_service_min: float
    total_dwell_min: float
    total_time_min: float
    total_distance_km: float
    active_days_count: int
    is_feasible: bool
    solver_status: str
    metadata: dict = field(default_factory=dict)
