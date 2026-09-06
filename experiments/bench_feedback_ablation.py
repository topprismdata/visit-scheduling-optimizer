# -*- coding: utf-8 -*-
"""反馈耦合消融实验 (Ablation Study): 严格在 [K_min, K_max] = [23, 35] 业务走廊内.

对比三大算法家族中"无反馈" vs "带反馈耦合"的净收益:
  1. ALNS 家族:
     - v1 (无反馈 / 把 TSP 当秤): 盲选移店, 每次评估冷启动 _nn2opt_open 从头重算
     - v3 (反馈耦合 / 把 TSP 当眼睛): Tour-carrying 路径携带 + worst-edge 路径感知拆除 + 增量插入
  2. HGS 家族:
     - Blind (无反馈): 盲目交叉/变异, 每次评估从头重解 TSP
     - Feedback (反馈耦合): 路径感知保留 + tour-carrying 增量打磨
  3. SP / CG 家族:
     - Static SP (无反馈 / 一次性): 静态路线池一次性求解 IP (rounds=0)
     - Closed-Loop CG (对偶闭环反馈): LP -> 对偶 u_c/w_d 反馈定价子问题 -> 产生负约简成本列回灌 -> 迭代至收敛
"""
import sys, os, time, json, random, math
from copy import deepcopy
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from data.loader import load_plan, load_line
from core.base import Algorithm, AlgoResult
from core.metric import day_km, total_km, check_capacity
from algos.tsp_engine import _nn2opt_open
from algos.alns_v3 import ALNSv3, two_opt, best_insert, worst_edge
from algos.hgs_pvrp import HGSPVRP, _greedy_warm, _sa_improve, _diversity, _counts, _Ind, _ins_deltas, _removal_delta
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, column_generate, sp_solve_ip, sp_solve_lp

pv = load_plan(); data = load_line(pv, '09')
D = np.load('output/road_dist_09.npy')
dates = list(data.dates)
min_daily = data.min_daily_capacity  # 23
max_daily = data.max_daily_capacity  # 35
SRP_BASE = 1116.0

print(f"=== 反馈耦合消融实验基准 (09线, 业务走廊 [{min_daily} ~ {max_daily}] 店) ===", flush=True)

# -----------------------------------------------------------------------------
# 1. ALNS v1 (无反馈 / 把 TSP 当秤) 实现 (严格走廊加限)
# -----------------------------------------------------------------------------
class ALNS_v1_NoFeedback(Algorithm):
    name = "alns_v1_nofeedback"
    def solve(self, data, D, time_budget=60, seed=42):
        rng = random.Random(seed)
        tours = {dd: _nn2opt_open(list(data.days_orig[dd]), D) for dd in dates}
        t0 = time.time(); deadline = t0 + time_budget
        for _ in range(30):
            if time.time() > deadline: break
            imp = False
            for dd1 in dates:
                if time.time() > deadline: break
                for dd2 in dates:
                    if time.time() > deadline: break
                    if dd1 == dd2: continue
                    s1, s2 = tours[dd1], tours[dd2]
                    if len(s1) <= min_daily or len(s2) >= max_daily: continue
                    for c in list(s1):
                        if c in s2: continue
                        ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
                        # 核心特征: 盲目从头重算整天 TSP 评估
                        old_c = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
                        new_c = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
                        if new_c < old_c - 0.05:
                            tours[dd1] = _nn2opt_open(ns1, D); tours[dd2] = _nn2opt_open(ns2, D)
                            imp = True; break
                    if imp: break
                if imp: break
            if not imp: break
            
        cur = total_km(tours, D)
        best = cur; best_t = {dd: list(tours[dd]) for dd in dates}
        its = 0
        while time.time() < deadline:
            its += 1
            dd1, dd2 = rng.choice(dates), rng.choice(dates)
            if dd1 == dd2: continue
            s1, s2 = tours[dd1], tours[dd2]
            if len(s1) <= min_daily or len(s2) >= max_daily: continue
            c = rng.choice(s1)
            if c in s2: continue
            ns1 = [x for x in s1 if x != c]; ns2 = s2 + [c]
            # 无反馈: 冷启动评估
            old_c = day_km(_nn2opt_open(s1, D), D) + day_km(_nn2opt_open(s2, D), D)
            new_c = day_km(_nn2opt_open(ns1, D), D) + day_km(_nn2opt_open(ns2, D), D)
            diff = new_c - old_c
            if diff < 0 or rng.random() < 0.05:  # 简单固定退火概率
                tours[dd1] = _nn2opt_open(ns1, D); tours[dd2] = _nn2opt_open(ns2, D)
                cur += diff
                if cur < best - 1e-6:
                    best = cur; best_t = {dd: list(tours[dd]) for dd in dates}
        final = {dd: _nn2opt_open(best_t[dd], D) for dd in dates}
        cap_ok = check_capacity(final, max_daily, min_daily)
        return AlgoResult(name=self.name, days=final, km=total_km(final, D),
                          capacity_ok=cap_ok, metadata={"iters": its, "type": "NoFeedback"})

