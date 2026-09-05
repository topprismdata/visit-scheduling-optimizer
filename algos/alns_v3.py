# -*- coding: utf-8 -*-
"""ALNS v3 - 反馈耦合 (tour-carrying). v1 只把 TSP 当秤(每候选从头重算);
v3 把 TSP 当眼睛: 每天携带 tour, 增量 2-opt, tour-informed destroy,
   regret 插入修复, 模拟退火接受.
参考: Ropke&Pisinger 2006; Shaw 1998 related-removal; Pisinger&Ropke 2007.
"""
import time, math, random
from core.metric import day_km, total_km, check_capacity
from core.base import Algorithm, AlgoResult
from algos.registry import register
from algos.tsp_engine import _nn2opt_open


def best_insert(tour, node, D):
    """node 插入 tour 最优位置 -> (新tour, delta). 增量 O(n), 不重建."""
    n = len(tour)
    if n == 0: return [node], 0.0
    best = float('inf'); pos = n
    # 端点插入
    d0 = D[node][tour[0]]
    if d0 < best: best = d0; pos = 0
    dl = D[tour[-1]][node]
    if dl < best: best = dl; pos = n
    for k in range(n - 1):
        delta = D[tour[k]][node] + D[node][tour[k+1]] - D[tour[k]][tour[k+1]]
        if delta < best: best = delta; pos = k + 1
    return tour[:pos] + [node] + tour[pos:], best


def two_opt(tour, D, max_pass=20):
    """开放路径 2-opt, 有限轮. 返回改进后 tour."""
    seq = list(tour); n = len(seq)
    if n <= 3: return seq
    improved = True; p = 0
    while improved and p < max_pass:
        improved = False; p += 1
        for a in range(1, n - 1):
            for b in range(a + 1, n):
                before = D[seq[a-1]][seq[a]] + (D[seq[b]][seq[b+1]] if b < n-1 else 0.0)
                after  = D[seq[a-1]][seq[b]] + (D[seq[a]][seq[b+1]] if b < n-1 else 0.0)
                if after < before - 1e-9:
                    seq[a:b+1] = seq[a:b+1][::-1]; improved = True
    return seq


def worst_edge(tour, D, zone_of=None, cross_pref=False):
    """当前 tour 里最"该拆"的边: 距离最大; cross_pref 时跨区边加权. 返回端点b."""
    if len(tour) < 2: return None
    best_s = -1; vb = None
    for k in range(len(tour)-1):
        a, b = tour[k], tour[k+1]
        d = D[a][b]
        if cross_pref and zone_of is not None and zone_of.get(a) == zone_of.get(b):
            d *= 0.25
        if d > best_s: best_s = d; vb = b
    return vb


