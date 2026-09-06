# -*- coding: utf-8 -*-
"""10 线反馈耦合 ALNS v3 全量跑, 对比 v1 ledger 基线 (同 300s 预算).
每线逐日优化 → 记录 v3 里程; 增量保存; 逐线容错."""
import sys, json, time, warnings, traceback
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import pandas as pd
from data.loader import load_plan, load_line, ALL_LINE_IDS
from data.road import load_cached
from core.metric import total_km, check_freq
from core.zone_graph import assign_zones_only
import algos.impl, algos.alns_v3
from algos.registry import get

ZONE_PATH = '/Users/ghb/Downloads/边界数据-路网-到区县带海岸线-四级路网-广东省-广州市.geojson'
KEEP = {'440103','440104','440105','440106','440111','440112','440113'}
BUDGET = 300

# v1 基线 (ledger_deep 的 alns 列)
try:
    deep = pd.read_csv('output/ledger_deep.csv')
    v1 = {int(r.line): r.km for r in deep[deep.algo=='alns'].itertuples()}
except Exception:
    v1 = {}

pv = load_plan()
out = {}
rows = []

def save():
    pd.DataFrame(rows).to_csv('output/ledger_v3_all.csv', index=False)
    json.dump(rows, open('output/ledger_v3_all.json','w'), ensure_ascii=False, indent=1)

for lid in ALL_LINE_IDS:
    try:
        data = load_line(pv, lid)
        Dm = load_cached(lid)
        if Dm is None:
            print(f"线 {lid}: 无矩阵, 跳过", flush=True); continue
        D = Dm.tolist()
        zlist = assign_zones_only(ZONE_PATH, data.lon, data.lat, KEEP)
        zone_of = {i: z for i, z in enumerate(zlist)}
        t0 = time.time()
        r = get('alns_v3')().solve(data, D, time_budget=BUDGET, zone_of=zone_of)
        ok = check_freq(r.days, data.codes, data.freq)
        v1km = v1.get(int(lid))
        rows.append(dict(line=lid, stores=data.stores, visits=data.visits, days=len(data.dates),
                         v1_alns=round(v1km,1) if v1km else None,
                         v3=round(r.km,1), freq_ok=bool(ok),
                         delta=round(r.km-v1km,1) if v1km else None,
                         sav_pct=round((r.km-v1km)/v1km*100,1) if v1km else None,
                         its=r.metadata.get('iters'), sec=round(time.time()-t0)))
        print(f"线 {lid}: v1={v1km} v3={r.km:.1f} " + (f"({(r.km-v1km)/v1km*100:+.1f}%)" if v1km else "") + f" freq_ok={ok} [{time.time()-t0:.0f}s]", flush=True)
        save()
    except Exception as e:
        print(f"线 {lid}: FAILED {e}", flush=True); traceback.print_exc()
        save()

save()
t = pd.DataFrame(rows)
if len(t):
    print("\n=== v3 全量汇总 ===")
    print(t[['line','v1_alns','v3','sav_pct','freq_ok','its']].to_string(index=False))
    v1s = t.v1_alns.sum(); v3s = t.v3.sum()
    print(f"\n合计: v1={v1s:.0f} km → v3={v3s:.0f} km ({(v3s-v1s)/v1s*100:+.1f}%)")
