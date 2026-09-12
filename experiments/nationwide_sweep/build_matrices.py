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


def full_matrix(coords, blk=85):
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
    printed_path = os.path.join(ROOT, "output", "nationwide", "printed.json")
    printed = json.load(open(printed_path)) if os.path.exists(printed_path) else {}
    specs = sorted(os.listdir(SPEC))
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
        coords = [(s["lon"], s["lat"]) for s in spec["stores"]]
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
