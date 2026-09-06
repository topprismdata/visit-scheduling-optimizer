# -*- coding: utf-8 -*-
"""合同-相位本体 (Contract-Cadence-Phase) — 语义层.

业务→数学→求解器三层纪律的第一道物理缝: 本模块只定义"拜访合同"的语义
原语, 纯函数, 零求解器依赖 (不 import 任何 algos/* / 求解器 / numpy).

定稿语义 (docs/design/CONTRACT_CADENCE_MODEL.md, SRP 数据 1,524 店零例外):
- 相位 φ(d) = ISO 自然周 mod 2;
- 周访 (W):    占满所选星期几 σ 的全部槽位;
- 双周 (B, φ): 占满 σ 中相位匹配的槽位;
- 月内次数 f = |S(c)| 是派生量, 不是合同.

模块分两段:
1. v2 均匀节拍松弛快筛 (自 core/metric.py 迁入) — 合法集 ⊃ 合同版,
   只能证伪不能证真, 保留作证伪快筛;
2. 合同-相位本体原语 (定稿) — 精确语义, 验收闸 check_contract 的依据.
"""
import itertools
from collections import defaultdict


# ---- v2 均匀节拍松弛快筛 (合法集 ⊃ 合同版, 只能证伪不能证真) ----

def slot_index_map(dates):
    """{date: (weekday, 周序idx)}; 同星期几按序编号 (7月: 周一/二 k=4, 其余 k=5)."""
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    m = {}
    for w, ds in by_wd.items():
        for i, dd in enumerate(ds):
            m[dd] = (w, i)
    return m


def slots_per_weekday(dates):
    n = defaultdict(int)
    for dd in dates:
        n[dd.weekday()] += 1
    return dict(n)


def _ok_gaps(k, f):
    return set(range(1, k + 1)) if f <= 1 else {k // f, -(-k // f)}


def legal_slot_sets(slots, f):
    """k 个升序槽位 + 频次 f → 合法(均匀节拍)子集列表. 圆形跨度全∈{⌊k/f⌋,⌈k/f⌉}."""
    k = len(slots)
    if f >= k:
        return [tuple(slots)] if f == k else []
    ok = _ok_gaps(k, f)
    out = []
    for combo in itertools.combinations(range(k), f):
        gaps = [combo[i+1] - combo[i] for i in range(f - 1)] + [combo[0] + k - combo[-1]]
        if all(g in ok for g in gaps):
            out.append(tuple(slots[c] for c in combo))
    return out


def illegal_slot_sets(slots, f):
    """全部非法 f-子集 (用于 SP 割)."""
    legal = {set(x) for x in legal_slot_sets(slots, f)}
    return [tuple(s) for s in itertools.combinations(slots, f) if set(s) not in legal]


def rhythm_ok_dates(ds, slot_of, spw):
    """单店日期集 R2'(单一星期几) + R3(均匀节拍)."""
    ds = list(ds)
    if not ds:
        return True
    ws = {slot_of[d][0] for d in ds}
    if len(ws) > 1:
        return False
    w = ws.pop()
    k = spw[w]
    idx = sorted(slot_of[d][1] for d in ds)
    f = len(idx)
    ok = _ok_gaps(k, f)
    gaps = [idx[i+1] - idx[i] for i in range(f - 1)] + [idx[0] + k - idx[-1]]
    return all(g in ok for g in gaps)


def check_rhythm(days, slot_of, spw):
    """全月解节奏验收 (返回违例店列表, 空=通过)."""
    shop = defaultdict(list)
    for dd, seq in days.items():
        for c in seq:
            shop[c].append(dd)
    return [c for c, ds in shop.items() if not rhythm_ok_dates(ds, slot_of, spw)]


# ---- 合同-相位本体 (定稿) ----

def phase_of(d):
    """ISO 自然周 mod 2 (相位锚).
    边界假设(2026-09-06 ChatGPT交叉审核): ISO 周序号每年重置, 53 周年(如2026)边界
    W53→次年W01 parity 不交替, 跨年连续性不保证; 本项目规划scope为单月(7月),
    与'连续全局周 mod 2'在该scope内数值等价. 跨月/跨年使用前必须先做 W53→W01 锚点实验."""
    return d.isocalendar()[1] % 2


def contract_of(days_orig, dates):
    """从原计划反解每店合同: {store_idx: ("W", None) | ("B", phi)}.
    月内次数 == 该星期几槽位数 → 周访; 否则双周, 相位 = 首日期 ISO 周 mod 2."""
    spw = slots_per_weekday(dates)
    sched = defaultdict(set)
    for dd, seq in days_orig.items():
        for c in seq:
            sched[c].add(dd)
    ct = {}
    for c, ds in sched.items():
        w = min(ds).weekday()
        ct[c] = ("W", None) if len(ds) == spw[w] else ("B", phase_of(min(ds)))
    return ct


def contract_slot_dates(kappa, phi, wd_dates):
    """合同×相位×星期几槽位 → 合法日期集. 周访=全槽位; 双周=相位匹配槽位."""
    s = set(wd_dates)
    if kappa == "W":
        return s
    return {d for d in s if phase_of(d) == phi}


def legal_date_map(contracts, dates):
    """{store_idx: 全月合法日期集} = ∪_σ contract_slot_dates (池过滤/定价剪枝用).

    合同不含 σ, 故取全星期几并集: W → 全月日期; B(φ) → 全月相位匹配日期.
    这是逐店合同槽位集的超集 (合法集 ⊃ 合同版) — 剪枝只证伪不证真, 安全."""
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    return {c: set().union(*(contract_slot_dates(k, p, by_wd[w]) for w in by_wd))
            for c, (k, p) in contracts.items()}


def check_contract(days, contracts, dates):
    """合同验收(第五闸): 每店日期集必须精确等于其 (合同,相位,σ) 合同槽位集.
    返回违例 store_idx 列表(空=通过). 蕴含 R2' (星期几分裂必违例)."""
    sched = defaultdict(set)
    for dd, seq in days.items():
        for c in seq:
            sched[c].add(dd)
    by_wd = defaultdict(list)
    for dd in sorted(dates):
        by_wd[dd.weekday()].append(dd)
    bad = []
    for c, (k, p) in contracts.items():
        ds = sched.get(c, set())
        if not ds or len({d.weekday() for d in ds}) != 1:
            bad.append(c)
            continue
        if ds != contract_slot_dates(k, p, by_wd[next(iter(ds)).weekday()]):
            bad.append(c)
    return bad
