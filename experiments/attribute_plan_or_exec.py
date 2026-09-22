# -*- coding: utf-8 -*-
"""归因：计划不够好 还是 执行有问题.

判据(业务逻辑, 不看覆盖率):
  习惯稳定度 = 每个地块的实际到访"集中在主力周几"的比例 (访问次数加权)
  形状稳定度 = 同相位周之间的地块集合重合度 (W1 vs W3, W2 vs W4 的 Jaccard 均值)
  计划-习惯一致 = 计划周几 == 该地块实际主力周几 的地块占比 (按店数加权)

规则:
  计划不够好   : 习惯稳定(≥0.60) 但 计划-习惯不一致占比 ≥ 25%
  执行有问题   : 习惯稳定度 < 0.50  或  形状稳定度 < 0.50
  两者都有     : 同时命中
  执行到位     : 计划-习惯一致 ≥ 85% 且 习惯稳定 ≥ 0.60
  待定         : 其余
输出: docs/reports/2026-09-22-attribution.{md,csv}
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.blocks import build as build_blocks  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))


def wk(d):
    return (d.day - 1) // 7 + 1


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
    act["wk"] = act["call_date"].apply(wk)
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
        # ---- 门店级(最直观): 每店 计划周几 vs 实际主力周几 + 该店自身规律性 ----
        svc = {str(r.customer_code): (int(r.服务日) - 1 if r.服务日 == r.服务日 and int(r.服务日) > 0
                                      else pd.Timestamp(r.plan_day).dayofweek) for r in pl.itertuples()}
        act_in = al[al["customer_code"].isin(set(sto["customer_code"]))]
        mism, habit_parts, tot = 0, [], 0
        for c, g in act_in.groupby("customer_code"):
            if c not in svc:
                continue
            vc = Counter(g["wd"]); modal, cnt = vc.most_common(1)[0]
            tot += 1
            habit_parts.append(cnt / len(g))            # 该店自己的规律性
            if modal != svc[c]:
                mism += 1
        habit = float(np.mean(habit_parts)) if habit_parts else 0.0
        mismatch = mism / max(tot, 1)                   # 计划周几 与 实际主力周几 不同的店占比
        # 平均每店 每月 有几个不同的周几(越少越规律)
        wd_spread = float(np.mean([act_in[act_in["customer_code"] == c]["wd"].nunique() for c in act_in["customer_code"].unique()])) if tot else 0.0
        # 归因: 他有规律 但 计划周几与实际主力不同 → 计划不够好; 他自己没规律 → 执行有问题
        plan_bad = bool(habit >= 0.60 and mismatch >= 0.25)
        exe_bad = bool(habit < 0.60)
        if plan_bad and exe_bad:
            verdict = "两者都有"
        elif plan_bad:
            verdict = "计划不够好（他有规律，计划写错天）"
        elif exe_bad:
            verdict = "执行有问题（他自己没规律）"
        elif mismatch < 0.25 and habit >= 0.60:
            verdict = "执行到位（计划与实际一致）"
        else:
            verdict = "待定"
        rows.append({"line": lid, "city": doss.get(lid, {}).get("city", ""),
                     "verdict": verdict, "习惯规律性": round(habit, 3),
                     "计划周几不同占比": round(mismatch, 3), "每店周几数": round(wd_spread, 2),
                     "门店数": tot})
    d = pd.DataFrame(rows)
    (ROOT / "docs/reports/2026-09-22-attribution.csv").write_text(d.to_csv(index=False), encoding="utf-8")
    print(f"线 {len(d)}\n")
    for k, g in d.groupby("verdict"):
        print(f"  {k}: {len(g):>3} 条 ({len(g)/len(d)*100:4.1f}%) | 他的规律性 {g['习惯规律性'].median():.2f} | "
              f"计划周几不同占比 {g['计划周几不同占比'].median():.2f} | 每店平均周几数 {g['每店周几数'].median():.2f}")
    md = ["# 归因：计划不够好 还是 执行有问题 · 2026-08\n",
          "判据（不看覆盖率）：习惯稳定度＝各地块实际到访集中在主力周几的比例；形状稳定度＝同相位周之间地块集合的重合度；计划-习惯一致＝计划周几与地块实际主力周几相符的店数占比。\n",
          "| 结论 | 条数 | 占比 | 他的规律性 | 计划周几不同占比 | 每店平均周几数 |", "|---|---|---|---|---|---|"]
    for k, g in d.groupby("verdict"):
        md.append(f"| {k} | {len(g)} | {len(g)/len(d)*100:.1f}% | {g['习惯规律性'].median():.2f} | {g['计划周几不同占比'].median():.2f} | {g['每店周几数'].median():.2f} |")
    md.append("\n## 城市（线≥8，按「计划不够好」占比降序）\n")
    t = d.groupby("city")["verdict"].value_counts(normalize=True).unstack().fillna(0) * 100
    t["线数"] = d.groupby("city").size()
    t = t[t["线数"] >= 8]
    col = "计划不够好" if "计划不够好" in t.columns else t.columns[0]
    for c, r in t.sort_values(col, ascending=False).head(12).iterrows():
        parts = " ｜ ".join(f"{k} {r[k]:.0f}%" for k in t.columns if k != "线数" and r[k] > 0)
        md.append(f"- **{c}**（{int(r['线数'])} 条）：{parts}")
    (ROOT / "docs/reports/2026-09-22-attribution.md").write_text("\n".join(md), encoding="utf-8")
    print("\n报告: docs/reports/2026-09-22-attribution.md")


if __name__ == "__main__":
    main()