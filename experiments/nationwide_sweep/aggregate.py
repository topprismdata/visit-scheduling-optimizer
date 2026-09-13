# -*- coding: utf-8 -*-
"""P1 national ledger: per-line printed vs optimized, stratified by province/lambda."""
import os, sys, json, math, glob
import numpy as np
from scipy.spatial import ConvexHull

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, "output", "nationwide")


def main():
    rows = []
    for p in glob.glob(os.path.join(R, "results", "*.json")):
        try:
            rows.append(json.load(open(p)))
        except Exception:
            pass
    cen = json.load(open(os.path.join(R, "census.json")))
    for r in rows:
        c = cen.get(r["line"], {})
        r["province"] = c.get("province", "?")
        r["burned"] = c.get("burned", False)
        spec_path = os.path.join(R, "specs", c.get("file", ""))
        if os.path.exists(spec_path):
            spec = json.load(open(spec_path))
            pts = np.array([(s["lon"], s["lat"]) for s in spec["stores"]])
            lat0 = pts[:, 1].mean()
            kx, ky = 111.32 * np.cos(np.radians(lat0)), 110.574
            try:
                A = ConvexHull(pts * [kx, ky]).volume
            except Exception:
                A = 0.0
            r["A_km2"] = round(A, 1)
            r["lam"] = round(math.sqrt(A / max(1, len(pts))), 2)
    ok = [r for r in rows if r.get("status") == "OK"]
    fails = [r for r in rows if r.get("status") != "OK"]

    def block(sub, tag):
        d = [r["delta_pct"] for r in sub if r.get("delta_pct") is not None]
        if not d:
            return f"{tag}: EMPTY"
        return (f"{tag}: n={len(sub)} 节省中位={-np.median(d):.1f}% "
                f"IQR=[{-np.percentile(d, 75):.1f}, {-np.percentile(d, 25):.1f}] "
                f"总省={sum(r['printed_km'] - r['optimized_km'] for r in sub):.0f}km")

    out = []
    out.append(block(ok, "全国(全部OK线)"))
    out.append(block([r for r in ok if r["burned"]], "北京烧毁19线"))
    out.append(block([r for r in ok if not r["burned"]], "新鲜553线"))
    for prov in sorted({r["province"] for r in ok}):
        out.append(block([r for r in ok if r["province"] == prov], f"省{prov}"))
    for lo, hi in [(0, 0.6), (0.6, 1.5), (1.5, 99)]:
        out.append(block([r for r in ok if lo <= r.get("lam", 0) < hi],
                         f"λ{lo}-{hi}"))
    out.append(f"总OK={len(ok)} / FAIL={len(fails)}")
    for r in fails:
        out.append(f"  FAIL {r['line']}: {r.get('status')}")
    out.append("对照: 广州10线 -12.6% | 北京18线 printed/opt 1.25x")

    json.dump(rows, open(os.path.join(R, "ledger_p1.json"), "w"), ensure_ascii=False)
    open(os.path.join(R, "ledger_p1.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
