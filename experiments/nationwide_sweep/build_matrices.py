# -*- coding: utf-8 -*-
"""Per-line OSRM distance matrix (local routed) + printed km along SRP order."""
import os, sys, json, time
import numpy as np
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(ROOT, "output", "nationwide", "specs")
MAT = os.path.join(ROOT, "output", "nationwide", "matrices")
os.makedirs(MAT, exist_ok=True)
OSRM = os.environ.get("NW_OSRM", "http://192.168.31.16:5001")

# GCJ02 -> WGS84: 全国 SRP 导出坐标系为 GCJ02, OSRM 需要 WGS84。
# 未转换时每点偏移 ~500m, snap 到错误道路, 链长虚高实测 74% (NP0011547)。
_A = 6378245.0; _EE = 0.00669342162296594
def _tl(x, y):
    r = -100 + 2*x + 3*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
    r += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi)) * 2/3
    r += (20*math.sin(y*math.pi) + 40*math.sin(y/3*math.pi)) * 2/3
    r += (160*math.sin(y/12*math.pi) + 320*math.sin(y*math.pi/30)) * 2/3
    return r
def _tg(x, y):
    r = 300 + x + 2*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
    r += (20*math.sin(6*x*math.pi) + 20*math.sin(2*x*math.pi)) * 2/3
    r += (20*math.sin(x*math.pi) + 40*math.sin(x/3*math.pi)) * 2/3
    r += (150*math.sin(x/12*math.pi) + 300*math.sin(x/30*math.pi)) * 2/3
    return r
def gcj2wgs(lng, lat):
    wlng, wlat = lng, lat
    for _ in range(6):
        rl = math.radians(wlat); mg = 1 - _EE*math.sin(rl)**2; sm = math.sqrt(mg)
        dlat = (_tl(wlng-105, wlat-35)*180)/((_A*(1-_EE))/(mg*sm)*math.pi)
        dlng = (_tg(wlng-105, wlat-35)*180)/(_A/sm*math.cos(rl)*math.pi)
        wlng += lng - (wlng+dlng); wlat += lat - (wlat+dlat)
    return wlng, wlat


def table(coords):
    pts = ";".join(f"{c[0]},{c[1]}" for c in coords)
    url = f"{OSRM}/table/v1/driving/{pts}?annotations=distance"
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                d = json.loads(r.read())
            if d.get("code") == "Ok":
                return np.array(d["distances"], dtype=np.float64) / 1000.0
        except Exception:
            time.sleep(2 * (k + 1))
    return None


def full_matrix(coords, blk=48):
    n = len(coords)
    if n <= 90:
        return table(coords)
    M = np.zeros((n, n))
    for i in range(0, n, blk):
        for j in range(0, n, blk):
            sub = table(coords[i:i + blk] + coords[j:j + blk])
            if sub is None:
                return None
            M[i:i + blk, j:j + blk] = sub[:len(coords[i:i + blk]), len(coords[i:i + blk]):]
    return M


def main():
    shard_n = int(os.environ.get("NW_SHARD_N", "1"))
    shard_i = int(os.environ.get("NW_SHARD_IDX", "0"))
    printed_path = os.path.join(ROOT, "output", "nationwide",
                                f"printed_shard{shard_i}.json")
    printed = json.load(open(printed_path)) if os.path.exists(printed_path) else {}
    specs = sorted(os.listdir(SPEC))
    specs = [f for si, f in enumerate(specs) if si % shard_n == shard_i]
    limit = int(os.environ.get("NW_LIMIT", "0"))
    if limit:
        specs = specs[:limit]
    errs = 0
    for si, fn in enumerate(specs):
        line = fn[:-5]
        out = os.path.join(MAT, f"{line}.npy")
        if os.path.exists(out) and line in printed and "error" not in printed[line]:
            continue
        spec = json.load(open(os.path.join(SPEC, fn)))
        coords = [gcj2wgs(s["lon"], s["lat"]) for s in spec["stores"]]
        M = full_matrix(coords)
        if M is None:
            printed[line] = dict(error="matrix-fail")
            errs += 1
            continue
        np.save(out, M)
        pk = sum(M[a, b]
                 for idx in spec["original_assignment_idx"].values()
                 for a, b in zip(idx[:-1], idx[1:]))
        printed[line] = dict(printed_km=round(float(pk), 2))
        json.dump(printed, open(printed_path, "w"))
        if si % 25 == 0:
            print(f"[{si + 1}/{len(specs)}] {line} printed={pk:.1f}km", flush=True)
    bad = [k for k, v in printed.items() if "error" in v]
    print(f"done; specs={len(specs)} errors={len(bad)} {bad[:5]}")


if __name__ == "__main__":
    main()
