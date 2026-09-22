# -*- coding: utf-8 -*-
"""TOP5(采纳率最高) 人物画像 — 地盘形状 + 星期模板 + 干活方式.

不输出统计表, 输出可写成"人话"的事实: 他的店长什么样、一个大工作日先在哪片、
每片多大、片区之间多远、店内多密、日期听不听话、欠访去哪了。

口径 (H3): res7 格 → 相邻格连通块 = "片区"(老板: 网格不严谨, 用概率表达)
禁用: 基于 xlsx"拜访顺序"串链算距离 (AGENTS.md 铁律, 该字段非业务顺序)
"""
from __future__ import annotations

import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KM = 111.0


def load_names() -> dict:
    d = pd.read_excel("/Users/ghb/Downloads/全部.xlsx", usecols=["district", "区县名称", "city", "城市名称"])
    d["district"] = d["district"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    d["city"] = d["city"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    dn = dict(zip(d["district"], d["区县名称"]))
    cn = dict(zip(d["city"], d["城市名称"]))
    return {"district": dn, "city": cn}


def haversine_km(a, b):
    R = 6371.0088
    la1, lo1 = np.radians(a[0]), np.radians(a[1])
    la2, lo2 = np.radians(b[0]), np.radians(b[1])
    d = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(d))


def components(cells):
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


def portrait(lid, plan, act, names):
    pl = plan[plan["sales_line_code"] == lid].copy()
    pl["lat"] = pd.to_numeric(pl["lat"], errors="coerce")
    pl["lng"] = pd.to_numeric(pl["lng"], errors="coerce")
    sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    a = act[act["salesperson_code"] == lid]
    cmap = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code").set_index("customer_code")[["lat", "lng"]]
    a = a.join(cmap, on="customer_code")
    out = {"线": lid, "店数": len(sto), "目标店数": pl["customer_code"].nunique(),
           "月访次": len(pl), "实际到访": len(a)}
    # 行政位置
    st_pl = pl.drop_duplicates("customer_code")
    top_city = st_pl["city"].astype(str).value_counts().head(2)
    top_dist = st_pl["district"].astype(str).value_counts().head(3)
    out["城市"] = ", ".join(f"{names['city'].get(c, c)}×{n}" for c, n in top_city.items())
    out["区县"] = ", ".join(f"{names['district'].get(c, c)}×{n}" for c, n in top_dist.items())
    # 经纬度跨度
    out["跨度km"] = round(float((sto["lat"].max() - sto["lat"].min()) * KM), 1)
    la, lo = float(sto["lat"].mean()), float(sto["lng"].mean())
    out["东西km"] = round(float((sto["lng"].max() - sto["lng"].min()) * KM * np.cos(np.radians(la))), 1)
    out["南北km"] = round(float((sto["lat"].max() - sto["lat"].min()) * KM), 1)
    # H3 片区
    cells = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7) for r in sto.itertuples()}
    comp = components(list(cells.values()))
    sto = sto.assign(blk=[comp[cells[c]] for c in sto["customer_code"]])
    sizes = sto.groupby("blk").size().sort_values(ascending=False)
    out["片区数"] = len(sizes)
    out["片区规模"] = [int(x) for x in sizes.head(6).values]
    # 每片区 bbox 面积与半径
    ext, rad = [], []
    for b, g in sto.groupby("blk"):
        la0 = g["lat"].mean()
        w = (g["lng"].max() - g["lng"].min()) * KM * np.cos(np.radians(la0))
        h = (g["lat"].max() - g["lat"].min()) * KM
        ext.append(w * h)
        c = (g["lat"].mean(), g["lng"].mean())
        rad.append(max(haversine_km(c, (r.lat, r.lng)) for r in g.itertuples()))
    out["片区面积km2"] = [round(float(x), 1) for x in sorted(ext, reverse=True)[:5]]
    out["片区半径km中位"] = round(float(np.median(rad)), 2)
    # 片区间距离
    cent = {b: (g["lat"].mean(), g["lng"].mean()) for b, g in sto.groupby("blk")}
    keys = list(cent)
    if len(keys) > 1:
        dm = [haversine_km(cent[i], cent[j]) for i in keys for j in keys if i < j]
        out["片区间km 最小/中位/最大"] = (round(float(min(dm)), 2), round(float(np.median(dm)), 2), round(float(max(dm)), 1))
    # 店内密度: 最近邻
    bad = []
    for b, g in sto.groupby("blk"):
        pts = list(zip(g["lat"], g["lng"]))
        for i, p in enumerate(pts):
            bad.append(min(haversine_km(p, q) * 1000 for j, q in enumerate(pts) if j != i)) if len(pts) > 1 else bad.append(np.nan)
    out["店内最近邻m中位"] = int(np.nanmedian(bad)) if bad else None
    # 实际: 星期→片区 模板
    ac = a.copy()
    ac["wd"] = pd.to_datetime(ac["call_date"]).dt.dayofweek
    ac["blk"] = [comp.get(cells.get(c)) for c in ac["customer_code"]]
    ac = ac.dropna(subset=["blk"])
    days = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
    tmpl = {}
    for nm, w in days.items():
        g = ac[ac["wd"] == w]
        if len(g) == 0:
            continue
        vc = g["blk"].value_counts()
        tmpl[nm] = (round(vc.iloc[0] / vc.sum() * 100), len(g), int(vc.iloc[0]), [int(x) for x in vc.values[:3]])
    out["星期模板"] = tmpl
    out["月内片区数"] = ac["blk"].nunique()
    # 每天跑几个片区 / 每天几店
    ac["d"] = pd.to_datetime(ac["call_date"])
    per_day = ac.groupby("d").agg(店=("customer_code", "size"), 片=("blk", "nunique"))
    out["日均店数中位"] = int(per_day["店"].median())
    out["日均片数中位"] = float(per_day["片"].median())
    out["工作日数"] = len(per_day)
    # 日半径 (当天店群离当天质心的最远距离)
    r = []
    for d, g in ac.groupby("d"):
        if len(g) < 2:
            continue
        c = (g["lat"].mean(), g["lng"].mean())
        r.append(max(haversine_km(c, (x.lat, x.lng)) for x in g.itertuples()))
    out["日半径km中位"] = round(float(np.median(r)), 2) if r else None
    # 覆盖与频次: 实际到访店 / 目标店; 店内月访次数分布
    cnt = ac.groupby("customer_code").size()
    out["实际覆盖店"] = int(ac["customer_code"].nunique())
    out["覆盖%"] = round(ac["customer_code"].nunique() / max(pl["customer_code"].nunique(), 1) * 100, 1)
    out["月访1次/2次/≥3次店数"] = [int((cnt == 1).sum()), int((cnt == 2).sum()), int((cnt >= 3).sum())]
    # 欠访: W1 计划未执行店 → 之后是否补回
    acw = ac.assign(wk=((ac["d"].dt.day - 1) // 7 + 1))
    plw = pl.assign(wk=((pd.to_datetime(pl["plan_day"]).dt.day - 1) // 7 + 1))
    mon = pl.groupby("customer_code").size()
    w1 = set(plw[plw["wk"] == 1]["customer_code"])
    miss = sorted(w1 - set(acw[acw["wk"] == 1]["customer_code"]))
    later = set(acw[acw["wk"] >= 2]["customer_code"])
    out["W1计划店"] = len(w1)
    out["W1缺访店"] = len(miss)
    out["其中之后补回"] = len(set(miss) & later)
    out["月访1次的店"] = int((mon == 1).sum())
    # 相位合规
    from orchestration.experience.compliance import phase_hit
    pp = pl.assign(ph=(((pd.to_datetime(pl["plan_day"]).dt.day - 1) // 7 + 1) % 2)).drop_duplicates("customer_code").set_index("customer_code")["ph"].to_dict()
    aph = ac.assign(ph=(((pd.to_datetime(ac["call_date"]).dt.day - 1) // 7 + 1) % 2)).groupby("customer_code")["ph"].apply(set).to_dict()
    out["相位合规%"] = round(phase_hit(pp, aph) * 100, 1)
    return out


def main():
    names = load_names()
    plan = pd.read_excel("/Users/ghb/UFS-demo/8月规划结果-调整.xlsx")
    plan["customer_code"] = plan["customer_code"].astype(str)
    act = pd.read_csv("/Users/ghb/UFS-demo/8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    codes = sys.argv[1:] or ["000699979", "000700020", "000734621", "000782642", "000855388"]
    for lid in codes:
        p = portrait(lid, plan, act, names)
        print("=" * 70)
        for k, v in p.items():
            if k == "星期模板":
                print("  星期模板:")
                for nm, (share, n, top, top3) in v.items():
                    print(f"    {nm}: 主力片区 {share}% (到访 {n} 次, 该片区 {top} 次) 前三片区次数 {top3}")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()