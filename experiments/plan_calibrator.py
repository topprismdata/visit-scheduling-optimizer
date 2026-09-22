# -*- coding: utf-8 -*-
"""计划校准器 — 让计划贴近业务实际(而不是找空白区).

老板口径(2026-09-22): "现在是如何让计划更贴近业务实际。"

思路: 计划之所以执行不到, 不是因为人不听话(区块星期一致中位 100%),
而是计划的"量"和"块分配"超过了这个人真实的作业能力与真实地盘。
所以用**他自己的作业模式**重编计划, 并回测它是否比现行计划更贴近实际:

  训练: 8月 W1-W2 的**实际到访**  →  生成 W3-W4 校准计划 P1
  对照: 现行计划 P0 = 《更新后的8月规划》里的 W3-W4 行
  评分: 对 W3-W4 实际到访 A, 比较 P0 与 P1 的
        同店同日命中 / 星期命中 / 门店覆盖 / 义务合规

校准规则(全部来自训练期实际, 不含任何主观权重):
  ① 门店池 = 训练期实际到访 ∩ 计划门店        (只编他真在跑的店)
  ② 频次   = 训练期该店到访次数 × 2 (半个月→月), 上限 4, 下限 1
  ③ 星期   = 该店训练期实际到访星期众数        (fallback: 所属块的主力星期)
  ④ 相位   = 该店训练期主要到访相位(奇/偶周), 只在与频次冲突时才打破
  ⑤ 日容量 = 训练期同星期的"日均到访数 × 1.1"(rounded) → 保证排得完
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.top5_portrait import components  # noqa: E402
from orchestration.experience.compliance import store_compliance  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def week_of(d):
    return (d.day - 1) // 7 + 1


def calibrate(trad_plan, trad_act, target_dates):
    """用训练期(W1-W2 实际)生成目标周(W3-W4)的校准计划 rows: (customer_code, date, wd, ph)."""
    if not len(trad_act):
        return []
    ps = set(trad_plan["customer_code"])
    act = trad_act[trad_act["customer_code"].isin(ps)]
    if not len(act):
        return []
    # 块
    sto = trad_plan.drop_duplicates("customer_code")
    cells = {r.customer_code: h3.latlng_to_cell(float(r.lat), float(r.lng), 7)
             for r in sto.dropna(subset=["lat", "lng"]).itertuples()}
    comp = components(list(cells.values())) if cells else {}
    blk = {c: comp[cells[c]] for c in cells}
    blk_wd = defaultdict(Counter)
    for r in act.itertuples():
        if r.customer_code in blk:
            blk_wd[blk[r.customer_code]][r.wd] += 1
    # 每店: 次数/星期/相位
    per = act.groupby("customer_code").agg(n=("wd", "size"), wd=("wd", lambda s: Counter(s).most_common(1)[0][0]),
                                           ph=("ph", lambda s: Counter(s).most_common(1)[0][0]))
    # 日容量: 训练期各星期的日均
    days = act["call_date"].dt.normalize().nunique() or 1
    cap = {}
    for w in range(5):
        cnt = int((act["wd"] == w).sum())
        cap[w] = max(2, int(np.ceil(cnt / max(days / 5 * 1.0, 1) * 1.1)))
    tgt = pd.DataFrame({"plan_day": pd.to_datetime(sorted(target_dates))})
    tgt["wd"] = tgt["plan_day"].dt.dayofweek
    tgt["ph"] = tgt["plan_day"].apply(lambda d: week_of(d) % 2)
    plan_rows = []
    # 按"店"展开需要安排的次数: 次数×2(半个月→月), 上限 4
    need = {c: min(4, max(1, int(row.n * 2))) for c, row in per.iterrows()}
    slots = defaultdict(list)                       # (wd, ph) -> [店]
    for c, row in per.iterrows():
        wd = int(row.wd)
        if c in blk and blk_wd.get(blk[c]):
            pass
        slots[(wd, int(row.ph))].append(c)
    # 逐日填空: 同星期同相位, 优先高频店; 容量满则溢出到同星期另一相位
    for c, _ in sorted(need.items(), key=lambda kv: -kv[1]):
        pass
    filled = Counter()
    for _, d in tgt.iterrows():
        key = (int(d.wd), int(d.ph))
        pool = [c for c in slots.get(key, []) if filled[c] < need[c]]
        pool.sort(key=lambda c: -need[c])
        take = pool[:cap.get(int(d.wd), 12)]
        for c in take:
            filled[c] += 1
            plan_rows.append((c, d.plan_day, int(d.wd), int(d.ph)))
    # 第二轮: 还有欠额的店, 找该星期任意相位(含另一相位)的剩余容量
    for c, k in sorted(need.items(), key=lambda kv: -kv[1]):
        while filled[c] < k:
            wd = int(per.loc[c, "wd"])
            placed = False
            for _, d in tgt[tgt["wd"] == wd].iterrows():
                if sum(1 for x in plan_rows if x[1] == d.plan_day) < cap.get(wd, 12):
                    plan_rows.append((c, d.plan_day, wd, int(d.ph)))
                    filled[c] += 1
                    placed = True
                    break
            if not placed:
                break
    return plan_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只看某分型(如 区块全开·区块内欠访)")
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args()

    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wd"] = plan["plan_day"].dt.dayofweek
    plan["wk"] = plan["plan_day"].apply(week_of)
    plan["ph"] = plan["wk"] % 2
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wd"] = act["call_date"].dt.dayofweek
    act["wk"] = act["call_date"].apply(week_of)
    act["ph"] = act["wk"] % 2

    kinds = {}
    dpath = ROOT / "output/rep_behavior/dossier.json"
    if dpath.exists():
        import json
        kinds = {r["line"]: r["kind"] for r in json.loads(dpath.read_text(encoding="utf-8"))}

    rows = []
    for lid, pl in plan.groupby("sales_line_code"):
        if a.only and kinds.get(lid) != a.only:
            continue
        al = act[act["salesperson_code"] == lid]
        if not len(al) or not len(pl):
            continue
        trad_plan = pl[pl["wk"] <= 2]
        trad_act = al[al["wk"] <= 2]
        tgt_plan = pl[pl["wk"] >= 3]
        tgt_act = al[al["wk"] >= 3]
        if not len(trad_act) or not len(tgt_act) or not len(tgt_plan):
            continue
        # 现行计划 P0
        p0 = set(zip(tgt_plan["customer_code"], tgt_plan["plan_day"]))
        # 校准计划 P1
        cal = calibrate(pl, trad_act, sorted(tgt_plan["plan_day"].unique()))
        p1 = set((c, d) for c, d, _, _ in cal)
        A = set(zip(tgt_act["customer_code"], tgt_act["call_date"]))
        awd = set(zip(tgt_act["customer_code"], tgt_act["wd"]))
        p0wd = set(zip(tgt_plan["customer_code"], tgt_plan["wd"]))
        p1wd = set((c, wd) for c, _, wd, _ in cal)
        p0s, p1s = set(tgt_plan["customer_code"]), set(c for c, _, _, _ in cal)
        as_ = set(tgt_act["customer_code"])
        r = {"line": lid, "kind": kinds.get(lid, "?")}
        for tag, P, Pw, Ps in (("P0现行", p0, p0wd, p0s), ("P1校准", p1, p1wd, p1s)):
            if not P:
                continue
            r[f"{tag}_行数"] = len(P)
            r[f"{tag}_同日%"] = round(len(P & A) / len(P) * 100, 1)
            r[f"{tag}_星期%"] = round(len(Pw & awd) / max(len(Pw), 1) * 100, 1)
            r[f"{tag}_覆盖%"] = round(len(Ps & as_) / max(len(Ps), 1) * 100, 1)
        rows.append(r)
    d = pd.DataFrame(rows)
    if a.sample:
        d = d.sample(min(a.sample, len(d)), random_state=0)
    if not len(d):
        print("无样本"); return
    print(f"线数 {len(d)}" + (f" | 仅分型 {a.only}" if a.only else ""))
    for m in ("同日%", "星期%", "覆盖%"):
        c0, c1 = f"P0现行_{m}", f"P1校准_{m}"
        print(f"  {m:6s} 现行中位 {d[c0].median():6.1f}  →  校准中位 {d[c1].median():6.1f}   (校准更高 {(d[c1]>d[c0]).mean()*100:.0f}% 的线)")
    print(f"  行数    现行中位 {d['P0现行_行数'].median():.0f}  →  校准中位 {d['P1校准_行数'].median():.0f}")
    # 分型对比
    if not a.only:
        print("\n按分型(同日命中 中位):")
        g = d.groupby("kind")[["P0现行_同日%", "P1校准_同日%", "P0现行_覆盖%", "P1校准_覆盖%"]].median().round(1)
        g["线数"] = d.groupby("kind").size()
        print(g.sort_values("P0现行_同日%").to_string())


if __name__ == "__main__":
    main()