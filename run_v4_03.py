
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from algos.alns_v4 import ALNSv4
from core.metric import check_freq

pv = load_plan()
data = load_line(pv, '03')
D = load_cached('03').tolist()
v4 = ALNSv4()

# 03 线自适应 λ 范围: 0~5.1
lams = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]
results = []

for lam in lams:
    r = v4.solve(data, D, time_budget=12, lam=lam, mu=0.0, seed=42)
    ok = check_freq(r.days, data.codes, data.freq)
    m = r.metadata
    results.append({
        'lam': lam, 'mu': 0.0, 'km': round(r.km, 2), 'delta': m['delta'],
        'freq_ok': ok, 'spread': m['spread'], 'min': m['min_visits'], 'max': m['max_visits']
    })
    print(f"\u03bb={lam:<5} km={r.km:8.2f} \u6539\u52a8={m['delta']:>3}\u5e97 \u6781\u5dee={m['spread']:>2} ok={ok}")

json.dump(results, open('output/v4_pareto_03.json', 'w'), indent=1)
print("Saved!")
