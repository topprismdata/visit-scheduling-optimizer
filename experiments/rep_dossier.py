# -*- coding: utf-8 -*-
"""逐人行为档案 v2 — 只看区块(计划划给他的地盘), 计划外门店不计入判定.

老板口径(2026-09-22): "我只看区块, 计划外不用管。"

区块定义: 计划门店按 H3 res7 相邻连通块切分 → 一个"区块"= 一块连续商圈。
每人三把尺子(全部只针对计划内的店):
  ① 区块开工率   = 被执行过的计划区块 / 计划区块总数          (他有没有按划分去开工)
  ② 区块内执行率 = 各区块(计划门店被执行比例)的中位            (开了工有没有做全)
  ③ 区块星期一致 = 执行的区块里, 该区块"计划主力星期"被实际执行的比例  (星期听不听话)
辅助(仅参考, 不进结论): 同日率、相位、量比

产出:
  output/rep_behavior/dossier.json / dossier.csv
  docs/reports/2026-09-22-rep-dossier.md      逐人档案(按城市分组, 顺序阅读)
  docs/reports/2026-09-22-rep-dossier.html    可搜索的档案看板

计划版本: 环境变量 PLAN_XLSX (默认《更新后的8月规划》)
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
from experiments.top5_portrait import components, haversine_km, KM  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
OUTDIR = ROOT / "output" / "rep_behavior"
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_names():
    """缓存优先: output/rep_behavior/names_cache.json (离线产物, 避免每次读 24MB Excel)."""
    cache = ROOT / "output/rep_behavior/names_cache.json"
    if cache.exists():
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("city"):
            return {"district": c.get("district", {}), "city": c["city"], "line_districts": c.get("line_districts", {})}
    d = pd.read_excel("/Users/ghb/Downloads/全部.xlsx", usecols=["district", "区县名称", "city", "城市名称"])
    for c in ("district", "city"):
        d[c] = d[c].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(6)
    return {"district": dict(zip(d["district"], d["区县名称"])), "city": dict(zip(d["city"], d["城市名称"]))}


def classify(r):
    worked = r["block_worked_rate"]
    within = r["block_exec_median"]
    wdok = r["block_wd_rate"]
    if r["cover"] < 0.3:
        return "计划与实际几乎不相交"
    if worked < 0.6:
        return "区块大面积没开工"
    if worked < 0.9:
        return "区块缺了没开"
    if within >= 0.85 and wdok >= 0.8:
        return "区块全开·星期照做"
    if within >= 0.85 and wdok < 0.8:
        return "区块全开·星期自己定"
    if within < 0.85 and wdok >= 0.8:
        return "区块全开·区块内欠访"
    if within < 0.85 and wdok < 0.8:
        return "区块全开·店和星期都有欠"
    return "待人工看"


def story(r):
    s = []
    s.append(f"{r['city']}（{r['districts']}）：计划 {r['plan_stores']} 店 / {r['plan_rows']} 次，"
             f"分成 {r['blocks']} 个区块（最大区块 {r['block_sizes'][0]} 店）。")
    if r.get("east_km") is not None:
        s.append(f"地盘东西 {r['east_km']} × 南北 {r['north_km']} km；区块内店距中位 {r.get('nn_median_m')} m。")
    wd = r.get("wd_visits") or []
    act_wd = "/".join(f"{WD[i]}{n}" for i, n in enumerate(wd) if n > 0)
    rest = [WD[i] for i, n in enumerate(wd) if n == 0]
    s.append(f"节奏：{r['workdays']} 个工作日、平均每天 {r.get('daily_avg')} 家店、一天 {r.get('zones_per_day')} 个区块、"
             f"当天作业半径中位 {r.get('day_radius_km')} km；出勤 {act_wd}"
             + (f"；{'、'.join(rest)} 没跑" if rest else "") + "。")
    s.append(f"① 区块开工：{r['blocks']} 块里他开工了 {r['blocks_worked']} 块；"
             f"② 区块内执行率中位 {r['block_exec_median']*100:.0f}%（最弱一块 {r['block_exec_min']*100:.0f}%）；"
             f"③ 区块星期一致 {r['block_wd_rate']*100:.0f}%。")
    s.append(f"参考：覆盖 {r['cover']*100:.0f}%、同日 {r['sameday']*100:.0f}%、相位 {r['phase']*100:.0f}%、量比 {r['qty']}。")
    k = r["kind"]
    if k == "区块全开·星期照做":
        s.append("结论：**计划怎么划他就怎么做**——区块全开工、区块内做全、星期按计划。")
    elif k == "区块全开·星期自己定":
        s.append("结论：区块都开了但**星期由他自己排**，周内顺序不跟计划。")
    elif k == "区块全开·区块内欠访":
        s.append("结论：区块都开了、星期也守，但**区块内没做全**（存在欠访）。")
    elif k == "区块全开·店和星期都有欠":
        s.append("结论：区块开了，但店没做全、星期也没守——属于执行力不足，要具体看到底缺在哪块。")
    elif k == "区块缺了没开":
        s.append("结论：**有 %d 个区块整块没开工**，但他开的那几块做得很好（执行率与星期都守）——先问为什么不去那几块。" % (r["blocks"] - r["blocks_worked"]))
    elif k == "区块大面积没开工":
        s.append("结论：**有区块整块没开工**（%d 块），先问为什么不去，而不是谈执行率。" % (r["blocks"] - r["blocks_worked"]))
    elif k == "计划与实际几乎不相交":
        s.append("结论：计划与实际几乎不相交——先查这块地盘是不是搞错了（管辖/门店清单），再谈行为。")
    else:
        s.append("结论：需要人工看。")
    if r.get("cold_blocks"):
        s.append("最冷的区块（计划内执行率最低）：%s。" % r["cold_blocks"])
    return " ".join(s)


def dossier_for(lid, pl, a, names):
    pl = pl.copy()
    pl["lat"] = pd.to_numeric(pl["lat"], errors="coerce")
    pl["lng"] = pd.to_numeric(pl["lng"], errors="coerce")
    pl["plan_day"] = pd.to_datetime(pl["plan_day"]).dt.normalize()
    pl["wd"] = pl["plan_day"].dt.dayofweek
    pl["ph"] = ((pl["plan_day"].dt.day - 1) // 7 + 1) % 2
    sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    if not len(a) or not len(sto):
        return None
    a = a.copy()
    a["call_date"] = pd.to_datetime(a["call_date"]).dt.normalize()
    a["wd"] = a["call_date"].dt.dayofweek
    a["ph"] = ((a["call_date"].dt.day - 1) // 7 + 1) % 2

    r = {"line": lid}
    r["city"] = names["city"].get(str(pl["city"].iloc[0]).zfill(6), str(pl["city"].iloc[0]))
    if names.get("line_districts", {}).get(lid):
        r["districts"] = names["line_districts"][lid]
    else:
        topd = pl["district"].astype(str).value_counts().head(2)
        r["districts"] = ", ".join(f"{names['district'].get(d.zfill(6), d)}×{n}" for d, n in topd.items())
    r["plan_stores"] = int(sto["customer_code"].nunique())
    r["plan_rows"] = int(len(pl))
    r["act_visits"] = int(len(a))
    r["act_stores"] = int(a["customer_code"].nunique())

    ps, as_ = set(sto["customer_code"]), set(a["customer_code"])
    pset = set(zip(pl["customer_code"], pl["plan_day"]))
    aset = set(zip(a["customer_code"], a["call_date"]))
    pwd = set(zip(pl["customer_code"], pl["wd"]))
    awd = set(zip(a["customer_code"], a["wd"]))
    aph = a.groupby("customer_code")["ph"].apply(set).to_dict()
    pp = pl.drop_duplicates("customer_code").set_index("customer_code")["ph"].to_dict()
    r["cover"] = round(len(ps & as_) / max(len(ps), 1), 3)
    r["purity"] = round(len(ps & as_) / max(len(as_), 1), 3)   # 仅供内部参考
    r["wd_match"] = round(len(pwd & awd) / max(len(pwd), 1), 3)
    r["sameday"] = round(len(pset & aset) / max(len(pset), 1), 3)
    r["phase"] = round(float(np.mean([pp[c] in aph.get(c, set()) for c in pp])), 3) if pp else 0.0
    r["qty"] = round(len(a) / max(len(pl), 1), 2)
    r["n_never"] = len(ps - as_)

    # ---- 区块(计划门店的 H3 连通块) ----
    cells = {x.customer_code: h3.latlng_to_cell(float(x.lat), float(x.lng), 7) for x in sto.itertuples()}
    comp = components(list(cells.values()))
    blk_of = {c: comp[cells[c]] for c in cells}
    sto2 = sto.assign(blk=[blk_of[c] for c in sto["customer_code"]])
    # 计划侧: 每区块的门店/星期分布
    pl_b = pl.assign(blk=pl["customer_code"].map(blk_of))
    plan_blk_stores = pl_b.groupby("blk")["customer_code"].nunique().to_dict()
    plan_blk_wd = {b: g["wd"].value_counts() for b, g in pl_b.groupby("blk")}
    # 实际侧: 只看计划内的店
    a_in = a[a["customer_code"].isin(ps)].assign(blk=lambda d: d["customer_code"].map(blk_of))
    act_by_blk = a_in.groupby("blk")["customer_code"].apply(set).to_dict()
    act_wd_by_blk = {b: g["wd"].value_counts() for b, g in a_in.groupby("blk")}
    blocks = sorted(plan_blk_stores, key=lambda x: -plan_blk_stores[x])
    want_by_blk = pl_b.groupby("blk")["customer_code"].apply(set).to_dict()
    cent_by_blk = sto2.groupby("blk")[["lat", "lng"]].mean().to_dict("index")
    exec_rates, wd_hits, worked = [], [], 0
    cold = []
    block_detail = []
    for bi, b in enumerate(blocks):
        want = want_by_blk.get(b, set())
        got = act_by_blk.get(b, set()) & want
        rate = len(got) / max(len(want), 1)
        exec_rates.append(rate)
        if got:
            worked += 1
            top_wd = int(plan_blk_wd[b].index[0])
            aw = act_wd_by_blk.get(b)
            ok = bool(aw is not None and top_wd in set(aw.index))
            wd_hits.append(1.0 if ok else 0.0)
            if rate < 0.6:
                cold.append((b, int(len(want)), round(rate * 100)))
        pw = plan_blk_wd.get(b)
        pw_top = int(pw.index[0]) if pw is not None and len(pw) else None
        aw = act_wd_by_blk.get(b)
        aw_top = int(aw.index[0]) if aw is not None and len(aw) else None
        c = cent_by_blk.get(b, {})
        block_detail.append({"块": f"块{bi+1}", "中心": f"{c.get('lat',0):.3f},{c.get('lng',0):.3f}",
                             "计划店": len(want),
                             "跑到的计划店": len(got), "执行率": round(rate, 3),
                             "计划星期": WD[pw_top] if pw_top is not None else "",
                             "实际主力星期": WD[aw_top] if aw_top is not None else "未开工"})
    r["blocks"] = len(blocks)
    r["block_sizes"] = [int(plan_blk_stores[b]) for b in blocks][:5]
    r["block_detail"] = block_detail
    r["blocks_worked"] = worked
    r["block_worked_rate"] = round(worked / max(len(blocks), 1), 3)
    r["block_exec_median"] = round(float(np.median(exec_rates)), 3) if exec_rates else 0.0
    r["block_exec_min"] = round(float(np.min(exec_rates)), 3) if exec_rates else 0.0
    r["block_wd_rate"] = round(float(np.mean(wd_hits)), 3) if wd_hits else 0.0
    r["cold_blocks"] = "; ".join(f"区块×{n}店 仅执行 {p}%" for _, n, p in sorted(cold, key=lambda x: x[2])[:3])
    # 形状
    if len(sto2):
        la = sto2["lat"].mean()
        r["east_km"] = round(float((sto2["lng"].max() - sto2["lng"].min()) * KM * np.cos(np.radians(la))), 1)
        r["north_km"] = round(float((sto2["lat"].max() - sto2["lat"].min()) * KM), 1)
        nn = []
        for b, g in sto2.groupby("blk"):
            pts = list(zip(g["lat"], g["lng"]))
            for i, p in enumerate(pts):
                nn.append(min(haversine_km(p, q) * 1000 for j, q in enumerate(pts) if j != i)) if len(pts) > 1 else None
        r["nn_median_m"] = int(np.nanmedian(nn)) if nn else None
    # 节奏(实际全部到访; 含计划外, 因为要描述他"怎么干活")
    cmap = sto.set_index("customer_code")[["lat", "lng"]]
    ac = a.join(cmap, on="customer_code").dropna(subset=["lat", "lng"])
    per_day = ac.groupby("call_date").agg(店=("customer_code", "size"))
    r["workdays"] = int(len(per_day))
    r["daily_median"] = int(per_day["店"].median()) if len(per_day) else 0
    r["daily_avg"] = round(len(a) / max(len(per_day), 1), 1)
    wdc = a["wd"].value_counts().to_dict()
    r["wd_visits"] = [int(wdc.get(i, 0)) for i in range(7)]
    rad = []
    for d, g in ac.groupby("call_date"):
        if len(g) < 2:
            continue
        c = (g["lat"].mean(), g["lng"].mean())
        rad.append(max(haversine_km(c, (x.lat, x.lng)) for x in g.itertuples()))
    r["day_radius_km"] = round(float(np.median(rad)), 2) if rad else None
    zpd = ac.assign(blk=lambda d: d["customer_code"].map(blk_of)).dropna(subset=["blk"]).groupby("call_date")["blk"].nunique()
    r["zones_per_day"] = round(float(zpd.median()), 1) if len(zpd) else None
    r["freq_1"] = int((a.groupby("customer_code").size() == 1).sum())
    r["freq_2p"] = int((a.groupby("customer_code").size() >= 2).sum())
    r["kind"] = classify(r)
    r["story"] = story(r)
    return r


def main():
    print("[1/4] 读城市名映射", flush=True)
    names = load_names()
    print("[2/4] 读计划", flush=True)
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    print("[3/4] 读实际走访", flush=True)
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    A = {l: g for l, g in act.groupby("salesperson_code")}
    recs = []
    done = 0
    for lid, pl in plan.groupby("sales_line_code"):
        done += 1
        if done % 50 == 0:
            print(f"  PROGRESS {done}", flush=True)
        try:
            d = dossier_for(lid, pl, A.get(lid, act.iloc[0:0]), names)
        except Exception as e:
            print(f"  [warn] {lid}: {type(e).__name__} {str(e)[:70]}")
            continue
        if d:
            recs.append(d)
    print(f"[4/4] 计算完成 {len(recs)} 人, 写出", flush=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "dossier.json").write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame([{k: v for k, v in r.items()} for r in recs]).to_csv(OUTDIR / "dossier.csv", index=False)

    md = ["# 逐人行为档案 · 2026-08（只看区块；计划外门店不计入判定）\n",
          f"> 计划版本：{PLAN_XLSX.name}。三把尺子：区块开工率 / 区块内执行率 / 区块星期一致。口径见 `experiments/rep_dossier.py`。\n"]
    df = pd.DataFrame([{"city": r["city"], "line": r["line"], "kind": r["kind"], "story": r["story"],
                        "worked": r["block_worked_rate"], "exec": r["block_exec_median"]} for r in recs])
    for city, g in df.sort_values(["city", "exec"]).groupby("city"):
        md.append(f"\n## {city}（{len(g)} 条线）\n")
        for x in g.itertuples():
            md.append(f"### {x.line} · {x.kind}\n\n{x.story}\n")
            det = next((r.get("block_detail") for r in recs if r["line"] == x.line), None)
            if det:
                md.append("| 块 | 中心 | 计划店 | 跑到 | 执行率 | 计划星期 | 实际主力星期 |\n|---|---|---|---|---|---|---|")
                for d in det[:12]:
                    md.append(f"| {d['块']} | {d['中心']} | {d['计划店']} | {d['跑到的计划店']} | {d['执行率']*100:.0f}% | {d['计划星期']} | {d['实际主力星期']} |")
                md.append("")
    md_text = "\n".join(md)
    (ROOT / "docs/reports/2026-09-22-rep-dossier.md").write_text(md_text, encoding="utf-8")
    print(f"档案 {len(recs)} 人 | Markdown {len(md_text)/1024:.0f} KB")
    print("\n分型:")
    print(df["kind"].value_counts().to_string())
    full = sum(1 for r in recs if r["block_worked_rate"] >= 0.999)
    part = sum(1 for r in recs if r["block_worked_rate"] < 0.999)
    print(f"\n区块开工: 全部区块都开工 {full} 人 | 有区块没开工 {part} 人")


if __name__ == "__main__":
    main()