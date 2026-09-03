# -*- coding: utf-8 -*-
"""V4 MO-ALNS — 多目标帕累托方案生成器 (NSGA-II + ALNS 混合).

定位: 独立的多目标求解器, 不是后处理器.
输入: 原始计划 + 路网矩阵 + 地理围栏
输出: 帕累托前沿上的一组非支配解, 自动命名 4 个代表方案.

四维目标:
  f1: 总里程 (km)          — 越小越好
  f2: 改动店数 (相对原始)   — 越小越好
  f3: 每日工作量变异系数 CV — 越小越好
  f4: 跨区边占比            — 越小越好

算法: NSGA-II 非支配排序 + 拥挤度 + ALNS destroy/repair 算子
"""
import time, math, random, copy
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_freq
from algos.registry import register
from algos.alns_v3 import two_opt, best_insert, worst_edge


def _dates_map(tours):
    m = {}
    for dd, seq in tours.items():
        for s in seq:
            m.setdefault(s, set()).add(dd)
    return m


def _cv(tours):
    counts = [len(seq) for seq in tours.values()]
    if not counts or sum(counts) == 0:
        return 0.0
    mean = sum(counts) / len(counts)
    if mean == 0:
        return 0.0
    var = sum((c - mean) ** 2 for c in counts) / len(counts)
    return math.sqrt(var) / mean


def _cross_ratio(tours, zone_of):
    total_edges = 0
    cross_edges = 0
    for dd, seq in tours.items():
        for k in range(len(seq) - 1):
            total_edges += 1
            if zone_of and zone_of.get(seq[k]) != zone_of.get(seq[k + 1]):
                cross_edges += 1
    return cross_edges / max(1, total_edges)


def dominates(a, b):
    """a dominates b if a is <= in all objectives and < in at least one."""
    better_any = False
    for i in range(4):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            better_any = True
    return better_any


def non_dominated_sort(pop):
    """Returns list of fronts (each front is list of indices)."""
    n = len(pop)
    S = [[] for _ in range(n)]
    rank = [0] * n
    fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates(pop[p]['obj'], pop[q]['obj']):
                S[p].append(q)
            elif dominates(pop[q]['obj'], pop[p]['obj']):
                rank[p] += 1
        if rank[p] == 0:
            fronts[0].append(p)
    i = 0
    while i < len(fronts):
        next_front = []
        for p in fronts[i]:
            for q in S[p]:
                rank[q] -= 1
                if rank[q] == 0:
                    next_front.append(q)
        i += 1
        if next_front:
            fronts.append(next_front)
    return fronts


def crowding_distance(pop, front):
    """Assign crowding distance to individuals in a front."""
    n = len(front)
    if n <= 2:
        return {i: float('inf') for i in front}
    dist = {i: 0.0 for i in front}
    for obj_idx in range(4):
        sorted_front = sorted(front, key=lambda i: pop[i]['obj'][obj_idx])
        dist[sorted_front[0]] = float('inf')
        dist[sorted_front[-1]] = float('inf')
        obj_range = pop[sorted_front[-1]]['obj'][obj_idx] - pop[sorted_front[0]]['obj'][obj_idx]
        if obj_range == 0:
            continue
        for k in range(1, n - 1):
            dist[sorted_front[k]] += (pop[sorted_front[k + 1]]['obj'][obj_idx] - pop[sorted_front[k - 1]]['obj'][obj_idx]) / obj_range
    return dist


