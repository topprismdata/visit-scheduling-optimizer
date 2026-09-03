# -*- coding: utf-8 -*-
"""ALNS v4 — 通用稳定化 / 增量重优化 / 帕累托精修器.

定位: 通用稳定化与帕累托双旋钮精修层 (Universal Stabilizer & Pareto Tuner).
      任意算法输出 X (或历史计划) 均可作为起点 start.
      以现计划 X⁰ (incumbent) 为锚点, 在"里程"、"换日成本 (稳定性)"和"每日工作量均衡度"三者间求帕累托最优.

目标函数:
  min  J = 里程 + λ · Δ(改动店数) + μ · Var(每日拜访量)

三维帕累托旋钮:
  - 日内顺序优化: 免费 (Δ=0, Var=0, 只要降低里程就采纳)
  - λ 旋钮 (稳定性): 每挪 1 店的最低里程收益门槛 (km/店). λ 大则倾向贴紧现计划
  - μ 旋钮 (均衡度): 每日拜访量方差的惩罚权重 (km/var). μ 大则强行平摊每天店数, 压缩极差

参考:
  - Groër, Sandholzer, Pisinger (2009) "The Consistent Vehicle Routing Problem", Trans. Sci.
  - Ritzinger, Puchinger et al. (2016) Dynamic VRP & Re-optimization Survey
  - 工业应用: 销售拜访路线平衡 (Workload Balancing in Period Routing)
"""
import time, math, random
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_freq
from algos.registry import register
from algos.alns_v3 import two_opt, best_insert, worst_edge


