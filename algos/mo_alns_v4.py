# -*- coding: utf-8 -*-
"""V4 MO-ALNS — 多目标帕累托方案生成器 (NSGA-II + ALNS 混合).

定位: 以 v3 月度优化结果为基准 (base), 在其邻域内演化, 生成帕累托前沿上的一组非支配解.

三目标 (跨区率 f4 已随 Clustered TSP 场景否决一并废弃):
  f1: 总里程 (km)                — 越小越好
  f2: 改动店数 (相对基准 base)   — 越小越好 (base=v3 时 = 在 v3 基础上再挪几家)
  f3: 每日工作量变异系数 CV       — 越小越均衡

算法: NSGA-II 非支配排序 + 拥挤度 + ALNS destroy/repair 算子.
锚点解 (extra_seeds, 如 CP-SAT 0改动下限) 参与进化且单独保全, 最终并入前沿不被淘汰.
"""
import time, math, random, copy
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_freq, check_capacity
from algos.registry import register
from algos.alns_v3 import two_opt, best_insert, worst_edge

NUM_OBJ = 3  # f1 km, f2 changed, f3 cv


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


def _feasible(tours, min_daily, max_daily):
    """可行性门禁 (评审 P1-3): 每日店数在 [min_daily, max_daily] 内且无同日重复店."""
    for seq in tours.values():
        if len(set(seq)) != len(seq):
            return False
        if min_daily > 0 and len(seq) < min_daily:
            return False
        if max_daily > 0 and len(seq) > max_daily:
            return False
    return True

def dominates(a, b):
    """a dominates b if a <= b in all objectives and < in at least one."""
    better_any = False
    for i in range(NUM_OBJ):
        if a[i] > b[i]:
            return False
        if a[i] < b[i]:
            better_any = True
    return better_any


def non_dominated_sort(pop):
    """Returns list of fronts (each is a list of indices)."""
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
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                rank[q] -= 1
                if rank[q] == 0:
                    nxt.append(q)
        i += 1
        if nxt:
            fronts.append(nxt)
    return fronts


def crowding_distance(pop, front):
    """Assign crowding distance to individuals in a front."""
    n = len(front)
    if n <= 2:
        return {i: float('inf') for i in front}
    dist = {i: 0.0 for i in front}
    for obj_idx in range(NUM_OBJ):
        sf = sorted(front, key=lambda i: pop[i]['obj'][obj_idx])
        dist[sf[0]] = float('inf')
        dist[sf[-1]] = float('inf')
        rng = pop[sf[-1]]['obj'][obj_idx] - pop[sf[0]]['obj'][obj_idx]
        if rng == 0:
            continue
        for k in range(1, n - 1):
            dist[sf[k]] += (pop[sf[k + 1]]['obj'][obj_idx] - pop[sf[k - 1]]['obj'][obj_idx]) / rng
    return dist


def _truncate(pop, pop_size):
    """NSGA-II environmental selection: keep pop_size by front rank + crowding."""
    fronts = non_dominated_sort(pop)
    new_pop = []
    for front in fronts:
        if len(new_pop) + len(front) <= pop_size:
            new_pop.extend([pop[i] for i in front])
        else:
            cd = crowding_distance(pop, front)
            ordered = sorted(front, key=lambda i: cd[i], reverse=True)
            new_pop.extend([pop[i] for i in ordered[:pop_size - len(new_pop)]])
            break
    return new_pop[:pop_size]


