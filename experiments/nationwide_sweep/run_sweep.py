# -*- coding: utf-8 -*-
"""Nationwide ALNS-v3 sweep: 600s/line, 5 workers, resumable, JSONL heartbeat."""
import os, sys, json, time, argparse, glob
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
    # printed: 分片构建器写 printed_shard*.json; 合并全部存在的视图, 缺则 None
    printed = None
    for pj_name in ["printed.json"] + sorted(
            glob.glob(f"{ROOT}/output/nationwide/printed_shard*.json")):
        if not os.path.exists(pj_name):
            continue
        pj = json.load(open(pj_name)).get(line)
        if isinstance(pj, dict) and "printed_km" in pj:
            printed = pj["printed_km"]; break

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
    delta = round(100 * (opt / printed - 1), 2) if printed else None
    return dict(line=line, printed_km=printed, optimized_km=round(opt, 2),
                delta_pct=delta,
                count_ok=count_ok, moves=getattr(res, "moves", 0),
                status="OK" if count_ok else "FAIL_count",
                sec=round(time.time() - t0, 1),
                days={d.isoformat(): list(v) for d, v in res.days.items()},
                meta=spec["meta"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=600)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    # 分片进程模式（矩阵阶段同款）: NW_SHARD_N 个独立进程, 各串行跑 1/N 线。
    # ProcessPoolExecutor 在 macOS spawn+ortools 下死锁, 弃用。
    shard_n = int(os.environ.get("NW_SHARD_N", "1"))
    shard_i = int(os.environ.get("NW_SHARD_IDX", "0"))
    R = f"{ROOT}/output/nationwide/results"
    os.makedirs(R, exist_ok=True)
    done = set(os.listdir(R))
    lines = sorted(f[:-5] for f in os.listdir(f"{ROOT}/output/nationwide/specs"))
    lines = [l for si, l in enumerate(lines) if si % shard_n == shard_i]
    if a.limit:
        lines = lines[:a.limit]
    todo = [l for l in lines if f"{l}.json" not in done]
    print(f"shard {shard_i}/{shard_n} todo {len(todo)}/{len(lines)}", flush=True)
    hb = open(f"{ROOT}/output/nationwide/progress_shard{shard_i}.jsonl", "a")
    for l in todo:
        try:
            r = solve_line(l, a.budget)
        except Exception as e:
            r = dict(line=l, status=f"FAIL_crash:{type(e).__name__}",
                     error=str(e)[:200])
        json.dump(r, open(f"{R}/{l}.json", "w"), ensure_ascii=False)
        hb.write(json.dumps({k: r.get(k) for k in
                             ("line", "status", "printed_km", "optimized_km",
                              "delta_pct", "sec")}, ensure_ascii=False) + "\n")
        hb.flush()
        print(f"{l}: {r.get('status')} {r.get('delta_pct')}% "
              f"{r.get('sec')}s", flush=True)


if __name__ == "__main__":
    main()
