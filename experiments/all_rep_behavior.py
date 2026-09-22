# -*- coding: utf-8 -*-
"""全量销售行为画像 — 把"地块"与"星期"分开量, 再分型.

老板命题(2026-09-22): "把所有销售都跑一遍，这样可以理解每个销售的行为。
可能有的人地块和规划一样，只是星期选择不同。"

两把尺子 (都相对计划):
  地块一致度 cover   = |计划门店 ∩ 实际到访门店| / |计划门店|      计划里的店他跑了几成
  星期一致度 wd_match = 计划(店,星期) 被实际同星期覆盖的比例        计划的"星期安排"他守了几成
辅助: 纯度 purity = |计划∩实际| / |实际|  (他跑的店里有多少是计划内的)
      同日 sameday = |计划(店,日) ∩ 实际(店,日)| / |计划(店,日)|   严格日期服从
      量比 qty = 实际到访次数 / 计划行数                          跑多还是跑少

分型 (阈值可调):
  照做型         cover≥0.9 & wd_match≥0.75 & sameday≥0.6
  地块同步·星期偏移 cover≥0.9 & wd_match<0.75        ← 老板假设的那一类
  少跑但没跑偏    cover<0.9 & purity≥0.9
  漂移/混合      其余

计划版本: 环境变量 PLAN_XLSX (默认《更新后的8月规划》= 业代真正执行的那一版)
输出: output/rep_behavior/all_reps.csv + 终端汇总
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OUT = ROOT / "output" / "rep_behavior"


def main():
    kpi = pd.read_excel(UFS / "采纳执行-8月.xlsx")
    kpi["sales_line_code"] = kpi["sales_line_code"].astype(str)
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wd"] = plan["plan_day"].dt.dayofweek
    plan["ph"] = (((plan["plan_day"].dt.day - 1) // 7 + 1) % 2)
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    act["ph"] = (((act["call_date"].dt.day - 1) // 7 + 1) % 2)

    A = {l: g for l, g in act.groupby("salesperson_code")}
    rows = []
    for lid, g in plan.groupby("sales_line_code"):
        lid = str(lid)
        a = A.get(lid)
        if a is None or not len(a):
            rows.append({"line": lid, "plan_rows": len(g), "act_rows": 0, "note": "无实际数据"})
            continue
        ps, as_ = set(g["customer_code"]), set(a["customer_code"])
        pset, aset = set(zip(g["customer_code"], g["plan_day"])), set(zip(a["customer_code"], a["call_date"]))
        pwd = set(zip(g["customer_code"], g["wd"]))
        awd = set(zip(a["customer_code"], a["wd"]))
        aph = a.groupby("customer_code")["ph"].apply(set).to_dict()
        pp = g.drop_duplicates("customer_code").set_index("customer_code")["ph"].to_dict()
        cover = len(ps & as_) / max(len(ps), 1)
        purity = len(ps & as_) / max(len(as_), 1)
        rows.append({
            "line": lid,
            "plan_rows": len(g), "plan_stores": len(ps),
            "act_rows": len(a), "act_stores": len(as_),
            "cover": round(cover, 4), "purity": round(purity, 4),
            "wd_match": round(len(pwd & awd) / max(len(pwd), 1), 4),
            "sameday": round(len(pset & aset) / max(len(pset), 1), 4),
            "phase": round(float(np.mean([pp[c] in aph.get(c, set()) for c in pp])), 4) if pp else np.nan,
            "qty": round(len(a) / max(len(g), 1), 3),
            "note": "",
        })
    d = pd.DataFrame(rows)
    d = d[d["act_rows"] > 0].copy()

    def kind(r):
        if r["cover"] >= 0.9 and r["wd_match"] >= 0.75 and r["sameday"] >= 0.6:
            return "照做型"
        if r["cover"] >= 0.9 and r["wd_match"] < 0.75:
            return "地块同步·星期偏移"
        if r["cover"] < 0.9 and r["purity"] >= 0.9:
            return "少跑但没跑偏"
        if r["cover"] >= 0.9:
            return "地块同步·日期松散"
        return "漂移/混合"

    d["kind"] = d.apply(kind, axis=1)
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT / "all_reps.csv", index=False)

    print(f"计划版本: {PLAN_XLSX.name} | 有实际数据的线: {len(d)}")
    print("\n分型分布:")
    cnt = d["kind"].value_counts()
    for k, v in cnt.items():
        sub = d[d["kind"] == k]
        print(f"  {k:18s} {v:>4} 条 ({v/len(d)*100:4.1f}%) | 覆盖中位 {sub['cover'].median():.3f} "
              f"| 星期中位 {sub['wd_match'].median():.3f} | 同日中位 {sub['sameday'].median():.3f} "
              f"| 量比中位 {sub['qty'].median():.2f}")
    print("\n整体分位:")
    for c in ("cover", "purity", "wd_match", "sameday", "phase", "qty"):
        q = d[c].quantile([.1, .25, .5, .75, .9]).round(3)
        print(f"  {c:9s} p10 {q[.1]:.3f} p25 {q[.25]:.3f} 中位 {q[.5]:.3f} p75 {q[.75]:.3f} p90 {q[.9]:.3f}")
    # 两轴交叉表: 地块 × 星期
    bc = pd.cut(d["cover"], [0, .6, .8, .9, 1.01], labels=["<60%", "60-80%", "80-90%", "≥90%"])
    bw = pd.cut(d["wd_match"], [0, .5, .7, .9, 1.01], labels=["<50%", "50-70%", "70-90%", "≥90%"])
    print("\n交叉表 (行=地块一致度 cover, 列=星期一致度 wd_match):")
    print(pd.crosstab(bc, bw).to_string())
    print(f"\n明细: {OUT/'all_reps.csv'}")


if __name__ == "__main__":
    main()