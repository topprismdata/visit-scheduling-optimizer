
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from algos.alns_v3 import ALNSv3, two_opt
from core.metric import day_km, total_km, check_freq

pv = load_plan()
data = load_line(pv, '03')
D = load_cached('03').tolist()
dates = list(data.dates)

# Step 1: v3 自由优化
print("Step 1: ALNS v3...")
v3 = ALNSv3()
r3 = v3.solve(data, D, time_budget=20, seed=42)
v3_km = r3.km
print(f"  v3: {v3_km:.1f} km")

# 建立原始计划映射
orig_dates = {}   # store -> set(dates)
for dd in dates:
    for s in data.days_orig.get(dd, []):
        orig_dates.setdefault(s, set()).add(dd)

v3_dates = {}     # store -> set(dates)
for dd in dates:
    for s in r3.days.get(dd, []):
        v3_dates.setdefault(s, set()).add(dd)

# 找出被 v3 挪动的店 + v3 改后的路径
moved_stores = []
for s in orig_dates:
    if v3_dates.get(s, set()) != orig_dates[s]:
        moved_stores.append(s)

print(f"  v3 挪动了 {len(moved_stores)} 店")

# Step 2: 对 v3 解做日内 2-opt 精修（得到 v3 的最优路径）
v3_tours = {dd: two_opt(list(r3.days.get(dd, [])), D, max_pass=30) for dd in dates}
v3_day_km = {dd: day_km(v3_tours[dd], D) for dd in dates}

# Step 3: 逐店计算"回退该店"的里程代价
# 对每家被挪的店 s:
#   当前位置: 在 v3 的某天 new_day
#   原始位置: 在原始计划的 orig_day
#   回退 = 从 new_day 移除 s, 加到 orig_day
#   代价 = (new_day 新里程 - new_day 旧里程) + (orig_day 新里程 - orig_day 旧里程)

revert_costs = []
for s in moved_stores:
    # 找 s 在 v3 中的日期
    v3_days_of_s = v3_dates.get(s, set())
    orig_days_of_s = orig_dates.get(s, set())
    
    # 简化: 取 s 在 v3 中的第一个日期和原始计划中的第一个日期
    v3_day = list(v3_days_of_s)[0] if v3_days_of_s else None
    orig_day = list(orig_days_of_s)[0] if orig_days_of_s else None
    
    if v3_day is None or orig_day is None or v3_day == orig_day:
        continue
    
    # 计算 v3_day 移除 s 的代价
    tour_v3 = [x for x in v3_tours[v3_day] if x != s]
    tour_v3_opt = two_opt(tour_v3, D, max_pass=10) if len(tour_v3) >= 2 else tour_v3
    km_after_remove = day_km(tour_v3_opt, D) if len(tour_v3_opt) >= 2 else 0
    km_before_remove = v3_day_km[v3_day]
    cost_remove = km_after_remove - km_before_remove  # 正值 = 变差
    
    # 计算 orig_day 加入 s 的代价
    tour_orig = list(data.days_orig.get(orig_day, []))
    tour_orig_opt = two_opt(tour_orig + [s], D, max_pass=10) if tour_orig else [s]
    km_after_add = day_km(tour_orig_opt, D) if len(tour_orig_opt) >= 2 else 0
    km_before_add = day_km(two_opt(tour_orig, D, max_pass=10), D) if len(tour_orig) >= 2 else 0
    cost_add = km_after_add - km_before_add
    
    total_cost = cost_remove + cost_add  # 正值 = 回退后变差 = v3 挪这店赚了这么多
    
    revert_costs.append({
        'store': s, 'from': str(v3_day), 'to': str(orig_day),
        'revert_cost': round(total_cost, 3),
        'v3_day': v3_day, 'orig_day': orig_day
    })

# 按 revert_cost 升序排列（回退代价最低的先退）
revert_costs.sort(key=lambda x: x['revert_cost'])

print(f"\nStep 2: 贪心回退分析 ({len(revert_costs)} 家可回退的店)")
print(f"{'回退第N家':<10} | {'累计回退':<8} | {'回退该店代价':<12} | {'累计新里程(km)'}")
print("-" * 60)

current_tours = {dd: list(v3_tours[dd]) for dd in dates}
current_km = sum(v3_day_km.values())

pareto = [{
    'reverted': 0, 'pct': 0.0, 'km': round(current_km, 1),
    'description': 'v3 最优（全部保留改动）'
}]

for i, rc in enumerate(revert_costs):
    s = rc['store']
    v3_day = rc['v3_day']
    orig_day = rc['orig_day']
    
    # 执行回退
    if s in current_tours.get(v3_day, []):
        current_tours[v3_day] = [x for x in current_tours[v3_day] if x != s]
        current_tours[v3_day] = two_opt(current_tours[v3_day], D, max_pass=8) if len(current_tours[v3_day]) >= 2 else current_tours[v3_day]
    
    if orig_day in current_tours:
        current_tours[orig_day] = current_tours[orig_day] + [s]
        current_tours[orig_day] = two_opt(current_tours[orig_day], D, max_pass=8)
    
    current_km = sum(day_km(current_tours[dd], D) for dd in dates)
    pct = (i+1) / len(moved_stores) * 100
    
    pareto.append({
        'reverted': i+1, 'pct': round(pct, 1), 'km': round(current_km, 1),
        'description': f'回退 {i+1}/{len(moved_stores)} 店 (代价 {rc["revert_cost"]:.1f}km)'
    })
    
    if (i+1) % 10 == 0 or i == len(revert_costs) - 1 or i < 5:
        print(f"  第{i+1:>3}家 | {pct:>5.1f}% | {rc['revert_cost']:>8.1f} km | {current_km:>8.1f} km")

# Step 4: 输出帕累托前沿
output = {
    'line': '03', 'rep_name': '欧祖良',
    'baseline_tsp': 260.8,
    'v3_km': round(v3_km, 1),
    'v3_moved': len(moved_stores),
    'total_stores': len(data.codes),
    'pareto': pareto,
    'revert_costs': revert_costs
}

json.dump(output, open('output/v4_refine_03_pareto.json', 'w'), ensure_ascii=False, indent=1)
print(f"\nSaved! Pareto 前沿共 {len(pareto)} 个点")
