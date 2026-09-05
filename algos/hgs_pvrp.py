# -*- coding: utf-8 -*-
"""HGS-PVRP - 混合遗传搜索 (周期VRP, 开放路径变体).

参考: Vidal et al. 2012 (UHGS, PVRP 参考 SOTA); Ropke & Pisinger 2006.
适配: 每日开放链(无仓库往返), 每店出现次数多集合守恒, 任意工作日可跨.

架构 (2026-09-05 终版, 经五轮剖析迭代):
- 种子: nn2opt + v3 式贪心热身 + 短 SA;
- 交叉: 日级均匀重组 (day-assignment uniform crossover), 计数差异多退少补守恒;
- 教育: v3 同款 SA (tour-carrying destroy + regret-2 + 退火) 短促深搜 —— 纯 Python
  下自研 descent 邻域的速度/强度两端不讨好, SA 机器是本项目实测最强的深度引擎;
- 进化: (mu+1), 偏置适应度(成本排名 + 多样性排名), 停滞注入扰动.
"""
import time, math, random
from copy import deepcopy
import numpy as np
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km
from algos.registry import register
from algos.tsp_engine import _nn2opt_open
from algos.alns_v3 import two_opt, best_insert, worst_edge


def _ins_deltas(tour, c, D):
    """把 c 插入 tour 各位置的增量数组 (len(tour)+1). 端点=开放链首尾."""
    if not tour:
        return np.zeros(1)
    t = np.asarray(tour)
    head = D[c, t[0]]
    tail = D[t[-1], c]
    if len(t) == 1:
        return np.array([head, tail])
    mid = D[c, t[:-1]] + D[t[1:], c] - D[t[:-1], t[1:]]
    return np.concatenate(([head], mid, [tail]))


def _removal_delta(tour, pos, D):
    n = len(tour)
    if n <= 1:
        return 0.0
    if pos == 0:
        return -D[tour[0], tour[1]]
    if pos == n - 1:
        return -D[tour[-2], tour[-1]]
    return D[tour[pos-1], tour[pos]] + D[tour[pos], tour[pos+1]] - D[tour[pos-1], tour[pos+1]]


def _assign_vec(tours, dates):
    return {c: tuple(dd for dd in dates if c in tours[dd]) for dd in dates for c in tours[dd]}


def _diversity(va, vb, n_stores):
    return sum(1 for c, s in va.items() if vb.get(c) != s) / n_stores


def _greedy_warm(tours, D, dates, budget_s):
    """v3 同款贪心跨日热身 (对照公平性)."""
    t0 = time.time()
    for _ in range(30):
        imp = False
        if time.time() - t0 > budget_s:
            break
        for dd1 in dates:
            for dd2 in dates:
                if dd1 == dd2:
                    continue
                s1, s2 = tours[dd1], tours[dd2]
                if len(s1) <= 5:
                    continue
                for c in list(s1):
                    if c in s2:
                        continue
                    ns1 = [x for x in s1 if x != c]
                    ns2 = s2 + [c]
                    if len(ns1) < 2:
                        continue
                    o1 = two_opt(ns1, D, 6)
                    o2 = two_opt(ns2, D, 6)
                    if day_km(o1, D) + day_km(o2, D) < day_km(s1, D) + day_km(s2, D) - 0.05:
                        tours[dd1] = o1
                        tours[dd2] = o2
                        imp = True
                        break
                if time.time() - t0 > budget_s:
                    break
            if time.time() - t0 > budget_s:
                break
        if not imp or time.time() - t0 > budget_s:
            break
    return tours


