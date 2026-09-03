
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from core.zone_graph import assign_zones_only
from algos.mo_alns_v4 import MOALNSv4
from core.metric import check_freq

pv = load_plan()
data = load_line(pv, '09')
D = load_cached('09').tolist()

ZONE_PATH = '/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson'
KEEP = {'440103','440104','440105','440106','440111','440112','440113'}
zlist = assign_zones_only(ZONE_PATH, data.lon, data.lat, KEEP)
zone_of = {i: z for i, z in enumerate(zlist)}

mo = MOALNSv4()
t0 = time.time()
res = mo.solve(data, D, time_budget=45, zone_of=zone_of, seed=42, pop_size=30)
dur = time.time() - t0

m = res.metadata
print(f"MO-ALNS v4 完成! 耗时 {dur:.1f}s, {m['generations']} 代, 前沿 {m['front_size']} 个非支配解")
print()

# 命名方案
print("=== 四个命名方案 ===")
names = {'aggressive': '激进型', 'recommended': '推荐型(膝点)', 'balanced': '均衡型', 'conservative': '保守型'}
for k, v in m['preset_names'].items():
    print(f"  {names[k]:<14} | km={v['km']:>7.1f} | 改动={v['changed']:>3}店 ({v['changed']/m['total_stores']*100:.1f}%) | CV={v['cv']:.3f} | 跨区率={v['cross']:.3f} | freq={v.get('freq_ok','')}")

# 帕累托前沿
print(f"\n=== 帕累托前沿 ({len(m['pareto_front'])} 个解) ===")
print(f"{'#':<4} | {'km':<8} | {'改动':<6} | {'CV':<8} | {'跨区率':<8}")
print("-" * 45)
for p in m['pareto_front'][:15]:
    print(f"{p['id']:<4} | {p['km']:<8.1f} | {p['changed']:<6} | {p['cv']:<8.4f} | {p['cross_ratio']:<8.4f}")

# 保存
json.dump({
    'line': '09', 'rep_name': '梁健满',
    'total_stores': m['total_stores'],
    'generations': m['generations'],
    'front_size': m['front_size'],
    'preset_names': m['preset_names'],
    'pareto_front': m['pareto_front'][:30]
}, open('output/mo_alns_v4_09.json', 'w'), ensure_ascii=False, indent=1)
print("\nSaved!")
