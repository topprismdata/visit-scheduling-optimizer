# -*- coding: utf-8 -*-
"""正常口径统计 — 剔除"换人/归属异常"特殊线后重算全国结论.

老板口径(2026-09-22): "换人的是特殊情况, 先不要管"。
判别(任一命中即视为特殊, 单独归类):
  ① 块开工率 = 0        (计划划的块一个都没动)
  ② 覆盖 < 30%          (计划门店几乎没碰)
  ③ 服务日命中 < 20%    (计划星期与实际完全对不上)
这三类在数据上表现为"计划跟这个人对不上", 属于管辖/门店清单/换人问题, 不是执行力问题。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))


def main():
    recs = json.loads((ROOT / "output/rep_behavior/dossier.json").read_text(encoding="utf-8"))
    d = pd.DataFrame([{k: v for k, v in r.items() if k not in ("block_detail", "never", "wd_visits")} for r in recs])
    d["block_worked_rate"] = d["blocks_worked"] / d["blocks"].clip(lower=1)
    special = (d["block_worked_rate"] <= 0) | (d["cover"] < 0.30) | (d["svc_wd_hit"] < 0.20)
    d["special"] = special
    d["kind2"] = np.where(special, "特殊·换人/归属待查", d["kind"])

    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    A = {l: g for l, g in act.groupby("salesperson_code")}
    cells = {}
    for lid, pl in plan.groupby("sales_line_code"):
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        al = A.get(lid)
        if al is None or not len(al):
            continue
        pc = {h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
        a2 = al.merge(sto[["customer_code", "lat", "lng"]], on="customer_code", how="inner")
        ac = {h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in a2.itertuples()}
        cells[lid] = (len(pc), len(pc - ac), len(pc - ac) / max(len(pc), 1))
    d["miss_cell_pct"] = d["line"].map(lambda l: cells.get(l, (np.nan,) * 3)[2] * 100)

    normal = d[~d["special"]]
    spec = d[d["special"]]
    print(f"总 {len(d)} 条 | 正常 {len(normal)} 条 ({len(normal)/len(d)*100:.0f}%) | 特殊 {len(spec)} 条 ({len(spec)/len(d)*100:.0f}%)")
    print("\n特殊线为什么被判特殊:")
    for lbl, m in (("块开工=0", spec["block_worked_rate"] <= 0),
                   ("覆盖<30%", spec["cover"] < 0.30),
                   ("服务日命中<20%", spec["svc_wd_hit"] < 0.20)):
        print(f"  {lbl:16s} {int(m.sum())} 条")
    print("\n=== 全国口径对比（中位） ===")
    rows = []
    for m, tag in ((normal, "正常线"), (d, "含特殊线")):
        rows.append({
            "口径": tag, "线数": len(m),
            "缺格率%": round(m["miss_cell_pct"].median(), 1),
            "块开工%": round((m["blocks_worked"] / m["blocks"].clip(lower=1)).median() * 100, 1),
            "块内执行%": round(m["block_exec_median"].median() * 100, 1),
            "服务日命中%": round(m["svc_wd_hit"].median() * 100, 1),
            "覆盖%": round(m["cover"].median() * 100, 1),
            "同日%": round(m["sameday"].median() * 100, 1),
            "死重门店占比%": round((m["n_never"] / m["plan_stores"]).median() * 100, 1),
            "量比": round(m["qty"].median(), 2),
            "块平衡CV": round(m["block_balance_cv"].median(), 3),
        })
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    t = t.rename(columns={"缺格率%": "缺格率%", "块开工%": "块开工%", "块内执行%": "块内执行%", "服务日命中%": "服务日命中%",
                          "覆盖%": "覆盖%", "同日%": "同日%", "死重门店占比%": "死重门店占比%"})
    md = ["# 正常口径统计（剔除换人/归属异常特殊线）· 2026-08\n",
          "> 特殊线判别：块开工率=0 或 覆盖<30% 或 服务日命中<20%（表现＝计划与这个人对不上，属管辖/清单/换人问题）。\n",
          "| 口径 | 线数 | 缺格率 | 块开工 | 块内执行 | 服务日命中 | 覆盖 | 同日 | 死重门店占比 | 量比 | 块平衡CV |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        md.append("| " + " | ".join((f"{r[c]}%" if str(c).endswith("%") else str(r[c])) for c in t.columns) + " |")
    md.append("\n## 正常线分型分布\n")
    for k, v in normal["kind2"].value_counts().items():
        md.append(f"- {k}: {v} 条 ({v/len(normal)*100:.1f}%)")
    (ROOT / "docs/reports/2026-09-22-normal-population.md").write_text("\n".join(md), encoding="utf-8")
    pd.DataFrame({"line": d["line"], "city": d["city"], "special": d["special"], "kind2": d["kind2"],
                  "cover": d["cover"], "blocks_worked": d["blocks_worked"], "blocks": d["blocks"],
                  "svc_wd_hit": d["svc_wd_hit"], "miss_cell_pct": d["miss_cell_pct"].round(1)}
                 ).to_csv(ROOT / "docs/reports/2026-09-22-normal-vs-special.csv", index=False)
    print("\n正常线分型:")
    print(normal["kind2"].value_counts().to_string())
    print("\n报告: docs/reports/2026-09-22-normal-population.md")


if __name__ == "__main__":
    main()