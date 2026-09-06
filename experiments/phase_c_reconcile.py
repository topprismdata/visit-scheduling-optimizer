# -*- coding: utf-8 -*-
"""Phase C 对账: 合同口径十线正式账 vs 基线A / 旧松弛口径 / free 普查.

产出 stdout 对账表 + output/sp_contract_ledger_all.json (合并).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LINES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]


def main():
    new = {}
    for f in sorted(glob.glob("output/sp_contract_ledger_??.json")):
        lid = f[-7:-5]
        new[lid] = json.load(open(f))
    if len(new) != 10:
        print(f"警告: 仅 {len(new)}/10 线完成")
    json.dump(new, open("output/sp_contract_ledger_all.json", "w"), indent=1, ensure_ascii=False)

    old = json.load(open("output/sp_r2_ledger_all.json"))          # 旧松弛口径 (历史参照)
    base = json.load(open("output/cpsat_plan_baselines.json"))     # 基线A
    free = {}
    for f in sorted(glob.glob("output/sp_r2_ledger_??.json")):     # Phase B free 普查账
        free[f[-7:-5]] = json.load(open(f))

    tb = sum(new[l]["baseA"] for l in new)
    ts = sum(new[l]["sp_km"] for l in new)
    tf = sum(free[l]["sp_km"] for l in free if l in new)
    print(f"合同口径: {ts:.1f} km vs 基线A {tb:.1f} ({(ts - tb) / tb * 100:+.2f}%)")
    print(f"旧松弛口径(历史参照, 不可比): {sum(old[l]['sp_km'] for l in old):.1f} km")
    if tf:
        print(f"free 普查(同预算同类): {tf:.1f} km | 相位收紧机会成本 {tf - ts:+.1f} km")
    viol_total = sum(new[l].get("contract_viol", 0) for l in new)
    print(f"十线 contract_viol 总数: {viol_total} (必须为 0)")
    print(f"{'线':>4} {'基线A':>8} {'合同SP':>8} {'vs基线':>8} {'违约':>4} {'all_opt':>7}")
    for l in LINES:
        r = new.get(l)
        if not r:
            print(f"{l:>4} {'—':>8}")
            continue
        print(f"{l:>4} {r['baseA']:>8.1f} {r['sp_km']:>8.1f} "
              f"{r['delta_vs_baseA_pct']:>7.2f}% {r.get('contract_viol', -1):>4} "
              f"{str(r.get('all_optimal')):>7}")


if __name__ == "__main__":
    main()