@register
class ALNSv3(Algorithm):
    name = "alns_v3"

    def solve(self, data, D, time_budget=300, zone_of=None, seed=42, weekday_lock=False):
        rng = random.Random(seed)
        dates = data.dates
        min_daily = getattr(data, 'min_daily_capacity', 0) or min(len(v) for v in data.days_orig.values())
        max_daily = getattr(data, 'max_daily_capacity', 0) or max(len(v) for v in data.days_orig.values())
        # ---- 起点: 每天 nn2opt + 一轮贪心跨日 (带双向走廊约束; weekday_lock=仅同星期几槽位互挪) ----
        wd_slots = {}
        for dd in dates: wd_slots.setdefault(dd.weekday(), []).append(dd)
        tours = {dd: _nn2opt_open(list(data.days_orig[dd]), D) for dd in dates}
        t0 = time.time(); warm = time_budget * 0.12
        for _ in range(30):
            imp = False
            if time.time() - t0 > warm: break
            for dd1 in dates:
                for dd2 in (wd_slots[dd1.weekday()] if weekday_lock else dates):
                    if dd1 == dd2: continue
                    s1, s2 = tours[dd1], tours[dd2]
                    if len(s1) <= min_daily or len(s2) >= max_daily: continue
                    for c in list(s1):
                        if c in s2: continue
                        ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                        if len(ns1) < 2: continue
                        o1 = two_opt(ns1, D, 6); o2 = two_opt(ns2, D, 6)
                        if day_km(o1, D) + day_km(o2, D) < day_km(s1, D) + day_km(s2, D) - 0.05:
                            tours[dd1] = o1; tours[dd2] = o2; imp = True; break
                    if time.time() - t0 > warm: break
                if time.time() - t0 > warm: break
            if not imp or time.time() - t0 > warm: break

        cur = total_km(tours, D)
        best = cur; best_t = {dd: list(tours[dd]) for dd in dates}
        # ---- 温度 ----
        edges = sum(max(0, len(tours[dd])-1) for dd in dates) or 1
        avg = cur / edges
        T0 = max(0.5, avg*3.0); Tend = 0.02
        T1 = max(0.05, avg*0.3); T2 = max(0.01, avg*0.05)
        T3 = max(0.01, avg*0.02)
        deadline = t0 + time_budget
        ops = ['worst', 'cross', 'segment', 'random']
        w = {o: 1.0 for o in ops}; sc = {o: 0.0 for o in ops}; cn = {o: 0 for o in ops}

        def pick():
            tw = sum(w.values()); r = rng.random()*tw
            for o in ops:
                r -= w[o]
                if r <= 0: return o
            return ops[0]

        its = 0
        while time.time() < deadline:
            its += 1
            el = (time.time()-t0)/max(1e-9,(deadline-t0))
            if el < 0.33: T = T0 + (T1-T0)*(el/0.33)
            elif el < 0.66: T = T1 + (T2-T1)*((el-0.33)/0.33)
            else: T = T2 + (T3-T2)*((el-0.66)/0.34)
            op = pick()
            dd1 = rng.choice(dates) if not weekday_lock else rng.choice([dd for dd in dates if len(wd_slots[dd.weekday()]) > 1])
            t1 = tours[dd1]
            if len(t1) <= min_daily: continue
            # destroy: tour-informed
            if op == 'worst':
                v = worst_edge(t1, D, zone_of, False); rem = [v] if v is not None else []
            elif op == 'cross':
                v = worst_edge(t1, D, zone_of, True); rem = [v] if v is not None else []
            elif op == 'segment':
                k = rng.randint(0, len(t1)-1); ln = min(rng.randint(2,4), len(t1)-2)
                rem = t1[k:k+ln]
            else:
                rem = [rng.choice(t1)]
            rem = [x for x in rem if x in t1]
            if len(rem) < 1 or len(t1)-len(rem) < 2: continue
            nt1 = two_opt([x for x in t1 if x not in rem], D, 10)
            trial = {dd: list(tours[dd]) for dd in dates}; trial[dd1] = nt1
            # repair: regret-2 over days
            ok = True
            for node in rem:
                # 走廊守卫: 欠载日优先补足, 确保不低于 min_daily; 其次在 < max_daily 中挑选
                # 走廊守卫: 欠载日优先补足; weekday_lock 时目标日与 dd1 同星期几 (R2' 合法列)
                tgt_pool = wd_slots[dd1.weekday()] if weekday_lock else dates
                deficits = [dd for dd in tgt_pool if len(trial[dd]) < min_daily and node not in trial[dd]]
                target_days = deficits if deficits else [dd for dd in tgt_pool if node not in trial[dd] and len(trial[dd]) < max_daily]
                cands = []
                for dd in target_days:
                    _, dl = best_insert(trial[dd], node, D); cands.append((dl, dd))
                if not cands: ok = False; break
                cands.sort()
                bdl, bdd = cands[0]
                newt, _ = best_insert(trial[bdd], node, D)
                trial[bdd] = two_opt(newt, D, 6)
            if not ok or any(len(trial[dd]) < min_daily or len(trial[dd]) > max_daily for dd in dates):
                continue  # 评审 P1-3: destroy/repair 后任一日期越出走廊即整试验作废
            new_obj = total_km(trial, D)
            diff = new_obj - cur
            if diff < 0 or rng.random() < math.exp(-diff/max(1e-9,T)):
                tours = trial; cur = new_obj
                w[op] = min(6.0, w[op] + 0.15) if diff < 0 else w[op]
                if new_obj < best - 1e-9:
                    best = new_obj; best_t = {dd: list(tours[dd]) for dd in dates}; w[op] = min(6.0, w[op]+0.2)
            else:
                w[op] = max(0.2, w[op]-0.01)
        final = {dd: two_opt(best_t[dd], D, 30) for dd in dates}
        cap_ok = check_capacity(final, max_daily, min_daily)
        return AlgoResult(name=self.name, days=final, km=total_km(final, D),
                          capacity_ok=cap_ok, metadata={"iters": its, "min_daily": min_daily, "max_daily": max_daily})