def _sa_improve(tours, D, dates, rng, deadline, zone_of=None, hot=1.0):
    """v3 主循环同款 SA (tour-carrying destroy + regret-2 修复 + 三段退火). 就地改进."""
    cur = total_km(tours, D)
    orig = tours  # 保存调用方字典引用: 循环内 tours 会被 trial 重绑定
    best = cur
    best_t = {dd: list(tours[dd]) for dd in dates}
    edges = sum(max(0, len(tours[dd])-1) for dd in dates) or 1
    avg = cur / edges
    T0 = max(0.5, avg*3.0) * hot; Tend = 0.02 * max(1.0, hot)
    T1 = max(0.05, avg*0.3) * hot; T2 = max(0.01, avg*0.05) * max(1.0, hot); T3 = max(0.01, avg*0.02) * max(1.0, hot)
    t0 = time.time()
    ops = ['worst', 'cross', 'segment', 'random']
    w = {o: 1.0 for o in ops}

    def pick():
        tw = sum(w.values())
        r = rng.random() * tw
        for o in ops:
            r -= w[o]
            if r <= 0:
                return o
        return ops[0]

    while time.time() < deadline:
        el = (time.time()-t0)/max(1e-9, (deadline-t0))
        if el < 0.33: T = T0 + (T1-T0)*(el/0.33)
        elif el < 0.66: T = T1 + (T2-T1)*((el-0.33)/0.33)
        else: T = T2 + (T3-T2)*((el-0.66)/0.34)
        op = pick()
        dd1 = rng.choice(dates)
        t1 = tours[dd1]
        if len(t1) <= 5:
            continue
        if op == 'worst':
            v = worst_edge(t1, D, zone_of, False); rem = [v] if v is not None else []
        elif op == 'cross':
            v = worst_edge(t1, D, zone_of, True); rem = [v] if v is not None else []
        elif op == 'segment':
            k = rng.randint(0, len(t1)-1); ln = min(rng.randint(2, 4), len(t1)-2)
            rem = t1[k:k+ln]
        else:
            rem = [rng.choice(t1)]
        rem = [x for x in rem if x in t1]
        if len(rem) < 1 or len(t1)-len(rem) < 2:
            continue
        nt1 = two_opt([x for x in t1 if x not in rem], D, 10)
        trial = {dd: list(tours[dd]) for dd in dates}
        trial[dd1] = nt1
        ok = True
        for node in rem:
            cands = []
            for dd in dates:
                if node in trial[dd]:
                    continue
                if len(trial[dd]) < 1:
                    continue
                _, dl = best_insert(trial[dd], node, D)
                cands.append((dl, dd))
            if not cands:
                ok = False
                break
            cands.sort()
            bdl, bdd = cands[0]
            newt, _ = best_insert(trial[bdd], node, D)
            trial[bdd] = two_opt(newt, D, 6)
        if not ok:
            continue
        new_obj = total_km(trial, D)
        diff = new_obj - cur
        if diff < 0 or rng.random() < math.exp(-diff/max(1e-9, T)):
            tours = trial
            cur = new_obj
            w[op] = min(6.0, w[op] + 0.15) if diff < 0 else w[op]
            if new_obj < best - 1e-9:
                best = new_obj
                best_t = {dd: list(tours[dd]) for dd in dates}
                w[op] = min(6.0, w[op]+0.2)
        else:
            w[op] = max(0.2, w[op]-0.01)
    orig.clear()
    orig.update(best_t)
    return best


def _counts(tours, dates):
    k = {}
    for dd in dates:
        for c in tours[dd]:
            k[c] = k.get(c, 0) + 1
    return k


class _Ind:
    __slots__ = ("tours", "avec", "km")

    def __init__(self, tours, D, dates):
        self.tours = tours
        self.avec = _assign_vec(tours, dates)
        self.km = total_km(tours, D)


def _perturb(src, D, dates, rng, k_moves=25):
    ind = deepcopy(src)
    for _ in range(k_moves):
        dd1 = rng.choice(dates)
        if len(ind[dd1]) <= 5:
            continue
        c = rng.choice(ind[dd1])
        dd2 = rng.choice([x for x in dates if c not in ind[x]] or [dd1])
        ind[dd1].remove(c)
        dl = _ins_deltas(ind[dd2], c, D)
        ind[dd2].insert(int(dl.argmin()), c)
    return ind


