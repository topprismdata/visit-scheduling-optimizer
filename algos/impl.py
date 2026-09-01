# -*- coding: utf-8 -*-
"""Algorithms: baseline, nn2opt, greedy_crossday, cpsat_route, alns, ensemble_sp.
All address (data, D, time_budget) -> AlgoResult."""
import time, random, math
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_freq
from algos.registry import register
from algos.tsp_engine import _nn2opt_open, _exact_open_tsp
from core.route_pool import RoutePool, Route


@register
class Baseline(Algorithm):
    name = "baseline"
    def solve(self, data, D, time_budget=60):
        days = {dd: list(seq) for dd, seq in data.days_orig.items()}
        return AlgoResult(name=self.name, days=days, km=total_km(days, D))


@register
class NN2Opt(Algorithm):
    name = "nn2opt"
    def solve(self, data, D, time_budget=60):
        days = {dd: _nn2opt_open(seq, D) for dd, seq in data.days_orig.items()}
        return AlgoResult(name=self.name, days=days, km=total_km(days, D))


@register
class GreedyCrossDay(Algorithm):
    name = "greedy_crossday"
    def solve(self, data, D, time_budget=180):
        days = {dd: _nn2opt_open(seq, D) for dd, seq in data.days_orig.items()}
        dates = data.dates; moves = 0; start = time.time(); tl = time_budget
        for _ in range(50):
            improved = False
            for dd1 in dates:
                for dd2 in dates:
                    if dd1 == dd2: continue
                    s1, s2 = days[dd1], days[dd2]
                    if len(s1) <= 5: continue
                    for c in list(s1):
                        if c in s2: continue
                        ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                        if len(ns1) < 2: continue
                        old = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
                        new = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
                        if new < old - 0.05:
                            days[dd1] = ns1; days[dd2] = ns2; moves += 1; improved = True
                    if time.time() - start > tl: break
                if time.time() - start > tl: break
            if not improved or time.time() - start > tl: break
        final = {dd: _nn2opt_open(seq, D) for dd, seq in days.items()}
        return AlgoResult(name=self.name, days=final, km=total_km(final, D), moves=moves)




