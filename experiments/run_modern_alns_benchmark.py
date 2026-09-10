# -*- coding: utf-8 -*-
"""2026 现代 ALNS 对比基准: 传统 R2ALNS vs HGS-R2' (融合 MAB UCB1 + 空间几何势能场).

用法:
  python experiments/run_modern_alns_benchmark.py --line 02 --pop-size 10 \
      --generations 30 --budget 60
  python experiments/run_modern_alns_benchmark.py --line FS --budget 90

流程:
  1. 载入线路实例 (--line FS=房山线 或 02~11 海珠荔湾线路);
  2. 初态里程 = 原计划经 CP-SAT 单日精排的共同口径 (两算法共享基线);
  3. R2ALNS (传统 R2' 邻域搜索) 与 HGSR2Optimizer (双种群 HGS, UCB1 自适应
     算子调度 + 空间势能引导换挡) 各自求解;
  4. 输出对比指标: 初态/最终里程, 压降率(%), 迭代次数, 耗时, 五道验收门
     (走廊 / 合同 / R2' / 容量 / 守恒), 并落盘 JSON.

门语义与实现见 check_five_gates; 门顺序: 走廊、合同、R2'、容量、守恒.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from core.base import LineData
from core.contract import check_contract, contract_of
from core.metric import check_capacity, check_freq, day_km, total_km
from algos.hgs_r2 import HGSR2Optimizer
from algos.r2_alns import R2ALNS
from algos.sp_matheuristic import check_r2prime
from algos.tsp_engine import _exact_open_tsp
from data.loader import ALL_LINE_IDS, load_line, load_plan

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"

# 五道验收门 (顺序即任务口径): 走廊、合同、R2'、容量、守恒
GATE_NAMES = ("corridor_ok", "contract_ok", "r2_ok",
              "capacity_ok", "conservation_ok")
GATE_LABELS = ("走廊", "合同", "R2'", "容量", "守恒")

FANGSHAN_FILES = {
    "coords": OUT_DIR / "fangshan_coords_wgs84.json",
    "matrix": OUT_DIR / "fangshan_dist_osm_drive.npy",
    "schedule": OUT_DIR / "fangshan_optimized_solution.json",
}


# ---------------------------------------------------------------------------
# 五道验收门
# ---------------------------------------------------------------------------


def check_five_gates(data: LineData, days: dict) -> dict:
    """对解 days 施加五道验收门, 返回 {gate_name: bool} (顺序见 GATE_NAMES)."""
    dates = sorted(data.dates)
    kmin, kmax = int(data.min_daily_capacity), int(data.max_daily_capacity)

    # 1 走廊: 全部日期覆盖, 每日店数落在 [K_min, K_max] (0 值表示该侧不设限)
    def size_ok(n):
        return not (kmax > 0 and n > kmax) and not (kmin > 0 and n < kmin)

    corridor_ok = all(d in days and size_ok(len(days[d])) for d in dates)
    # 2 合同: 每店日期集 == (κ, φ, 其星期几槽位) 精确派生集
    contract_ok = not check_contract(days, contract_of(data.days_orig, dates),
                                     dates)
    # 3 R2': 每店全月单一星期几
    r2_ok = not check_r2prime(days)
    # 4 容量: 单日店数硬上限 (经典 capacity 闸, 与双向走廊区分)
    capacity_ok = bool(check_capacity(days, kmax))
    # 5 守恒: 每店全月拜访次数 == 原频次 + 日内无重复店 + 店索引合法
    conservation_ok = (
        check_freq(days, data.codes, data.freq)
        and all(len(set(seq)) == len(seq) for seq in days.values())
        and all(0 <= c < data.stores for seq in days.values() for c in seq))
    return dict(zip(GATE_NAMES,
                    (corridor_ok, contract_ok, r2_ok, capacity_ok,
                     conservation_ok)))


# ---------------------------------------------------------------------------
# 实例载入
# ---------------------------------------------------------------------------


def _load_fangshan() -> tuple[LineData, np.ndarray]:
    """房山线 FS: 201 店 / 2026-08 共 21 个工作日.

    距离矩阵行序 = sorted(coords 键序) (经与 haversine 重算相关性 0.999996 验证);
    参考计划取自 fangshan_optimized_solution.json 的 schedule.
    """
    coords = json.loads(FANGSHAN_FILES["coords"].read_text())
    codes = sorted(coords)                     # 矩阵行序
    idx = {c: i for i, c in enumerate(codes)}
    sol = json.loads(FANGSHAN_FILES["schedule"].read_text())
    days_orig = {}
    for iso, seq in sol["schedule"].items():
        days_orig[dt.date.fromisoformat(iso)] = [idx[c] for c in seq
                                                 if c in idx]
    freq = defaultdict(int)
    for seq in days_orig.values():
        for c in seq:
            freq[codes[c]] += 1
    data = LineData(
        line_id="FS", line_name="房山线FS",
        codes=codes,
        lon=[coords[c]["lng"] for c in codes],
        lat=[coords[c]["lat"] for c in codes],
        dates=sorted(days_orig), days_orig=days_orig,
        freq=dict(freq), stores=len(codes),
        visits=sum(len(v) for v in days_orig.values()),
    )
    D = np.load(FANGSHAN_FILES["matrix"])
    return data, D


def load_instance(line_id: str) -> tuple[LineData, np.ndarray]:
    """载入线路实例: FS=房山线, 其余为海珠荔湾 02~11."""
    if line_id == "FS":
        if not all(p.exists() for p in FANGSHAN_FILES.values()):
            missing = [str(p) for p in FANGSHAN_FILES.values() if not p.exists()]
            raise FileNotFoundError(f"房山线数据缺失: {missing}")
        return _load_fangshan()
    if line_id in ALL_LINE_IDS:
        npy = OUT_DIR / f"road_dist_{line_id}.npy"
        if not npy.exists():
            raise FileNotFoundError(f"路网矩阵缺失: {npy}")
        return load_line(load_plan(), line_id), np.load(npy)
    raise ValueError(f"--line 仅支持 FS 或 {'/'.join(ALL_LINE_IDS)}, 收到 {line_id!r}")


# ---------------------------------------------------------------------------
# 对比基准
# ---------------------------------------------------------------------------


def _initial_km(data: LineData, D: np.ndarray, exact_tl: float) -> float:
    """初态里程: 原计划逐日 CP-SAT 精排的共同口径 (两算法共享基线)."""
    return sum(day_km(_exact_open_tsp(sorted(data.days_orig[d]), D, exact_tl), D)
               for d in sorted(data.dates))


def run_benchmark(data: LineData, D, *, pop_size=10, generations=30,
                  ls_iters=20, budget=60.0, alns_budget=None, seed=42,
                  exact_tl=5.0) -> dict:
    """R2ALNS (传统) vs HGS-R2' (2026) 同实例对比, 返回结构化报告."""
    D = np.asarray(D, dtype=float)
    alns_budget = budget if alns_budget is None else alns_budget
    init_km = _initial_km(data, D, exact_tl)

    t0 = time.time()
    r_alns = R2ALNS().solve(data, D, time_budget=alns_budget, seed=seed)
    alns_sec = time.time() - t0
    t1 = time.time()
    opt = HGSR2Optimizer(pop_size=pop_size, n_gens=generations,
                         ls_iters=ls_iters)
    r_hgs = opt.solve(data, D, time_budget=budget, seed=seed,
                      exact_tl=exact_tl)
    hgs_sec = time.time() - t1

    def _blk(days, iters, sec):
        final = round(total_km(days, D), 3)
        return {
            "final_km": final,
            "reduction_pct": round((init_km - final) / init_km * 100, 3)
            if init_km > 0 else 0.0,
            "iterations": int(iters),
            "elapsed": round(sec, 3),
            "gates": check_five_gates(data, days),
        }

    pulls = r_hgs.metadata["mab_pulls"]
    return {
        "line_id": data.line_id,
        "line_name": data.line_name,
        "initial_km": round(init_km, 3),
        "params": {"pop_size": pop_size, "generations": generations,
                   "ls_iters": ls_iters, "budget": budget,
                   "alns_budget": alns_budget, "seed": seed,
                   "exact_tl": exact_tl},
        "r2_alns": {
            **_blk(r_alns.days, r_alns.metadata.get("iters", 0), alns_sec),
            "accepted": int(r_alns.metadata.get("accepted", 0)),
        },
        "hgs_r2": {
            **_blk(r_hgs.days, r_hgs.metadata["gens"], hgs_sec),
            "gens": int(r_hgs.metadata["gens"]),
            "ls_pulls": int(sum(pulls.values())),
            "mab_pulls": {k: int(v) for k, v in pulls.items()},
            "mab_mean_rewards": r_hgs.metadata["mab_mean_rewards"],
            "spatial_penalty": r_hgs.metadata["spatial_penalty"],
            "capacity_penalty": r_hgs.metadata["capacity_penalty"],
        },
    }


