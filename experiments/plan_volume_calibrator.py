# -*- coding: utf-8 -*-
"""计划校准 v2 — 只改"量": 剔除零执行门店 + 频次对齐实际产能; 服务日与日期尽量不动.

教训(v1 失败): 用两周实际众数重排星期 → 样本外更差(改善5%/变差55%)。所以 v2:
  ① 门店: 训练期(W1–W2)从未到访的计划门店 → 从计划行中剔除(不是改星期, 是不再计划)
  ② 频次: 训练期实际到访次数 ×2(半个月→月) 作为该店计划行数
  ③ 日期: 优先沿用**现行计划里该店已有的日期**(不动日期); 不足的行次补在该店"服务日"对应的剩余日期上
  ④ 服务日/相位: 完全不动(样本外命中 88.1%, 动则更差)

样本外验证: 训练 W1–W2 → 生成 W3–W4 计划 P2, 与现行计划 P0 对 W3–W4 实际评分。
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestration.experience.compliance import store_compliance  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))


def wk(d):
    return (d.day - 1) // 7 + 1


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wk"] = plan["plan_day"].apply(wk)
    plan["wd"] = plan["plan_day"].dt.dayofweek
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wk"] = act["call_date"].apply(wk)
    act["wd"] = act["call_date"].dt.dayofweek
    A = {l: g for l, g in act.groupby("salesperson_code")}

    rows = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        if al is None or not len(al) or not len(pl):
            continue
        tr = al[al["wk"] <= 2]
        tg = al[al["wk"] >= 3]
        p_tr = pl[pl["wk"] <= 2]
        p_tg = pl[pl["wk"] >= 3]
        if not len(tr) or not len(tg) or not len(p_tg):
            continue
        visited_tr = set(tr["customer_code"])
        visits_tr = tr.groupby("customer_code").size().to_dict()
        # ---- P2: 剔死重 + 频次对齐 ----
        keep = p_tg[p_tg["customer_code"].isin(visited_tr)].copy()
        keep["need"] = keep["customer_code"].map(lambda c: min(4, max(1, int(visits_tr.get(c, 1)) * 2)))
        # 每店保留其"现有日期"的前 need 个; 不足则用该店服务日对应的剩余日期补
        out_rows = []
        svc_dates = {}
        for c, g in p_tg.groupby("customer_code"):
            svc = int(g["服务日"].iloc[0]) if g["服务日"].iloc[0] == g["服务日"].iloc[0] else -1
            svc_dates[c] = sorted(p_tg[p_tg["wd"] == svc - 1]["plan_day"].unique()) if svc > 0 else []
        for c, g in keep.groupby("customer_code"):
            need = int(g["need"].iloc[0])
            dates = list(g.sort_values("plan_day")["plan_day"])[:need]
            if len(dates) < need:
                for d in svc_dates.get(c, []):
                    if len(dates) >= need:
                        break
                    if d not in dates:
                        dates.append(d)
            for d in dates:
                out_rows.append((c, pd.Timestamp(d)))
        # ---- 评分 ----
        A_tg = set(zip(tg["customer_code"], tg["call_date"]))
        awd = set(zip(tg["customer_code"], tg["wd"]))
        as_ = set(tg["customer_code"])
        res = {"line": lid}
        for tag, P in (("P0", set(zip(p_tg["customer_code"], p_tg["plan_day"]))), ("P2", set(out_rows))):
            if not P:
                continue
            Pw = set((c, pd.Timestamp(d).dayofweek) for c, d in P)
            Ps = set(c for c, _ in P)
            res[f"{tag}_rows"] = len(P)
            res[f"{tag}_sameday"] = round(len(P & A_tg) / len(P) * 100, 1)
            res[f"{tag}_wd"] = round(len(Pw & awd) / max(len(Pw), 1) * 100, 1)
            res[f"{tag}_cover"] = round(len(Ps & as_) / max(len(Ps), 1) * 100, 1)
            pc = Counter(c for c, _ in P)
            ac = Counter(tg["customer_code"])
            res[f"{tag}_compliance"] = round(store_compliance(dict(pc), dict(ac)) * 100, 1)
        res["dropped_stores"] = len(set(p_tg["customer_code"]) - visited_tr)
        res["dropped_rows"] = len(p_tg) - len(out_rows) if len(out_rows) else len(p_tg)
        rows.append(res)

    d = pd.DataFrame(rows)
    outdir = ROOT / "output/rep_behavior"
    d.to_csv(outdir / "plan_volume_calibration.csv", index=False)
    print(f"线数 {len(d)}")
    for m in ("sameday", "wd", "cover", "compliance"):
        c0, c2 = f"P0_{m}", f"P2_{m}"
        print(f"  {m:11s} 现行 中位 {d[c0].median():6.1f}  →  校准v2 中位 {d[c2].median():6.1f}"
              f"   (改善 {(d[c2]>d[c0]).mean()*100:.0f}% / 持平 {(d[c2]==d[c0]).mean()*100:.0f}% / 变差 {(d[c2]<d[c0]).mean()*100:.0f}%)")
    print(f"  计划行数    现行 中位 {d['P0_rows'].median():.0f}  →  v2 中位 {d['P2_rows'].median():.0f}"
          f"（剔除零执行门店 {d['dropped_stores'].median():.0f} 家）")
    print(f"\n明细: {outdir/'plan_volume_calibration.csv'}")


if __name__ == "__main__":
    main()