@register
class LKHRoute(Algorithm):
    """① LKH 精确开放 TSP (ATSP 矩阵, 大常数 dummy depot)."""
    name = "lkh_route"
    def solve(self, data, D, time_budget=300):
        from algos.lkh_engine import lkh_open_path
        tl = max(30, time_budget // max(len(data.dates), 1))
        days = {}
        for dd in data.dates:
            seq = data.days_orig[dd]
            if len(seq) <= 4:
                days[dd] = list(seq)
            else:
                r = lkh_open_path(seq, D, runs=10, max_trials=5000, cand=20, time_limit=tl)
                days[dd] = r
        return AlgoResult(name=self.name, days=days, km=total_km(days, D))

@register
class CpsatRoute(Algorithm):
    name = "cpsat_route"
    def solve(self, data, D, time_budget=300):
        tl = max(30, time_budget // max(len(data.dates), 1))
        days = {dd: _exact_open_tsp(seq, D, tl) for dd, seq in data.days_orig.items()}
        return AlgoResult(name=self.name, days=days, km=total_km(days, D))


@register
class ALNS(Algorithm):
    """ALNS: 算子池 (move/swap/ruin-repair) + 自适应权重 (菜鸟/美团模式).
    破坏: 随机移, 最差成本移, 聚簇移
    修复: 贪心插, 后悔插
    权重: 按算子历史表现动态调整 (多臂老虎机)
    """
    name = "alns"

    def solve(self, data, D, time_budget=600, seed=42):
        rng = random.Random(seed)
        dates = list(data.dates)
        n_days = len(dates)
        # 初始解 = greedy_crossday 全预算 (与 greedy_crossday 算法同起点)
        days = {dd: _nn2opt_open(seq, D) for dd, seq in data.days_orig.items()}
        start = time.time(); tl = time_budget
        greedy_start = time.time()
        for _ in range(50):
            improved = False
            for dd1 in dates:
                for dd2 in dates:
                    if dd1 == dd2: continue
                    s1, s2 = days[dd1], days[dd2]
                    if len(s1) <= 5: continue
                    for c in list(s1):
                        if c in s2: continue
                        ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                        if len(ns1) < 2: continue
                        old = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
                        new = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
                        if new < old - 0.05:
                            days[dd1] = ns1; days[dd2] = ns2; improved = True
                    if time.time() - greedy_start > tl * 0.5: break
                if time.time() - greedy_start > tl * 0.5: break
            if not improved or time.time() - greedy_start > tl * 0.5: break
        current = {dd: list(seq) for dd, seq in days.items()}
        best = {dd: list(seq) for dd, seq in days.items()}
        best_km = total_km(best, D)

        # 算子池权重
        op_names = ["move", "swap", "ruin_repair", "cluster_ruin"]
        weights = {o: 1.0 for o in op_names}
        scores = {o: 0.0 for o in op_names}
        score_count = {o: 0 for o in op_names}
        op_choice_count = 0
        UPDATE_EVERY = 50

        def pick_op():
            total = sum(weights.values())
            r = rng.random() * total
            for o in op_names:
                r -= weights[o]
                if r <= 0: return o
            return op_names[-1]

        def local_cost(dd):
            return day_km(_nn2opt_open(current[dd], D), D)

        its = 0
        while time.time() - start < tl and its < 20000:
            its += 1
            op = pick_op()
            dd1 = rng.choice(dates); dd2 = rng.choice(dates)
            if dd1 == dd2: continue
            s1, s2 = current[dd1], current[dd2]
            improved_now = False
            gain = 0.0
            if op == "move":
                if len(s1) <= 5: 
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                # 最差成本优先选择移动候选
                c = max(s1, key=lambda x: local_delta_out(current, dd1, x, D))
                if c in s2:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                if len(ns1) < 2: continue
                old = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
                new = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
                gain = old - new
                if gain > 0.01:
                    current[dd1] = ns1; current[dd2] = ns2; improved_now = True
            elif op == "swap":
                if len(s1) < 2 or len(s2) < 2:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                c1 = rng.choice(s1); c2 = rng.choice(s2)
                if c1 == c2 or c2 in s1 or c1 in s2: continue
                ns1 = [x for x in s1 if x != c1] + [c2]; ns2 = [x for x in s2 if x != c2] + [c1]
                old = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
                new = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
                gain = old - new
                if gain > 0.01:
                    current[dd1] = ns1; current[dd2] = ns2; improved_now = True
            elif op == "ruin_repair":  # 破坏一个日, 重建顺序
                if len(s1) <= 3:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                old = day_km(_nn2opt_open(s1, D), D)
                shuf = list(s1); rng.shuffle(shuf)
                newr = _nn2opt_open(shuf, D)
                new = day_km(newr, D)
                gain = old - new
                if gain > 0.01:
                    current[dd1] = newr; improved_now = True
            elif op == "cluster_ruin":  # 移除相邻店, 重新插入
                if len(s1) <= 4:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                # 找当日路径上相邻的2-4家店作为"簇"
                base = _nn2opt_open(s1, D)
                n_b = len(base)
                if n_b < 4:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                k = rng.randint(2, min(4, n_b // 2))
                st = rng.randint(0, n_b - k)
                cluster = set(base[st:st + k])
                rest = [x for x in base if x not in cluster]
                if len(rest) < 2:
                    scores[op] -= 0.01; score_count[op] += 1
                    continue
                old = day_km(base, D)
                best_r = None; best_gain = 0
                for _ in range(20):
                    shuf = list(cluster); rng.shuffle(shuf)
                    # 插入所有空隙
                    cand = list(rest)
                    pos = rng.randint(0, len(cand))
                    cand[pos:pos] = shuf
                    r2 = _nn2opt_open(cand, D)
                    g = old - day_km(r2, D)
                    if g > best_gain:
                        best_gain = g; best_r = r2
                if best_r is not None and best_gain > 0.01:
                    current[dd1] = best_r; improved_now = True
            # 权重更新
            if improved_now:
                scores[op] += min(gain, 2.0)
            else:
                scores[op] -= 0.05
            score_count[op] += 1
            op_choice_count += 1
            # 周期性更新权重 (自适应)
            if op_choice_count % UPDATE_EVERY == 0:
                for o in op_names:
                    if score_count[o] > 0:
                        weights[o] = 0.7 * weights[o] + 0.3 * max(scores[o] / score_count[o], 0.01)
                scores = {o: 0.0 for o in op_names}
                score_count = {o: 0 for o in op_names}
        final = {dd: _nn2opt_open(seq, D) for dd, seq in current.items()}
        final_km = total_km(final, D)
        best_km2 = total_km({dd: _nn2opt_open(seq, D) for dd, seq in best.items()}, D)
        if final_km < best_km2: best = final
        return AlgoResult(name=self.name, days=best, km=min(final_km, best_km2), moves=its)


def local_delta_out(current, dd, c, D):
    """计算移除 c 对当日路径的边际节省 (近似)."""
    seq = current[dd]
    if len(seq) < 2: return 0.0
    return day_km(seq, D) - day_km([x for x in seq if x != c], D)


@register
class EnsembleSP(Algorithm):
    """集合划分重组合: 消费路线池 (含其他算法产出), 选最优组合.
    若未给 pool, 则自己用多起点生成.
    """
    name = "ensemble_sp"

    def solve(self, data, D, time_budget=600, pool=None, multistart=5, warm_start=None):
        from ortools.sat.python import cp_model
        dates = data.dates; codes = data.codes

        if pool is None:
            pool = RoutePool()
            # 从计划 + 各生成器产路线
            for dd in dates:
                seeds = list(data.days_orig[dd])
                pool.add(Route(date=dd, stores=tuple(seeds), cost=day_km(seeds, D), algo="plan"))
                pool.add(Route(date=dd, stores=tuple(_nn2opt_open(seeds, D)), cost=day_km(_nn2opt_open(seeds, D), D), algo="nn2opt"))
                rng = random.Random(7)
                for _ in range(multistart):
                    shuf = list(seeds); rng.shuffle(shuf)
                    r = _nn2opt_open(shuf, D)
                    pool.add(Route(date=dd, stores=tuple(r), cost=day_km(r, D), algo="ms" + str(_)))
        # SP: 每天选1条, 每店覆盖 freq 次
        model = cp_model.CpModel()
        x = {}
        routes_by_date = {}
        for dd in dates:
            routes_by_date[dd] = pool.get_routes(dd)
        for dd in dates:
            for ri, r in enumerate(routes_by_date[dd]):
                x[(dd, ri)] = model.NewBoolVar(f'x_{dd}_{ri}')
        for dd in dates:
            model.Add(sum(x[(dd, ri)] for ri in range(len(routes_by_date[dd]))) == 1)
        store_incs = {si: [] for si in range(len(codes))}
        for dd in dates:
            for ri, r in enumerate(routes_by_date[dd]):
                for si in r.stores:
                    store_incs[si].append((dd, ri))
        for si in range(len(codes)):
            c = codes[si]
            freq = data.freq.get(c, 0)
            if freq:
                model.Add(sum(x[(dd, ri)] for (dd, ri) in store_incs[si]) == freq)
        model.Minimize(sum(r.cost * x[(dd, ri)] for dd in dates for ri, r in enumerate(routes_by_date[dd])))
        # Warm start: 用启发式解的店序匹配路线池, 命中则 AddHint
        if warm_start:
            for dd, seq in warm_start.items():
                key = tuple(seq)
                for ri, r in enumerate(routes_by_date[dd]):
                    if r.stores == key:
                        model.AddHint(x[(dd, ri)], 1)
                        break
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(60, time_budget // 2)
        solver.parameters.num_search_workers = 8
        st = solver.Solve(model)
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            days = {}
            for dd in dates:
                for ri, r in enumerate(routes_by_date[dd]):
                    if solver.Value(x[(dd, ri)]):
                        days[dd] = list(r.stores); break
            return AlgoResult(name=self.name, days=days, km=total_km(days, D),
                              metadata={"pool": pool.stats()})
        return AlgoResult(name=self.name, days={dd: list(seq) for dd, seq in data.days_orig.items()},
                          km=total_km(data.days_orig, D))
