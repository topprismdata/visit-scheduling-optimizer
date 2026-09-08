# -*- coding: utf-8 -*-
"""Branch-and-Price (B&P) — 合同-相位集合划分的分支定价 matheuristic.

与 SPMatheuristic (CG 收敛后池上一次性 IP = restrict-and-price) 的本质区别:
B&P 在分支树上搜索, 每个节点用列生成求解 LP 松弛; 分支变量 y_cd 的 0/1 性由
x 积分性蕴含（店-日指派分支，customer–date assignment branching；非经典 Ryan–Foster
配对分支）. 节点 LP 值的语义: 仅当该节点经精确定价证明不存在负 rc 列后, 才是子树的
有效下界 (node_valid_lb); 启发式定价停住时的值只是受限主问题 LP 值 (rmp_lp_value),
不得用于剪枝或证书 (2026-09-07 评审修正).

主问题 (节点, v2 链接形态: 固定 (店,日期) 行空间, 对偶语义同
visitmodel.sp.formulation.sp_solve_lp_v2):
    min Σ c_r x_r
    s.t. Σ_{r∈R_d} x_r = 1                 ∀d            (对偶 π_d)
         y_cd − Σ_{r∈R_d∋c} x_r = 0        ∀(c,d)        (对偶 β_cd, 链接行)
         y_cd ≤ z_{c,wd(d)}                 ∀(c,d)        (星期几绑定)
         Σ_d y_cd = Σ_w f_cw·z_cw           ∀c            (合同频次, 经 y 计数)
         Σ_w z_cw = 1                        ∀c            (R2′ 唯一星期几)
         forced: y_cd ∈ [1,1]; forbidden: y_cd ∈ [0,0]; 非法 (c,d): UB=0
z 只定义于正频次星期域 W⁺ (f_cw > 0), 不参与分支; 合法域由 y 上界内生化,
不再依赖逐列 x ≤ z 绑定行 → 行空间固定, 回归标准 fixed-row CG。

定价 (代数闭环): rc(r@d) = km(r) − π_d + Σ_{c∈r} β_cd, 即 reward_cd = −β_cd。

分支规则: y_cd = Σ_{r∈R_d∋c} x_r ∈ (0,1) 分数 → forced(c,d)=1 | forbidden(c,d)=0.
分数 x 必给出分数 y (列含 ≥2 店); y 全整 ⇒ x 全整 → incumbent. 分支变量
(c,d) 对有限, 每层固定一个指派 → 有限收敛.

定价: rc(r@d) = km(r) − Σ_{c∈r}(μ_c + λ_{c,d}) − π_d.
启发式 top-m 奖励贪心插入 (走廊/合同合法域/节点 forbidden 硬剪) 收敛后,
CP-SAT 精确奖收集开链 (dummy depot 0 成本弧 + 自环可选节点 AddCircuit) 兜底.

能力边界 (与 price_columns 同一口径): 定价为启发式+限时精确兜底, 界是"已探索
列空间的界；受限池上节点 LP 不可行时先尝试强制/未覆盖店的贪心可行性恢复；恢复失败才按启发式剪枝，任何此类节点均不签发全局最优证明。
TSP 因子口径与 ALNS/HGS 一致: 树内代价为插入序 km (raw 口径), 产出列由调用方
按选定 TSP 重排计价后交 Contract-SP 终闸.
"""
from __future__ import annotations

import time
from datetime import datetime
from collections import Counter

from algos.registry import register
from core.base import Algorithm, AlgoResult
from core.contract import (
    check_contract, contract_of, contract_slot_dates, legal_date_map,
)
from core.metric import check_capacity, day_km
from opticore.heuristics import nn2opt_open as _nn2opt_open
from visitmodel.sp.formulation import _fw_table, _wd, weekday_dates
from algos.pricing_contract import (
    CGTerminationStatus, ColumnCandidate, ColumnLineage,
    ColumnValidator, PricingCertificate, ProofLevel)

_EPS = 1e-6      # 数值零 (对偶/约简成本)
_FRAC = 1e-6     # 分数判定阈


class _BPNode:
    """分支树节点 = 两组分支决策 (forced/forbidden 店-日指派)."""

    __slots__ = ("forbidden", "forced")

    def __init__(self, forbidden=frozenset(), forced=frozenset()):
        self.forbidden = frozenset(forbidden)   # {(store, date)}
        self.forced = frozenset(forced)         # {(store, date)}

    def child_forced(self, c, d):
        return _BPNode(self.forbidden, self.forced | {(c, d)})

    def child_forbidden(self, c, d):
        return _BPNode(self.forbidden | {(c, d)}, self.forced)


