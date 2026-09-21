# -*- coding: utf-8 -*-
"""芜湖三线 · 习惯-里程帕累托前沿 (σ 预算扫描).

问题: 在"最多移动 B% 门店出服务日"的预算下, 里程最优能到多少?
B=0 → coverage_v2 (习惯全保持); B→∞ → coverage_v1 (习惯不设防).

方法: 列池 = 基线列 ∪ R2ALNS(σ自由)多seed列; sp_solve_ip 加 sigma_budget
约束 (违反服务日的店数 ≤ B), 逐 B 求整数最优 → 前沿点.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

from run_wuhu_342_coverage import load_coverage_line, hav_mat  # noqa: E402
from visitmodel.sp.formulation import sp_solve_ip  # noqa: E402

XLSX = "/Users/ghb/UFS-demo/更新后的8月规划.xlsx"
BUDGETS = [0.0, 0.05, 0.10, 0.15, 0.20]
ALNS_SEEDS = [42, 137]
ALNS_S = 30.0

def main(lid):
    line, plan_df, svc_wd = _load(lid)
    D = hav_mat(line.lat, line.lon)
    dates = list(line.dates)
    kmc = lambda seq: float(sum(D[seq[k]][seq[k + 1]] for k in range(len(seq) - 1)))
    base_km = sum(kmc(s) for s in line.days_orig.values())
    N = len(line.codes)

    # sigma: 店idx → 允许星期几 (1-5)
    sigma = {i: set(int(w) for w in svc_wd.get(str(c), {1, 2, 3, 4, 5}))
             for i, c in enumerate(line.codes)}
    k_c = {i: int(line.freq[c]) for i, c in enumerate(line.codes)}

    # ---- 列池 ----
    pool = [(dd, list(v), kmc(v)) for dd, v in line.days_orig.items()]
    from algos.r2_alns import R2ALNS
    for seed in ALNS_SEEDS:
        r = R2ALNS().solve(line, D, time_budget=ALNS_S, seed=seed)
        for dd, v in r.days.items():
            pool.append((dd, list(v), kmc(v)))
    pool = [p for p in pool if p[2] > 0 or len(p[1]) <= 1]
    print(f"\n===== {lid}: {N} 店 基线 {base_km:.1f} km | 列池 {len(pool)} =====")

    rows = []
    for frac in BUDGETS:
        B = int(round(frac * N))
        km, days, info = sp_solve_ip(dates, k_c, pool, timeout_s=45,
                                     sigma=sigma, sigma_budget=B,
                                     return_diagnostics=True)
        if km is None:
            rows.append({"预算%": f"{frac*100:.0f}", "预算店数": B, "km": None})
            continue
        viol = sum(1 for dd, seq in days.items() for i in seq
                   if dd.weekday() + 1 not in sigma[i])
        rows.append({
            "预算%": f"{frac*100:.0f}", "预算店数": B,
            "实际移动": viol, "移动%": f"{viol/N*100:.0f}%",
            "km": round(km, 1), "降幅%": round((km - base_km) / base_km * 100, 1),
            "状态": info.get("status"),
        })
    print(pd.DataFrame(rows).to_string(index=False))


def _load(lid):
    import run_wuhu_342_coverage as R
    R.LINE = lid
    return R.load_coverage_line()


if __name__ == "__main__":
    for lid in (sys.argv[1:] or ["000707342", "NP0011193", "NP8800295"]):
        main(lid)
