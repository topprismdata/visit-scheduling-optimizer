# -*- coding: utf-8 -*-
"""SP+CG 全办推广汇总: 汇集各线 SP 结果 vs 池内 v3 基线, 出总账表."""
import sys, os, json, csv
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
rows = []
for lid in LINES:
    mf = f'output/sp_runs_{lid}.json'
    if not os.path.exists(mf):
        print(f"线{lid}: 缺 {mf}, 跳过")
        continue
    manifest = json.load(open(mf))
    v3 = sorted(v['km'] for t, v in manifest.items()
                if v.get('name') == 'alns_v3' and v.get('km'))
    # SP 结果: bench CSV 中该线最新 sp_matheuristic 行 (csv 模块解析, 元数据含逗号)
    sp_km = lb = gap = None
    with open('output/bench_20260905.csv') as f:
        for p in csv.reader(f):
            if len(p) > 8 and p[1] == 'sp_matheuristic' and p[2] == lid:
                sp_km = float(p[5])
                try:
                    meta = json.loads(p[8])
                    lb, gap = meta.get('lb'), meta.get('gap')
                except Exception:
                    pass
    v3_best = min(v3) if v3 else None
    v3_mean = round(sum(v3) / len(v3), 1) if v3 else None
    delta = round((sp_km - v3_best) / v3_best * 100, 2) if (sp_km and v3_best) else None
    rows.append({'line': lid, 'v3_n': len(v3), 'v3_best': v3_best, 'v3_mean': v3_mean,
                 'sp_km': sp_km, 'lb': round(lb, 1) if lb else None,
                 'cert_gap_pct': gap, 'vs_v3_best_pct': delta})

hdr = f"{'线':>4} {'v3最优':>9} {'v3均值':>9} {'SP+CG':>9} {'LP下界':>9} {'认证gap':>8} {'vs v3最优':>10}"
print(hdr)
print('-' * len(hdr))
for r in rows:
    def fmt(v, suf=''):
        return (str(v) + suf) if v is not None else '-'
    print(f"{r['line']:>4} {fmt(r['v3_best']):>9} {fmt(r['v3_mean']):>9} {fmt(r['sp_km']):>9} "
          f"{fmt(r['lb']):>9} {fmt(r['cert_gap_pct'], '%'):>8} {fmt(r['vs_v3_best_pct'], '%'):>10}")

tot_v3 = sum(r['v3_best'] for r in rows if r['v3_best'])
tot_sp = sum(r['sp_km'] for r in rows if r['sp_km'])
if tot_v3 and tot_sp:
    print(f"\n全办: Σv3最优 {tot_v3:.1f} -> ΣSP {tot_sp:.1f} ({(tot_sp-tot_v3)/tot_v3*100:+.2f}%)")
json.dump(rows, open('output/sp_all_lines_summary.json', 'w'), ensure_ascii=False, indent=1)
print("\n已写 output/sp_all_lines_summary.json")