def print_report(rep: dict) -> None:
    """打印人类可读对比表: 里程 / 压降率 / 迭代 / 耗时 / 五道门."""
    title = f"2026 现代 ALNS 对比基准 — 线路 {rep['line_id']} ({rep['line_name']})"
    print("=" * max(len(title) + 8, 72))
    print(title)
    print("=" * max(len(title) + 8, 72))
    print(f"初态里程 (原计划 CP-SAT 精排): {rep['initial_km']} km")
    header = (f"{'算法':<28}{'最终里程(km)':>14}{'压降率(%)':>11}"
              f"{'迭代':>10}{'耗时(s)':>9}  五道门")
    print(header)
    rows = [
        ("R2ALNS (传统)", rep["r2_alns"]),
        ("HGS-R2' 2026 (UCB1+空间势能)", rep["hgs_r2"]),
    ]
    for label, blk in rows:
        gates = " ".join(f"{lb}={'PASS' if blk['gates'][gn] else 'FAIL'}"
                         for lb, gn in zip(GATE_LABELS, GATE_NAMES))
        hgs_extra = (f" ({blk['gens']}代/{blk['ls_pulls']}步)"
                     if blk is rep["hgs_r2"] else
                     f" (接受{rep['r2_alns'].get('accepted', 0)})")
        print(f"{label:<28}{blk['final_km']:>14.3f}"
              f"{blk['reduction_pct']:>11.2f}{blk['iterations']:>10}"
              f"{blk['elapsed']:>9.1f}  {gates}{hgs_extra}")
    print(f"门图例: {' / '.join(GATE_LABELS)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="传统 R2ALNS vs 2026 HGS-R2' (MAB UCB1 + 空间势能场) 对比基准")
    ap.add_argument("--line", default="02",
                    choices=["FS"] + ALL_LINE_IDS, help="线路: FS=房山线 或 02~11")
    ap.add_argument("--pop-size", type=int, default=10, help="HGS 种群规模")
    ap.add_argument("--generations", type=int, default=30, help="HGS 世代数")
    ap.add_argument("--ls-iters", type=int, default=20,
                    help="HGS 每子代局部搜索步数")
    ap.add_argument("--budget", type=float, default=60.0,
                    help="HGS-R2' 总时限 (秒)")
    ap.add_argument("--alns-budget", type=float, default=None,
                    help="R2ALNS 时限 (秒), 默认同 --budget")
    ap.add_argument("--exact-tl", type=float, default=5.0,
                    help="CP-SAT 单日精排限时 (秒)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default=None,
                    help="JSON 落盘路径 (默认 output/modern_alns_benchmark_<line>.json)")
    args = ap.parse_args(argv)

    data, D = load_instance(args.line)
    print(f"实例: {data.line_name} | {data.stores} 店 | {len(data.dates)} 日 "
          f"| 走廊 [{data.min_daily_capacity}, {data.max_daily_capacity}]",
          flush=True)
    rep = run_benchmark(data, D, pop_size=args.pop_size,
                        generations=args.generations, ls_iters=args.ls_iters,
                        budget=args.budget, alns_budget=args.alns_budget,
                        seed=args.seed, exact_tl=args.exact_tl)
    print_report(rep)

    out = args.output or str(OUT_DIR / f"modern_alns_benchmark_{args.line}.json")
    with open(out, "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1, default=str)
    print(f"已落盘: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
