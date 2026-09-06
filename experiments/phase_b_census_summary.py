# -*- coding: utf-8 -*-
"""Phase B 普查汇总: 十线 free 模式重建解的合同违约普查 (2026-09-06 审查后口径).

产出 output/contract_audit_r2_ledger.json:
  lines[lid] = {sp_km, contract_viol, viol_stores, mode, days_file}
  total_contract_viol / affected_biweekly_stores
口径: 解恒等比对用规范化 day-set (每日排序成员); free 模式严格 audit-only.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.contract import check_contract, contract_of  # noqa: E402
from data.loader import load_line, load_plan  # noqa: E402

LINES = ["02", "03", "04", "05", "06", "07", "08", "09", "10", "11"]


def main():
    pv = load_plan()
    out = {}
    for lid in LINES:
        ledger_f = f"output/sp_r2_ledger_{lid}.json"
        days_f = f"output/sp_days_free_{lid}.json"
        if not (os.path.exists(ledger_f) and os.path.exists(days_f)):
            print(f"线{lid}: 缺 {ledger_f if not os.path.exists(ledger_f) else days_f}, 跳过")
            continue
        rec = json.load(open(ledger_f))
        days = {__import__("datetime").date.fromisoformat(k): v
                for k, v in json.load(open(days_f)).items()}
        d = load_line(pv, lid)
        ct = contract_of(d.days_orig, list(d.dates))
        viol = check_contract(days, ct, list(d.dates))
        biw = [c for c, (k, _p) in ct.items() if k == "B"]
        viol_biw = [c for c in viol if c in biw]
        out[lid] = {"sp_km": rec.get("sp_km"), "contract_viol": len(viol),
                    "viol_stores": viol, "viol_biweekly": len(viol_biw),
                    "biweekly_total": len(biw), "mode": rec.get("mode")}
        print(f"线{lid}: sp_km={rec.get('sp_km')} 相位违约={len(viol)}"
              f" (双周店违约 {len(viol_biw)}/{len(biw)})")
    total = sum(v["contract_viol"] for v in out.values())
    json.dump({"lines": out, "total_contract_viol": total},
              open("output/contract_audit_r2_ledger.json", "w"), indent=1, ensure_ascii=False)
    print(f"\n普查完成: 相位违约总数 {total} (双周店共 187 家)")


if __name__ == "__main__":
    main()
