# -*- coding: utf-8 -*-
"""Nationwide ALNS-v3 sweep: 600s/line, 5 workers, resumable, JSONL heartbeat."""
import os, sys, json, time, argparse
from datetime import date, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def solve_line(line, budget):
    os.environ["OMP_NUM_THREADS"] = "1"
    import numpy as np
    from core.base import LineData
    from core.metric import check_freq, day_km
    import algos.impl, algos.alns_v3, algos.sp_matheuristic  # noqa: F401 registry
    from algos.registry import get

    spec = json.load(open(f"{ROOT}/output/nationwide/specs/{line}.json"))
    D = np.load(f"{ROOT}/output/nationwide/matrices/{line}.npy")
    pj = json.load(open(f"{ROOT}/output/nationwide/printed.json"))[line]
    printed = pj["printed_km"] if isinstance(pj, dict) else pj

    dates = [date.fromisoformat(d) for d in spec["cycle"]["dates"]]
    days_orig = {date.fromisoformat(d): idx
                 for d, idx in spec["original_assignment_idx"].items()}
    codes = [s["code"] for s in spec["stores"]]
    freq = {s["code"]: int(s["frequency"]["visits"]) for s in spec["stores"]}
    data = LineData(line_id=line, line_name=line, codes=codes,
                    lon=[s["lon"] for s in spec["stores"]],
                    lat=[s["lat"] for s in spec["stores"]],
                    dates=dates, days_orig=days_orig, freq=freq,
                    stores=len(codes), visits=spec["meta"]["n_visits"])
    t0 = time.time()
    algo = get("alns_v3")()
    res = algo.solve(data, D, time_budget=budget)
    opt = float(np.sum([day_km(d, D) for d in res.days.values()]))
    count_ok = bool(check_freq(res.days, data.codes, data.freq))
    return dict(line=line, printed_km=printed, optimized_km=round(opt, 2),
                delta_pct=round(100 * (opt / printed - 1), 2),
                count_ok=count_ok, moves=getattr(res, "moves", 0),
                status="OK" if count_ok else "FAIL_count",
                sec=round(time.time() - t0, 1),
                days={d.isoformat(): list(v) for d, v in res.days.items()},
                meta=spec["meta"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    R = f"{ROOT}/output/nationwide/results"
    os.makedirs(R, exist_ok=True)
    done = set(os.listdir(R))
    lines = sorted(f[:-5] for f in os.listdir(f"{ROOT}/output/nationwide/specs"))
    if a.limit:
        lines = lines[:a.limit]
    todo = [l for l in lines if f"{l}.json" not in done]
    print(f"todo {len(todo)}/{len(lines)}", flush=True)
    with open(f"{ROOT}/output/nationwide/progress.jsonl", "a") as hb, \
         ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(solve_line, l, a.budget): l for l in todo}
        for f in as_completed(futs):
            line = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = dict(line=line, status=f"FAIL_crash:{type(e).__name__}",
                         error=str(e)[:200])
            json.dump(r, open(f"{R}/{line}.json", "w"), ensure_ascii=False)
            hb.write(json.dumps({k: r.get(k) for k in
                                 ("line", "status", "printed_km", "optimized_km",
                                  "delta_pct", "sec")}, ensure_ascii=False) + "\n")
            hb.flush()
            print(f"{line}: {r.get('status')} {r.get('delta_pct')}%", flush=True)


if __name__ == "__main__":
    main()