class BranchAndPrice:
    """合同模式 B&P 引擎 (一条线一次求解)."""

    def __init__(self, dates, k_c, D, contracts, days_orig, min_daily, max_daily,
                 time_budget=60.0, max_nodes=200, top_m=40,
                 exact_pricing=True, exact_tl=1.0, verbose=False,
                 initial_days=None, initial_pool=None, cg_max_iters=15):
        self.dates = list(dates)
        self.k_c = dict(k_c)
        self.D = D
        self.contracts = contracts
        self.days_orig = days_orig
        self.min_daily = min_daily
        self.max_daily = max_daily
        self.time_budget = time_budget
        self.max_nodes = max_nodes
        self.top_m = top_m
        self.cg_max_iters = cg_max_iters
        self.exact_pricing = exact_pricing
        self.exact_tl = exact_tl
        self.verbose = verbose
        self.initial_days = initial_days
        self.initial_pool = list(initial_pool or [])

        self.wd_groups = weekday_dates(self.dates)
        self.legal = legal_date_map(contracts, self.dates)   # {c: set(date)}
        self.fw = _fw_table(contracts, self.wd_groups)       # {c: {w: f}}
        self.w_plus = {c: sorted(w for w, f in self.fw[c].items() if f > 0)
                       for c in self.k_c}            # 正频次星期域 (v2)
        self.pool = []            # [(date, route, km_internal)] 树内共享, 节点按分支过滤
        self.pool_keys = set()
        self.validator = ColumnValidator(self.legal, self.min_daily, self.max_daily)
        self.lineage = []                 # ColumnLineage (契约层 v0.4)
        self._next_col_id = 0
        self.incumbent = None     # (km_internal, {date: route})
        self.root_lb = None
        self.nodes_explored = 0
        self.cg_iters_total = 0
        self.exact_pricing_calls = 0
        self.lp_infeasible_prunes = 0
        self.propagate_prunes = 0         # 分支传播判死的子节点数
        self.converge_attempts = 0        # "无负列→节点LP收敛"判定次数
        self.converge_proven = 0          # 其中精确定价给出证明 (全部 OPTIMAL) 的次数
        self.lp_nonoptimal_nodes = 0      # GLOP 未返回 OPTIMAL 的节点数
        self.cg_nonconverged_nodes = 0    # 列生成达到上限/恢复失败的节点数
        self.pricing_stalled = 0          # 有负列候选但未能扩充节点池的次数
        self.t0 = time.perf_counter()
        self._warm_start()

    # ---------------- 池管理 ----------------
    def add_columns(self, cols, source="HEURISTIC"):
        """契约层: 定价产出禁止直接入池 — Normalizer/Validator 验证后成 MasterColumn."""
        added = 0
        for dd, route, km in cols:
            cand = ColumnCandidate(route=list(route), reduced_cost=float(km),
                                   source=source)
            vroute, vresult = self.validator.validate(cand, dd)
            if vroute is None:
                continue
            key = (dd, frozenset(vroute))   # 同店集不同顺序 = 同一列 (x 劈裂防护)
            if key in self.pool_keys:
                continue
            self.pool_keys.add(key)
            self.pool.append((dd, list(vroute), km))
            self.lineage.append(ColumnLineage(
                column_id=self._next_col_id, source_oracle=source,
                candidate_rc=float(km), validated_at=datetime.now().isoformat(),
                validator_result=vresult))
            self._next_col_id += 1
            added += 1
        return added

    def _node_pool(self, node: _BPNode):
        forb = node.forbidden
        return [(dd, route, km) for dd, route, km in self.pool
                if not any((c, dd) in forb for c in route)]

    def _randomized_schedule(self, rng, swaps=0):
        """Return a legal schedule after whole-store weekday swaps."""
        days = {dd: set(seq) for dd, seq in self.days_orig.items()}
        store_dates = {c: {dd for dd, seq in days.items() if c in seq}
                       for c in self.k_c}
        groups = {}
        for c, dates in store_dates.items():
            weekdays = {dd.weekday() for dd in dates}
            if len(weekdays) != 1:
                continue
            signature = (self.contracts[c], len(dates))
            groups.setdefault(signature, []).append(c)

        target = max(0, int(swaps))
        for _ in range(target):
            pairs = []
            for stores in groups.values():
                for i, a in enumerate(stores):
                    for b in stores[i + 1:]:
                        a_dates = store_dates[a]
                        b_dates = store_dates[b]
                        if not a_dates or not b_dates or a_dates & b_dates:
                            continue
                        if next(iter(a_dates)).weekday() != next(iter(b_dates)).weekday():
                            pairs.append((a, b))
            if not pairs:
                break
            a, b = rng.choice(pairs)
            a_dates = store_dates[a]
            b_dates = store_dates[b]
            for dd in a_dates:
                days[dd].remove(a)
                days[dd].add(b)
            for dd in b_dates:
                days[dd].remove(b)
                days[dd].add(a)
            store_dates[a], store_dates[b] = b_dates, a_dates
        return {dd: sorted(days[dd]) for dd in self.dates}
    def _calendar_search(self, rng, iterations):
        """Find a lower-cost contract-feasible calendar by whole-store moves."""
        sched = {c: {dd for dd, seq in self.days_orig.items() if c in seq}
                 for c in self.k_c}
        day_members = {dd: set(seq) for dd, seq in self.days_orig.items()}

        def nn2(c, members):
            rest = sorted(members - {c})
            if not rest:
                return None, None
            if len(rest) == 1:
                return rest[0], None
            ordered = sorted(rest, key=lambda j: (float(self.D[c][j]), j))
            return ordered[0], ordered[1]

        def removal_gain(dd, c):
            x, y = nn2(c, day_members[dd])
            if x is None:
                return -1e9
            if y is None:
                return float(self.D[c][x])
            return float(self.D[c][x]) + float(self.D[c][y]) - float(self.D[x][y])

        def insertion_cost(dd, c):
            members = day_members[dd]
            if not members:
                return None
            x, _ = nn2(c, members)
            y, _ = nn2(x, members)
            if y is None:
                return float(self.D[c][x])
            return float(self.D[c][x]) + float(self.D[c][y]) - float(self.D[x][y])

        def day_km_est(members):
            if len(members) <= 1:
                return 0.0
            rest = sorted(members)
            route = [rest[0]]
            unused = set(rest[1:])
            while unused:
                cur = route[-1]
                nxt = min(unused, key=lambda j: (float(self.D[cur][j]), j))
                route.append(nxt)
                unused.remove(nxt)
            for _ in range(30):
                improved = False
                for i in range(1, len(route) - 1):
                    for j in range(i + 1, len(route)):
                        old = float(self.D[route[i - 1]][route[i]])
                        if j + 1 < len(route):
                            old += float(self.D[route[j]][route[j + 1]])
                        new = float(self.D[route[i - 1]][route[j]])
                        if j + 1 < len(route):
                            new += float(self.D[route[i]][route[j + 1]])
                        if new < old - 1e-12:
                            route[i:j + 1] = reversed(route[i:j + 1])
                            improved = True
                if not improved:
                    break
            return sum(float(self.D[route[i]][route[i + 1]])
                       for i in range(len(route) - 1))

        cur_km = sum(day_km_est(day_members[dd]) for dd in self.dates)
        best_km = cur_km
        best_days = {dd: sorted(day_members[dd]) for dd in self.dates}
        stores = sorted(sched)
        accepted = 0
        for its in range(max(0, int(iterations))):
            c = rng.choice(stores)
            old_dates = sorted(sched[c], key=str)
            best_move = None
            kappa, phi = self.contracts[c]
            for slots in self.wd_groups.values():
                new_dates = sorted(contract_slot_dates(kappa, phi, slots), key=str)
                if not new_dates or len(new_dates) != len(old_dates):
                    continue
                if set(new_dates) == set(old_dates):
                    continue
                given = [dd for dd in old_dates if dd not in new_dates]
                shared = [dd for dd in new_dates if dd not in old_dates]
                if any(len(day_members[dd]) <= self.min_daily for dd in given):
                    continue
                if any(len(day_members[dd]) >= self.max_daily for dd in shared):
                    continue
                delta = sum(-removal_gain(dd, c) for dd in given)
                delta += sum(insertion_cost(dd, c) or 1e9 for dd in shared)
                if best_move is None or delta < best_move[0]:
                    best_move = (delta, given, shared)
            if best_move is None:
                continue
            delta, given, shared = best_move
            if delta >= -1e-9 and rng.random() >= 0.05:
                continue
            accepted += 1
            for dd in given:
                day_members[dd].remove(c)
                sched[c].remove(dd)
            for dd in shared:
                day_members[dd].add(c)
                sched[c].add(dd)
            if its % 50 == 0:
                cur_km = sum(day_km_est(day_members[dd]) for dd in self.dates)
            else:
                cur_km += delta
            if cur_km < best_km - 1e-9:
                best_km = cur_km
                best_days = {dd: sorted(day_members[dd]) for dd in self.dates}
        return best_days, accepted
    def _warm_start(self):
        """Seed original and randomized feasible columns before node CG.

        A single original column per date makes the root RMP integral and leaves
        no useful branching signal.  Feasible within-contract swaps preserve
        visit counts, legal dates, daily load, and R2' semantics while exposing
        alternative calendar columns.
        """
        import random
        rng = random.Random(42)
        original = {dd: _nn2opt_open(list(seq), self.D)
                    for dd, seq in self.days_orig.items()}
        original_km = sum(day_km(route, self.D) for route in original.values())
        self.incumbent = (original_km, original)
        self.warm_start_schedule_count = 0
        self.warm_start_columns = 0
        self.calendar_search_iterations = 0
        self.calendar_search_accepted = 0

        for dd, route in original.items():
            self.warm_start_columns += self.add_columns(
                [(dd, route, day_km(route, self.D))])

        if self.initial_days is not None:
            if set(self.initial_days) != set(self.dates):
                raise ValueError("initial_days must contain every B&P date")
            seed_days = {dd: list(self.initial_days[dd]) for dd in self.dates}
            violations = check_contract(seed_days, self.contracts, self.dates)
            if violations or not check_capacity(seed_days, self.max_daily, self.min_daily):
                raise ValueError("initial_days must satisfy contract and capacity gates")
            seed_km = sum(day_km(route, self.D) for route in seed_days.values())
            self.warm_start_schedule_count += 1
            self.warm_start_columns += self.add_columns(
                [(dd, route, day_km(route, self.D))
                 for dd, route in seed_days.items()])
            if seed_km < self.incumbent[0] - 1e-6:
                self.incumbent = (seed_km, seed_days)

        self.warm_start_columns += self.add_columns(self.initial_pool)

        if self.initial_days is None and not self.initial_pool:
            calendar_iterations = max(300, min(3000, int(self.time_budget * 50)))
            calendar_days, calendar_accepted = self._calendar_search(
                rng, calendar_iterations)
            calendar_routes = {dd: _nn2opt_open(list(seq), self.D)
                               for dd, seq in calendar_days.items()}
            calendar_km = sum(day_km(route, self.D) for route in calendar_routes.values())
            self.calendar_search_iterations = calendar_iterations
            self.calendar_search_accepted = calendar_accepted
            self.warm_start_schedule_count += 1
            self.warm_start_columns += self.add_columns(
                [(dd, route, day_km(route, self.D))
                 for dd, route in calendar_routes.items()])
            if calendar_km < self.incumbent[0] - 1e-6:
                self.incumbent = (calendar_km, calendar_routes)

            swap_budget = max(20, len(self.k_c) // 2)
            for _round in range(8):
                schedule = self._randomized_schedule(rng, swaps=swap_budget)
                routes = {dd: _nn2opt_open(list(seq), self.D)
                          for dd, seq in schedule.items()}
                km_total = sum(day_km(route, self.D) for route in routes.values())
                self.warm_start_schedule_count += 1
                self.warm_start_columns += self.add_columns(
                    [(dd, route, day_km(route, self.D))
                     for dd, route in routes.items()])
                if km_total < self.incumbent[0] - 1e-6:
                    self.incumbent = (km_total, routes)

        # Pseudo-dual perturbations add route-level diversity that swaps may miss.
        # v2 链接对偶语义: 扰动撒在 (店,日期) 链接对偶 β 上 (合法域内).
        for _round in range(2):
            pert = {(c, dd): rng.uniform(0.5, 2.0)
                    for c in self.k_c for dd in self.dates
                    if dd in self.legal.get(c, ()) and rng.random() < 0.3}
            duals = {"date": {dd: 0.0 for dd in self.dates}, "link": pert}
            cols = self._price_heuristic(_BPNode(), duals)
            by_date = {}
            for r in cols:
                by_date.setdefault(r[0], []).append(r)
            for dd, lst in by_date.items():
                self.warm_start_columns += self.add_columns(lst[:2])
        self.initial_pool_count = len(self.pool)

    # ---------------- 节点 LP (GLOP, v2 链接形态, 对偶语义同 formulation.sp_solve_lp_v2) ----------------
    def _solve_node_lp(self, node: _BPNode):
        """v2 链接形态节点 LP: 固定 (店,日期) 行空间; forced/forbidden 由 y 界承担."""
        from ortools.linear_solver import pywraplp
        pool = self._node_pool(node)
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:
            return None
        x = {i: solver.NumVar(0, 1, f"x{i}") for i in range(len(pool))}
        y = {}
        for c in self.k_c:
            for dd in self.dates:
                lb, ub = 0, 1
                if dd not in self.legal.get(c, ()):
                    ub = 0                      # 合同非法日期: 合法域内生化
                if (c, dd) in node.forced:
                    lb, ub = 1, 1               # 分支 forced → y 界
                elif (c, dd) in node.forbidden:
                    ub = 0                      # 分支 forbidden → y 界
                y[(c, dd)] = solver.NumVar(lb, ub, f"y_{c}_{dd}")
        z = {c: {w: solver.NumVar(0, 1, f"z_{c}_{w}")
                 for w in self.w_plus[c]} for c in self.k_c}
        cons_date = {}
        for dd in self.dates:
            cols = [i for i, (d2, _, _) in enumerate(pool) if d2 == dd]
            if not cols:
                return None                      # 该日期零候选列 (受限池) — 启发式剪枝
            cons_date[dd] = solver.Add(sum(x[i] for i in cols) == 1)
        cons_link = {}
        members = {}
        for i, (dd, route, _) in enumerate(pool):
            for c in set(route):
                members.setdefault((c, dd), []).append(i)
        for c in self.k_c:
            for dd in self.dates:
                cons_link[(c, dd)] = solver.Add(
                    y[(c, dd)] - sum(x[i] for i in members.get((c, dd), [])) == 0)
        for c in self.k_c:
            for dd in self.dates:
                w = _wd(dd)
                if w in z[c]:
                    solver.Add(y[(c, dd)] <= z[c][w])
            solver.Add(sum(y[(c, dd)] for dd in self.dates)
                       == sum(self.fw[c][w] * z[c][w] for w in self.w_plus[c]))
            solver.Add(sum(z[c].values()) == 1)
        solver.Minimize(sum(pool[i][2] * x[i] for i in x))
        solver.SetTimeLimit(30_000)
        st = solver.Solve()
        if st != pywraplp.Solver.OPTIMAL:
            self.lp_nonoptimal_nodes += 1
        if st not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            return None
        duals = {"date": {dd: cons_date[dd].DualValue() for dd in self.dates},
                 "link": {k: cons_link[k].DualValue() for k in cons_link}}
        return {"obj": solver.Objective().Value(),
                "x": {i: x[i].SolutionValue() for i in x},
                "pool": pool, "duals": duals}

    # ---------------- 定价: 启发式 ----------------
    def _price_heuristic(self, node: _BPNode, duals):
        link_dual, wd_dual = duals["link"], duals["date"]
        forced_by_date = {}
        for (c, dd) in node.forced:
            forced_by_date.setdefault(dd, []).append(c)
        out = []                                  # (rc, dd, route, km)
        for dd in self.dates:
            u = {c: -link_dual.get((c, dd), 0.0) for c in self.k_c}
            order = [c for c in self.k_c
                     if dd in self.legal.get(c, ()) and (c, dd) not in node.forbidden]
            order.sort(key=lambda c: -u[c])
            forced_set = set(forced_by_date.get(dd, ()))
            # 候选与起点都截断 top_m (对齐 price_columns 复杂度; forced 恒入候选)
            cand = [c for c in order if c in forced_set]
            pos = [c for c in order if c not in forced_set and u[c] > _EPS][:self.top_m]
            if not pos:                            # 冷启动对偶退化 (μ≈0): 零对偶起点
                pos = [c for c in order if c not in forced_set][:max(2, self.min_daily)]
            cand += [c for c in pos if c not in cand]
            if len(cand) < max(2, self.min_daily): # 走廊下限兜底扩容
                cand += [c for c in order if c not in cand][:max(2, self.min_daily) - len(cand)]
            starts = list(forced_by_date.get(dd, ())) + pos
            wdd = wd_dual.get(dd, 0.0)
            for start_c in starts:
                if start_c not in forced_set and u[start_c] <= _EPS:
                    break                         # starts 尾部按 u 降序, 可安全截断
                route = [start_c]
                in_day = {start_c}
                while len(route) < self.max_daily:
                    best_c, best_margin, best_pos = None, _EPS, None
                    for c in cand:
                        if c in in_day:
                            continue
                        uc = u[c]
                        if uc <= best_margin:
                            break
                        bd, bp = self.D[c][route[0]], 0
                        for k in range(len(route) - 1):
                            dlt = (self.D[route[k]][c] + self.D[c][route[k + 1]]
                                   - self.D[route[k]][route[k + 1]])
                            if dlt < bd:
                                bd, bp = dlt, k + 1
                        d_last = self.D[route[-1]][c]
                        if d_last < bd:
                            bd, bp = d_last, len(route)
                        margin = uc - bd
                        if margin > best_margin:
                            best_c, best_margin, best_pos = c, margin, bp
                    if best_c is None:
                        break
                    route.insert(best_pos, best_c)
                    in_day.add(best_c)
                if len(route) < max(2, self.min_daily):
                    continue
                km_exact = day_km(route, self.D)
                rc = km_exact - sum(u[c] for c in route) - wdd
                if rc < -1e-6:
                    out.append((rc, dd, list(route), km_exact))
        out.sort(key=lambda t: t[0])
        if not out:
            # GRASP 阶段 (v0.4): 贪心插入在强对偶下失效 (line 09 实测 priced=0),
            # 随机化贪心 + 2-opt 可发现 rc −75 级负列 (0.1s 首列).
            out = self._price_grasp(node, duals)
        out.sort(key=lambda t: t[0])
        return [(dd, route, km) for _rc, dd, route, km in out[:60]]

    def _price_grasp(self, node: _BPNode, duals, iters_per_date=60,
                     k_greedy=8, seed=1234):
        """GRASP 定价: 随机化贪心构造 + 2-opt 改进 (确定性: 按 date 索引播种)."""
        import random
        link_dual, wd_dual = duals["link"], duals["date"]
        forced_by_date = {}
        for (c, dd) in node.forced:
            forced_by_date.setdefault(dd, []).append(c)
        out = []
        for di, dd in enumerate(self.dates):
            if time.perf_counter() - self.t0 > self.time_budget:
                break
            wdd = wd_dual.get(dd, 0.0)
            u = {c: -link_dual.get((c, dd), 0.0) for c in self.k_c}
            order = [c for c in self.k_c
                     if dd in self.legal.get(c, ()) and (c, dd) not in node.forbidden]
            if len(order) < max(2, self.min_daily):
                continue
            forced_set = set(forced_by_date.get(dd, ()))
            rng = random.Random(seed + di)
            best_rc, best_route = 0.0, None
            for _it in range(iters_per_date):
                start = rng.choice(order)
                route = [start]
                in_day = {start}
                while len(route) < self.max_daily:
                    cands = []
                    for c in order:
                        if c in in_day:
                            continue
                        bd, bpos = self.D[c][route[0]], 0
                        for k in range(len(route) - 1):
                            dlt = (self.D[route[k]][c] + self.D[c][route[k + 1]]
                                   - self.D[route[k]][route[k + 1]])
                            if dlt < bd:
                                bd, bpos = dlt, k + 1
                        if self.D[route[-1]][c] < bd:
                            bd, bpos = self.D[route[-1]][c], len(route)
                        cands.append((u[c] - bd, c, bpos))
                    if not cands:
                        break
                    cands.sort(reverse=True)
                    pool = [t for t in cands[:k_greedy] if t[0] > 0] or cands[:1]
                    _m, c, bpos = rng.choice(pool)
                    route.insert(bpos, c)
                    in_day.add(c)
                if len(route) < max(2, self.min_daily):
                    continue
                route = self._two_opt_open(route)
                km = day_km(route, self.D)
                rc = km - sum(u[c] for c in route) - wdd
                if rc < best_rc:
                    best_rc, best_route = rc, list(route)
                if best_rc < -1e-6:
                    break   # CG 只需负列回灌, 首列即止 (实验: 首列 ~0.1s)
                    in_day.add(c)
                if len(route) < max(2, self.min_daily):
                    continue
                if any(c in forced_set for c in route) or not forced_set:
                    pass
                route = self._two_opt_open(route)
                km = day_km(route, self.D)
                rc = km - sum(u[c] for c in route) - wdd
                if rc < best_rc:
                    best_rc, best_route = rc, list(route)
            if best_route is not None and best_rc < -1e-6:
                if not forced_set or any(c in forced_set for c in best_route):
                    out.append((best_rc, dd, best_route, day_km(best_route, self.D)))
        return out

    def _two_opt_open(self, route):
        """开放路径 2-opt (距离下降, 不改店集)."""
        route = list(route)
        improved = True
        while improved:
            improved = False
            for i in range(len(route) - 1):
                for j in range(i + 1, len(route)):
                    new = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                    if day_km(new, self.D) < day_km(route, self.D) - 1e-9:
                        route = new
                        improved = True
        return route

    # ---------------- 定价: CP-SAT 精确兜底 ----------------
    def _price_exact(self, node: _BPNode, duals):
        from ortools.sat.python import cp_model
        link_dual, wd_dual = duals["link"], duals["date"]
        forced_by_date = {}
        for (c, dd) in node.forced:
            forced_by_date.setdefault(dd, []).append(c)
        self.exact_pricing_calls += 1
        self._exact_all_proven = True
        out = []
        for dd in self.dates:
            if time.perf_counter() - self.t0 > self.time_budget:
                self._exact_all_proven = False    # 预算内未证完 → 诚实降级
                break
            wdd = wd_dual.get(dd, 0.0)
            u = {c: -link_dual.get((c, dd), 0.0) for c in self.k_c}
            eligible = [c for c in self.k_c
                        if dd in self.legal.get(c, ()) and (c, dd) not in node.forbidden]
            eligible.sort(key=lambda c: -u[c])
            # 完整候选集用于证明“无负列”；截断只能用于启发式定价。
            must = [c for c in forced_by_date.get(dd, ()) if c in eligible]
            if len(eligible) < max(2, self.min_daily):
                continue
            n, dummy = len(eligible), len(eligible)
            m = cp_model.CpModel()
            visit = [m.NewBoolVar(f"v{i}") for i in range(n)]
            arcs = [(i, i, m.NewBoolVar(f"s{i}")) for i in range(n)]        # 自环 = 跳过
            for i in range(n):
                for j in range(n):
                    if i != j:
                        arcs.append((i, j, m.NewBoolVar(f"a{i}_{j}")))
            for i in range(n):
                arcs.append((i, dummy, m.NewBoolVar(f"d{i}")))
                arcs.append((dummy, i, m.NewBoolVar(f"e{i}")))
            m.AddCircuit(arcs)
            for i in range(n):
                self_loop = next(v for (a, b, v) in arcs if a == i and b == i)
                m.Add(visit[i] + self_loop == 1)
            m.Add(sum(visit) >= max(2, self.min_daily))
            m.Add(sum(visit) <= self.max_daily)
            for c in must:
                m.Add(visit[eligible.index(c)] == 1)
            obj = sum(float(self.D[eligible[i]][eligible[j]]) * v
                      for (i, j, v) in arcs if i < n and j < n)
            obj -= sum(float(u[eligible[i]]) * visit[i] for i in range(n))
            obj -= wdd
            m.Minimize(obj)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = self.exact_tl
            solver.parameters.num_search_workers = 2
            st = solver.Solve(m)
            if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                self._exact_all_proven = False
                continue
            if st != cp_model.OPTIMAL:
                self._exact_all_proven = False
            if solver.ObjectiveValue() >= -1e-6:
                continue
            succ = {}
            for (i, j, v) in arcs:
                if i != j and solver.Value(v):
                    succ[i] = j
            route, cur = [], succ[dummy]
            while cur != dummy:
                route.append(eligible[cur])
                cur = succ[cur]
            if len(route) >= max(2, self.min_daily):
                out.append((dd, route, day_km(route, self.D)))
        return out

    # ---------------- 分支候选 ----------------
    def _branch_key(self, lp):
        y = {}
        for i, (dd, route, _) in enumerate(lp["pool"]):
            xv = lp["x"][i]
            if xv <= _FRAC:
                continue
            for c in set(route):
                y[(c, dd)] = y.get((c, dd), 0.0) + xv
        frac = [(abs(v - 0.5), k) for k, v in y.items() if _FRAC < v < 1 - _FRAC]
        if not frac:
            return None
        frac.sort()
        return frac[0][1]                          # (c, dd)

    # ---------------- 节点 CG ----------------
    # ---------------- 可行性恢复定价 (rc 可为正 — 对偶定价只产负 rc 列) ----------------
    def _gen_greedy_column(self, node: _BPNode, c0, dd):
        """从 c0 出发的距离贪心列 (不依赖对偶), 供 forced/未覆盖店恢复可行性."""
        route = [c0]
        in_day = {c0}
        while len(route) < self.max_daily:
            best_c, best_ins, best_pos = None, None, None
            for c in self.k_c:
                if c in in_day or dd not in self.legal.get(c, ()) \
                        or (c, dd) in node.forbidden:
                    continue
                bd, bp = self.D[c][route[0]], 0
                for k in range(len(route) - 1):
                    dlt = (self.D[route[k]][c] + self.D[c][route[k + 1]]
                           - self.D[route[k]][route[k + 1]])
                    if dlt < bd:
                        bd, bp = dlt, k + 1
                d_last = self.D[route[-1]][c]
                if d_last < bd:
                    bd, bp = d_last, len(route)
                if best_ins is None or bd < best_ins:
                    best_c, best_ins, best_pos = c, bd, bp
            if best_c is None:
                break
            route.insert(best_pos, best_c)
            in_day.add(best_c)
        if len(route) < max(2, self.min_daily):
            return None
        return (dd, route, day_km(route, self.D))

    def _restore_feasibility(self, node: _BPNode):
        """受限池缺 forced 列或缺店覆盖时补列. 返回是否新增."""
        pool = self._node_pool(node)
        have = {(dd, c) for dd, route, _ in pool for c in route}
        covered = {c for _, route, _ in pool for c in route}
        cols = []
        for (c, dd) in node.forced:
            if (dd, c) not in have:
                col = self._gen_greedy_column(node, c, dd)
                if col:
                    cols.append(col)
        for c in self.k_c:
            if c in covered:
                continue
            for dd in self.dates:
                if dd in self.legal.get(c, ()) and (c, dd) not in node.forbidden:
                    col = self._gen_greedy_column(node, c, dd)
                    if col:
                        cols.append(col)
                        break
        return self.add_columns(cols) > 0

    # ---------------- 节点 CG ----------------
    def _solve_node_cg(self, node: _BPNode, max_iters=15):
        self._exact_all_proven = False
        for _it in range(max_iters):
            self.cg_iters_total += 1
            lp = self._solve_node_lp(node)
            if lp is None:
                if self._restore_feasibility(node):
                    continue          # 可行性列已补, 重解 LP (耗一次迭代)
                self.lp_infeasible_prunes += 1
                self.cg_nonconverged_nodes += 1
                return None
            cols = self._price_heuristic(node, lp["duals"])
            col_source = "HEURISTIC"
            if not cols and self.exact_pricing and \
                    time.perf_counter() - self.t0 < self.time_budget:
                cols = self._price_exact(node, lp["duals"])
                col_source = "EXACT"
            if not cols:
                self.converge_attempts += 1
                if self._exact_all_proven:
                    self.converge_proven += 1
                    lp["pricing_proven"] = True   # 完整精确定价证明无负 rc 列 → 子树有效下界
                    lp["cg_termination"] = CGTerminationStatus.EXACT_NO_NEGATIVE_RC
                    lp["pricing_certificate"] = PricingCertificate(False, ProofLevel.EXACT)
                else:
                    # relaxed 无候选 ≠ 证明 (CG 终止契约 v0.4)
                    lp["cg_termination"] = CGTerminationStatus.RELAXED_NO_CANDIDATE
                    lp["pricing_certificate"] = PricingCertificate(False, ProofLevel.RELAXED)
                return lp                          # 未证明时 lp 无 pricing_proven: 值仅作观测, 不可剪枝
            if self.add_columns(cols, source=col_source) == 0:
                self.pricing_stalled += 1
                lp["cg_termination"] = CGTerminationStatus.RELAXED_ONLY_INVALID
                lp["pricing_certificate"] = PricingCertificate(True, ProofLevel.HEURISTIC)
                return lp
        lp["cg_termination"] = CGTerminationStatus.TIMEOUT_UNKNOWN
        lp["pricing_certificate"] = PricingCertificate(True, ProofLevel.UNKNOWN)
        return None                                # 迭代上限未收敛: 丢弃节点 (不计界)

    # ---------------- incumbent 抽取与 LP 下潜 ----------------
    def _extract_incumbent(self, lp):
        """逐日 argmax 抽取 (免 GLOP 容差); 全日期覆盖才成 incumbent."""
        best_per_date = {}
        for i, (dd, route, _km) in enumerate(lp["pool"]):
            xv = lp["x"][i]
            if xv <= _FRAC:
                continue
            if dd not in best_per_date or xv > best_per_date[dd][0]:
                best_per_date[dd] = (xv, route)
        if len(best_per_date) != len(self.dates):
            return False
        days = {dd: list(r) for dd, (_xv, r) in best_per_date.items()}
        km_total = sum(day_km(days[dd], self.D) for dd in self.dates)
        if self.incumbent is None or km_total < self.incumbent[0] - 1e-6:
            self.incumbent = (km_total, days)
        return True

    def _dive(self, node, lp):
        """LP 下潜: 逐轮把各日 argmax 列变为 forced, 快速制造可行 incumbent."""
        fix = set(node.forced)
        cur = lp
        for _round in range(2 * len(self.dates)):
            if self._branch_key(cur) is None:   # 仅 y 全整 (LP 整分) 时抽取才合同可行
                self._extract_incumbent(cur)
                return
            pick = {}
            for i, (dd, route, _km) in enumerate(cur["pool"]):
                xv = cur["x"][i]
                if xv <= _FRAC:
                    continue
                if dd not in pick or xv > pick[dd][0]:
                    pick[dd] = (xv, route)
            new_fix = set(fix)
            for dd, (_xv, route) in pick.items():
                for c in route:
                    new_fix.add((c, dd))
            if len(new_fix) == len(fix):
                return
            fix = new_fix
            cur = self._solve_node_cg(_BPNode(node.forbidden, fix), max_iters=8)
            if cur is None:
                return

    def _tree_status(self):
        """Sign a global proof only after all node certificates are complete."""
        if time.perf_counter() - self.t0 > self.time_budget:
            return "TIME_LIMIT"
        if (
            self.exact_pricing_calls > 0
            and self.converge_attempts > 0
            and self.converge_attempts == self.converge_proven
            and self.lp_nonoptimal_nodes == 0
            and self.cg_nonconverged_nodes == 0
            and self.pricing_stalled == 0
        ):
            return "PROVEN_OPTIMAL"
        return "BOUND_HEURISTIC"

    # ---------------- 主循环: DFS 分支树 ----------------
    def solve(self):
        stack = [_BPNode()]
        status = None                      # 结束时按证明账定性
        while stack:
            if time.perf_counter() - self.t0 > self.time_budget or \
                    self.nodes_explored >= self.max_nodes:
                status = "TIME_LIMIT"
                break
            node = stack.pop()
            lp = self._solve_node_cg(node, max_iters=self.cg_max_iters)
            if lp is None:
                continue
            proven = lp.get("pricing_proven", False)
            if self.root_lb is None:
                if proven:
                    self.root_lb = lp["obj"]     # 仅精确定价证明后的 LP 值才可作下界记录
            if self.incumbent is not None and proven and \
                    lp["obj"] >= self.incumbent[0] - 1e-6:
                continue                            # 界剪枝: 仅精确定价证明后的下界可安全剪
            key = self._branch_key(lp)
            if key is None:                         # y 全整 ⇒ x 全整 → incumbent
                self._extract_incumbent(lp)
                continue
            if self.incumbent is None:              # 尚无 incumbent: 下潜制造
                self._dive(node, lp)
                if self.incumbent is not None and proven and \
                        lp["obj"] >= self.incumbent[0] - 1e-6:
                    continue                        # 下潜后本子树已无改进空间
            self.nodes_explored += 1
            c, dd = key
            for child in (node.child_forbidden(c, dd), node.child_forced(c, dd)):
                if self._propagate_feasible(child):
                    stack.append(child)
                else:
                    self.propagate_prunes += 1
        if status is None:                 # 搜索树耗尽 = 未超时
            status = self._tree_status()
        return {
            "status": status,
            "incumbent_km": round(self.incumbent[0], 3) if self.incumbent else None,
            "incumbent_days": self.incumbent[1] if self.incumbent else None,
            "root_lb": self.root_lb,
            "nodes": self.nodes_explored,
            "cg_iters": self.cg_iters_total,
            "pool": list(self.pool),
            "exact_pricing_calls": self.exact_pricing_calls,
            "lp_infeasible_prunes": self.lp_infeasible_prunes,
            "propagate_prunes": self.propagate_prunes,
            "converge_attempts": self.converge_attempts,
            "converge_proven": self.converge_proven,
            "lp_nonoptimal_nodes": self.lp_nonoptimal_nodes,
            "cg_nonconverged_nodes": self.cg_nonconverged_nodes,
            "pricing_stalled": self.pricing_stalled,
            "warm_start_schedule_count": self.warm_start_schedule_count,
            "warm_start_columns": self.warm_start_columns,
            "calendar_search_iterations": self.calendar_search_iterations,
            "calendar_search_accepted": self.calendar_search_accepted,
            "initial_pool_count": self.initial_pool_count,
            "elapsed": time.perf_counter() - self.t0,
        }

    # ---------------- 分支传播预剪枝 ----------------
    def _propagate_feasible(self, node: _BPNode) -> bool:
        """子节点可行性传播: 不动用 CG 即可判死的分支不进栈.

        - forced 店必须单星期几且不超过该店最大合同频次;
        - forbidden 后每店仍须存在某个 f>0 星期几, 其剩余合法日期 ≥ f."""
        from collections import Counter
        fcnt = Counter(c for (c, _dd) in node.forced)
        ws_by_c = {}
        for (c, dd) in node.forced:
            ws_by_c.setdefault(c, set()).add(_wd(dd))
        for c, k in fcnt.items():
            if len(ws_by_c[c]) > 1 or k > max(self.fw[c].values()):
                return False
        for c in self.k_c:
            avail = [dd for dd in self.legal.get(c, ())
                     if (c, dd) not in node.forbidden and (c, dd) not in node.forced]
            ok = any(sum(1 for dd in avail if _wd(dd) == w) + fcnt.get(c, 0) >= f
                     for w, f in self.fw[c].items() if f > 0)
            if not ok:
                return False
        return True


@register
class BranchAndPriceAlg(Algorithm):
    """Branch-and-Price (合同原生; 树内插入序代价, raw 口径记 metadata)."""
    name = "branch_and_price"

    def solve(self, data, D, time_budget=60, seed=42, max_nodes=200,
              exact_pricing=True, exact_tl=1.0, initial_days=None, initial_pool=None):
        import numpy as np
        D = np.asarray(D)
        dates = list(data.dates)
        contracts = contract_of(data.days_orig, dates)
        k_c = dict(Counter(c for dd in dates for c in data.days_orig[dd]))
        min_daily = getattr(data, "min_daily_capacity", 0) or min(len(v) for v in data.days_orig.values())
        max_daily = getattr(data, "max_daily_capacity", 0) or max(len(v) for v in data.days_orig.values())
        engine = BranchAndPrice(dates, k_c, D, contracts, data.days_orig,
                                min_daily, max_daily,
                                time_budget=time_budget, max_nodes=max_nodes,
                                exact_pricing=exact_pricing, exact_tl=exact_tl,
                                initial_days=initial_days, initial_pool=initial_pool)
        res = engine.solve()
        meta = {"status": res["status"], "nodes": res["nodes"],
                "cg_iters": res["cg_iters"], "root_lb": res["root_lb"],
                "exact_pricing_calls": res["exact_pricing_calls"],
                "lp_infeasible_prunes": res["lp_infeasible_prunes"],
                "propagate_prunes": res["propagate_prunes"],
                "converge_attempts": res["converge_attempts"],
                "converge_proven": res["converge_proven"],
                "lp_nonoptimal_nodes": res["lp_nonoptimal_nodes"],
                "cg_nonconverged_nodes": res["cg_nonconverged_nodes"],
                "pricing_stalled": res["pricing_stalled"],
                "warm_start_schedule_count": res["warm_start_schedule_count"],
                "warm_start_columns": res["warm_start_columns"],
                "calendar_search_iterations": res["calendar_search_iterations"],
                "calendar_search_accepted": res["calendar_search_accepted"],
                "initial_pool_count": res["initial_pool_count"],
                "min_daily": min_daily, "max_daily": max_daily}
        if res["incumbent_days"]:
            days = res["incumbent_days"]
            viol = check_contract(days, contracts, dates)
            return AlgoResult(name=self.name, days=days, km=res["incumbent_km"],
                              capacity_ok=check_capacity(days, max_daily, min_daily),
                              contract_ok=not viol, metadata=meta)
        meta["error"] = "no incumbent within budget"
        return AlgoResult(name=self.name, days={}, km=float("inf"), capacity_ok=False,
                          metadata=meta)


__all__ = ["BranchAndPrice", "BranchAndPriceAlg"]
