# -*- coding: utf-8 -*-
"""HGS-R2' — 方案一: 双种群演化底座与 R2' 算子融合 (Hybrid Genetic Search).

文献锚点:
- Vidal et al. 2012 (EJOR) / 2014 (IEEE TEVC): HGS 双种群架构 — 可行种群与
  惩罚松弛种群并行演化, 违反约束的中间解得以穿越不可行区域; 偏差适应度
  存活选择 (精英保留 + 种群截断);
- Auer, Cesa-Bianchi & Fischer 2002: UCB1 自适应算子调度 (方案二组件复用,
  algos.mab_selector);
- Daganzo 1984 + core.spatial_potential: 空间几何势能软惩罚 (方案三组件
  复用), 引导日分配保持紧致作业组团.

染色体与解码:
  σ: store → weekday (星期几指派)。解码经合同-相位本体 (visit_ir, 经
  core.contract 消费) 派生每店日期集: 周访 = 目标星期几全部槽位, 双周访 =
  相位匹配槽位。每店全月只出现在单一星期几 → R2' 不变量由构造保证
  (星期几本身是决策变量, 换了就整店全月一致)。

适应度 (越小越好):
  fit = 里程 + w_capacity·走廊平方惩罚 + w_spatial·空间势能
  走廊惩罚 Σ_d [max(0,|S_d|-K_max)² + max(0,K_min-|S_d|)²] (HGS 平方罚形态);
  空间势能 Σ_d SpatialPotentialField.evaluate_day_assignment(S_d)。

主循环 (每代):
  二锦标赛选双亲 (可行 ∪ 松弛联合池) → σ 均匀交叉 → UCB1 调度的 R2'
  局部搜索 (四臂: 随机/走廊修复/势能引导/里程引导换挡) → 按可行性分流
  入两种群 → 各自偏差适应度截断存活 + 全局可行精英保留。
"""
import math
import random
import time
from collections import Counter, defaultdict

import numpy as np

from core.base import Algorithm, AlgoResult
from core.contract import contract_of, contract_slot_dates
from core.metric import check_capacity, day_km
from core.spatial_potential import SpatialPotentialField
from algos.mab_selector import UCB1Selector
from algos.registry import register
from algos.sp_matheuristic import check_r2prime
from algos.tsp_engine import _exact_open_tsp, _nn2opt_open


def _ins_cost(members, c, D):
    """把 c 插入 members 开放链的最优位置代价 (空集=0)."""
    if not members:
        return 0.0
    cand = [D[c][members[0]], D[members[-1]][c]]
    cand += (D[a][c] + D[c][b] - D[a][b] for a, b in zip(members, members[1:]))
    return min(cand)


def _rem_gain(members, c, D):
    """从 members 开放链移除 c 的里程增益 (正=变短). 若 c 不在 members 则返回 0.0."""
    if c not in members:
        return 0.0
    i = members.index(c)
    if len(members) == 1:
        return 0.0
    if i == 0:
        return D[c][members[1]]
    if i == len(members) - 1:
        return D[members[-2]][c]
    return D[members[i - 1]][c] + D[c][members[i + 1]] - D[members[i - 1]][members[i + 1]]


class _Ind:
    """个体: σ 染色体 + 缓存评估 (里程/走廊罚/空间势能/总适应度/可行性)."""

    __slots__ = ("sigma", "km", "cap_pen", "sp_pen", "fit", "feasible")

    def __init__(self, sigma, km, cap_pen, sp_pen, w_capacity, w_spatial):
        self.sigma = sigma
        self.km = km
        self.cap_pen = cap_pen
        self.sp_pen = sp_pen
        self.fit = km + w_capacity * cap_pen + w_spatial * sp_pen
        self.feasible = cap_pen <= 1e-9

    @property
    def key(self):
        return tuple(sorted(self.sigma.items()))