@register
class HGSPVRP(Algorithm):
    name = "hgs_pvrp"

    def solve(self, data, D, time_budget=300, seed=42, pop_size=24):
        D = np.asarray(D)
        rng = random.Random(seed)
        dates = list(data.dates)
        t0 = time.time(); deadline = t0 + time_budget
        n_stores = len({c for dd in dates for c in data.days_orig[dd]})

        # ---- 种子: nn2opt + 贪心热身 + 短 SA ----
        base = {dd: _nn2opt_open(list(data.days_orig[dd]), D) for dd in dates}
        base = _greedy_warm(base, D, dates, time_budget * 0.08)
        k_true = _counts(base, dates)
        _sa_improve(base, D, dates, rng, t0 + time_budget * 0.18)

        pool = [_Ind(deepcopy(base), D, dates)]
        for _ in range(min(7, pop_size // 2)):
            pool.append(_Ind(_perturb(base, D, dates, rng), D, dates))

        best = min(pool, key=lambda p: p.km)
        best_km = best.km
        S = 6
        stall = 0
        gens = 0

        while time.time() < deadline:
            gens += 1
            n = len(pool)
            pool.sort(key=lambda p: p.km)
            divs = []
            for i in range(n):
                acc = sum(_diversity(pool[i].avec, pool[j].avec, n_stores)
                          for j in range(n) if j != i)
                divs.append(acc / max(1, n - 1))
            div_rank = {i: r for r, i in enumerate(sorted(range(n), key=lambda i: -divs[i]))}
            bf = [(1 - S / (n + 1)) * k + (S / (n + 1)) * div_rank[k] for k in range(n)]

            def pick():
                a, b = rng.randrange(n), rng.randrange(n)
                return pool[a] if bf[a] < bf[b] else pool[b]

            # ---- 交叉: 日级均匀重组 ----
            p1, p2 = pick(), pick()
            child = {}
            for dd in dates:
                child[dd] = list(p1.tours[dd] if rng.random() < 0.5 else p2.tours[dd])

            # ---- 守恒兜底: 多退少补 ----
            cnt = _counts(child, dates)
            removed = []
            for c, k in k_true.items():
                d = cnt.get(c, 0) - k
                if d > 0:
                    for _ in range(d):
                        bdd, bpos, bd = None, None, 1e18
                        for dd in dates:
                            t = child[dd]
                            if c in t:
                                pos = t.index(c)
                                dr = _removal_delta(t, pos, D)
                                if dr < bd:
                                    bdd, bpos, bd = dd, pos, dr
                        if bdd is not None:
                            child[bdd].pop(bpos)
                elif d < 0:
                    removed.extend([c] * (-d))
            rng.shuffle(removed)
            for c in removed:
                cands = [(dd, int(dls.argmin()), float(dls.min()))
                         for dd in dates if c not in child[dd]
                         for dls in (_ins_deltas(child[dd], c, D),)]
                if not cands:
                    continue
                bdd, bpos, _ = min(cands, key=lambda z: z[2])
                child[bdd].insert(bpos, c)

            # ---- 教育: v3 SA 短促深搜 ----
            _sa_improve(child, D, dates, rng,
                        min(deadline, time.time() + max(1.5, (deadline - time.time()) * 0.12)),
                        hot=0.15)
            ind = _Ind(child, D, dates)
            pool.append(ind)
            pool = pool[:pop_size]
            if ind.km < best_km - 1e-9:
                best_km = ind.km
                best = ind
                stall = 0
            else:
                stall += 1
            if stall >= 40 and time.time() < deadline:
                for i in range(len(pool) - max(1, pop_size // 3), len(pool)):
                    pool[i] = _Ind(_perturb(best.tours, D, dates, rng), D, dates)
                stall = 0

        final = {dd: two_opt(best.tours[dd], D, 30) for dd in dates}
        return AlgoResult(name=self.name, days=final, km=total_km(final, D),
                          metadata={"gens": gens, "budget": time_budget})