# -----------------------------------------------------------------------------
# 2. HGS (无反馈版本: 盲目交叉, 冷启动重评)
# -----------------------------------------------------------------------------
class HGS_NoFeedback(Algorithm):
    name = "hgs_nofeedback"
    def solve(self, data, D, time_budget=60, seed=42, pop_size=12):
        rng = random.Random(seed)
        t0 = time.time(); deadline = t0 + time_budget
        base = {dd: _nn2opt_open(list(data.days_orig[dd]), D) for dd in dates}
        k_true = _counts(base, dates)
        pool = [{dd: list(base[dd]) for dd in dates}]
        # 初始盲扰动
        for _ in range(min(5, pop_size // 2)):
            pert = deepcopy(base)
            for _ in range(20):
                dd1 = rng.choice(dates)
                if len(pert[dd1]) <= min_daily: continue
                c = rng.choice(pert[dd1])
                tgts = [x for x in dates if c not in pert[x] and len(pert[x]) < max_daily]
                if not tgts: continue
                dd2 = rng.choice(tgts)
                pert[dd1].remove(c); pert[dd2].append(c)
            pert = {dd: _nn2opt_open(pert[dd], D) for dd in dates}
            pool.append(pert)
        best_t = deepcopy(base); best_km = total_km(best_t, D)
        gens = 0
        while time.time() < deadline:
            gens += 1
            p1, p2 = rng.choice(pool), rng.choice(pool)
            child = {}
            for dd in dates:
                child[dd] = list(p1[dd] if rng.random() < 0.5 else p2[dd])
            # 守恒兜底
            cnt = _counts(child, dates)
            removed = []
            for c, k in k_true.items():
                d = cnt.get(c, 0) - k
                if d > 0:
                    for _ in range(d):
                        cand_days = [dd for dd in dates if c in child[dd] and len(child[dd]) > min_daily]
                        if cand_days:
                            child[rng.choice(cand_days)].remove(c)
                elif d < 0:
                    removed.extend([c] * (-d))
            for c in removed:
                valid_days = [dd for dd in dates if c not in child[dd] and len(child[dd]) < max_daily]
                if valid_days:
                    child[rng.choice(valid_days)].append(c)
            # 无反馈教育: 冷启动重新排序 (没有路径携带)
            child = {dd: _nn2opt_open(child[dd], D) for dd in dates}
            km = total_km(child, D)
            pool.append(child)
            pool.sort(key=lambda t: total_km(t, D))
            pool = pool[:pop_size]
            if km < best_km - 1e-6:
                best_km = km; best_t = deepcopy(child)
        cap_ok = check_capacity(best_t, max_daily, min_daily)
        return AlgoResult(name=self.name, days=best_t, km=best_km,
                          capacity_ok=cap_ok, metadata={"gens": gens, "type": "NoFeedback"})

# -----------------------------------------------------------------------------
# 3. SP 静态一次性 (无对偶闭环定价反馈)
# -----------------------------------------------------------------------------
def solve_sp_static_oneshot(pool, D, dates, data):
    """一次性求解静态池的集合划分整数规划 (rounds=0, 零列生成定价反馈)."""
    t0 = time.perf_counter()
    k_c = dict(_counts(data.days_orig, dates))
    legal = dedupe_pool(pool, max_daily=max_daily, min_daily=min_daily)
    lb, _ = sp_solve_lp(dates, k_c, legal)
    km, days = sp_solve_ip(dates, k_c, legal, timeout_s=60)
    dur = time.perf_counter() - t0
    cap_ok = check_capacity(days, max_daily, min_daily) if days else False
    gap = round((km - lb) / km * 100, 2) if (km and lb) else None
    return AlgoResult(name="sp_static_oneshot", days=days or {}, km=km or float("inf"),
                      capacity_ok=cap_ok, elapsed=dur,
                      metadata={"lb": lb, "gap_pct": gap, "pool": len(legal), "type": "NoFeedback"})

# =============================================================================
# 执行全量消融实验: 60s 和 300s 两个时间档位
# =============================================================================
TIME_TIERS = [60, 300]
ablation_records = []

# 预先构建基础合规池 (用于 SP 消融)
pool_raw = []
dmap = {str(d): d for d in dates}
if os.path.exists('output/sp_pool_09.json'):
    pool_raw += [(dmap[p[0]], p[1], p[2]) for p in json.load(open('output/sp_pool_09.json'))]
import glob
for f in glob.glob('output/sp_pool_09_one_*.json'):
    pool_raw += [(dmap[p[0]], p[1], p[2]) for p in json.load(open(f))]
base_legal_pool = dedupe_pool(pool_raw, max_daily=max_daily, min_daily=min_daily)

for budget in TIME_TIERS:
    print(f"\n========================================================", flush=True)
    print(f">>> 开始时间预算档位: {budget} 秒 消融对决", flush=True)
    print(f"========================================================", flush=True)
    
    # ---------------- 家族 1: ALNS ----------------
    print(f"\n[ALNS 家族对决: v1 无反馈 vs v3 反馈耦合]", flush=True)
    t0 = time.time()
    r_v1 = ALNS_v1_NoFeedback().solve(data, D, time_budget=budget, seed=42)
    r_v1.elapsed = time.time() - t0
    
    t0 = time.time()
    r_v3 = ALNSv3().solve(data, D, time_budget=budget, seed=42)
    r_v3.elapsed = time.time() - t0
    
    delta_alns = round((r_v1.km - r_v3.km) / r_v1.km * 100, 2)
    print(f"  ALNS v1 (无反馈/把TSP当秤) : {r_v1.km:>6.1f} km | 迭代: {r_v1.metadata['iters']:>5} 次 | 耗时: {r_v1.elapsed:>5.1f}s | 容量合规: {r_v1.capacity_ok}", flush=True)
    print(f"  ALNS v3 (反馈耦合/带路径)   : {r_v3.km:>6.1f} km | 迭代: {r_v3.metadata['iters']:>5} 次 | 耗时: {r_v3.elapsed:>5.1f}s | 容量合规: {r_v3.capacity_ok}", flush=True)
    print(f"  >> 反馈耦合带来的净收益    : 净省 {r_v1.km - r_v3.km:.1f} km (额外削减 -{delta_alns}%)! 迭代吞吐暴增 {r_v3.metadata['iters']/max(1,r_v1.metadata['iters']):.0f} 倍!", flush=True)
    
    ablation_records.append({
        "family": "ALNS", "budget": budget,
        "no_feedback": {"km": round(r_v1.km, 1), "iters": r_v1.metadata['iters'], "sec": round(r_v1.elapsed, 1)},
        "feedback":    {"km": round(r_v3.km, 1), "iters": r_v3.metadata['iters'], "sec": round(r_v3.elapsed, 1)},
        "saved_km": round(r_v1.km - r_v3.km, 1), "pct_gain": delta_alns
    })

    # ---------------- 家族 2: HGS ----------------
    print(f"\n[HGS 家族对决: Blind 无反馈 vs 路径感知反馈耦合]", flush=True)
    t0 = time.time()
    r_hgs_blind = HGS_NoFeedback().solve(data, D, time_budget=budget, seed=42)
    r_hgs_blind.elapsed = time.time() - t0
    
    t0 = time.time()
    r_hgs_fb = HGSPVRP().solve(data, D, time_budget=budget, seed=42)
    r_hgs_fb.elapsed = time.time() - t0
    
    delta_hgs = round((r_hgs_blind.km - r_hgs_fb.km) / r_hgs_blind.km * 100, 2)
    print(f"  HGS Blind (无反馈/纯重排)  : {r_hgs_blind.km:>6.1f} km | 代数: {r_hgs_blind.metadata['gens']:>5} 代 | 耗时: {r_hgs_blind.elapsed:>5.1f}s | 容量合规: {r_hgs_blind.capacity_ok}", flush=True)
    print(f"  HGS-PVRP (路径感知反馈)    : {r_hgs_fb.km:>6.1f} km | 代数: {r_hgs_fb.metadata['gens']:>5} 代 | 耗时: {r_hgs_fb.elapsed:>5.1f}s | 容量合规: {r_hgs_fb.capacity_ok}", flush=True)
    print(f"  >> 反馈耦合带来的净收益    : 净省 {r_hgs_blind.km - r_hgs_fb.km:.1f} km (额外削减 -{delta_hgs}%)!", flush=True)
    
    ablation_records.append({
        "family": "HGS", "budget": budget,
        "no_feedback": {"km": round(r_hgs_blind.km, 1), "iters": r_hgs_blind.metadata['gens'], "sec": round(r_hgs_blind.elapsed, 1)},
        "feedback":    {"km": round(r_hgs_fb.km, 1), "iters": r_hgs_fb.metadata['gens'], "sec": round(r_hgs_fb.elapsed, 1)},
        "saved_km": round(r_hgs_blind.km - r_hgs_fb.km, 1), "pct_gain": delta_hgs
    })

    # ---------------- 家族 3: SP / CG ----------------
    print(f"\n[SP / CG 家族对决: 静态一次性 SP vs 闭环对偶列生成 CG]", flush=True)
    r_sp_static = solve_sp_static_oneshot(base_legal_pool, D, dates, data)
    
    t0 = time.time()
    r_sp_cg = SPMatheuristic().solve(data, D, time_budget=budget, pool=base_legal_pool, rounds=2,
                                     sa_burst=10.0, top_m=40, col_iter=60,
                                     max_daily=max_daily, min_daily=min_daily)
    r_sp_cg.elapsed = time.time() - t0
    
    delta_sp = round((r_sp_static.km - r_sp_cg.km) / r_sp_static.km * 100, 2)
    print(f"  Static SP (一次性/无对偶反馈): {r_sp_static.km:>6.1f} km | 池大小: {r_sp_static.metadata['pool']:>4} 列 | 耗时: {r_sp_static.elapsed:>5.1f}s | gap: {r_sp_static.metadata['gap_pct']}%", flush=True)
    print(f"  Closed-Loop CG (对偶反馈循环): {r_sp_cg.km:>6.1f} km | 池大小: {r_sp_cg.metadata['pool']:>4} 列 | 耗时: {r_sp_cg.elapsed:>5.1f}s | gap: {r_sp_cg.metadata['gap_pct']}%", flush=True)
    print(f"  >> 对偶反馈带来的净收益    : 净省 {r_sp_static.km - r_sp_cg.km:.1f} km (额外削减 -{delta_sp}%)!", flush=True)
    
    ablation_records.append({
        "family": "SP_CG", "budget": budget,
        "no_feedback": {"km": round(r_sp_static.km, 1), "iters": r_sp_static.metadata['pool'], "sec": round(r_sp_static.elapsed, 1)},
        "feedback":    {"km": round(r_sp_cg.km, 1), "iters": r_sp_cg.metadata['pool'], "sec": round(r_sp_cg.elapsed, 1)},
        "saved_km": round(r_sp_static.km - r_sp_cg.km, 1), "pct_gain": delta_sp
    })

json.dump(ablation_records, open("output/feedback_ablation_benchmark.json", "w"), ensure_ascii=False, indent=2)
print("\n=== 反馈耦合全量消融实验完成! 结果保存在 output/feedback_ablation_benchmark.json ===", flush=True)
