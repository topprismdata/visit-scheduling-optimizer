# -*- coding: utf-8 -*-
"""动态适配 + 偏差级联回溯 单测 (合成数据)."""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestration.experience.adapt import SCOPE_MONTH, adapt_plan
from orchestration.experience.deviation_cascade import cascade_curve, cascade_table

MON = [datetime(2026, 8, 3), datetime(2026, 8, 10), datetime(2026, 8, 17)]
WED = [datetime(2026, 8, 5), datetime(2026, 8, 12), datetime(2026, 8, 19)]


def _plan():
    rows = []
    for i, d in enumerate(MON):
        for c in (f"M{i}a", f"M{i}b"):
            rows.append({"customer_code": c, "plan_day": d, "服务日": 1})
    for i, d in enumerate(WED):
        for c in (f"W{i}a", f"W{i}b"):
            rows.append({"customer_code": c, "plan_day": d, "服务日": 3})
    return pd.DataFrame(rows)


def _act(skip=()):
    rows = []
    for i, d in enumerate(MON):
        for c in (f"M{i}a", f"M{i}b"):
            if c not in skip:
                rows.append({"customer_code": c, "call_date": d})
    for i, d in enumerate(WED):
        for c in (f"W{i}a", f"W{i}b"):
            if c not in skip:
                rows.append({"customer_code": c, "call_date": d})
    return pd.DataFrame(rows)


class TestAdapt:
    def test_backlog_recovered_into_same_weekday(self):
        """W1 周一漏一家 → 最小扰动插进剩余周一空位, 绝不落周三 (σ 锁)."""
        r = adapt_plan("L", _plan(), _act(skip=("M0a",)), as_of="2026-08-07",
                       corridor=(0, 3), scope=SCOPE_MONTH)
        assert r.backlog_at_trigger == 1 and r.backlog_recovered == 1
        assert r.unabsorbed == ()
        mon = [d for d, stores in r.adapted_days.items() if "M0a" in stores]
        assert len(mon) == 1
        assert datetime.fromisoformat(mon[0]).weekday() == 0
        # 最小扰动: 未来店一个没动
        assert all(len(v) <= 3 for v in r.adapted_days.values())

    def test_tight_corridor_leaves_unabsorbed(self):
        """剩余周一已满 (k_max=2) → 欠账排不下 → 升级人工/REP_MONTH."""
        r = adapt_plan("L", _plan(), _act(skip=("M0a", "M0b")), as_of="2026-08-07",
                       corridor=(0, 2), scope=SCOPE_MONTH)
        assert r.backlog_recovered == 0 and len(r.unabsorbed) == 2

    def test_no_deviation_noop(self):
        """无偏差 → 适配是 no-op (未来安排原样)."""
        r = adapt_plan("L", _plan(), _act(), as_of="2026-08-07", corridor=(0, 3))
        assert r.backlog_at_trigger == 0 and r.moved == ()
        assert sum(len(v) for v in r.adapted_days.values()) == 8


class TestCascade:
    def test_cascade_solidified(self):
        """W1 全漏且永不补 → cascade_solidified."""
        c = cascade_curve("L", _plan(), _act(skip=("M0a", "M0b", "W0a", "W0b")))
        assert c.w1_backlog == 4
        assert c.cascade_risk == "cascade_solidified"
        assert c.never_share == 1.0

    def test_cascade_recovered(self):
        """W1 漏 2 家 (50%) 且 W2 补上 → recovered."""
        act = _act(skip=("M0a", "M0b"))
        act = pd.concat([act, pd.DataFrame([
            {"customer_code": "M0a", "call_date": datetime(2026, 8, 10)},
            {"customer_code": "M0b", "call_date": datetime(2026, 8, 10)}])])
        c = cascade_curve("L", _plan(), act)
        assert c.w1_backlog == 2
        assert c.cascade_risk == "cascade_recovered"
        assert c.never_share == 0.0

    def test_stable(self):
        c = cascade_curve("L", _plan(), _act())
        assert c.cascade_risk == "stable" and c.first_dev is None

    def test_table_shape(self):
        t = cascade_table([cascade_curve("L", _plan(), _act())])
        assert set(t.columns) >= {"line", "w1_backlog", "never_share", "risk"}
