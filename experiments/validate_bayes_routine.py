# -*- coding: utf-8 -*-
"""贝叶斯时空习惯学习的 prequential 验证 (v0.4 Experience Bayesian Layer).

方法 (GPT 研究 + 2026-08 612线验证):
  状态 θ_{r,d} = P(zone | rep, weekday), zone = H3 res7 连通块(邻居=同片地)
  更新 α_z ← λ·α_z + x_z (x = 该周该星期几各块访问计数)
  先验 α0 = 城市(线)级 zone 混合 × a (层次收缩)
  评估: prequential log-loss, W1..Wt → 预测 W(t+1), 对比 uniform/static/exp

2026-08 结果 (348 线, 4624 预测样本):
  uniform 1.3609 | static 3.1519 | exp(λ=.7) 0.5012 | Dirichlet(λ=.9,a=5) 0.6254
  → 在线更新 vs uniform -63%, vs static -76% (强证据)
  → 点预测最优 = 指数平滑; Dirichlet 的价值 = posterior strength 置信度门控
用法: python experiments/validate_bayes_routine.py [--lam 0.9] [--a0 5.0]
"""
import argparse
import os
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

UFS = Path("/Users/ghb/UFS-demo")


def components(cells):
    cs = set(cells); comp = {}
    for c in cs:
        if c in comp: continue
        stack = [c]; grp = set()
        while stack:
            x = stack.pop()
            if x in grp: continue
            grp.add(x)
            stack += [nb for nb in h3.grid_disk(x, 1) if nb in cs and nb not in grp]
        g = min(grp)
        for x in grp: comp[x] = g
    return comp


def prequential(act: pd.DataFrame, plan_coords: dict, lam=0.9, a0=5.0, min_visits=60):
    act = act.copy()
    act["wd"] = pd.to_datetime(act["call_date"]).dt.dayofweek
    act["wk"] = (pd.to_datetime(act["call_date"]).dt.day - 1) // 7 + 1
    out = {k: [] for k in ("uniform", "static", "exp", "dirichlet")}
    n = 0
    for lid, g in act.groupby("salesperson_code"):
        g = g[g["customer_code"].isin(plan_coords)]
        if len(g) < min_visits: continue
        comp = components([plan_coords[c] for c in g["customer_code"]])
        g = g.assign(blk=[comp[plan_coords[c]] for c in g["customer_code"]])
        zones = sorted(g["blk"].unique()); K = len(zones)
        if K < 2: continue
        n += 1
        for wd in range(5):
            gw = g[g["wd"] == wd]; weeks = sorted(gw["wk"].unique())
            if len(weeks) < 3: continue
            cnt = {w: np.array([gw[(gw["wk"] == w) & (gw["blk"] == z)].shape[0]
                                for z in zones], float) for w in weeks}
            city = np.array([gw[gw["blk"] == z].shape[0] for z in zones], float)
            city = city / max(city.sum(), 1)
            for t in range(len(weeks) - 1):
                past, x = weeks[:t + 1], cnt[weeks[t + 1]]
                if x.sum() == 0: continue
                pn = x / x.sum()
                preds = {"uniform": np.full(K, 1 / K)}
                cum = sum(cnt[w] for w in past) + 1e-9
                preds["static"] = cum / cum.sum()
                p = city.copy()
                for w in past: p = 0.7 * p + 0.3 * (cnt[w] / max(cnt[w].sum(), 1))
                preds["exp"] = p
                al = city * a0
                for w in past: al = lam * al + cnt[w]
                preds["dirichlet"] = al / al.sum()
                for m, p in preds.items():
                    out[m].append(-float(np.sum(x * np.log(np.clip(p, 1e-9, 1))) / x.sum()))
    return n, {m: float(np.mean(v)) for m, v in out.items()}, len(out["uniform"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lam", type=float, default=0.9)
    ap.add_argument("--a0", type=float, default=5.0)
    a = ap.parse_args()
    KPI = pd.read_excel(UFS / "采纳执行-8月.xlsx")
    ok = set(KPI[KPI["销售计划数"] >= 100]["sales_line_code"])
    PLAN = pd.read_excel(Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx"))))
    PLAN["customer_code"] = PLAN["customer_code"].astype(str)
    crd = PLAN.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    coords = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7)
              for r in crd.itertuples()}
    ACT = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    ACT["customer_code"] = ACT["customer_code"].astype(str)
    ACT = ACT[ACT["salesperson_code"].isin(ok)]
    n, res, ns = prequential(ACT, coords, a.lam, a.a0)
    print(f"线数 {n} | 预测样本 {ns}")
    for m, v in res.items():
        print(f"  {m:10s} {v:.4f}")