@register
class MOALNSv4(Algorithm):
    name = "mo_alns_v4"

    def solve(self, data, D, time_budget=60, zone_of=None, seed=42,
              pop_size=30, num_presets=4):
        rng = random.Random(seed)
        dates = list(data.dates)
        t0 = time.time()
        deadline = t0 + time_budget

        # ===== 初始化种群 =====
        population = []

        def evaluate(tours):
            km = total_km(tours, D)
            dm = _dates_map(tours)
            inc_dm = _dates_map(data.days_orig)
            changed = sum(1 for s in set(list(dm.keys()) + list(inc_dm.keys()))
                          if dm.get(s, set()) != inc_dm.get(s, set()))
            cv = _cv(tours)
            cr = _cross_ratio(tours, zone_of)
            return [km, changed, cv, cr]

        def deep_copy_tours(t):
            return {dd: list(seq) for dd, seq in t.items()}

        # 1. 原始计划
        pop_orig = deep_copy_tours(data.days_orig)
        population.append({'tours': pop_orig, 'obj': evaluate(pop_orig)})

        # 2. TSP 重排
        pop_tsp = {dd: two_opt(list(data.days_orig.get(dd, [])), D, 20) for dd in dates}
        population.append({'tours': pop_tsp, 'obj': evaluate(pop_tsp)})

        # 3. 随机扰动解
        for _ in range(min(5, pop_size // 6)):
            t = deep_copy_tours(data.days_orig)
            dds = list(dates)
            for _ in range(rng.randint(3, 10)):
                d1, d2 = rng.sample(dds, 2)
                if len(t.get(d1, [])) > 3 and t.get(d2) is not None:
                    c = rng.choice(t[d1])
                    t[d1].remove(c)
                    if len(t[d1]) >= 2:
                        t[d1] = two_opt(t[d1], D, 6)
                    t[d2].append(c)
                    t[d2] = two_opt(t[d2], D, 6)
            population.append({'tours': t, 'obj': evaluate(t)})

        # 4. 2-opt 变异解
        for _ in range(min(5, pop_size // 6)):
            t = deep_copy_tours(data.days_orig)
            dd = rng.choice(dates)
            if len(t.get(dd, [])) > 3:
                t[dd] = two_opt(t[dd], D, 15)
            population.append({'tours': t, 'obj': evaluate(t)})

        # 补足种群
        while len(population) < pop_size:
            base = rng.choice(population)
            t = deep_copy_tours(base['tours'])
            dds = list(dates)
            for _ in range(rng.randint(1, 5)):
                d1, d2 = rng.sample(dds, 2)
                if len(t.get(d1, [])) > 3 and t.get(d2) is not None:
                    c = rng.choice(t[d1])
                    t[d1].remove(c)
                    if len(t[d1]) >= 2:
                        t[d1] = two_opt(t[d1], D, 5)
                    t[d2].append(c)
                    t[d2] = two_opt(t[d2], D, 5)
            population.append({'tours': t, 'obj': evaluate(t)})

        # ===== NSGA-II 主循环 =====
        generation = 0
        ops = ['worst_move', 'random_move', 'swap', 'oropt']
        w = {o: 1.0 for o in ops}

        while time.time() < deadline:
            generation += 1
            # 非支配排序
            fronts = non_dominated_sort(population)
            # 环境选择
            new_pop = []
            for front in fronts:
                if len(new_pop) + len(front) <= pop_size:
                    new_pop.extend([population[i] for i in front])
                else:
                    cd = crowding_distance(population, front)
                    sorted_front = sorted(front, key=lambda i: cd[i], reverse=True)
                    new_pop.extend([population[i] for i in sorted_front[:pop_size - len(new_pop)]])
                    break
            population = new_pop[:pop_size]

            # 生成子代 (ALNS 算子)
            offspring = []
            num_offspring = max(2, pop_size // 3)
            for _ in range(num_offspring):
                if time.time() >= deadline:
                    break
                # 锦标赛选择 parent
                candidates = rng.sample(range(len(population)), min(3, len(population)))
                parent = min(candidates, key=lambda i: (
                    0 if i in (fronts[0] if fronts else []) else 1,
                    -len(population[i].get('tours', {}))
                ))
                tours = deep_copy_tours(population[parent]['tours'])

                # 选择算子
                total_w = sum(w.values())
                r = rng.random() * total_w
                op = ops[0]
                for o in ops:
                    r -= w[o]
                    if r <= 0:
                        op = o
                        break

                dds = list(dates)

                if op in ('worst_move', 'random_move'):
                    d1 = rng.choice(dds)
                    t1 = tours.get(d1, [])
                    if len(t1) > 3:
                        if op == 'worst_move':
                            c = worst_edge(t1, D, zone_of, False)
                            if c is None or c not in t1:
                                c = rng.choice(t1)
                        else:
                            c = rng.choice(t1)
                        candidates_d2 = [d2 for d2 in dds if d2 != d1 and c not in tours.get(d2, [])]
                        if candidates_d2:
                            d2 = rng.choice(candidates_d2)
                            t1_new = [x for x in t1 if x != c]
                            if len(t1_new) >= 2:
                                t1_new = two_opt(t1_new, D, 6)
                                t2_new, _ = best_insert(tours[d2], c, D)
                                t2_new = two_opt(t2_new, D, 6)
                                tours[d1] = t1_new
                                tours[d2] = t2_new
                elif op == 'swap':
                    d1, d2 = rng.sample(dds, 2)
                    t1, t2 = tours.get(d1, []), tours.get(d2, [])
                    if len(t1) > 2 and len(t2) > 2:
                        c1, c2 = rng.choice(t1), rng.choice(t2)
                        if c1 not in t2 and c2 not in t1:
                            t1_new = [c2 if x == c1 else x for x in t1]
                            t2_new = [c1 if x == c2 else x for x in t2]
                            tours[d1] = two_opt(t1_new, D, 6)
                            tours[d2] = two_opt(t2_new, D, 6)
                elif op == 'oropt':
                    dd = rng.choice(dds)
                    t = tours.get(dd, [])
                    if len(t) > 3:
                        t_new = two_opt(t, D, 8)
                        if day_km(t_new, D) < day_km(t, D) - 1e-9:
                            tours[dd] = t_new

                obj = evaluate(tours)
                offspring.append({'tours': tours, 'obj': obj})

            # 合并父子代
            population.extend(offspring)

            # 截断至 pop_size (环境选择)
            fronts = non_dominated_sort(population)
            new_pop = []
            for front in fronts:
                if len(new_pop) + len(front) <= pop_size:
                    new_pop.extend([population[i] for i in front])
                else:
                    cd = crowding_distance(population, front)
                    sorted_front = sorted(front, key=lambda i: cd[i], reverse=True)
                    new_pop.extend([population[i] for i in sorted_front[:pop_size - len(new_pop)]])
                    break
            population = new_pop[:pop_size]

        # ===== 提取帕累托前沿 =====
        fronts = non_dominated_sort(population)
        pareto_pop = [population[i] for i in fronts[0]]

        # 按里程排序
        pareto_pop.sort(key=lambda p: p['obj'][0])

        # 去重（按目标向量去重）
        seen = set()
        unique_pareto = []
        for p in pareto_pop:
            key = tuple(round(v, 4) for v in p['obj'])
            if key not in seen:
                seen.add(key)
                unique_pareto.append(p)

        # ===== 自动命名方案 =====
        ideal = [min(p['obj'][i] for p in unique_pareto) for i in range(4)]
        ranges = [max(p['obj'][i] for p in unique_pareto) - ideal[i] for i in range(4)]

        def dist_to_ideal(p):
            return math.sqrt(sum(
                ((p['obj'][i] - ideal[i]) / max(ranges[i], 1e-9)) ** 2
                for i in range(4)
            ))

        # 激进型: f1 最小
        aggressive = unique_pareto[0]
        # 保守型: f2 最小
        conservative = min(unique_pareto, key=lambda p: p['obj'][1])
        # 均衡型: f3 最小
        balanced = min(unique_pareto, key=lambda p: p['obj'][2])
        # 推荐型: 距理想点最近（膝点）
        knee = min(unique_pareto, key=dist_to_ideal)

        presets = {
            'aggressive': {'tours': aggressive['tours'], 'obj': aggressive['obj']},
            'recommended': {'tours': knee['tours'], 'obj': knee['obj']},
            'balanced': {'tours': balanced['tours'], 'obj': balanced['obj']},
            'conservative': {'tours': conservative['tours'], 'obj': conservative['obj']},
        }

        # ===== 构建输出 =====
        inc_dm = _dates_map(data.days_orig)
        all_pareto = []
        for i, p in enumerate(unique_pareto):
            dm = _dates_map(p['tours'])
            changes = []
            for s in sorted(set(list(dm.keys()) + list(inc_dm.keys()))):
                if dm.get(s, set()) != inc_dm.get(s, set()):
                    code = data.codes[s] if s < len(data.codes) else str(s)
                    changes.append({
                        'store': code,
                        'orig': sorted(str(d) for d in inc_dm.get(s, set())),
                        'new': sorted(str(d) for d in dm.get(s, set()))
                    })
            all_pareto.append({
                'id': i,
                'km': round(p['obj'][0], 2),
                'changed': p['obj'][1],
                'cv': round(p['obj'][2], 4),
                'cross_ratio': round(p['obj'][3], 4),
                'changes': changes
            })

        named = {}
        for name, p in presets.items():
            dm = _dates_map(p['tours'])
            changed = sum(1 for s in set(list(dm.keys()) + list(inc_dm.keys()))
                          if dm.get(s, set()) != inc_dm.get(s, set()))
            named[name] = {
                'km': round(p['obj'][0], 2),
                'changed': p['obj'][1],
                'cv': round(p['obj'][2], 4),
                'cross_ratio': round(p['obj'][3], 4),
                'days': {str(dd): [data.codes[s] if s < len(data.codes) else str(s) for s in seq]
                         for dd, seq in p['tours'].items()},
                'freq_ok': check_freq(p['tours'], data.codes, data.freq)
            }

        return AlgoResult(
            name=self.name,
            days=pareto_pop[0]['tours'],
            km=pareto_pop[0]['obj'][0],
            metadata={
                'pareto_front': all_pareto,
                'presets': named,
                'generations': generation,
                'pop_size': len(population),
                'front_size': len(unique_pareto),
                'preset_names': {k: {'km': v['km'], 'changed': v['changed'],
                                     'cv': v['cv'], 'cross': v['cross_ratio']}
                                 for k, v in named.items()},
                'total_stores': len(data.codes),
            }
        )
