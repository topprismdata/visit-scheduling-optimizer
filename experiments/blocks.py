# -*- coding: utf-8 -*-
"""区块定义 — 业务口径 vs 我的旧几何口径, 按文献三条判据对撞.

老板质疑(2026-09-22): "你分几块有逻辑吗"; "有论文支撑吗"。

文献判据 (Zoltners & Sinha 1983, Management Science 29(11):1237-1256):
  ① 连通性 contiguity  ② 紧凑性 compactness  ③ 工作量平衡 balance
方法定位 (Duque/Ramos/Suriñach 2007, Int. Regional Science Review 30(3):195-220;
        Guo 2008 REDCAP): 这是 regionalization/连通约束聚类, 结果对"连通图与阈值"极敏感。

本模块提供两种口径:
  A. service_blocks : **业务口径** = 服务日(系统指派星期) × H3 res7 连通
  B. geo_blocks     : 旧几何口径 = H3 res7 连通 (忽略业务字段)
两者都返回: store→block, 每块诊断(店数/直径/紧凑度/服务日/实际主力星期), 以及
  线路级: 块数、块内店数CV(平衡)、紧凑度中位、以及 **关键** 星期一致率(实际主力星期==服务日)
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import h3
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.top5_portrait import components, haversine_km  # noqa: E402


def _kompact(pts):
    """紧凑度 = 块内店到质心的中位距离 / 块半径 (越小越紧凑; 0..1)。"""
    if len(pts) < 2:
        return 1.0
    a = np.array(pts)
    c = a.mean(axis=0)
    d = np.sqrt(((a - c) ** 2).sum(axis=1)) * 111.0
    mx = max(float(d.max()), 1e-6)
    return float(np.median(d) / mx)


def _diag(stores, act_wd_by_store, svc_of, blk_name):
    """对一组门店算块诊断. stores: [(code, lat, lng)]"""
    if not stores:
        return None
    codes = [c for c, _, _ in stores]
    pts = [(la, lo) for _, la, lo in stores]
    a = np.array(pts)
    lat_span = (a[:, 0].max() - a[:, 0].min()) * 111.0
    lng_span = (a[:, 1].max() - a[:, 1].min()) * 111.0 * np.cos(np.radians(a[:, 0].mean()))
    diam = float(max(lat_span, lng_span, 1e-6))
    wds = [act_wd_by_store[c] for c in codes if c in act_wd_by_store]
    top_act = Counter(wds).most_common(1)[0][0] if wds else -1
    svc = Counter([svc_of[c] for c in codes if c in svc_of]).most_common(1)
    svc_day = svc[0][0] if svc else -1
    # 服务日 1-based(1=周一) vs 实际星期 0-based(0=周一)
    hit = float(np.mean([1.0 if act_wd_by_store.get(c, -9) == (svc_day - 1) else 0.0 for c in codes])) if (wds and svc_day > 0) else 0.0
    return {"blk": blk_name, "n": len(codes), "diam_km": round(diam, 2),
            "compact": round(_kompact(pts), 3), "svc_day": svc_day, "act_wd": top_act,
            "wd_hit": round(hit, 3), "codes": codes}


def _group_blocks(sto, cells, keyfn):
    """按 keyfn 分组, 组内做 H3 res7 连通分块; 返回 (store→blk, [组诊断])。"""
    groups = {}
    for r in sto:
        groups.setdefault(keyfn(r), []).append(r)
    store2blk, diags = {}, []
    for k, rs in groups.items():
        sub_cells = {r[0]: cells[r[0]] for r in rs if r[0] in cells}
        comp = components(list(sub_cells.values()))
        by_blk = {}
        for code, cell in sub_cells.items():
            by_blk.setdefault(comp[cell], []).append(code)
        ordered = sorted(by_blk.items(), key=lambda kv: -len(kv[1]))
        for i, (b, codes) in enumerate(ordered):
            name = f"{k}-{i+1}" if len(ordered) > 1 else str(k)
            for c in codes:
                store2blk[c] = name
        diags.append((k, ordered, comp))
    return store2blk, diags


def build(plan_line, act_line, svc_col="服务日"):
    """返回 dict: blocks(store→名), block_diag, line_diag(含两条口径对比)。"""
    sto = plan_line.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    sto = [(str(r.customer_code), float(r.lat), float(r.lng), int(getattr(r, svc_col)) if getattr(r, svc_col) == getattr(r, svc_col) else -1)
           for r in sto.itertuples()]
    if not sto or not len(act_line):
        return None
    cells = {c: h3.latlng_to_cell(la, lo, 7) for c, la, lo, _ in sto}
    svc_of = {c: s for c, _, _, s in sto}
    act_wd_by_store = act_line.groupby("customer_code")["wd"].apply(
        lambda s: int(s.value_counts().index[0])).to_dict()

    # A. 业务口径: 服务日 × 连通
    s2b_svc, _ = _group_blocks(sto, cells, lambda r: r[3] if r[3] > 0 else 0)
    # B. 旧几何口径: 忽略服务日
    s2b_geo, _ = _group_blocks(sto, cells, lambda r: 0)

    out = {"blocks": s2b_svc, "blocks_geo": s2b_geo, "detail": [], "diag": {}}
    for name in sorted(set(s2b_svc.values())):
        codes = [c for c, b in s2b_svc.items() if b == name]
        stores = [(c, dict(zip([x[0] for x in sto], [x[1] for x in sto]))[c],
                   dict(zip([x[0] for x in sto], [x[2] for x in sto]))[c]) for c in codes]
        d = _diag(stores, act_wd_by_store, svc_of, name)
        if d:
            out["detail"].append(d)
    out["detail"].sort(key=lambda x: -x["n"])
    n_svc = [d["n"] for d in out["detail"]]
    geo_names = sorted(set(s2b_geo.values()))
    geo_n = [sum(1 for v in s2b_geo.values() if v == g) for g in geo_names]
    hit = np.mean([d["wd_hit"] for d in out["detail"]]) if out["detail"] else 0.0
    out["diag"] = {
        "svc_blocks": len(n_svc), "svc_cv": round(float(np.std(n_svc) / max(np.mean(n_svc), 1e-9)), 3) if n_svc else None,
        "svc_compact": round(float(np.median([d["compact"] for d in out["detail"]])), 3) if out["detail"] else None,
        "geo_blocks": len(geo_n), "geo_cv": round(float(np.std(geo_n) / max(np.mean(geo_n), 1e-9)), 3) if geo_n else None,
        "geo_compact": None,
        "wd_hit_svc": round(float(hit), 3),      # 实际主力星期 == 服务日 的比例
    }
    return out