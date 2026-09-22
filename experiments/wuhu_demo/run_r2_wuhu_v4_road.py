# 芜湖 v4: R2'-ALNS + SP 自由重组, OSRM 骑行路网距离 (FOSSGIS routed-bike, WGS84)
# 铁律: OSRM 查询前 GCJ02->WGS84 (gcj2wgs 复用 GeoGov common.py)
import sys, os, json, math, time
from datetime import date
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/Users/ghb/zcode/geogov")
import numpy as np
from core.base import LineData
from core.metric import day_km
import data.road as _road
_road.URL = "http://127.0.0.1:5001/table/v1/driving/"
_road.BATCH = 200
from data.road import fetch_matrix
from common import gcj2wgs
from algos.r2_alns_v2_backup import R2ALNS
from algos.tsp_engine import _exact_open_tsp
from algos.sp_matheuristic import SPMatheuristic, dedupe_pool, _wd
from visit_ir.contract import check_rhythm, slots_per_weekday, slot_index_map, rhythm_ok_dates
from collections import defaultdict as _dd
from preflight import preflight

def build_line(sp):
    all_stores = {}
    for d in sp["days"]:
        for s in d["stores"]: all_stores.setdefault(s["code"], s)
    codes = sorted(all_stores); idx = {c: i for i, c in enumerate(codes)}
    lat = [all_stores[c]["lat"] for c in codes]; lon = [all_stores[c]["lng"] for c in codes]
    # GCJ02 -> WGS84 (OSRM 查询铁律)
    wgs = [gcj2wgs(lo, la) for lo, la in zip(lon, lat)]
    lon_w = [w[0] for w in wgs]; lat_w = [w[1] for w in wgs]
    n = len(codes)
    dates = sorted(date.fromisoformat(d["date"]) for d in sp["days"])
    days_orig = {date.fromisoformat(d["date"]): [idx[s["code"]] for s in d["stores"]] for d in sp["days"]}
    freq = {}
    for d in sp["days"]:
        for s in d["stores"]: freq[s["code"]] = freq.get(s["code"], 0) + 1
    ld = LineData(line_id=sp_id_global, line_name=sp_id_global, codes=codes, lon=lon_w, lat=lat_w,
                  dates=dates, days_orig=days_orig, freq=freq, stores=n, visits=sum(freq.values()))
    return ld, all_stores, codes, lon_w, lat_w

def road_matrix(sp_id, codes, lon_w, lat_w):
    cp = os.path.join(HERE, f"road_codes_{sp_id}.json")
    mp = os.path.join(HERE, f"road_dist_{sp_id}.npy")
    if os.path.exists(mp) and os.path.exists(cp) and json.load(open(cp)) == codes:
        return np.load(mp)
    print(f"  拉取骑行矩阵 {len(codes)}x{len(codes)} (FOSSGIS routed-bike, WGS84)...")
    t0 = time.time()
    D = fetch_matrix(codes, lon_w, lat_w)
    np.save(mp, D); json.dump(codes, open(cp, "w"))
    print(f"  矩阵完成 {time.time()-t0:.0f}s | 中位路网km={np.median(D[D>0]):.2f}")
    return D

def interval_violations(days_dict, min_gap=14):
    vis = {}
    for dd, seq in days_dict.items():
        for c in seq: vis.setdefault(c, []).append(dd)
    v = 0
    for c, ds in vis.items():
        ds = sorted(ds)
        for a, b in zip(ds, ds[1:]):
            if (b - a).days < min_gap: v += 1
    return v

