# -*- coding: utf-8 -*-
"""顺序修复基线: 每线同日集合 + 每日地理最优排序 (OSRM 2opt open chain).
产出 printed_fixed.json: line -> {printed_wrong, printed_fixed}"""
import os, sys, json
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
R = os.path.join(ROOT, "output", "nationwide")


def nn_2opt_open(D, idx):
    sub = D[np.ix_(idx, idx)]
    n = len(idx)
    if n < 2: return 0.0
    unv = set(range(1, n)); tour = [0]
    while unv:
        last = tour[-1]; nxt = min(unv, key=lambda j: sub[last, j])
        tour.append(nxt); unv.remove(nxt)
    def L(t): return sum(sub[t[i], t[i+1]] for i in range(len(t)-1))
    best = tour[:]; bl = L(best); imp = True; it = 0
    while imp and it < 200:
        imp = False; it += 1
        for i in range(n-1):
            for j in range(i+1, n):
                nt = best[:i+1] + best[i+1:j+1][::-1] + best[j+1:]
                nl = L(nt)
                if nl < bl - 1e-9: best, bl, imp = nt, nl, True
    return bl


def main():
    out_path = os.path.join(R, "printed_fixed.json")
    done = json.load(open(out_path)) if os.path.exists(out_path) else {}
    specs = sorted(f for f in os.listdir(os.path.join(R, "specs")) if f.endswith(".json"))
    for si, fn in enumerate(specs):
        key = fn[:-5]
        if key in done:
            continue
        spec = json.load(open(os.path.join(R, "specs", fn)))
        mp = os.path.join(R, "matrices", key + ".npy")
        if not os.path.exists(mp):
            continue
        M = np.load(mp)
        wrong = sum(M[a, b]
                    for idx in spec["original_assignment_idx"].values()
                    for a, b in zip(idx[:-1], idx[1:]))
        fixed = sum(nn_2opt_open(M, list(idx))
                    for idx in spec["original_assignment_idx"].values())
        done[key] = dict(printed_wrong=round(float(wrong), 1),
                         printed_fixed=round(float(fixed), 1))
        if si % 25 == 0:
            json.dump(done, open(out_path, "w"))
            print(f"[{si}/{len(specs)}] {key} wrong={wrong:.1f} fixed={fixed:.1f}", flush=True)
    json.dump(done, open(out_path, "w"))
    import numpy as np2
    wr = [v["printed_wrong"] for v in done.values()]
    fx = [v["printed_fixed"] for v in done.values()]
    print(f"done {len(done)} lines; wrong_sum={sum(wr):.0f} fixed_sum={sum(fx):.0f} "
          f"median_ratio={np2.median([w/f for w, f in zip(wr, fx) if f > 0]):.2f}")


if __name__ == "__main__":
    main()
