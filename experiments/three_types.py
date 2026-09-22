# -*- coding: utf-8 -*-
"""三类对比 — ①基本一样 ②区块基本一样但星期几不一样 ③都不一样.

老板口径(2026-09-22): "大概有3种, 1基本一样 2区块基本一样星期几不一样 3都不一样"

两把尺子(都是 H3 res7 格级):
  形状像不像 = |计划格 ∩ 实际格| / |计划格 ∪ 实际格|  (对称重合/Jaccard)
  星期一致 = 共同格上 计划周几 == 实际周几 的比例
阈值: 区块一致 ≥ 80% → 区块"基本一样"; 星期一致 ≥ 70% → 星期"也基本一样"
输出: docs/reports/2026-09-22-three-types.{md,csv}
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
BLOCK_T, WD_T = 0.80, 0.70


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    A = {l: g for l, g in act.groupby("salesperson_code")}
    doss = {}
    dp = ROOT / "output/rep_behavior/dossier.json"
    if dp.exists():
        doss = {r["line"]: r for r in json.loads(dp.read_text(encoding="utf-8"))}

    rows = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        if not len(sto) or al is None or not len(al):
            continue
        pc, pw = Counter(), {}
        for r in sto.itertuples():
            c = h3.latlng_to_cell(float(r.lat), float(r.lng), 7)
            pw.setdefault(c, Counter())
            sd = getattr(r, "服务日")
            wd = int(sd) - 1 if sd == sd and int(sd) > 0 else pd.Timestamp(r.plan_day).dayofweek
            pw[c][wd] += 1
        sto2 = sto.set_index("customer_code")[["lat", "lng"]]
        a2 = al[al["customer_code"].isin(sto2.index)]
        aw = {}
        for r in a2.itertuples():
            la, lo = sto2.loc[r.customer_code, ["lat", "lng"]]
            c = h3.latlng_to_cell(float(la), float(lo), 7)
            aw.setdefault(c, Counter())[int(r.wd)] += 1
        P = {c: v.most_common(1)[0][0] for c, v in pw.items()}
        Awd = {c: v.most_common(1)[0][0] for c, v in aw.items()}
        # 形状像不像: 对称重合 = |P∩A| / |P∪A|  (Jaccard; 对称, 无跑到/没跑到概念)
        inter = len(set(P) & set(Awd))
        blk = inter / max(len(set(P) | set(Awd)), 1)
        common = set(P) & set(Awd)
        wdm = (sum(1 for c in common if P[c] == Awd[c]) / len(common)) if common else 0.0
        if blk >= BLOCK_T and wdm >= WD_T:
            kind = "①基本一样"
        elif blk >= BLOCK_T:
            kind = "②区块基本一样·星期几不一样"
        else:
            kind = "③都不一样"
        rows.append({"line": lid, "city": doss.get(lid, {}).get("city", ""), "kind3": kind,
                     "block_match": round(blk, 3), "wd_match_cell": round(wdm, 3),
                     "plan_cells": len(P), "act_cells": len(Awd)})
    d = pd.DataFrame(rows)
    (ROOT / "docs/reports/2026-09-22-three-types.csv").write_text(d.to_csv(index=False), encoding="utf-8")
    print(f"线 {len(d)} | 阈值: 区块≥{BLOCK_T:.0%} 且 星期≥{WD_T:.0%} 视为'也基本一样'\n")
    for k, g in d.groupby("kind3"):
        print(f"  {k}: {len(g)} 条 ({len(g)/len(d)*100:.1f}%) | 区块一致中位 {g['block_match'].median()*100:.0f}% | 星期一一致中位 {g['wd_match_cell'].median()*100:.0f}%")
    print("\n各城市(线≥8) 类型占比 %:")
    t = d.groupby("city")["kind3"].value_counts(normalize=True).unstack().fillna(0) * 100
    t["线数"] = d.groupby("city").size()
    t = t[t["线数"] >= 8].sort_values("②区块基本一样·星期几不一样", ascending=False)
    print(t.round(0).head(12).to_string())
    md = ["# 三类对比（计划 vs 实际）· 2026-08\n",
          f"> 尺子：形状重合度＝|计划格∩实际格|/min(|计划格|,|实际格|)；周一一致＝共同格上计划周几与实际周几相同的比例。阈值：形状≥{BLOCK_T:.0%} 且 星期≥{WD_T:.0%} → ①。\n",
          "| 类型 | 条数 | 占比 | 区块一致中位 | 星期一一致中位 |", "|---|---|---|---|---|"]
    for k, g in d.groupby("kind3"):
        md.append(f"| {k} | {len(g)} | {len(g)/len(d)*100:.1f}% | {g['block_match'].median()*100:.0f}% | {g['wd_match_cell'].median()*100:.0f}% |")
    md.append("\n## 城市（线≥8，按②占比降序，%）\n")
    md.append("| 城市 | 线数 | ①基本一样 | ②区块一样·星期不同 | ③都不一样 |")
    md.append("|---|---|---|---|---|")
    for c, r in t.head(20).iterrows():
        md.append(f"| {c} | {int(r['线数'])} | {r.get('①基本一样',0):.0f} | {r.get('②区块基本一样·星期几不一样',0):.0f} | {r.get('③都不一样',0):.0f} |")
    (ROOT / "docs/reports/2026-09-22-three-types.md").write_text("\n".join(md), encoding="utf-8")
    print("\n报告: docs/reports/2026-09-22-three-types.md")


if __name__ == "__main__":
    main()