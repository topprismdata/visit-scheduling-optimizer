# -*- coding: utf-8 -*-
"""R2'-ALNS: 星期几一致约束下的原生搜索层 (2026-09-05).

语义 (用户澄清): 门店可以从周一改到周二, 但改了就全月一致 (第1234周都在周二).
即 σ: store → weekday 可重指派, 每店在其星期几的槽位中选 f_c 个日期.

核心算子 (保持 R2' + 走廊):
  MOVE: 选店 c (现星期几 w, 频次 f), 枚举目标星期几 w' (含 w 自身=槽位轮换) 及其
        C(|w'|, f) 个槽位子集 (f≤5, |w'|≤5 → ≤10 组合), 走廊校验后取最优插入组合;
  估价: 旧日期移除增益 O(1) + 新日期最优插入 O(n); 接受后 CP-SAT 精确重排受影响日.

输出: 全月列池 (每个 incumbent 状态的 23 条日列, 全部 R2'-合法) → 供 SP(r2_prime) 重组.
"""
import time, random, itertools
from collections import defaultdict
import numpy as np
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_capacity
from algos.registry import register
from algos.tsp_engine import _exact_open_tsp, _nn2opt_open
from algos.sp_matheuristic import check_r2prime, _wd


@register
class R2ALNS(Algorithm):
    name = "r2_alns"

    def solve(self, data, D, time_budget=300, seed=42, collect_every=25, keep_history=True):
        rng = random.Random(seed)
        D = np.asarray(D)
        dates = list(data.dates)
        wd_g = defaultdict(list)
        for dd in dates:
            wd_g[_wd(dd)].append(dd)
        min_cap, max_cap = data.min_daily_capacity, data.max_daily_capacity

        sched = {}                       # store -> set(dates)
        day_members = defaultdict(set)   # date -> stores
        for dd, seq in data.days_orig.items():
            for c in seq:
                sched.setdefault(c, set()).add(dd)
                day_members[dd].add(c)
        routes = {dd: _exact_open_tsp(sorted(day_members[dd]), D, 30) for dd in dates}
        cur_km = total_km(routes, D)
        best_km = cur_km
        best_routes = {dd: list(r) for dd, r in routes.items()}
        columns = []                     # 历史列池: [(date, route, km)]

        def snapshot():
            for dd in dates:
                columns.append((dd, list(routes[dd]), round(day_km(routes[dd], D), 3)))

        def removal_gain(dd, c):
            """从 dd 移除 c 的里程增益 (正=变短). O(len)."""
            r = routes[dd]
            if c not in r or len(r) <= 3:
                return -1e9
            i = r.index(c)
            if i == 0:
                return D[c][r[1]]
            if i == len(r) - 1:
                return D[r[-2]][c]
            return D[r[i-1]][c] + D[c][r[i+1]] - D[r[i-1]][r[i+1]]

        def insertion_cost(dd, c):
            """把 c 插进 dd 最优位置的代价."""
            r = routes[dd]
            if not r:
                return None
            best = float("inf")
            for k in range(len(r) + 1):
                cst = (D[c][r[k]] if k < len(r) else 0.0) + \
                      (D[r[k-1]][c] if k > 0 else 0.0) - \
                      (D[r[k-1]][r[k]] if 0 < k < len(r) else 0.0)
                best = min(best, cst)
            return best

        its = accepted = 0
        t0 = time.time(); deadline = t0 + time_budget
        stores = sorted(sched)
        while time.time() < deadline:
            its += 1
            c = rng.choice(stores)
            f = len(sched[c])
            old_wd = next(iter(_wd(d) for d in sched[c]))
            old_dates = sorted(sched[c], key=str)
            # 候选: 目标星期几 w' (含自身槽位轮换) 的 f-槽位子集
            best_ev = None
            for w2, slots in wd_g.items():
                if f > len(slots):
                    continue
                new_ds = rng.choice(list(itertools.combinations(slots, f))) if len(slots) > f else tuple(slots)
                new_dates = sorted(new_ds, key=str)
                # 走廊校验 (c 不在新旧交集里才动)
                if set(new_dates) == set(old_dates):
                    continue
                rel_ok = all(min_cap < len(day_members[d]) for d in old_dates)
                rcv_ok = True
                shared = [d for d in new_dates if d not in old_dates]
                given = [d for d in old_dates if d not in new_dates]
                # 每个新日期 +1, 每个旧日期 -1 (同日 c 已有则不变)
                cnt = defaultdict(int)
                for d in shared: cnt[d] += 0
                for d in given: cnt[d] -= 1
                for d in [x for x in new_dates if x not in old_dates]: cnt[d] += 1
                for d, dv in cnt.items():
                    if len(day_members[d]) + dv > max_cap or len(day_members[d]) + dv < min_cap:
                        rcv_ok = False; break
                if not (rel_ok and rcv_ok):
                    continue
                ev = sum(-removal_gain(d, c) if d in given else 0.0 for d in old_dates) + \
                     sum(insertion_cost(d, c) or 1e9 for d in shared)
                if best_ev is None or ev < best_ev[0]:
                    best_ev = (ev, given, shared)
            if best_ev is None:
                continue
            delta, given, shared = best_ev
            if delta < -1e-9 or rng.random() < 0.05:
                accepted += 1
                for d in given:
                    day_members[d].discard(c); sched[c].discard(d)
                for d in shared:
                    day_members[d].add(c); sched[c].add(d)
                touched = set(given) | set(shared)
                # 精确重排受影响日 (CP-SAT, 短限时)
                for d in touched:
                    routes[d] = _exact_open_tsp(sorted(day_members[d]), D, 10)
                if its % 20 == 0:
                    cur_km = total_km(routes, D)   # 周期性精确校准
                else:
                    cur_km += delta                # 增量近似 (仅影响接受阈值)
                if cur_km < best_km - 1e-9:
                    best_km = cur_km
                    best_routes = {dd: list(r) for dd, r in routes.items()}
                    if keep_history:
                        snapshot()                 # 结构保证: SP 输入列池必含最优状态 (评审整改)
                if keep_history and its % max(1, collect_every) == 0:
                    snapshot()

        if keep_history:
            snapshot()
        days = best_routes
        return AlgoResult(
            name=self.name, days=days, km=round(best_km, 3),
            capacity_ok=check_capacity(days, max_cap, min_cap),
            metadata={"iters": its, "accepted": accepted,
                      "r2_ok": len(check_r2prime(days)) == 0,
                      "columns": len(columns), "_columns": columns})
