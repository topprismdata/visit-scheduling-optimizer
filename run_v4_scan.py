
import sys, json, time
sys.path.insert(0, '.')
from data.loader import load_plan, load_line
from data.road import load_cached
from algos.alns_v4 import ALNSv4
from core.metric import check_freq

pv = load_plan()
data = load_line(pv, '09')
D = load_cached('09').tolist()
v4 = ALNSv4()

results = []

# λ 扫描 (μ=0, 固定均衡度)
lams = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
for lam in lams:
    t0 = time.time()
    r = v4.solve(data, D, time_budget=15, lam=lam, mu=0.0, seed=42)
    dur = round(time.time()-t0, 1)
    ok = check_freq(r.days, data.codes, data.freq)
    m = r.metadata
    results.append({
        'type': 'lambda', 'lam': lam, 'mu': 0.0,
        'km': round(r.km, 2), 'delta': m['delta'],
        'freq_ok': ok, 'spread': m['spread'],
        'min_visits': m['min_visits'], 'max_visits': m['max_visits'],
        'elapsed_ms': m.get('elapsed_ms', 0), 'sec': dur,
        'changes': [{'store': c['store'], 'inc': c['inc_dates'], 'new': c['new_dates']} for c in m['changes'][:5]]
    })
    print(f"λ={lam:<5} km={r.km:8.2f} 改动={m['delta']:>3}店 极差={m['spread']:>2} ok={ok} [{dur}s]")

# μ 扫描 (λ=0, 固定稳定性)
mus = [0.0, 0.5, 1.0, 2.0, 5.0]
for mu in mus:
    t0 = time.time()
    r = v4.solve(data, D, time_budget=15, lam=0.0, mu=mu, seed=42)
    dur = round(time.time()-t0, 1)
    ok = check_freq(r.days, data.codes, data.freq)
    m = r.metadata
    results.append({
        'type': 'mu', 'lam': 0.0, 'mu': mu,
        'km': round(r.km, 2), 'delta': m['delta'],
        'freq_ok': ok, 'spread': m['spread'],
        'min_visits': m['min_visits'], 'max_visits': m['max_visits'],
        'elapsed_ms': m.get('elapsed_ms', 0), 'sec': dur,
        'changes': [{'store': c['store'], 'inc': c['inc_dates'], 'new': c['new_dates']} for c in m['changes'][:5]]
    })
    print(f"μ={mu:<5} km={r.km:8.2f} 改动={m['delta']:>3}店 极差={m['spread']:>2} ok={ok} [{dur}s]")

# 组合扫描 (λ+μ)
combos = [(0.5, 0.5), (1.0, 1.0), (2.0, 1.0), (0.5, 2.0)]
for lam, mu in combos:
    t0 = time.time()
    r = v4.solve(data, D, time_budget=15, lam=lam, mu=mu, seed=42)
    dur = round(time.time()-t0, 1)
    ok = check_freq(r.days, data.codes, data.freq)
    m = r.metadata
    results.append({
        'type': 'combo', 'lam': lam, 'mu': mu,
        'km': round(r.km, 2), 'delta': m['delta'],
        'freq_ok': ok, 'spread': m['spread'],
        'min_visits': m['min_visits'], 'max_visits': m['max_visits'],
        'elapsed_ms': m.get('elapsed_ms', 0), 'sec': dur,
        'changes': [{'store': c['store'], 'inc': c['inc_dates'], 'new': c['new_dates']} for c in m['changes'][:5]]
    })
    print(f"λ={lam} μ={mu} km={r.km:8.2f} 改动={m['delta']:>3}店 极差={m['spread']:>2} ok={ok} [{dur}s]")

# 参照基线
baseline_tsp = 381.7  # TSP 重排
baseline_v3 = 262.6   # ALNS v3

output = {
    'line': '09', 'rep_name': '梁健满',
    'baseline_tsp': baseline_tsp, 'baseline_v3': baseline_v3,
    'total_stores': 163,
    'results': results
}

os.makedirs('output', exist_ok=True)
json.dump(output, open('output/v4_pareto_09.json', 'w'), ensure_ascii=False, indent=1)
print(f"\n已保存至 output/v4_pareto_09.json ({len(results)} 个数据点)")
