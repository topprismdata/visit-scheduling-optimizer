# -*- coding: utf-8 -*-
"""TOP5(采纳率最高) 的结论画像 — 对比全国.

采纳率口径 (KPI 表): 采纳率 = 是否采纳-不含日期 / 系统编排
  ⚠ 8月 612 线中 188 条并列 100%, 全国中位 97.2% → 该指标已饱和,
    取 TOP5 必须声明并列规则。本脚本默认规则:
      R1 采纳率 desc → R2 含日期执行率 desc → R3 系统编排量 desc → R4 线码升序(确定性)

指标 (今日建立, 见 design v0.4 §10):
  义务合规率   Σ min(实际,计划)/计划 / 门店数        (超访不加分)
  相位合规率   实际到访周相位(0=偶/1=奇)含计划相位 的门店占比
  星期命中率   W3-W4 实际到访的星期 == 该店计划星期
  同日执行率   计划(店,日) 中被同日实际执行的占比 (严格)
  欠账恢复率   W1 计划未执行店中, 月内恢复的比例
  片区top2     实际到访落在该片区(W1-W2)top2星期的占比

用法: .venv/bin/python experiments/top5_conclusion.py [--n 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestration.experience.compliance import phase_hit, store_compliance  # noqa: E402
from experiments.validate_projection import components, load  # noqa: E402


def top_lines(n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    k = pd.read_excel("/Users/ghb/UFS-demo/采纳执行-8月.xlsx").dropna(subset=["采纳率"])
    k["含日期"] = k["执行率.1"].fillna(0.0)
    k["编排量"] = k["系统编排"].fillna(0.0)
    k = k.sort_values(["采纳率", "含日期", "编排量", "sales_line_code"], ascending=[False, False, False, True])
    return k.head(n).reset_index(drop=True), k


def line_metrics(lid, plan, act, cell):
    pl = plan[plan["sales_line_code"] == lid]
    a = act[act["salesperson_code"] == lid]
    pc = pl.groupby("customer_code").size()
    ac = a.groupby("customer_code").size()
    pp = pl.drop_duplicates("customer_code").set_index("customer_code")["ph"]
    ap = a.groupby("customer_code")["ph"].apply(set)
    comp = store_compliance(pc.to_dict(), ac.to_dict())
    phv = phase_hit(pp.to_dict(), ap.to_dict())
    # 同日执行率 (严格: 计划(店,日) ∩ 实际(店,日))
    P = set(zip(pl["customer_code"], pl["plan_day"]))
    A = set(zip(a["customer_code"], a["call_date"]))
    sameday = len(P & A) / len(P) if P else np.nan
    # 星期命中率: W3-W4 实际到访 == 该店计划星期 (首槽)
    pwd = pl.drop_duplicates("customer_code").set_index("customer_code")["wd"].to_dict()
    v = a[a["wk"] >= 3]
    hit = [int(pwd[r.customer_code]) == r.wd for r in v.itertuples() if r.customer_code in pwd]
    wdhit = float(np.mean(hit)) if hit else np.nan
    # 欠账恢复率: W1 未执行店 → 月内是否恢复
    w1 = pl[pl["wk"] == 1][["customer_code"]].drop_duplicates("customer_code")
    done = set(a[a["wk"] == 1]["customer_code"])
    miss = [c for c in w1["customer_code"] if c not in done]
    later = set(a[a["wk"] >= 2]["customer_code"])
    rec = len(set(miss) & later) / len(miss) if miss else np.nan
    # 片区 top2 结构
    b = a[a["customer_code"].isin(cell)]
    top2 = np.nan
    if len(b) >= 60:
        cm = components([cell[c] for c in b["customer_code"]])
        b = b.assign(blk=[cm[cell[c]] for c in b["customer_code"]])
        t, vv = b[b["wk"] <= 2], b[b["wk"] >= 3]
        if len(t) and len(vv):
            tz = {z: set(g["wd"].value_counts().index[:2]) for z, g in t.groupby("blk")}
            top2 = float(np.mean([r.wd in tz.get(r.blk, set()) for r in vv.itertuples()]))
    return dict(compliance=comp, phase=phv, sameday=sameday, wdhit=wdhit,
                recovery=rec, top2=top2)


def cohort_lines(name: str, n: int = 5) -> list:
    """队列选择.

    top : 采纳率→含日期→编排量→线码 的前 n 条
    A   : 采纳率=100% 且 含日期=100% (无争议最强, 8月 n=16)
    B   : 采纳率=100% (8月 n=188)
    """
    k = pd.read_excel("/Users/ghb/UFS-demo/采纳执行-8月.xlsx").dropna(subset=["采纳率"])
    k["含日期"] = k["执行率.1"].fillna(0.0)
    if name == "A":
        return k[(k["采纳率"] >= 0.999999) & (k["含日期"] >= 0.999999)]["sales_line_code"].tolist()
    if name == "B":
        return k[k["采纳率"] >= 0.999999]["sales_line_code"].tolist()
    k["编排量"] = k["系统编排"].fillna(0.0)
    k = k.sort_values(["采纳率", "含日期", "编排量", "sales_line_code"],
                      ascending=[False, False, False, True])
    return k.head(n)["sales_line_code"].tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--cohort", default="top", choices=["top", "A", "B"])
    a = ap.parse_args()
    ok, plan, act, cell = load()
    oks = set(ok)
    lines = [l for l in cohort_lines(a.cohort, a.n) if l in oks]
    df = pd.DataFrame([line_metrics(l, plan, act, cell) for l in lines]) * 100
    nat = pd.DataFrame([line_metrics(l, plan, act, cell) for l in ok]).median() * 100
    print(f"队列 {a.cohort} | 采纳率最高 n={len(lines)} (有实际数据)")
    print("  " + " | ".join(f"{c} {df[c].median():.1f}%" for c in df.columns))
    print("  全国中位: " + " | ".join(f"{c} {nat[c]:.1f}%" for c in df.columns))
    print("  差值:     " + " | ".join(f"{c} {df[c].median()-nat[c]:+.1f}pt" for c in df.columns))
    if a.cohort == "top":
        print("\n明细:")
        print(df.round(1).to_string())


if __name__ == "__main__":
    main()