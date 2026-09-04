# -*- coding: utf-8 -*-
"""MO-ALNS v4 09线: 以 v3 为基准, 注入 CP-SAT 0改动锚点, 三目标帕累托."""
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from core.zone_graph import assign_zones_only
from core.metric import total_km
from algos.mo_alns_v4 import MOALNSv4
from algos.tsp_engine import _exact_open_tsp

pv = load_plan()
data = load_line(pv, '09')
D = load_cached('09').tolist()

ZONE_PATH = '/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson'
KEEP = {'440103','440104','440105','440106','440111','440112','440113'}
zlist = assign_zones_only(ZONE_PATH, data.lon, data.lat, KEEP)
zone_of = {i: z for i, z in enumerate(zlist)}

# 基准: v3 日级结果
v3w = json.load(open('output/v3_09_weekly.json'))
date_by_str = {str(dd): dd for dd in data.dates}
v3_base = {date_by_str[e['date']]: e['seq_alns_v3'] for days in v3w.values() for e in days.values()}
print(f"v3 基准: {total_km(v3_base, D):.1f} km (0 相对改动端)")

# 锚点: CP-SAT 精确日内重排 (相对 v3 有改动, 但里程最优)
cpsat = {dd: _exact_open_tsp(seq, D, 10) for dd, seq in data.days_orig.items()}
print(f"CP-SAT 锚点: {total_km(cpsat, D):.1f} km")

mo = MOALNSv4()
t1 = time.time()
res = mo.solve(data, D, time_budget=60, zone_of=zone_of, seed=42, pop_size=40,
               base=v3_base, extra_seeds={'cpsat_exact': cpsat})
m = res.metadata
print(f"MO-ALNS v4 完成! 耗时 {time.time()-t1:.1f}s, {m['generations']} 代, 前沿 {m['front_size']} 解\n")

names = {'aggressive':'激进型','recommended':'推荐型(膝点)','balanced':'均衡型','conservative':'保守型'}
print("=== 命名方案 (f2=相对v3的改动) ===")
for k,v in m['preset_names'].items():
    print(f"  {names[k]:<14} km={v['km']:>7.1f} | 再改动={v['changed']:>3}店 | CV={v['cv']:.3f} | freq_ok={v['freq_ok']}")

pf = m['pareto_front']
print(f"\n=== 前沿范围 === km: {min(p['km'] for p in pf):.1f}~{max(p['km'] for p in pf):.1f} | 改动: 0~{max(p['changed'] for p in pf)}")

json.dump({'line':'09','rep_name':'梁健满','total_stores':m['total_stores'],
           'generations':m['generations'],'front_size':m['front_size'],
           'preset_names':m['preset_names'],'pareto_front':pf[:40]},
          open('output/mo_alns_v4_09.json','w'), ensure_ascii=False, indent=1)
print("Saved output/mo_alns_v4_09.json")
