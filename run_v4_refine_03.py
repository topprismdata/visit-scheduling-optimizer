
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from algos.alns_v3 import ALNSv3
from algos.alns_v4 import ALNSv4
from core.metric import check_freq, total_km

pv = load_plan()
data = load_line(pv, '03')
D = load_cached('03').tolist()

# ===== Step 1: v3 自由优化（激进搜索）=====
print("Step 1: ALNS v3 自由优化...")
v3 = ALNSv3()
r3 = v3.solve(data, D, time_budget=20, seed=42)
v3_km = round(r3.km, 1)
print(f"  v3 结果: {v3_km} km")

# v3 改动了多少店
inc_dates = {}
for dd, seq in data.days_orig.items():
    for s in seq: inc_dates.setdefault(s, set()).add(dd)
v3_dates = {}
for dd, seq in r3.days.items():
    for s in seq: v3_dates.setdefault(s, set()).add(dd)
v3_moved = sum(1 for s in inc_dates if v3_dates.get(s,set()) != inc_dates[s])
print(f"  v3 改动店数: {v3_moved} / {len(data.codes)} ({v3_moved/len(data.codes)*100:.1f}%)")

# ===== Step 2: v4 精修（以 v3 为 start，原始计划为 incumbent）=====
print("\nStep 2: V4 精修（v3 解 → 往回拉）")
v4 = ALNSv4()

# 混合策略: 把 v3 解中"不值得的改动"回退
# 方法: 用 v4 以 v3 解为 start, 原始计划为 incumbent, 大 λ 促使回退
results = []
for lam in [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]:
    r = v4.solve(data, D,
                 incumbent=data.days_orig,      # 锚点 = 原始计划
                 start=r3.days,                  # 起点 = v3 激进解
                 time_budget=10, lam=lam, mu=0.0, seed=42)
    ok = check_freq(r.days, data.codes, data.freq)
    m = r.metadata
    # 计算最终解相对原始计划的改动量
    final_dates = {}
    for dd, seq in r.days.items():
        for s in seq: final_dates.setdefault(s, set()).add(dd)
    final_moved = sum(1 for s in inc_dates if final_dates.get(s,set()) != inc_dates[s])

    results.append({
        'lam': lam, 'km': round(r.km, 1), 'delta_vs_orig': final_moved,
        'v3_moved': v3_moved, 'freq_ok': ok,
        'spread': m.get('spread', 0), 'min': m.get('min_visits',0), 'max': m.get('max_visits',0)
    })
    print(f"  \u03bb={lam:<5} km={r.km:8.1f} | \u6539\u52a8={final_moved:>3}\u5e97 ({final_moved/len(data.codes)*100:.1f}%) | \u6781\u5dee={m.get('spread',0):>2} | ok={ok}")

# ===== 汇总 =====
tsp_km = total_km(data.days_orig, D)
print(f"\n=== 03 \u7ebf\u7cbe\u4fee\u94fe\u6761 ===")
print(f"原始计划: {tsp_km:.1f} km (0\u5e97\u6539\u52a8)")
print(f"TSP \u91cd\u6392: 260.8 km (0\u5e97\u6539\u52a8)")
print(f"ALNS v3: {v3_km} km ({v3_moved}\u5e97\u6539\u52a8, {v3_moved/len(data.codes)*100:.1f}%)")
print(f"--- V4 \u7cbe\u4fee\u5e26 (\u4ece v3 \u5f80\u56de\u62c9) ---")
for r in results:
    print(f"  \u03bb={r['lam']:<5} {r['km']:>8.1f} km | \u6539\u52a8 {r['delta_vs_orig']:>3} \u5e97 ({r['delta_vs_orig']/len(data.codes)*100:.1f}%)")

json.dump(results, open('output/v4_refine_03.json', 'w'), indent=1)
print("\nSaved!")
