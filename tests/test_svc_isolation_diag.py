"""隔离诊断: 频次 -> 铺排 -> ALNS -> 闸, 每阶段带断言 (真实 09 线).

用法: .venv/bin/python -m pytest tests/test_svc_isolation_diag.py -v -m slow
失败的第一条断言即定位 bug 所在阶段.
"""
import datetime as _dt
import json
from collections import Counter
from pathlib import Path

import pytest

pytestmark = [pytest.mark.slow]

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "output" / "svc_golden" / "09"


def _load_problem():
    f = GOLDEN / "problem_2.2.json"
    if not f.exists():
        pytest.skip("golden problem_2.2.json 不存在")
    return json.loads(f.read_text(encoding="utf-8"))


def _window_visits(f, n_days):
    return max(1, round(f["visits"] * n_days / f["horizon"]))


def test_stage_a_spread_preserves_counts():
    """阶段 A: 频次 -> 铺排. 断言: 每店次数 == 窗口目标, 日负载在走廊内."""
    from svc.stages.solve import _spread
    spec = _load_problem()
    n = spec["cycle"]["n_days"]
    target, load = _spread(spec, n)

    # 1. 每店次数 == 该店所选相位在窗口内的出现数 (相位是决策变量)
    for s in spec["stores"]:
        f = s["frequency"]
        days = target[s["id"]]
        assert days, f"店 {s['id']}: 铺排为空"
        phase = ((days[0] - 1) % f["horizon"]) + 1
        exp = len(range(phase, n + 1, f["horizon"]))
        assert len(days) == exp, \
            f"店 {s['id']}: 铺排 {len(days)} 次 != 相位{phase}出现数 {exp}"
        # 等差性: 拜访日必须等差 (公差 = horizon)
        diffs = {b - a for a, b in zip(days, days[1:])}
        assert diffs <= {f["horizon"]}, f"店 {s['id']}: 拜访日不等差 {sorted(days)[:6]}"

    # 2. 总次数 = 各店相位出现数之和
    total = sum(len(v) for v in target.values())
    expect_total = sum(
        len(range(((target[s['id']][0] - 1) % s['frequency']['horizon']) + 1,
                  n + 1, s['frequency']['horizon']))
        for s in spec['stores'])
    assert total == expect_total, f"铺排总次数 {total} != {expect_total}"

    # 3. 日负载在走廊内
    lo, hi = spec["corridor"]["min_daily"], spec["corridor"]["max_daily"]
    for d, v in load.items():
        assert lo <= v <= hi, f"日 {d} 负载 {v} 越走廊 [{lo},{hi}]"


def test_stage_b_alns_preserves_counts():
    """阶段 B: ALNS 以铺排为初始解. 断言: 输出总次数 == 铺排总次数."""
    from core.base import LineData
    from algos.r2_alns import R2ALNS
    from svc.stages.solve import _spread
    import numpy as np

    spec = _load_problem()
    n = spec["cycle"]["n_days"]
    target, _load = _spread(spec, n)
    codes = [s["code"] for s in spec["stores"]]
    dates = [_dt.date(2000, 1, 1) + _dt.timedelta(days=i) for i in range(n)]
    init_days = {d: [] for d in dates}
    for sid, days in target.items():
        for d in days:
            init_days[dates[d - 1]].append(sid)
    freq = {s["code"]: len(target[s["id"]]) for s in spec["stores"]}
    line = LineData(
        line_id=spec["line_id"], line_name="diag", codes=codes,
        lon=[s["lon"] for s in spec["stores"]],
        lat=[s["lat"] for s in spec["stores"]],
        dates=dates, days_orig=init_days, freq=freq,
        stores=len(codes), visits=sum(freq.values()),
        min_daily_capacity=spec["corridor"]["min_daily"],
        max_daily_capacity=spec["corridor"]["max_daily"])
    D = np.load(ROOT / "output" / f"road_dist_{spec['line_id']}.npy")

    eng = R2ALNS().solve(line, D, iteration_budget=600, seed=42,
                          combo_mode="contract", final_reroute=False,
                          init_days=init_days)
    cnt = Counter()
    for dd, v in eng.days.items():
        for c in v:
            cnt[c] += 1
    after = sum(cnt.values())
    before = sum(len(v) for v in target.values())
    assert after == before, f"ALNS 后总次数 {after} != 铺排 {before}"
    for s in spec["stores"]:
        i = s["id"]
        assert cnt[i] == len(target[i]), \
            f"店 {i}: ALNS 后 {cnt[i]} 次 != 铺排 {len(target[i])} 次"
