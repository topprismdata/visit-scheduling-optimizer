import sys, json
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from algos.alns_v3 import ALNSv3, two_opt
from core.metric import day_km, check_freq
from core.zone_graph import assign_zones_only

pv = load_plan()
data = load_line(pv, '09')
D = load_cached('09').tolist()

v3 = ALNSv3()
ZONE_PATH = '/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson'
KEEP = {'440103','440104','440105','440106','440111','440112','440113'}
zlist = assign_zones_only(ZONE_PATH, data.lon, data.lat, KEEP)
zone_of = {i: z for i, z in enumerate(zlist)}
res = v3.solve(data, D, time_budget=300, seed=42, zone_of=zone_of)
print(f"v3 09线: {res.km:.1f} km, iters={res.metadata.get('iters')}")
print(f"freq_ok: {check_freq(res.days, data.codes, data.freq)}")

# 构建周-日级 v3 序列 (与 line09_detail.weekly_routes 结构对齐)
import pandas as pd
weeks = {}
for dd, seq in res.days.items():
    wk = dd.isocalendar()[1] - data.dates[0].isocalendar()[1] + 1
    wd = dd.weekday()
    weeks.setdefault(str(wk), {})[str(wd)] = {
        'date': str(dd), 'n': len(seq),
        'seq_alns_v3': seq,
        'km_alns_v3': round(day_km(two_opt(seq, D, 30), D), 1)
    }

json.dump(weeks, open('output/v3_09_weekly.json', 'w'), indent=1)
print(f"saved v3_09_weekly.json: {len(weeks)} weeks")
