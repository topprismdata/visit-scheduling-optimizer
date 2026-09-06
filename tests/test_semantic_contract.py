# -*- coding: utf-8 -*-
"""语义层测试: 合同-相位本体 == SRP 数据 (docs/design/CONTRACT_CADENCE_MODEL.md).
定稿标准: 精确重构(集合相等), 不只是"不违例"; 反例必须被拒绝."""
import sys
import datetime as dt
from collections import Counter
from datetime import date

import pytest

sys.path.insert(0, ".")

SRP = "/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx"
LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']


def _july_workdays():
    d0 = date(2026, 7, 1)
    return [d0 + dt.timedelta(days=i) for i in range(31)
            if (d0 + dt.timedelta(days=i)).weekday() < 5]


def test_phase_of_iso_week_parity():
    from core.contract import phase_of
    assert phase_of(date(2026, 7, 1)) == 1    # ISO 27 奇
    assert phase_of(date(2026, 7, 8)) == 0    # ISO 28 偶
    assert phase_of(date(2026, 7, 15)) == 1   # ISO 29 奇
    assert phase_of(date(2026, 7, 6)) == 0    # 周一 ISO 28 偶
    assert phase_of(date(2026, 7, 13)) == 1   # 周一 ISO 29 奇


def test_slot_sets_exhaustive_15_row_table():
    from core.contract import contract_slot_dates
    dates = _july_workdays()
    wd = {w: [d for d in dates if d.weekday() == w] for w in range(5)}
    for w, ds in wd.items():
        assert contract_slot_dates("W", None, ds) == set(ds)
    for w in (0, 1):
        assert len(contract_slot_dates("B", 0, wd[w])) == 2
        assert len(contract_slot_dates("B", 1, wd[w])) == 2
    for w in (2, 3, 4):
        even = contract_slot_dates("B", 0, wd[w])
        odd = contract_slot_dates("B", 1, wd[w])
        assert len(even) == 2 and len(odd) == 3
        assert even | odd == set(wd[w]) and not (even & odd)
    assert contract_slot_dates("B", 1, wd[2]) == \
        {date(2026, 7, 1), date(2026, 7, 15), date(2026, 7, 29)}


def test_contract_of_weekly_and_biweekly():
    from core.contract import contract_of
    dates = _july_workdays()
    mon = [d for d in dates if d.weekday() == 0]
    wed = [d for d in dates if d.weekday() == 2]
    days = {mon[0]: [0], mon[1]: [0], mon[2]: [0], mon[3]: [0],
            wed[0]: [1, 2], wed[2]: [1, 2], wed[4]: [1, 2],
            wed[1]: [2], wed[3]: [2]}
    ct = contract_of(days, dates)
    assert ct[0] == ("W", None)
    assert ct[1] == ("B", 1)
    assert ct[2] == ("W", None)


def test_check_contract_rejects_all_counterexamples():
    from core.contract import check_contract
    dates = _july_workdays()
    wed = [d for d in dates if d.weekday() == 2]
    thu = [d for d in dates if d.weekday() == 3]
    ct = {7: ("B", 1), 8: ("W", None)}
    good = {**{d: [7] for d in (wed[0], wed[2], wed[4])},
            **{d: [8] for d in thu}}
    assert check_contract(good, ct, dates) == []
    assert 7 in check_contract({wed[1]: [7], wed[3]: [7],
                                **{d: [8] for d in thu}}, ct, dates)          # 反例1 相位翻转
    bad2 = dict(good); bad2[wed[0]] = [8]; bad2[thu[0]] = [7, 8]
    assert 7 in check_contract(bad2, ct, dates)                                # 反例2 星期几分裂
    bad3 = {wed[0]: [7, 8], wed[2]: [7, 8], wed[4]: [8], **{d: [8] for d in thu}}
    assert 7 in check_contract(bad3, ct, dates)                                # 反例3 缺访
    bad4 = dict(good); bad4[wed[1]] = [7, 8]
    assert 7 in check_contract(bad4, ct, dates)                                # 反例4 多访
    bad5 = dict(good); bad5[thu[0]] = []
    assert 8 in check_contract(bad5, ct, dates)                                # 反例5 周访漏一天


def test_real_data_exact_reconstruction_all_lines():
    from data.loader import load_plan, load_line
    from core.contract import contract_of, contract_slot_dates, check_contract
    pv = load_plan()
    f_dist, ct_dist, total = Counter(), Counter(), 0
    for lid in LINES:
        d = load_line(pv, lid)
        dates = list(d.dates)
        ct = contract_of(d.days_orig, dates)
        assert check_contract(d.days_orig, ct, dates) == []
        sched = {}
        for dd, seq in d.days_orig.items():
            for c in seq:
                sched.setdefault(c, set()).add(dd)
        for c, (k, p) in ct.items():
            ds = sched[c]
            w = next(iter(ds)).weekday()
            wd_dates = [t for t in dates if t.weekday() == w]
            assert ds == contract_slot_dates(k, p, wd_dates), \
                f"线{lid} 店{c}: 重构不等"
        for c, (k, p) in ct.items():
            ct_dist[(k, p)] += 1
            f_dist[len(sched[c])] += 1
        total += len(ct)
    assert total == 1524
    assert dict(ct_dist) == {("W", None): 1337, ("B", 0): 88, ("B", 1): 99}
    assert dict(f_dist) == {2: 125, 3: 62, 4: 557, 5: 780}


def test_service_week_field_is_iso_week_mod4():
    import pandas as pd
    df = pd.read_excel(SRP, sheet_name="Sheet1")
    df = df[df["计划是否有效标识"] == "有效"]
    bad = sum(1 for _, r in df.iterrows()
              if str(int(r["服务周"])) != str(pd.to_datetime(r["拜访日期"]).date().isocalendar()[1] % 4))
    assert bad == 0, f"服务周 != ISO周 mod4 的行数: {bad}"


def test_calendar_property_2025_2029():
    """有界穷举: 2025~2029 每个月的工作日历上, 双周相位集合互斥且并集=全槽位,
    次数由 (k, phase) 唯一决定; 并固化 W53 年(2026)边界假设的作用域."""
    from core.contract import contract_slot_dates
    import datetime as dt
    for year in range(2025, 2030):
        for month in range(1, 13):
            first = date(year, month, 1)
            last = date(year + (month == 12), (month % 12) + 1, 1) - dt.timedelta(days=1)
            days = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)
                    if (first + dt.timedelta(days=i)).weekday() < 5]
            for w in range(5):
                ds = [d for d in days if d.weekday() == w]
                if not ds:
                    continue
                even = contract_slot_dates("B", 0, ds)
                odd = contract_slot_dates("B", 1, ds)
                assert not (even & odd) and (even | odd) == set(ds)
                assert abs(len(odd) - len(even)) <= 1   # 53周年边界只允许差1
    # W53 断言: 2026-W53 与 2027-W01 同为奇 (跨年断裂的显式文档化)
    from core.contract import phase_of
    assert phase_of(date(2026, 12, 30)) == phase_of(date(2027, 1, 6)) == 1
