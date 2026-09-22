# -*- coding: utf-8 -*-
"""月内适应 vs 跨月投影 — 决定性对照实验 (v0.4 §9).

老板 ML framing: "第一周、第二周是训练样本"。
本脚本把月循环拆成可证伪的对照:

  A. 训练窗口: W1-W2 批量训练 vs 每周在线更新 (prequential log-loss, 片区混合)
  B. 月内适应 (店级): 原计划 / 欠账插入 (adapt_plan) / 模型重排 → W3-W4 槽位 Jaccard
  C. 粒度诊断 (店级): 习惯槽位重复率 / 客户群稳定性 → 说明为什么店级指标全线失败 (月访轮换)
  D. 跨月投影 (片区级): W1-W2 后验预测 W3-W4 星期 → 命中率 vs 原计划 vs 随机

用法:
  .venv/bin/python experiments/validate_projection.py [--part A|B|C|D|all]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UFS = Path("/Users/ghb/UFS-demo")
KPI_F = UFS / "采纳执行-8月.xlsx"
PLAN_F = UFS / "8月规划结果-调整.xlsx"
ACT_F = UFS / "8月实际走访数据-了解实际情况.csv"


def load():
    kpi = pd.read_excel(KPI_F)
    ok = set(kpi[kpi["销售计划数"] >= 100]["sales_line_code"])
    plan = pd.read_excel(PLAN_F)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wd"] = plan["plan_day"].dt.dayofweek
    plan["wk"] = (plan["plan_day"].dt.day - 1) // 7 + 1
    plan["ph"] = plan["wk"] % 2
    act = pd.read_csv(ACT_F, encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    act["wk"] = (act["call_date"].dt.day - 1) // 7 + 1
    act["ph"] = act["wk"] % 2
    crd = plan.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    cell = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7)
            for r in crd.itertuples()}
    return ok, plan, act, cell


def components(cells):
    """H3 res7 相邻格连通块 = 片区 (老板: 网格不严谨 → 概率表达)."""
    cs = set(cells)
    comp = {}
    for c in cs:
        if c in comp:
            continue
        stack, grp = [c], set()
        while stack:
            x = stack.pop()
            if x in grp:
                continue
            grp.add(x)
            stack += [nb for nb in h3.grid_disk(x, 1) if nb in cs and nb not in grp]
        g = min(grp)
        for x in grp:
            comp[x] = g
    return comp


def part_C(ok, plan, act, cell):
    """店级粒度诊断: 为什么店级适配指标全线失败."""
    rr, rr_wd, pl_hit, cov = [], [], [], []
    for lid in ok:
        pl = plan[plan["sales_line_code"] == lid]
        if len(pl) < 100:
            continue
        a = act[act["salesperson_code"] == lid]
        t, v = a[a["wk"] <= 2], a[a["wk"] >= 3]
        if len(t) < 20 or len(v) < 20:
            continue
        T = set(zip(t["customer_code"], t["wd"], t["ph"]))
        V = set(zip(v["customer_code"], v["wd"], v["ph"]))
        if not T:
            continue
        rr.append(len(T & V) / len(T))
        T2 = set(zip(t["customer_code"], t["wd"]))
        V2 = set(zip(v["customer_code"], v["wd"]))
        rr_wd.append(len(T2 & V2) / len(T2))
        P3 = set(zip(pl[pl["wk"] >= 3]["customer_code"], pl[pl["wk"] >= 3]["wd"],
                     pl[pl["wk"] >= 3]["ph"]))
        pl_hit.append(len(P3 & V) / len(P3) if P3 else np.nan)
        cover.append(len(set(v["customer_code"]) & set(t["customer_code"]))
                     / len(set(v["customer_code"])))
    print(f"C) 店级粒度诊断 | 线 {len(rr)}")
    print(f"   习惯槽位重复率(店,星期,相位) {np.nanmean(rr):.3f}")
    print(f"   只对齐星期(店,星期)          {np.nanmean(rr_wd):.3f}")
    print(f"   原计划 W3-W4 槽位命中率      {np.nanmean(pl_hit):.3f}")
    print(f"   客户群稳定性(W3W4∩W1W2)     {np.nanmean(cover):.3f}")
    print("   → 店级槽位重复率低 = 月度轮访(多数店月访一次), 非业代乱; 正确粒度=片区级概率")


def part_D(ok, plan, act, cell):
    """跨月投影(片区级): 后验预测星期 vs 原计划 vs 随机."""
    post, plana, uni, top2 = [], [], [], []
    n = 0
    for lid in ok:
        pl = plan[plan["sales_line_code"] == lid]
        if len(pl) < 100:
            continue
        a = act[act["salesperson_code"] == lid]
        a = a[a["customer_code"].isin(cell)]
        if len(a) < 60:
            continue
        comp = components([cell[c] for c in a["customer_code"]])
        a = a.assign(blk=[comp[cell[c]] for c in a["customer_code"]])
        t, v = a[a["wk"] <= 2], a[a["wk"] >= 3]
        if len(t) < 20 or len(v) < 20:
            continue
        n += 1
        pz, tz = {}, {}
        for z, g in t.groupby("blk"):
            vc = g["wd"].value_counts()
            pz[z] = vc
            tz[z] = set(vc.index[:2])
        pd_wd = (pl[pl["wk"] >= 3].drop_duplicates("customer_code")
                 .set_index("customer_code")["wd"].to_dict())
        for r in v.itertuples():
            vc = pz.get(r.blk)
            if vc is None:
                continue
            post.append(int(vc.index[0]) == r.wd)
            uni.append(0.2)
            top2.append(r.wd in tz.get(r.blk, set()))
            pw = pd_wd.get(r.customer_code)
            if pw is not None:
                plana.append(int(pw) == r.wd)
    print(f"D) 跨月投影(片区级) | 线 {n} | W3-W4 实际访问 {len(post)} 人次")
    print(f"   ① 后验投影预测星期 命中率 {np.mean(post):.3f}")
    print(f"   ② 原计划星期 命中率       {np.mean(plana):.3f}")
    print(f"   ③ 随机基线               {np.mean(uni):.3f}")
    print(f"   ④ 实际访问落在片区top2星期 {np.mean(top2):.3f}")
    print(f"   → 后验投影 vs 原计划: {np.mean(post) - np.mean(plana):+.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="CD", choices=["A", "B", "C", "D", "all", "CD"])
    a = ap.parse_args()
    ok, plan, act, cell = load()
    if a.part in ("C", "CD", "all"):
        part_C(ok, plan, act, cell)
    if a.part in ("D", "CD", "all"):
        part_D(ok, plan, act, cell)


if __name__ == "__main__":
    main()