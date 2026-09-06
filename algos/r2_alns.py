# -*- coding: utf-8 -*-
"""R2'-ALNS: 星期几一致约束下的原生搜索层 (2026-09-05).

语义 (用户澄清): 门店可以从周一改到周二, 但改了就全月一致 (第1234周都在周二).
即 σ: store → weekday 可重指派, 每店在其星期几的槽位中选 f_c 个日期.

核心算子 (保持 R2' + 走廊):
  MOVE: 选店 c, 枚举目标星期几 w' (含 w 自身), 每个目标星期几取其 (合同,相位) 槽位集
        (move_candidates, combo_mode="contract"; "free"=旧口径全组合, 仅审计), 走廊校验后取最优插入组合;
  估价: 移除增益/插入代价 = 2-NN 三角恒等式估计 (纯 (成员集, D) 函数, 次序无关 → 确定性).
  确定性方案 (同种子逐位复现红线): 搜索期不含任何求解器调用 — CP-SAT 实测不可作确定性路由源
        (8-worker 证明最优时平局次序仍跨次抖动 → delta/接受判据发散; 1-worker/确定性时限在
        ≥29 店日不证最优或分钟级)。终局对 best day-sets 做一次状态门控精确重排: 仅接受
        PROVEN OPTIMAL 的路线, 最优成本唯一 → 汇报 km 逐位确定 (平局次序可变, 不入门槛)。

输出: 终局最优状态的 23 条日列 (状态门控精确重排, 全部 R2'-合法) → 供 SP(r2_prime) 重组.
"""
import random, itertools, time
from collections import defaultdict
import numpy as np
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_capacity
from algos.registry import register
from algos.tsp_engine import _exact_open_tsp_status
from algos.sp_matheuristic import check_r2prime, _wd
from core.contract import contract_of, contract_slot_dates, check_contract


def move_candidates(c, sched_dates, wd_g, contracts, combo_mode, rng):
    """MOVE 候选生成 (纯函数, 确定性可测).
    contract: 每目标星期几恰一个合同槽位集 (v1 全组合=C(k,f) 是月频次错误, 已废);
    free: 旧口径随机全组合 (仅供 Phase B 旧账复现审计). 返回 [(weekday, 新日期集)]."""
    old = set(sched_dates)
    out = []
    kappa, phi = contracts[c]
    for w2, slots in wd_g.items():
        if combo_mode == "contract":
            new_ds = contract_slot_dates(kappa, phi, slots)
        else:
            f = len(old)
            if f > len(slots):
                continue
            new_ds = set(rng.choice(list(itertools.combinations(slots, f)))) \
                if len(slots) > f else set(slots)
        if new_ds and new_ds != old:
            out.append((w2, new_ds))
    return out