@register
class ALNSv4(Algorithm):
    name = "alns_v4"

    def solve(self, data, D,
              incumbent=None,
              start=None,
              time_budget=300,
              zone_of=None,
              seed=42,
              lam=5.0,
              mu=0.0,
              max_changes=None,
              same_weekday_only=True):
        """
        参数:
          incumbent: 参照解 X⁰ {date: [store_indices]}, 默认 SRP 现计划 (data.days_orig)
          start: 起点解 {date: [store_indices]}, 默认=incumbent. 可是任意算法产出
          time_budget: 超时时间(秒)
          lam: λ, 稳定性旋钮. 每增加一个改动店的惩罚成本(km). λ=0 纯里程优化
          mu: μ, 均衡度旋钮. 每日拜访门店数方差的惩罚权重(km/var). μ=0 忽略均衡度
          max_changes: 模式 B 改动店数硬上限 (None 表示不限制)
          same_weekday_only: True 则只允许在同星期几之间挪动(如周一挪周一)
        """
        rng = random.Random(seed)
        dates = list(data.dates)
        num_days = len(dates)

        # 1. 建立锚点 (incumbent) 映射: store -> set(dates)
        inc_raw = incumbent if incumbent is not None else data.days_orig
        inc_dates = {}
        for dd in dates:
            for s in inc_raw.get(dd, []):
                inc_dates.setdefault(s, set()).add(dd)

        # 2. 建立起点 (start) 映射并进行日内快速 2-opt 暖启动 (日内优化免费)
        st_raw = start if start is not None else inc_raw
        tours = {dd: two_opt(list(st_raw.get(dd, [])), D, max_pass=20) for dd in dates}

        # 当前门店到日期的映射
        store_dates = {}
        for dd in dates:
            for s in tours[dd]:
                store_dates.setdefault(s, set()).add(dd)

        # 判定当前与锚点相比, 被改动的门店集合 (日期集合不完全一致的门店)
        all_stores = set(inc_dates.keys()) | set(store_dates.keys())
        moved = {s for s in all_stores if store_dates.get(s, set()) != inc_dates.get(s, set())}

        # 3. 计算初始里程、初始方差与初始目标函数
        day_kms = {dd: day_km(tours[dd], D) for dd in dates}
        cur_km = sum(day_kms.values())

        # 每日工作量均衡度指标
        total_visits = sum(len(tours[dd]) for dd in dates)
        avg_visits = total_visits / max(1, num_days)
        cur_var = sum((len(tours[dd]) - avg_visits) ** 2 for dd in dates) / max(1, num_days)

        cur_J = cur_km + lam * len(moved) + mu * cur_var

        # 记录基线数据用于元数据汇报
        plan_km = total_km({dd: list(inc_raw.get(dd, [])) for dd in dates}, D)
        start_km = cur_km

        best_tours = {dd: list(tours[dd]) for dd in dates}
        best_km = cur_km
        best_moved = set(moved)
        best_var = cur_var
        best_J = cur_J

        # 星期几到日期的映射
        def get_wd(d):
            return d.weekday() if hasattr(d, "weekday") else 0
        wd_map = {}
        for dd in dates:
            wd_map.setdefault(get_wd(dd), []).append(dd)

        # 模拟退火参数设置
        t0 = time.time()
        deadline = t0 + time_budget
        edges = sum(max(0, len(tours[dd]) - 1) for dd in dates) or 1
        avg_edge = cur_km / edges
        T0 = max(0.5, avg_edge * 1.5)
        Tend = max(0.01, avg_edge * 0.02)

        ops = ['oropt', 'shift', 'swap']
        w = {o: 1.0 for o in ops}

        def pick_op():
            tw = sum(w.values())
            r = rng.random() * tw
            for o in ops:
                r -= w[o]
                if r <= 0:
                    return o
            return ops[0]

        its = 0
        while time.time() < deadline:
            its += 1
            el = (time.time() - t0) / max(1e-9, (deadline - t0))
            T = T0 * ((Tend / T0) ** el)
            op = pick_op()

            if op == 'oropt':
                # 日内微调: 免费, Δ_moved = 0, Δ_var = 0
                dd = rng.choice(dates)
                t = tours[dd]
                if len(t) <= 3:
                    continue
                new_t = two_opt(t, D, max_pass=6)
                new_dkm = day_km(new_t, D)
                diff = new_dkm - day_kms[dd]
                if diff < -1e-9:
                    tours[dd] = new_t
                    cur_km += diff
                    cur_J += diff
                    day_kms[dd] = new_dkm
                    w['oropt'] = min(5.0, w['oropt'] + 0.1)
                    if cur_J < best_J:
                        best_J = cur_J
                        best_km = cur_km
                        best_var = cur_var
                        best_tours = {d: list(tours[d]) for d in dates}
                        best_moved = set(moved)
                else:
                    w['oropt'] = max(0.2, w['oropt'] - 0.01)

            elif op == 'shift':
                # 跨日单店移动: store c 从 dd1 挪到 dd2
                dd1 = rng.choice(dates)
                t1 = tours[dd1]
                if len(t1) <= 3:
                    continue
                c = worst_edge(t1, D, zone_of=zone_of, cross_pref=False)
                if c is None or c not in t1:
                    c = rng.choice(t1)

                wday = get_wd(dd1)
                candidates = [d for d in (wd_map[wday] if same_weekday_only else dates)
                              if d != dd1 and c not in tours[d]]
                if not candidates:
                    continue

                # 若启用均衡度调节, 优先挑选目前店数较少的目标日
                if mu > 0 and len(candidates) > 1:
                    candidates.sort(key=lambda d: len(tours[d]))
                    dd2 = candidates[0] if rng.random() < 0.7 else rng.choice(candidates)
                else:
                    dd2 = rng.choice(candidates)

                t2 = tours[dd2]

                # 尝试从 dd1 移除 c, 插入 dd2
                new_t1 = [x for x in t1 if x != c]
                if len(new_t1) < 2:
                    continue
                new_t1 = two_opt(new_t1, D, max_pass=6)
                new_t2, _ = best_insert(t2, c, D)
                new_t2 = two_opt(new_t2, D, max_pass=6)

                new_dkm1 = day_km(new_t1, D)
                new_dkm2 = day_km(new_t2, D)
                delta_km = (new_dkm1 + new_dkm2) - (day_kms[dd1] + day_kms[dd2])

                # 1. 稳定性改动数变化
                c_dates_after = (store_dates.get(c, set()) - {dd1}) | {dd2}
                c_inc_dates = inc_dates.get(c, set())
                was_moved = (c in moved)
                will_be_moved = (c_dates_after != c_inc_dates)
                delta_moved = (1 if will_be_moved else 0) - (1 if was_moved else 0)

                new_moved_cnt = len(moved) + delta_moved
                if max_changes is not None and new_moved_cnt > max_changes:
                    continue

                # 2. 均衡度方差变化 (O(1) 增量精确计算)
                # dd1 店数 len(t1) -> len(t1)-1, dd2 店数 len(t2) -> len(t2)+1
                delta_var = (2.0 * (len(t2) - len(t1) + 1)) / max(1, num_days)

                # 综合帕累托目标增量
                delta_J = delta_km + lam * delta_moved + mu * delta_var
                if delta_J < 0 or rng.random() < math.exp(-delta_J / max(1e-9, T)):
                    tours[dd1] = new_t1
                    tours[dd2] = new_t2
                    day_kms[dd1] = new_dkm1
                    day_kms[dd2] = new_dkm2
                    cur_km += delta_km
                    cur_var += delta_var
                    cur_J += delta_J
                    store_dates[c] = c_dates_after
                    if will_be_moved:
                        moved.add(c)
                    else:
                        moved.discard(c)

                    w['shift'] = min(5.0, w['shift'] + (0.15 if delta_J < 0 else 0.05))
                    if cur_J < best_J:
                        best_J = cur_J
                        best_km = cur_km
                        best_var = cur_var
                        best_tours = {d: list(tours[d]) for d in dates}
                        best_moved = set(moved)
                else:
                    w['shift'] = max(0.2, w['shift'] - 0.02)

            elif op == 'swap':
                # 跨日两店互换: 店数不发生变化, 因此 delta_var 严格等于 0!
                dd1 = rng.choice(dates)
                t1 = tours[dd1]
                if len(t1) <= 3:
                    continue
                wday = get_wd(dd1)
                candidates = [d for d in (wd_map[wday] if same_weekday_only else dates) if d != dd1 and len(tours[d]) >= 2]
                if not candidates:
                    continue
                dd2 = rng.choice(candidates)
                t2 = tours[dd2]

                c1 = rng.choice(t1)
                valid_c2 = [x for x in t2 if x not in t1 and c1 not in t2]
                if not valid_c2:
                    continue
                c2 = rng.choice(valid_c2)

                new_t1 = [c2 if x == c1 else x for x in t1]
                new_t2 = [c1 if x == c2 else x for x in t2]
                new_t1 = two_opt(new_t1, D, max_pass=6)
                new_t2 = two_opt(new_t2, D, max_pass=6)

                new_dkm1 = day_km(new_t1, D)
                new_dkm2 = day_km(new_t2, D)
                delta_km = (new_dkm1 + new_dkm2) - (day_kms[dd1] + day_kms[dd2])

                # 计算 c1, c2 两店 moved 状态变更
                c1_after = (store_dates.get(c1, set()) - {dd1}) | {dd2}
                c2_after = (store_dates.get(c2, set()) - {dd2}) | {dd1}
                c1_inc = inc_dates.get(c1, set())
                c2_inc = inc_dates.get(c2, set())

                delta_moved = 0
                c1_will = (c1_after != c1_inc)
                if c1_will != (c1 in moved):
                    delta_moved += (1 if c1_will else -1)
                c2_will = (c2_after != c2_inc)
                if c2_will != (c2 in moved):
                    delta_moved += (1 if c2_will else -1)

                new_moved_cnt = len(moved) + delta_moved
                if max_changes is not None and new_moved_cnt > max_changes:
                    continue

                # swap 不改变各日总店数, delta_var = 0
                delta_J = delta_km + lam * delta_moved
                if delta_J < 0 or rng.random() < math.exp(-delta_J / max(1e-9, T)):
                    tours[dd1] = new_t1
                    tours[dd2] = new_t2
                    day_kms[dd1] = new_dkm1
                    day_kms[dd2] = new_dkm2
                    cur_km += delta_km
                    cur_J += delta_J
                    store_dates[c1] = c1_after
                    store_dates[c2] = c2_after
                    if c1_will: moved.add(c1)
                    else: moved.discard(c1)
                    if c2_will: moved.add(c2)
                    else: moved.discard(c2)

                    w['swap'] = min(5.0, w['swap'] + (0.15 if delta_J < 0 else 0.05))
                    if cur_J < best_J:
                        best_J = cur_J
                        best_km = cur_km
                        best_var = cur_var
                        best_tours = {d: list(tours[d]) for d in dates}
                        best_moved = set(moved)
                else:
                    w['swap'] = max(0.2, w['swap'] - 0.02)

        # 最终精修与产出
        final_tours = {dd: two_opt(best_tours[dd], D, max_pass=30) for dd in dates}
        final_km = total_km(final_tours, D)

        final_dates = {}
        for dd in dates:
            for s in final_tours[dd]:
                final_dates.setdefault(s, set()).add(dd)

        final_moved = {s for s in all_stores if final_dates.get(s, set()) != inc_dates.get(s, set())}

        # 统计最终每日拜访量分布
        daily_counts = [len(final_tours[dd]) for dd in dates]
        min_v = min(daily_counts)
        max_v = max(daily_counts)
        spread = max_v - min_v
        final_var = sum((c - avg_visits) ** 2 for c in daily_counts) / max(1, num_days)

        changes = []
        for s in sorted(final_moved):
            code = data.codes[s] if s < len(data.codes) else str(s)
            i_ds = sorted([d.isoformat() if hasattr(d, "isoformat") else str(d) for d in inc_dates.get(s, set())])
            n_ds = sorted([d.isoformat() if hasattr(d, "isoformat") else str(d) for d in final_dates.get(s, set())])
            changes.append({"store": code, "inc_dates": i_ds, "new_dates": n_ds})

        return AlgoResult(
            name=self.name,
            days=final_tours,
            km=final_km,
            metadata={
                "changes": changes,
                "delta": len(final_moved),
                "lam": lam,
                "mu": mu,
                "plan_km": round(plan_km, 1),
                "start_km": round(start_km, 1),
                "v4_km": round(final_km, 1),
                "min_visits": min_v,
                "max_visits": max_v,
                "spread": spread,
                "variance": round(final_var, 2),
                "daily_counts": daily_counts,
                "its": its,
                "best_J": round(best_J, 2),
            }
        )