@register
class HGSR2Optimizer(Algorithm):
    """双种群混合遗传搜索 (可行 + 惩罚松弛), R2' 合法解空间原生搜索."""

    name = "hgs_r2"
    ARMS = ("weekday_random", "weekday_capacity", "weekday_spatial",
            "weekday_distance")

    def __init__(self, pop_size=10, n_gens=30, ls_iters=20,
                 w_capacity=50.0, w_spatial=0.1):
        if not (isinstance(pop_size, int) and pop_size >= 2):
            raise ValueError(f"pop_size 必须 ≥ 2, 收到 {pop_size!r}")
        if not (isinstance(n_gens, int) and n_gens >= 1):
            raise ValueError(f"n_gens 必须 ≥ 1, 收到 {n_gens!r}")
        if not (isinstance(ls_iters, int) and ls_iters >= 1):
            raise ValueError(f"ls_iters 必须 ≥ 1, 收到 {ls_iters!r}")
        for nm, w in (("w_capacity", w_capacity), ("w_spatial", w_spatial)):
            if not (isinstance(w, (int, float)) and math.isfinite(w) and w >= 0.0):
                raise ValueError(f"{nm} 必须为非负有限值, 收到 {w!r}")
        self.pop_size = pop_size
        self.n_gens = n_gens
        self.ls_iters = ls_iters
        self.w_capacity = float(w_capacity)
        self.w_spatial = float(w_spatial)
        # 双种群容器 + 方案二组件 (solve 时按次重置, 可重复调用)
        self.feasible_pop = []
        self.infeasible_pop = []
        self.selector = UCB1Selector(list(self.ARMS))
        self.potential = None
        self.stats = {"created_feasible": 0, "created_infeasible": 0}

    # ------------------------------------------------------------------
    def solve(self, data, D, time_budget=60.0, seed=42, exact_tl=5.0):
        rng = random.Random(seed)
        D = np.asarray(D, dtype=float)
        t0 = time.time()
        deadline = t0 + time_budget

        dates = sorted(data.dates)
        if len(dates) < 2:
            raise ValueError("dates 至少需要 2 个工作日")
        wd_dates = defaultdict(list)
        for d in dates:
            wd_dates[d.weekday()].append(d)
        weekdays = sorted(wd_dates)
        if len(weekdays) < 2:
            raise ValueError("至少需要 2 个不同星期几才能换挡")
        contracts = contract_of(data.days_orig, dates)
        if not contracts:
            raise ValueError("days_orig 无门店, 无法反解合同")
        stores = sorted(contracts)
        kmin, kmax = int(data.min_daily_capacity), int(data.max_daily_capacity)
        if kmin > 0 and kmax > 0 and kmin > kmax:
            raise ValueError(f"走廊非法: K_min={kmin} > K_max={kmax}")

        # 方案三组件: 空间几何势能场 (总凸包面积逐日公平份额)
        self.potential = SpatialPotentialField(
            list(zip(data.lon, data.lat)), n_days=len(dates))
        self.selector = UCB1Selector(list(self.ARMS))
        self.feasible_pop, self.infeasible_pop = [], []
        self.stats = {"created_feasible": 0, "created_infeasible": 0}

        def decode(sigma):
            """σ → {date: [store]} (合同槽位派生, R2' 由构造保证)."""
            days = defaultdict(list)
            for c in stores:
                kappa, phi = contracts[c]
                for d in contract_slot_dates(kappa, phi, wd_dates[sigma[c]]):
                    days[d].append(c)
            return days

        def evaluate(sigma):
            days = decode(sigma)
            km = cap = sp = 0.0
            for d in sorted(days):
                members = days[d]
                km += day_km(_nn2opt_open(sorted(members), D), D)
                n = len(members)
                if kmax > 0 and n > kmax:
                    cap += (n - kmax) ** 2
                if kmin > 0 and n < kmin:
                    cap += (kmin - n) ** 2
                sp += self.potential.evaluate_day_assignment(members)
            return _Ind(dict(sigma), km, cap, sp, self.w_capacity, self.w_spatial)

        # ---- 初始种群: 原计划 σ (可行锚) + 随机 σ (分流进两种群) ----
        orig_wd = {}
        for dd, seq in data.days_orig.items():
            for c in seq:
                orig_wd.setdefault(c, dd.weekday())
        sigma_orig = {c: orig_wd[c] for c in stores}
        base = evaluate(sigma_orig)
        self._admit(base)
        for _ in range(self.pop_size - 1):
            self._admit(evaluate(
                {c: rng.choice(weekdays) for c in stores}))
        gbest = min(self.feasible_pop, key=lambda x: x.fit) if self.feasible_pop \
            else min(self.infeasible_pop, key=lambda x: x.fit)

        # ---- UCB1 调度的 R2' 算子臂 (方案二 × R2' 融合) ----
        def op_random(sigma):
            c = rng.choice(stores)
            w2 = rng.choice([w for w in weekdays if w != sigma[c]])
            return {**sigma, c: w2}

        def op_capacity(sigma):
            """走廊修复: 过载星期几迁出 / 欠载星期几迁入."""
            counts = Counter(sigma[c] for c in stores)
            over = [w for w in weekdays if kmax > 0 and counts[w] > kmax]
            under = [w for w in weekdays if kmin > 0 and counts[w] < kmin]
            if over:
                w_from = max(over, key=lambda w: counts[w])
                w_to = min(weekdays, key=lambda w: counts[w])
            elif under:
                w_to = min(under, key=lambda w: counts[w])
                w_from = max(weekdays, key=lambda w: counts[w])
                if counts[w_from] <= counts[w_to]:
                    return op_random(sigma)
            else:
                return op_random(sigma)
            if w_from == w_to:
                return op_random(sigma)
            c = rng.choice(sorted(c for c in stores if sigma[c] == w_from))
            return {**sigma, c: w_to}

        def _best_weekday(sigma, delta_fn):
            """对随机店枚举全部目标星期几, 按 Δ 度量取最优换挡."""
            c = rng.choice(stores)
            w1 = sigma[c]
            best_w, best_delta = None, math.inf
            for w2 in weekdays:
                if w2 == w1:
                    continue
                delta = delta_fn(sigma, c, w1, w2)
                if delta < best_delta:
                    best_w, best_delta = w2, delta
            return {**sigma, c: best_w} if best_w is not None else None

        def op_spatial(sigma):
            """势能引导: 换挡目标 = 空间势能增量最小的星期几 (方案三评估)."""
            days = decode(sigma)
            pot = self.potential.evaluate_day_assignment

            def delta(sigma_, c, w1, w2):
                kappa, phi = contracts[c]
                d2_set = contract_slot_dates(kappa, phi, wd_dates[w2])
                d1_set = contract_slot_dates(kappa, phi, wd_dates[w1])
                dv = 0.0
                for d in d2_set:
                    m = sorted(days[d])
                    dv += pot(m + [c]) - pot(m)
                for d in d1_set:
                    m = sorted(days[d])
                    dv += pot([x for x in m if x != c]) - pot(m)
                return dv

            return _best_weekday(sigma, delta)

        def op_distance(sigma):
            """里程引导: 换挡目标 = 插入代价-移除增益 最小的星期几."""
            days = {d: sorted(m) for d, m in decode(sigma).items()}

            def delta(sigma_, c, w1, w2):
                kappa, phi = contracts[c]
                d2_set = contract_slot_dates(kappa, phi, wd_dates[w2])
                d1_set = contract_slot_dates(kappa, phi, wd_dates[w1])
                return (sum(_ins_cost(days[d], c, D) for d in d2_set)
                        - sum(_rem_gain(days[d], c, D) for d in d1_set))

            return _best_weekday(sigma, delta)

        ops = dict(zip(self.ARMS, (op_random, op_capacity, op_spatial,
                                   op_distance)))

        def local_search(ind):
            cur = ind
            for _ in range(self.ls_iters):
                arm = self.selector.select_arm()
                cand_sigma = ops[arm](cur.sigma)
                if cand_sigma is None:
                    self.selector.update(arm, 0.0)
                    continue
                cand = evaluate(cand_sigma)
                reward = cur.fit - cand.fit
                if cand.fit < cur.fit - 1e-12:
                    self.selector.update(arm, reward)
                    cur = cand
                else:
                    self.selector.update(arm, 0.0)
            return cur

        def pick_parent():
            a, b = rng.sample(self.feasible_pop + self.infeasible_pop, 2)
            return a if a.fit <= b.fit else b

        # ---- 世代演化 ----
        history = []
        for gen in range(self.n_gens):
            if time.time() >= deadline:
                break
            for _ in range(self.pop_size):
                pa, pb = pick_parent(), pick_parent()
                child_sigma = {c: (pa.sigma[c] if rng.random() < 0.5 else pb.sigma[c])
                               for c in stores}
                self._admit(local_search(evaluate(child_sigma)))
            # 存活: 各种群偏差适应度截断 (精英在前, σ 去重), 可行精英强制续代
            self.feasible_pop = self._truncate(self.feasible_pop)
            self.infeasible_pop = self._truncate(self.infeasible_pop)
            pool_best = self.feasible_pop[0] if self.feasible_pop else \
                self.infeasible_pop[0]
            if pool_best.feasible and pool_best.fit < gbest.fit - 1e-12:
                gbest = pool_best
            if gbest.feasible and not any(x is gbest for x in self.feasible_pop):
                self.feasible_pop.append(gbest)
            history.append({"gen": gen, "best_fit": gbest.fit,
                            "best_km": gbest.km,
                            "n_feasible": len(self.feasible_pop),
                            "n_infeasible": len(self.infeasible_pop)})

        # ---- 终解: 可行精英解码 + CP-SAT 单日精确重排 (Layer 2 口径) ----
        best_days = decode(gbest.sigma)
        days, km = {}, 0.0
        for d in sorted(best_days):
            route = _exact_open_tsp(sorted(best_days[d]), D, exact_tl)
            days[d] = route
            km += day_km(route, D)
        return AlgoResult(
            name=self.name, days=days, km=round(km, 3),
            capacity_ok=check_capacity(days, kmax, kmin),
            elapsed=round(time.time() - t0, 3),
            metadata={
                "gens": len(history), "history": history,
                "baseline_km": round(base.km, 3), "baseline_fit": base.fit,
                "r2_ok": len(check_r2prime(days)) == 0,
                "arms": list(self.ARMS),
                "mab_pulls": dict(self.selector.pulls),
                "mab_mean_rewards": self.selector.mean_rewards,
                "spatial_penalty": gbest.sp_pen,
                "capacity_penalty": gbest.cap_pen,
                "pop_feasible": len(self.feasible_pop),
                "pop_infeasible": len(self.infeasible_pop),
                "created": dict(self.stats), "seed": seed,
            })

    # ------------------------------------------------------------------
    def _admit(self, ind):
        """按可行性分流个体进双种群 (Vidal 双种群准入)."""
        if ind.feasible:
            self.feasible_pop.append(ind)
            self.stats["created_feasible"] += 1
        else:
            self.infeasible_pop.append(ind)
            self.stats["created_infeasible"] += 1

    def _truncate(self, pop):
        """偏差适应度存活: 按 fit 升序 σ 去重截断至 pop_size."""
        seen, out = set(), []
        for ind in sorted(pop, key=lambda x: (x.fit, x.key)):
            if ind.key in seen:
                continue
            seen.add(ind.key)
            out.append(ind)
            if len(out) == self.pop_size:
                break
        return out
