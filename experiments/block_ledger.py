# -*- coding: utf-8 -*-
"""区块台账 — 把左右地图的结论变成可执行清单.

对每条线输出: H3 计划格 → 实际格 (缺格) / 计划块 → 开工块 / 块内执行中位 / 服务日命中 / 覆盖,
并按严重程度排序 + 城市汇总。数据源: 计划 + 实际 + dossier.json(块口径指标)。

产出: output/rep_behavior/block_ledger.csv
      docs/reports/2026-09-22-block-ledger.md (TOP 名单 + 城市汇总)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
REPO = ROOT


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["lat"] = pd.to_numeric(plan["lat"], errors="coerce")
    plan["lng"] = pd.to_numeric(plan["lng"], errors="coerce")
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    doss = {}
    dp = ROOT / "output/rep_behavior/dossier.json"
    if dp.exists():
        doss = {r["line"]: r for r in json.loads(dp.read_text(encoding="utf-8"))}
    A = {l: g for l, g in act.groupby("salesperson_code")}

    rows = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        if al is None or not len(al):
            continue
        sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
        pcells = {h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
        a2 = al.merge(sto[["customer_code", "lat", "lng"]], on="customer_code", how="inner")
        acells = {h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in a2.itertuples()}
        d = doss.get(lid, {})
        rows.append({
            "line": lid, "city": d.get("city", ""), "kind": d.get("kind", ""),
            "plan_cells": len(pcells), "act_cells": len(acells), "miss_cells": len(pcells - acells),
            "miss_cell_pct": round(len(pcells - acells) / max(len(pcells), 1) * 100, 1),
            "blocks": d.get("blocks"), "blocks_worked": d.get("blocks_worked"),
            "block_exec_median": d.get("block_exec_median"), "svc_wd_hit": d.get("svc_wd_hit"),
            "cover": d.get("cover"), "sameday": d.get("sameday"),
            "plan_stores": d.get("plan_stores"), "never": d.get("n_never"),
        })
    d = pd.DataFrame(rows)
    out = ROOT / "output/rep_behavior"
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "block_ledger.csv", index=False)
    (REPO / "docs/reports/2026-09-22-block-ledger.csv").write_text(d.to_csv(index=False), encoding="utf-8")

    d = d.sort_values("miss_cell_pct", ascending=False)
    md = ["# 区块台账 · 2026-08（计划格 → 实际格 / 块开工 / 服务日命中）\n",
          f"> 计划版本：《{PLAN_XLSX.name}》；口径＝H3 res7 格 + 服务日块（见 experiments/blocks.py）。"
          f"共 {len(d)} 条线。\n",
          "## 一、缺格最严重（计划格与实际格之差）\n",
          "| 线 | 城市 | 分型 | 计划格 | 实际格 | 缺格 | 缺格% | 计划块 | 开工块 | 块内执行 | 服务日命中 | 覆盖 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in d.head(30).itertuples():
        md.append(f"| {r.line} | {r.city} | {r.kind} | {r.plan_cells} | {r.act_cells} | {r.miss_cells} | {r.miss_cell_pct}% | "
                  f"{r.blocks} | {r.blocks_worked} | {r.block_exec_median} | {r.svc_wd_hit} | {r.cover} |")
    cities = d.groupby("city").agg(线数=("line", "size"), 缺格率中位=("miss_cell_pct", "median"),
                                   块开工率中位=("blocks_worked", lambda s: None),
                                   覆盖中位=("cover", "median")).drop(columns=["块开工率中位"])
    cities["未开工块占比中位"] = d.assign(未开工=lambda x: (x["blocks"] - x["blocks_worked"]) / x["blocks"].clip(lower=1)).groupby("city")["未开工"].median()
    cities = cities[cities["线数"] >= 8].sort_values("缺格率中位", ascending=False)
    md.append("\n## 二、城市汇总（线数≥8，按缺格率降序）\n")
    md.append("| 城市 | 线数 | 缺格率中位 | 未开工块占比中位 | 覆盖中位 |")
    md.append("|---|---|---|---|---|")
    for c, r in cities.head(20).iterrows():
        md.append(f"| {c} | {int(r['线数'])} | {r['缺格率中位']:.1f}% | {r['未开工块占比中位']*100:.0f}% | {r['覆盖中位']:.2f} |")
    md.append(f"\n## 三、全国概览\n")
    md.append(f"- 缺格率中位 **{d['miss_cell_pct'].median():.1f}%**（计划格与实际格之差）")
    md.append(f"- 块开工率中位 **{(d['blocks_worked']/d['blocks'].clip(lower=1)).median()*100:.0f}%**；块内执行中位 **{d['block_exec_median'].median()*100:.0f}%**")
    md.append(f"- 服务日命中中位 **{d['svc_wd_hit'].median()*100:.0f}%**；覆盖中位 **{d['cover'].median()*100:.0f}%**")
    (REPO / "docs/reports/2026-09-22-block-ledger.md").write_text("\n".join(md), encoding="utf-8")
    print(f"线 {len(d)} | 缺格率中位 {d['miss_cell_pct'].median():.1f}% | "
          f"块开工中位 {(d['blocks_worked']/d['blocks'].clip(lower=1)).median()*100:.0f}% | 服务日命中中位 {d['svc_wd_hit'].median()*100:.0f}%")
    print("TOP5 缺格:")
    for r in d.head(5).itertuples():
        print(f"  {r.line} {r.city} {r.kind} | 计划{r.plan_cells}格→实际{r.act_cells}格(缺{r.miss_cells}) | 块 {r.blocks_worked}/{r.blocks} | 服务日命中 {r.svc_wd_hit}")
    print(f"明细: {out/'block_ledger.csv'} | 报告: docs/reports/2026-09-22-block-ledger.md")


if __name__ == "__main__":
    main()