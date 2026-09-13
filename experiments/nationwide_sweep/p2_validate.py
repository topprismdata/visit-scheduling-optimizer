# -*- coding: utf-8 -*-
"""P2: nationwide CA-framework validation (deferred from sweep, now data-ready).

Truth = ALNS-v3 optimized_km (569 lines). Prediction via library entry
preassess() (band semantics identical to release). Two circuity variants:
A) prior:   c = national_default 1.27 (library default, city=None)
B) declared: c_route = median(OSRM/haversine) over the line's own print-order
   edges - input-side measurement from the already-built matrix, no truth leak.
"""
import os, sys, json, math, glob
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, "/Users/ghb/spatial-ca-benchmark")
from spatial_ca.report import preassess  # noqa: E402

R = os.path.join(ROOT, "output", "nationwide")
R_ = 6371.0


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[0], b[1], b[0]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R_ * math.asin(math.sqrt(h))


def main():
    cen = json.load(open(os.path.join(R, "census.json")))
    printed = json.load(open(os.path.join(R, "printed.json")))
    rows = []
    files = sorted(glob.glob(os.path.join(R, "specs", "*.json")))
    file2line = {}
    for f in glob.glob(os.path.join(R, "specs", "*.json")):
        try:
            file2line[os.path.basename(f)[:-5]] = json.load(open(f)).get("line_id")
        except Exception:
            pass
    for fi, f in enumerate(files):
        line_id = json.load(open(f)).get("line_id")
        if line_id is None:  # hash-named file: read line_id
            d0 = json.load(open(f)); line_id = d0["line_id"]
        rpath = os.path.join(R, "results", os.path.basename(f))
        if not os.path.exists(rpath):
            continue
        res = json.load(open(rpath))
        if res.get("status") != "OK":
            continue
        spec = json.load(open(f))
        opt = res["optimized_km"]
        pts = [(s["lon"], s["lat"]) for s in spec["stores"]]
        w = [s["frequency"]["visits"] for s in spec["stores"]]
        V = spec["meta"]["n_visits"]; K = spec["meta"]["k_workdays"]
        rep = preassess(pts, total_visits=V, available_workdays=K,
                        source_crs="GCJ02", visit_weights=w,
                        measured_km=opt)  # version A: prior c
        b = rep.band
        if b is None:
            rows.append(dict(line=res["line"], province=cen.get(file2line.get(res["line"], ""), {}).get("province"),
                             burned=cen.get(file2line.get(res["line"], ""), {}).get("burned", False),
                             status=rep.gate, n=spec["meta"]["n_stores"],
                             V=V, K=K, opt=opt, ultra=False))
            continue
        # version B: c_route from matrix + print edges
        M = np.load(os.path.join(R, "matrices", os.path.basename(f)[:-5] + ".npy"))
        ratios = []
        for idx in spec["original_assignment_idx"].values():
            for a, bb in zip(idx[:-1], idx[1:]):
                hv = hav(pts[a], pts[bb])
                if hv >= 0.3:
                    ratios.append(M[a, bb] / hv)
        c_route = float(np.median(ratios)) if ratios else None
        if c_route:
            # recompute two-term with c_route via band internals
            from spatial_ca.band import BETA, KAPPA_BOUNDARY as KAPPA
            mid_c = c_route * (BETA * math.sqrt(V * b["geometry"]["hull_area_km2"])
                               + KAPPA * math.sqrt(K * b["geometry"]["hull_area_km2"]))
            r_b = opt / mid_c
        else:
            r_b = None
        c = cen.get(file2line.get(res["line"], ""), {})
        rows.append(dict(line=res["line"], province=c.get("province"),
                         burned=c.get("burned", False), n=spec["meta"]["n_stores"],
                         V=V, K=K, lam=round(math.sqrt(
                             b["geometry"]["hull_area_km2"] / len(pts)), 2),
                         c_route=round(c_route, 3) if c_route else None,
                         mid_prior=b["monthly_km"], opt=opt,
                         r_prior=round(opt / b["monthly_km"], 3),
                         r_croute=round(r_b, 3) if r_b is not None else None,
                         ultra=bool(b.get("ultra_dense_urban_warning"))))
        if fi % 100 == 0:
            print(f"[{fi}/{len(files)}]", flush=True)

    json.dump(rows, open(os.path.join(R, "p2_validation.json"), "w"), ensure_ascii=False)

    def cov(rs, lo=0.75, hi=1.30):
        rs = [x for x in rs if x is not None]
        return (f"median={np.median(rs):.3f} cov={sum(1 for x in rs if lo<=x<=hi)}"
                f"/{len(rs)} ({100*sum(1 for x in rs if lo<=x<=hi)/len(rs):.0f}%)")

    notass = [r for r in rows if "r_prior" not in r]
    rows = [r for r in rows if "r_prior" in r]
    print(f"NOT_ASSESSED(退化几何): {len(notass)} 线")
    print("\n===== P2 全国框架验证 (真值=ALNS-v3 优化里程) =====")
    print(f"A 先验c版 : {cov([r['r_prior'] for r in rows])}")
    print(f"B 实测c版 : {cov([r['r_croute'] for r in rows])}")
    print("\n--- 按 λ 分层 (r_prior) ---")
    for lo, hi, tag in [(0, 0.6, "超密"), (0.6, 1.5, "中间"), (1.5, 99, "区域")]:
        sub = [r["r_prior"] for r in rows if lo <= r["lam"] < hi]
        print(f"λ{lo}-{hi} {tag}: n={len(sub)} {cov(sub)}")
    print("\n--- 按旗标 ---")
    u = [r["r_prior"] for r in rows if r["ultra"]]
    n = [r["r_prior"] for r in rows if not r["ultra"]]
    print(f"ultra_dense_flag: n={len(u)} {cov(u)}")
    print(f"无旗标:           n={len(n)} {cov(n)}")
    print("\n--- c_route 全国分布 ---")
    cs = [r["c_route"] for r in rows if r["c_route"]]
    print(f"median={np.median(cs):.2f} IQR=[{np.percentile(cs,25):.2f},{np.percentile(cs,75):.2f}] "
          f"range=[{min(cs):.2f},{max(cs):.2f}]")
    print("\n--- 烧毁/新鲜 ---")
    print(f"烧毁: n={sum(1 for r in rows if r['burned'])} "
          f"{cov([r['r_prior'] for r in rows if r['burned']])}")
    print(f"新鲜: n={sum(1 for r in rows if not r['burned'])} "
          f"{cov([r['r_prior'] for r in rows if not r['burned']])}")


if __name__ == "__main__":
    main()