@register
class R2ALNS(Algorithm):
    name = "r2_alns"

    def solve(self, data, D, time_budget=300, seed=42, collect_every=25,
              keep_history=True, init_days=None, combo_mode="contract",
              iteration_budget=None, wall_time_budget=None, final_reroute=True):
        rng = random.Random(seed)
        D = np.asarray(D)
        dates = list(data.dates)
        wd_g = defaultdict(list)
        for dd in dates:
            wd_g[_wd(dd)].append(dd)
        contracts = contract_of(data.days_orig, dates)
        min_cap, max_cap = data.min_daily_capacity, data.max_daily_capacity

        sched = {}                       # store -> set(dates)
        day_members = defaultdict(set)   # date -> stores
        _src = init_days if init_days else data.days_orig
        for dd, seq in _src.items():
            for c in seq:
                sched.setdefault(c, set()).add(dd)
                day_members[dd].add(c)

        def nn2(c, members):
            """c 在 members 中按距离最近的两个店 (距离平局以店号升序破, 确定性)."""
            rest = sorted(members - {c})
            if not rest:
                return None, None
            if len(rest) == 1:
                return rest[0], None
            srt = sorted(rest, key=lambda j: (float(D[c][j]), j))
            return srt[0], srt[1]

        def removal_gain(dd, c):
            """移除 c 的估计里程增益 (正=变短). 2-NN 三角恒等式, O(day), 次序无关."""
            x, y = nn2(c, day_members[dd])
            if x is None:
                return -1e9
            if y is None:
                return float(D[c][x])
            return float(D[c][x]) + float(D[c][y]) - float(D[x][y])

        def insertion_cost(dd, c):
            """插入 c 的估计代价: x=c 最近店, y=x 次近店, 三角恒等式, O(day), 次序无关."""
            members = day_members[dd]
            if not members:
                return None
            x, _ = nn2(c, members)
            y, _ = nn2(x, members)
            if y is None:
                return float(D[c][x])
            return float(D[c][x]) + float(D[c][y]) - float(D[x][y])

        def _nn_chain(members):
            rest = sorted(members)
            cur = rest[0]
            unv = set(rest[1:])
            out = [cur]
            while unv:
                nxt = min(unv, key=lambda j: (float(D[cur][j]), j))
                out.append(nxt)
                unv.discard(nxt)
                cur = nxt
            return out

        def day_km_est(members):
            """单日估计里程: NN 链 + 2-opt 收敛 (自最小店号起, 距离平局店号升序破; 确定性).
            2-opt 后与真 km 排序高度一致 (纯 2-NN 三角和实测使 proxy 最优偏真 +30km)."""
            if len(members) <= 1:
                return 0.0
            seq = _nn_chain(members)
            n = len(seq)
            for _ in range(30):
                imp = False
                for i in range(1, n - 1):
                    for j in range(i + 1, n):
                        old = float(D[seq[i - 1]][seq[i]]) + \
                              (float(D[seq[j]][seq[j + 1]]) if j + 1 < n else 0.0)
                        new = float(D[seq[i - 1]][seq[j]]) + \
                              (float(D[seq[i]][seq[j + 1]]) if j + 1 < n else 0.0)
                        if new < old - 1e-12:
                            seq[i:j + 1] = seq[i:j + 1][::-1]
                            imp = True
                if not imp:
                    break
            return sum(float(D[seq[k]][seq[k + 1]]) for k in range(n - 1))
        cur_km = 0.0                      # 估计里程簿记 (NN 链成本, 与真值强相关)
        for dd in dates:
            cur_km += day_km_est(day_members[dd])
        best_km = cur_km
        best_routes = {dd: sorted(day_members[dd]) for dd in dates}
        columns = []                      # 终局列池: [(date, route, km)]
        its = accepted = 0
        # 搜索由显式迭代预算驱动；time_budget 仅保留为旧 API 的迭代预算换算。
        if iteration_budget is None:
            its_budget = max(1, int(time_budget * 600))
        else:
            its_budget = int(iteration_budget)
            if its_budget < 0:
                raise ValueError("iteration_budget must be non-negative")
        if wall_time_budget is not None:
            wall_time_budget = float(wall_time_budget)
            if wall_time_budget < 0:
                raise ValueError("wall_time_budget must be non-negative")
            wall_deadline = time.perf_counter() + wall_time_budget
        else:
            wall_deadline = None
        search_t0 = time.perf_counter()
        stores = sorted(sched)
        while its < its_budget and (
            wall_deadline is None or time.perf_counter() < wall_deadline
        ):
            its += 1
            c = rng.choice(stores)
            old_dates = sorted(sched[c], key=str)
            best_ev = None
            for w2, new_ds in move_candidates(c, sched[c], wd_g, contracts, combo_mode, rng):
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
                if its % 50 == 0:
                    cur_km = sum(day_km_est(day_members[dd]) for dd in dates)   # 周期校准
                else:
                    cur_km += delta                # 增量簿记 (仅影响接受/最优阈值)
                if cur_km < best_km - 1e-9:
                    best_km = cur_km
                    best_routes = {dd: sorted(day_members[dd]) for dd in dates}
        # 终局状态门控精确重排: 只接受 PROVEN OPTIMAL 的路线 (最优成本唯一 → km 确定).
        # 日历生成模式可跳过此步骤, 让下游算法按自己的 TSP 口径重排。
        if final_reroute:
            reroute_statuses = {}
            for dd in dates:
                r_opt, st, _ms = _exact_open_tsp_status(list(best_routes[dd]), D, 30)
                reroute_statuses[str(dd)] = st
                if st == "OPTIMAL":
                    best_routes[dd] = r_opt
        else:
            reroute_statuses = {str(dd): "SKIPPED" for dd in dates}

        # Private columns retain full precision for downstream LP bounds.
        columns = [(dd, list(best_routes[dd]), day_km(best_routes[dd], D))
                   for dd in dates]
        days = best_routes
        return AlgoResult(
            name=self.name, days=days, km=round(total_km(days, D), 3),
            capacity_ok=check_capacity(days, max_cap, min_cap),
            metadata={"iters": its, "iteration_budget": its_budget,
                      "accepted": accepted,
                      "legacy_time_budget_sec": float(time_budget),
                      "wall_time_budget_sec": wall_time_budget,
                      "search_elapsed_sec": round(time.perf_counter() - search_t0, 6),
                      "r2_ok": len(check_r2prime(days)) == 0,
                      "contract_ok": len(check_contract(days, contracts, dates)) == 0,
                      "reroute_statuses": reroute_statuses,
                      "all_optimal": all(s == "OPTIMAL" for s in reroute_statuses.values()),
                      "final_reroute": bool(final_reroute),
                      "columns": len(columns), "_columns": columns})
