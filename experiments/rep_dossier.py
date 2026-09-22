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
from experiments.blocks import build as build_blocks  # noqa: E402

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


def classify(r):  # noqa: D401  (服务日块口径)
    worked = r["block_worked_rate"]
    within = r["block_exec_median"]
    wdok = r.get("svc_wd_hit", r.get("block_wd_rate", 0))
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
             f"业务上分成 {r['blocks']} 个区块（服务日×空间连通；最大块 {r['block_sizes'][0] if r['block_sizes'] else 0} 店）。")
    s.append(f"地盘东西 {r['east_km']} × 南北 {r['north_km']} km；块内店距中位 {r['nn_median_m']} m；"
             f"块大小均衡度 CV {r['block_balance_cv']}、紧凑度 {r['block_compact']}。")
    wd = r.get("wd_visits") or []
    act_wd = "/".join(f"{WD[i]}{n}" for i, n in enumerate(wd) if n > 0)
    rest = [WD[i] for i, n in enumerate(wd) if n == 0]
    s.append(f"节奏：{r['workdays']} 个工作日、平均每天 {r['daily_avg']} 家店、一天 {r['zones_per_day']} 个区块、"
             f"当天作业半径中位 {r['day_radius_km']} km；出勤 {act_wd}" + (f"；{'、'.join(rest)} 没跑" if rest else "") + "。")
    s.append(f"① 区块开工：{r['blocks']} 块里开工 {r['blocks_worked']} 块；② 块内执行率中位 {r['block_exec_median']*100:.0f}%"
             f"（最弱 {r['block_exec_min']*100:.0f}%）；③ **实际星期 == 服务日 命中 {r['svc_wd_hit']*100:.0f}%**（缺口 {r['wd_gap_stores']} 店）。")
    if r.get("wd_gap_blocks"):
        s.append(f"星期缺口最大的块：{r['wd_gap_blocks']}。")
    s.append(f"参考：覆盖 {r['cover']*100:.0f}%、同日 {r['sameday']*100:.0f}%、相位 {r['phase']*100:.0f}%、量比 {r['qty']}。")
    k = r["kind"]
    if k == "区块全开·星期照做":
        s.append("结论：**计划怎么划他就怎么做**——区块全开工、块内做全、星期与服务日一致。")
    elif k == "区块全开·星期自己定":
        s.append("结论：区块都开了，但**他按自己的星期跑**，服务日与实际主力星期不符。")
    elif k == "区块全开·区块内欠访":
        s.append("结论：区块都开了、星期也对，但**块内没做全**（存在欠访）。")
    elif k == "区块全开·店和星期都有欠":
        s.append("结论：区块开了，但店没做全、星期也没跟服务日——要具体看到底缺在哪块。")
    elif k == "区块缺了没开":
        s.append(f"结论：有 {r['blocks'] - r['blocks_worked']} 个区块整块没开工；开的那几块做得不错——先问为什么不去那几块。")
    elif k == "区块大面积没开工":
        s.append("结论：**有相当比例区块整块没开工**，先问为什么不去，而不是谈执行率。")
    elif k == "计划与实际几乎不相交":
        s.append("结论：计划与实际几乎不相交——先查这块地盘是不是搞错了（管辖/门店清单），再谈行为。")
    else:
        s.append("结论：需要人工看。")
    return " ".join(s)


