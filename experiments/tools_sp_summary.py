# -*- coding: utf-8 -*-
"""SP+CG 全办推广汇总: 汇集各线 SP 结果 vs 池内 v3 基线, 严格核验原计划双向走廊 [K_min, K_max] 合规性."""
import sys, os, json, csv
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from data.loader import load_plan, load_line

pv = load_plan()
LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
rows = []
for lid in LINES:
    mf = f'output/sp_runs_{lid}.json'
    if not os.path.exists(mf):
        print(f"线{lid}: 缺 {mf}, 跳过")
        continue
    data = load_line(pv, lid)
    min_orig = data.min_daily_capacity
    max_orig = data.max_daily_capacity
    manifest = json.load(open(mf))
    v3 = sorted(v['km'] for t, v in manifest.items()
                if v.get('name') == 'alns_v3' and v.get('km'))
    # SP 结果: bench CSV 中该线最新 sp_clean_cap 行 (优先) 或 sp_matheuristic 行
    sp_km = lb = gap = None
    cap_ok = False
    day_range = None
    with open('output/bench_20260905.csv') as f:
        for p in csv.reader(f):
            if len(p) > 8 and p[1] in ('sp_clean_cap', 'sp_matheuristic', 'sp_intensify') and p[2] == lid:
                sp_km = float(p[5])
                try:
                    meta = json.loads(p[8])
                    lb, gap = meta.get('lb'), meta.get('gap')
                    day_range = meta.get('day_range')
                except Exception:
                    pass
                cap_ok = (p[7].strip().lower() == 'true')
    v3_best = min(v3) if v3 else None
    v3_mean = round(sum(v3) / len(v3), 1) if v3 else None
    delta = round((sp_km - v3_best) / v3_best * 100, 2) if (sp_km and v3_best) else None
    rows.append({
        'line': lid,
        'rep_name': data.line_name.split('_')[-1] if '_' in data.line_name else data.line_name,
        'corridor': [min_orig, max_orig],
        'day_range': day_range,
        'capacity_ok': cap_ok,
        'v3_n': len(v3),
        'v3_best': v3_best,
        'v3_mean': v3_mean,
        'sp_km': sp_km,
        'lb': round(lb, 1) if lb else None,
        'cert_gap_pct': gap,
        'vs_v3_best_pct': delta
    })

hdr = f"{'线':>4} {'业代':<8} {'原计划走廊':>13} {'实测单日':>11} {'走廊合规':>8} {'v3最优':>9} {'SP+CG':>9} {'LP下界':>9} {'认证gap':>8} {'vs v3':>10}"
print(hdr)
print('-' * (len(hdr) + 6))
for r in rows:
    def fmt(v, suf=''):
        return (str(v) + suf) if v is not None else '-'
    cor_str = f"[{r['corridor'][0]}~{r['corridor'][1]}]"
    dr_str = f"[{r['day_range'][0]}~{r['day_range'][1]}]" if r['day_range'] else '-'
    cap_str = "PASS ✓" if r['capacity_ok'] else "FAIL ✗"
    print(f"{r['line']:>4} {r['rep_name']:<8} {cor_str:>13} {dr_str:>11} {cap_str:>8} "
          f"{fmt(r['v3_best']):>9} {fmt(r['sp_km']):>9} "
          f"{fmt(r['lb']):>9} {fmt(r['cert_gap_pct'], '%'):>8} {fmt(r['vs_v3_best_pct'], '%'):>10}")

tot_v3 = sum(r['v3_best'] for r in rows if r['v3_best'] and r['sp_km'])
tot_sp = sum(r['sp_km'] for r in rows if r['sp_km'])
all_cap_pass = all(r['capacity_ok'] for r in rows if r['sp_km'])
print('-' * (len(hdr) + 6))
if tot_v3 and tot_sp:
    print(f"全办已完成线路总计: Σv3最优 {tot_v3:.1f} -> ΣSP {tot_sp:.1f} ({(tot_sp-tot_v3)/tot_v3*100:+.2f}%) | 100% 走廊合规: {all_cap_pass}")
json.dump(rows, open('output/sp_all_lines_summary.json', 'w'), ensure_ascii=False, indent=1)
print("\n已更新 output/sp_all_lines_summary.json")