def main():
    global sp_id_global
    src = os.path.expanduser("~/Downloads/GeoGov_Demo_Final/demo_dashboard_data.json")
    data = json.load(open(src, encoding="utf-8"))
    out_all, report = {}, ["# 芜湖 R2'-ALNS + SP (OSRM 骑行路网距离, WGS84)", ""]
    for sp_id, sp in data.items():
        sp_id_global = sp_id
        t0 = time.time()
        ld, all_stores, codes, lon_w, lat_w = build_line(sp)
        D = road_matrix(sp_id, codes, lon_w, lat_w)
        dates = list(ld.dates)
        mn, mx = ld.min_daily_capacity, ld.max_daily_capacity

        pool = []
        for dd, seq in ld.days_orig.items():
            so = _exact_open_tsp(list(seq), D, 30)
            pool.append((dd, list(so), round(day_km(so, D), 3)))
        base_km = sum(k for _, _, k in pool)
        for seed in (42, 7):
            r = R2ALNS().solve(ld, D, time_budget=90, seed=seed, combo_mode="free")
            pool += r.metadata["_columns"]
        legal = dedupe_pool(pool, top_k=8, max_daily=mx, min_daily=mn)

        rs = SPMatheuristic().solve(ld, D, time_budget=120, pool=legal, rounds=1, sa_burst=10.0,
                                    r2_prime=False)
        rs_days = {}
        for k, v in rs.days.items():
            kk = k if isinstance(k, date) else date.fromisoformat(str(k)[:10])
            rs_days[kk] = list(v)

        # R3 节奏修复 (14天)
        slot_of = slot_index_map(dates)
        spw = slots_per_weekday(dates)
        shop = _dd(list)
        for dd in dates:
            for c in rs_days.get(dd, []): shop[c].append(dd)
        repairs = 0
        for c, ds in shop.items():
            if len(ds) < 2: continue
            ds = sorted(ds)
            if rhythm_ok_dates(ds, slot_of, spw): continue
            k = spw[_wd(ds[0])]
            idxs = sorted(slot_of[d][1] for d in ds)
            half = k // 2
            if half and idxs[1] - idxs[0] != half:
                target_slot = (idxs[0] + half) % k
                cand = [d for d in dates if slot_of[d][0] == _wd(ds[0]) and slot_of[d][1] == target_slot]
                src_day = ds[1]
                if cand and src_day in rs_days and c in rs_days[src_day]:
                    tgt = cand[0]
                    if len(rs_days.get(tgt, [])) + 1 <= mx and len(rs_days[src_day]) - 1 >= mn:
                        rs_days[src_day].remove(c); rs_days[tgt].append(c)
                        repairs += 1
        iv_after = interval_violations({d: v for d, v in rs_days.items()})

        # 转通用 schema (route km 用列路径)
        col_km = {}
        for dd, seq in ld.days_orig.items():
            so = _exact_open_tsp(list(seq), D, 30)
            col_km[(dd, frozenset(so))] = round(day_km(so, D), 3)
        def day_road_km(dd, members):
            key = (dd, frozenset(members))
            if key in col_km: return col_km[key]
            so = _exact_open_tsp(list(members), D, 30)
            v = round(day_km(so, D), 3); col_km[key] = v; return v
        days_out = []
        for dd in dates:
            members = sorted(rs_days.get(dd, []))
            stores_out = []
            for i in members:
                s = dict(all_stores[codes[i]]); s.pop("audit", None); stores_out.append(s)
            days_out.append({"date": dd.isoformat(), "stores": stores_out,
                             "store_count": len(members), "total_km": day_road_km(dd, members)})
        out_all[sp_id] = {"name": sp_id, "total_stores": len(all_stores), "days": days_out}

        pf_before = preflight(sp_id, sp["days"])
        pf_after = preflight(sp_id, days_out)
        cnt = lambda r: (sum(1 for s in r["signals"] if s["level"]=="红"),
                         sum(1 for s in r["signals"] if s["level"]=="黄"))
        rb, yb = cnt(pf_before); ra, ya = cnt(pf_after)
        iv_orig = interval_violations(ld.days_orig)
        km_new = sum(d["total_km"] for d in days_out)
        rng_new = (min(d["store_count"] for d in days_out), max(d["store_count"] for d in days_out))
        assert mn <= rng_new[0] and rng_new[1] <= mx, "走廊越界!"
        report += [
            f"## {sp_id}  ({time.time()-t0:.0f}s)",
            f"- 骑行路网km: 基线A **{base_km:.0f}** → SP **{km_new:.0f}** ({(km_new-base_km)/base_km*100:+.1f}%) | 池列 {len(legal)}",
            f"- 走廊[{mn},{mx}] ✓ | 日店数 {rng_new[0]}~{rng_new[1]}",
            f"- 间隔<14天: 原{iv_orig} → 修复后{iv_after} (R3修复{repairs}店)",
            f"- Preflight 红/黄: {rb}/{yb} → {ra}/{ya}",
            "",
        ]
        print("\n".join(report[-5:]), flush=True)

    dst = os.path.join(HERE, "r2v4_plan_road.json")
    json.dump(out_all, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    report += ["", f"产物: {dst}"]
    open(os.path.join(HERE, "r2v4_report_road.md"), "w").write("\n".join(report))
    print("saved", dst)

if __name__ == "__main__":
    main()
