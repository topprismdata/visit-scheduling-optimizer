"""PlanningPolicy — 统一约束契约 (P0 / Task 1, 来源: 优化建议 §3.3)

CG 求解器、CP-SAT、ALNS、validator、报告与文档全部引用同一份约束对象,
消除隐藏全局常量 (solver.MAX_PER_DAY = 6 / baselines 全局) 与口径漂移。

用法:
    policy = PlanningPolicy(n_customers=40, freq=[...])
    policy.validate_solution(sol, day_times=[...]) -> list[str]  # 违规清单, 空 = 合法
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping, Sequence

DEFAULT_MAX_VISITS_PER_DAY = 6
DEFAULT_MAX_WORK_MINUTES_PER_DAY = 540.0


@dataclass(frozen=True)
class PlanningPolicy:
    """统一约束契约 (frozen)。所有求解器与 validator 的唯一约束事实源。

    Attributes:
        horizon_days: 规划期天数 (默认 20 个工作日)。
        max_visits_per_day: 单日拜访客户数上限 (替代散落的 MAX_PER_DAY = 6)。
        max_work_minutes_per_day: 单日在途+在店工时上限 (分钟; None = 不限,
            对齐 solver.solve_time_cg 的 daily_cap 语义)。
        min_interval_days: 频次 f>=2 客户的最小重访间隔 (天)。None = 由
            horizon // (freq + 1) 推导 (沿用 ALNS gap 公式)。
        frequency_rules: 客户 id -> 目标月频次 (必须逐户给出, 不可缺省)。
        workload_balance_policy: 负载均衡策略声明 ("none" / "min_max_spread"),
            仅作契约声明, 由求解器各自实现并在 DecisionEvidence 中回报。
        depot_policy / route_type: 口径声明 ("round_trip"/"open"), 同上。
    """

    n_customers: int
    frequency_rules: Mapping[int, int]
    horizon_days: int = 20
    max_visits_per_day: int = DEFAULT_MAX_VISITS_PER_DAY
    max_work_minutes_per_day: float | None = DEFAULT_MAX_WORK_MINUTES_PER_DAY
    min_interval_days: Mapping[int, int] | None = None
    depot_policy: str = "round_trip"
    route_type: str = "closed"
    workload_balance_policy: str = "none"
    tier_service_minutes: Mapping[str, float] | None = None  # {"Key":60,"A":45,"B":45,...}
    max_work_minutes_by_tier: Mapping[str, float] | None = None  # 差异化工时上限
    coverage_policies: tuple | None = None  # CoveragePolicy 引用列表 (可选, Phase 1+)

    def __post_init__(self) -> None:
        if self.horizon_days <= 0:
            raise ValueError(f"horizon_days 必须 > 0, 实际 {self.horizon_days}")
        if self.max_visits_per_day <= 0:
            raise ValueError(f"max_visits_per_day 必须 > 0, 实际 {self.max_visits_per_day}")
        if self.max_work_minutes_per_day is not None and self.max_work_minutes_per_day <= 0:
            raise ValueError("max_work_minutes_per_day 必须 > 0 或 None")
        if sorted(self.frequency_rules) != list(range(self.n_customers)):
            raise ValueError(
                "frequency_rules 必须恰好覆盖客户 0..n-1 "
                f"(n={self.n_customers}, 实际键={sorted(self.frequency_rules)})"
            )
        if any(f < 1 for f in self.frequency_rules.values()):
            raise ValueError("拜访频次必须 >= 1")
        if self.depot_policy not in ("round_trip", "open"):
            raise ValueError(f"depot_policy 非法: {self.depot_policy!r}")

    # ------------------------------------------------------------------
    def effective_gap(self, cust: int) -> int:
        """客户最小重访间隔: 显式规则优先, 否则按频次推导 (days // (f + 1))。"""
        if self.min_interval_days is not None and cust in self.min_interval_days:
            return self.min_interval_days[cust]
        return self.horizon_days // (self.frequency_rules[cust] + 1)

    def gaps(self) -> dict[int, int]:
        return {i: self.effective_gap(i) for i in range(self.n_customers)}

    # ------------------------------------------------------------------
    def validate_solution(
        self,
        sol: Sequence[set[int]],
        day_times: Sequence[float] | None = None,
        *,
        tol: float = 1e-6,
    ) -> list[str]:
        """独立 solution validator — 与任何求解器实现无关的最终裁决。

        Args:
            sol: len(horizon_days) 的每日客户集合。
            day_times: 可选的每日实际工时 (分钟); 提供则校验工时上限。
            tol: 浮点比较容差。

        Returns:
            违规描述列表; 空列表 = 方案在契约下完全合法。
        """
        v: list[str] = []
        if len(sol) != self.horizon_days:
            v.append(f"sol 天数 {len(sol)} != horizon {self.horizon_days}")

        visits_of: dict[int, list[int]] = {}
        for d, day in enumerate(sol):
            if self.max_visits_per_day is not None and len(day) > self.max_visits_per_day:
                v.append(
                    f"day{d}: 客户数 {len(day)} 超上限 {self.max_visits_per_day}"
                )
            for c in day:
                if not (0 <= c < self.n_customers):
                    v.append(f"day{d}: 非法客户 id {c}")
                    continue
                visits_of.setdefault(c, []).append(d)
            if day_times is not None and self.max_work_minutes_per_day is not None:
                if day_times[d] > self.max_work_minutes_per_day + tol:
                    v.append(
                        f"day{d}: 工时 {day_times[d]:.1f} 超上限 "
                        f"{self.max_work_minutes_per_day:.1f}"
                    )

        # 频次与间隔
        for c in range(self.n_customers):
            days_c = sorted(visits_of.get(c, []))
            want = self.frequency_rules[c]
            if len(days_c) != want:
                v.append(f"cust{c}: 频次 {len(days_c)} != 要求 {want}")
            gap = self.effective_gap(c)
            for a, b in zip(days_c, days_c[1:]):
                if b - a < gap:
                    v.append(f"cust{c}: 重访间隔 {b}-{a}={b - a} < 最小 {gap}")
        return v

    def service_minutes_for_tier(self, tier: str) -> float:
        """按门店级别返回差异化服务时长 (默认 45 min)。"""
        if self.tier_service_minutes and tier in self.tier_service_minutes:
            return self.tier_service_minutes[tier]
        return 45.0

    def summary(self) -> dict:
        """供 CG/ALNS 对比报告与 DecisionEvidence 引用的约束参数摘要。"""
        return {
            "horizon_days": self.horizon_days,
            "max_visits_per_day": self.max_visits_per_day,
            "max_work_minutes_per_day": self.max_work_minutes_per_day,
            "depot_policy": self.depot_policy,
            "route_type": self.route_type,
            "workload_balance_policy": self.workload_balance_policy,
            "n_customers": self.n_customers,
        }