@register
class MOALNSv4(Algorithm):
    name = "mo_alns_v4"

    def solve(self, data, D, time_budget=60, zone_of=None, seed=42,
              pop_size=30, num_presets=4, extra_seeds=None, base=None):
        """
        参数:
          base: 基准解 {date:[store_idx]}. 提供时 (通常=v3 结果), 种群围绕它演化,
                f2 改动量 = 相对 base 的偏离 (即在 v3 基础上再挪几家).
                省略则退回以 data.days_orig (原始计划) 为基准.
          extra_seeds: {label: tours} 额外锚点解 (如 CP-SAT 0改动下限), 强制并入最终前沿.
        """
        rng = random.Random(seed)
        dates = list(data.dates)
        min_daily = getattr(data, 'min_daily_capacity', 0) or (min(len(v) for v in data.days_orig.values()) if data.days_orig else 0)
        max_daily = getattr(data, 'max_daily_capacity', 0) or (max(len(v) for v in data.days_orig.values()) if data.days_orig else 0)
        ref = base if base else data.days_orig
        ref_dm = _dates_map(ref)
        deadline = time.time() + time_budget

        def dc(t):
            return {dd: list(seq) for dd, seq in t.items()}

        def evaluate(tours):
            dm = _dates_map(tours)
            changed = sum(1 for s in set(list(dm.keys()) + list(ref_dm.keys()))
                          if dm.get(s, set()) != ref_dm.get(s, set()))
            return [total_km(tours, D), changed, _cv(tours)]

        def perturb(tours, n_moves):
            t = dc(tours)
            if len(dates) < 2:
                return t
            for _ in range(n_moves):
                d1, d2 = rng.sample(dates, 2)
                t1 = t.get(d1, [])
                if len(t1) <= max(3, min_daily):
                    continue
                cands = [c for c in t1 if any(d2b != d1 and c not in t.get(d2b, []) and len(t.get(d2b, [])) < max_daily for d2b in dates)]
                if not cands:
                    continue
                c = rng.choice(cands)
                tgt = [d2b for d2b in dates if d2b != d1 and c not in t.get(d2b, []) and len(t.get(d2b, [])) < max_daily]
                d2 = rng.choice(tgt)
                t[d1] = [x for x in t1 if x != c]
                if len(t[d1]) >= 2:
                    t[d1] = two_opt(t[d1], D, 5)
                t[d2] = two_opt(t.get(d2, []) + [c], D, 5)
            return t

        # 锚点解单独保全 (不随进化截断丢失), 最终并入前沿
        anchors = [{'tours': dc(t), 'obj': evaluate(dc(t)), 'seed_label': lb}
                   for lb, t in (extra_seeds or {}).items()]

        # ===== 初始化种群 (以 v3/基准出发, 邻域扰动) =====
        base_t = dc(ref)
        population = [{'tours': base_t, 'obj': evaluate(base_t)}]
        pop_tsp = {dd: two_opt(list(base_t.get(dd, [])), D, 20) for dd in dates}
        population.append({'tours': pop_tsp, 'obj': evaluate(pop_tsp)})
        while len(population) < pop_size:
            t = perturb(base_t, rng.randint(1, 6))
            population.append({'tours': t, 'obj': evaluate(t)})

        # ===== NSGA-II 主循环 =====
        generation = 0
        ops = ['worst_move', 'random_move', 'swap', 'oropt']
        w = {o: 1.0 for o in ops}

        while time.time() < deadline:
            generation += 1
            population = _truncate(population, pop_size)
            fronts0 = set(non_dominated_sort(population)[0]) if population else set()

            offspring = []
            for _ in range(max(2, pop_size // 3)):
                if time.time() >= deadline or len(dates) < 2:
                    break
                cands = rng.sample(range(len(population)), min(3, len(population)))
                parent = min(cands, key=lambda i: (0 if i in fronts0 else 1, i))
                tours = dc(population[parent]['tours'])

                total_w = sum(w.values())
                r = rng.random() * total_w
                op = ops[0]
                for o in ops:
                    r -= w[o]
                    if r <= 0:
                        op = o
                        break

                if op in ('worst_move', 'random_move'):
                    d1 = rng.choice(dates)
                    t1 = tours.get(d1, [])
                    if len(t1) > max(3, min_daily):
                        if op == 'worst_move':
                            c = worst_edge(t1, D, zone_of, False)
                            if c is None or c not in t1:
                                c = rng.choice(t1)
                        else:
                            c = rng.choice(t1)
                        cd2 = [d2 for d2 in dates if d2 != d1 and c not in tours.get(d2, [])
                               and len(tours.get(d2, [])) < max_daily]
                        if cd2:
                            d2 = rng.choice(cd2)
                            t1n = [x for x in t1 if x != c]
                            if len(t1n) >= 2:
                                t2n, _ = best_insert(tours[d2], c, D)
                                tours[d1] = two_opt(t1n, D, 6)
                                tours[d2] = two_opt(t2n, D, 6)
                elif op == 'swap':
                    d1, d2 = rng.sample(dates, 2)
                    t1, t2 = tours.get(d1, []), tours.get(d2, [])
                    if len(t1) > 2 and len(t2) > 2:
                        c1, c2 = rng.choice(t1), rng.choice(t2)
                        if c1 not in t2 and c2 not in t1:
                            tours[d1] = two_opt([c2 if x == c1 else x for x in t1], D, 6)
                            tours[d2] = two_opt([c1 if x == c2 else x for x in t2], D, 6)
                elif op == 'oropt':
                    dd = rng.choice(dates)
                    t = tours.get(dd, [])
                    if len(t) > 3:
                        tn = two_opt(t, D, 8)
                        if day_km(tn, D) < day_km(t, D) - 1e-9:
                            tours[dd] = tn

                if _feasible(tours, min_daily, max_daily):
                    offspring.append({'tours': tours, 'obj': evaluate(tours)})

            population.extend(offspring)

        # ===== 最终前沿: 先过滤不合规解 (容量+同日去重), 再支配排序 (评审 P1-3) =====
        cand = [p for p in population + [copy.deepcopy(a) for a in anchors]
                if _feasible(p['tours'], min_daily, max_daily)]
        fronts = non_dominated_sort(cand)
        pareto_pop = sorted([cand[i] for i in fronts[0]], key=lambda p: p['obj'][0]) if cand else []
        if not pareto_pop:
            raise ValueError("V4 无可行解: base/锚点本身违反容量走廊 [min,max]=%s, 请先以走廊约束版 v3/SP 产出合规基准" % [min_daily, max_daily])
        seen = set()
        uniq = []
        for p in pareto_pop:
            key = tuple(round(v, 4) for v in p['obj'])
            if key not in seen:
                seen.add(key)
                uniq.append(p)

        # ===== 自动命名 (激进/膝点/均衡/保守) =====
        ideal = [min(p['obj'][i] for p in uniq) for i in range(NUM_OBJ)]
        ranges = [max(p['obj'][i] for p in uniq) - ideal[i] for i in range(NUM_OBJ)]

        def dist_to_ideal(p):
            return math.sqrt(sum(((p['obj'][i] - ideal[i]) / max(ranges[i], 1e-9)) ** 2
                                 for i in range(NUM_OBJ)))

        aggressive = uniq[0]                                            # min km
        conservative = min(uniq, key=lambda p: (p['obj'][1], p['obj'][0]))  # min changed
        balanced = min(uniq, key=lambda p: p['obj'][2])                # min cv
        knee = min(uniq, key=dist_to_ideal)                           # closest to ideal
        presets = {'aggressive': aggressive, 'recommended': knee,
                   'balanced': balanced, 'conservative': conservative}

        # ===== 构建输出 =====
        all_pareto = []
        for i, p in enumerate(uniq):
            dm = _dates_map(p['tours'])
            changes = [{'store': data.codes[s] if s < len(data.codes) else str(s),
                        'orig': sorted(str(d) for d in ref_dm.get(s, set())),
                        'new': sorted(str(d) for d in dm.get(s, set()))}
                       for s in sorted(set(list(dm.keys()) + list(ref_dm.keys())))
                       if dm.get(s, set()) != ref_dm.get(s, set())]
            all_pareto.append({'id': i, 'km': round(p['obj'][0], 2),
                               'changed': p['obj'][1], 'cv': round(p['obj'][2], 4),
                               'changes': changes})

        named = {}
        for name, p in presets.items():
            named[name] = {
                'km': round(p['obj'][0], 2),
                'changed': p['obj'][1],
                'cv': round(p['obj'][2], 4),
                'days': {str(dd): [data.codes[s] if s < len(data.codes) else str(s) for s in seq]
                         for dd, seq in p['tours'].items()},
                'capacity_ok': _feasible(p['tours'], min_daily, max_daily),
                'freq_ok': check_freq(p['tours'], data.codes, data.freq)
            }

        return AlgoResult(
            name=self.name,
            days=uniq[0]['tours'],
            km=uniq[0]['obj'][0],
            capacity_ok=_feasible(uniq[0]['tours'], min_daily, max_daily),
            metadata={
                'pareto_front': all_pareto,
                'presets': named,
                'generations': generation,
                'front_size': len(uniq),
                'preset_names': {k: {'km': v['km'], 'changed': v['changed'],
                                     'cv': v['cv'], 'freq_ok': v['freq_ok'],
                                     'capacity_ok': v['capacity_ok']}
                                 for k, v in named.items()},
                'total_stores': len(data.codes),
                'base_is_v3': bool(base),
                'capacity_bounds': [min_daily, max_daily],
            }
        )