def dossier_for(lid, pl, a, names):
    """单条线档案: 业务口径区块(服务日 × H3连通) + 节奏 + 对计划偏差."""
    pl = pl.copy()
    pl["lat"] = pd.to_numeric(pl["lat"], errors="coerce")
    pl["lng"] = pd.to_numeric(pl["lng"], errors="coerce")
    pl["plan_day"] = pd.to_datetime(pl["plan_day"]).dt.normalize()
    pl["wd"] = pl["plan_day"].dt.dayofweek
    pl["ph"] = ((pl["plan_day"].dt.day - 1) // 7 + 1) % 2
    a = a.copy()
    a["call_date"] = pd.to_datetime(a["call_date"]).dt.normalize()
    a["wd"] = a["call_date"].dt.dayofweek
    a["ph"] = ((a["call_date"].dt.day - 1) // 7 + 1) % 2
    sto = pl.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    if not len(a) or not len(sto):
        return None
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
    pset = set(zip(pl["customer_code"], pl["plan_day"])); aset = set(zip(a["customer_code"], a["call_date"]))
    pwd = set(zip(pl["customer_code"], pl["wd"])); awd = set(zip(a["customer_code"], a["wd"]))
    aph = a.groupby("customer_code")["ph"].apply(set).to_dict()
    pp = pl.drop_duplicates("customer_code").set_index("customer_code")["ph"].to_dict()
    r["cover"] = round(len(ps & as_) / max(len(ps), 1), 3)
    r["purity"] = round(len(ps & as_) / max(len(as_), 1), 3)
    r["wd_match"] = round(len(pwd & awd) / max(len(pwd), 1), 3)
    r["sameday"] = round(len(pset & aset) / max(len(pset), 1), 3)
    r["phase"] = round(float(np.mean([pp[c] in aph.get(c, set()) for c in pp])), 3) if pp else 0.0
    r["qty"] = round(len(a) / max(len(pl), 1), 2)
    r["n_never"] = len(ps - as_)

    # ---- 区块: 服务日 × H3 res7 连通 (文献三判据; 见 experiments/blocks.py) ----
    blk = build_blocks(pl, a)
    if blk is None:
        return None
    dt = blk["detail"]
    got_by_blk = {}
    for d in dt:
        got_by_blk[d["blk"]] = len(set(d["codes"]) & as_)
    detail = []
    for d in dt:
        got = got_by_blk.get(d["blk"], 0)
        detail.append({"块": d["blk"], "计划店": d["n"], "跑到的计划店": got,
                       "执行率": round(got / max(d["n"], 1), 3),
                       "服务日": WD[d["svc_day"] - 1] if d["svc_day"] > 0 else "",
                       "实际主力": WD[d["act_wd"]] if d["act_wd"] >= 0 else "未开工",
                       "星期命中": round(d["wd_hit"], 3), "直径km": d["diam_km"], "紧凑度": d["compact"]})
    r["blocks"] = len(detail)
    r["block_detail"] = detail
    r["blocks_worked"] = sum(1 for d in detail if d["跑到的计划店"] > 0)
    r["block_worked_rate"] = round(r["blocks_worked"] / max(len(detail), 1), 3)
    execv = [d["执行率"] for d in detail]
    r["block_exec_median"] = round(float(np.median(execv)), 3) if execv else 0.0
    r["block_exec_min"] = round(float(np.min(execv)), 3) if execv else 0.0
    r["svc_wd_hit"] = round(float(np.mean([d["星期命中"] for d in detail])), 3) if detail else 0.0
    r["block_balance_cv"] = blk["diag"]["svc_cv"]
    r["block_compact"] = blk["diag"]["svc_compact"]
    r["block_sizes"] = [d["计划店"] for d in detail][:5]
    # 哪些块的"服务日"和实际主力不同(星期缺口, 就是"计划不贴实际"的位置)
    gaps = [d for d in detail if d["服务日"] and d["星期命中"] < 0.999]
    r["wd_gap_blocks"] = "; ".join(
        f"{d['块']}(服务日{d['服务日']}·{d['计划店']}店·命中{d['星期命中']*100:.0f}%·实际主力{d['实际主力']})" for d in gaps[:5])
    r["wd_gap_stores"] = int(round(sum(d["计划店"] * (1 - d["星期命中"]) for d in gaps)))

    # 形状
    la = sto["lat"].mean()
    r["east_km"] = round(float((sto["lng"].max() - sto["lng"].min()) * KM * np.cos(np.radians(la))), 1)
    r["north_km"] = round(float((sto["lat"].max() - sto["lat"].min()) * KM), 1)
    nn = []
    for b, g in sto.assign(blk=[blk["blocks"].get(c) for c in sto["customer_code"]]).groupby("blk"):
        pts = list(zip(g["lat"], g["lng"]))
        for i, pt in enumerate(pts):
            if len(pts) > 1:
                nn.append(min(haversine_km(pt, q) * 1000 for j, q in enumerate(pts) if j != i))
    r["nn_median_m"] = int(np.nanmedian(nn)) if nn else None
    # 节奏
    cmap = sto.set_index("customer_code")[["lat", "lng"]]
    ac = a.join(cmap, on="customer_code").dropna(subset=["lat", "lng"])
    per_day = ac.groupby("call_date").agg(店=("customer_code", "size"))
    r["workdays"] = int(len(per_day))
    r["daily_median"] = int(per_day["店"].median()) if len(per_day) else 0
    r["daily_avg"] = round(len(a) / max(len(per_day), 1), 1)
    wdc = a["wd"].value_counts().to_dict()
    r["wd_visits"] = [int(wdc.get(i, 0)) for i in range(7)]
    rad = []
    for _, g in ac.groupby("call_date"):
        if len(g) < 2:
            continue
        c = (g["lat"].mean(), g["lng"].mean())
        rad.append(max(haversine_km(c, (x.lat, x.lng)) for x in g.itertuples()))
    r["day_radius_km"] = round(float(np.median(rad)), 2) if rad else None
    ac = ac.assign(blk=[blk["blocks"].get(c) for c in ac["customer_code"]])
    zpd = ac.dropna(subset=["blk"]).groupby("call_date")["blk"].nunique()
    r["zones_per_day"] = round(float(zpd.median()), 1) if len(zpd) else None
    freq = a.groupby("customer_code").size()
    r["freq_1"] = int((freq == 1).sum()); r["freq_2p"] = int((freq >= 2).sum())
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
                md.append("| 块(服务日) | 计划店 | 跑到 | 执行率 | 服务日 | 实际主力 | 星期命中 | 直径km | 紧凑度 |\n|---|---|---|---|---|---|---|---|---|")
                for d in det[:12]:
                    md.append(f"| {d['块']} | {d['计划店']} | {d['跑到的计划店']} | {d['执行率']*100:.0f}% | {d['服务日']} | {d['实际主力']} | {d['星期命中']*100:.0f}% | {d['直径km']} | {d['紧凑度']} |")
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