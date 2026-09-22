# -*- coding: utf-8 -*-
"""服务日校准器 — 把计划的"服务日"改成业务实际去的星期, 并用样本外验证.

背景: 全量实测(582 线)显示 **实际主力星期 == 服务日 只有中位 66.9%**,
      即约 1/3 门店: 系统让它某天去, 业务实际在别的天去。这是"计划不贴实际"最锋利的位置。

方法(不增门店/不增频次/不动相位, 只改星期):
  训练 = W1–W2 实际到访 → 每店校准后服务日 := 训练期实际主力星期(1-based);
                          训练期没去过的店 → 保留原服务日(不猜)
  验证 = W3–W4 实际到访(样本外) → 星店命中率 = 该店新服务日出现在其 W3–W4 实际星期集合的比例
  对照 = 原服务日 在同一批门店上的命中率

同时检查副作用:
  ① 日容量匹配: 各星期"计划店数"与"实际到访店数"的 L1 距离(越小越贴)
  ② 块结构: 校准后重算 服务日×连通 块 → 块数/平衡CV/紧凑度是否劣化
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.blocks import build as build_blocks  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def wk(d):
    return (d.day - 1) // 7 + 1


def main():
    plan = pd.read_excel(PLAN_XLSX)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["sales_line_code"] = plan["sales_line_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wk"] = plan["plan_day"].apply(wk)
    act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    act["wk"] = act["call_date"].apply(wk)
    act["wd"] = act["call_date"].dt.dayofweek
    A = {l: g for l, g in act.groupby("salesperson_code")}

    rows = []
    for lid, pl in plan.groupby("sales_line_code"):
        al = A.get(lid)
        if al is None or not len(al) or not len(pl):
            continue
        tr = al[al["wk"] <= 2]
        tg = al[al["wk"] >= 3]
        if not len(tr) or not len(tg):
            continue
        mode_tr = tr.groupby("customer_code")["wd"].apply(lambda s: int(s.value_counts().index[0])).to_dict()
        wset_tg = tg.groupby("customer_code")["wd"].apply(set).to_dict()
        sto = pl.drop_duplicates("customer_code").set_index("customer_code")
        svc = {}
        for c in sto.index:
            v = sto.loc[c, "服务日"]
            svc[c] = int(v) if v == v and int(v) > 0 else -1
        # 校准
        new = {}
        changed = 0
        for c in sto.index:
            m = mode_tr.get(c)
            if m is None or svc[c] <= 0:
                new[c] = svc[c]
            else:
                new[c] = m + 1
                if new[c] != svc[c]:
                    changed += 1
        # 样本外命中(W3–W4): 该店(新/原)服务日的星期 是否出现在其 W3–W4 实际星期集合中
        base_hit, new_hit, n = [], [], 0
        only = [c for c in sto.index if c in wset_tg and svc[c] > 0]
        for c in only:
            n += 1
            base_hit.append(1.0 if (svc[c] - 1) in wset_tg[c] else 0.0)
            new_hit.append(1.0 if (new[c] - 1) in wset_tg[c] else 0.0)
        if not n:
            continue
        # 日容量匹配
        pl2 = pl.copy()
        pl2["服务日"] = pl2["customer_code"].map(new)
        cap_o = np.array([len(pl[pl["服务日"] == w]) for w in range(1, 6)], float)
        cap_n = np.array([len(pl2[pl2["服务日"] == w]) for w in range(1, 6)], float)
        cap_a = np.array([len(tg[tg["wd"] == w - 1]["customer_code"].unique()) for w in range(1, 6)], float)
        l1o = float(np.abs(cap_o / max(cap_o.sum(), 1) - cap_a / max(cap_a.sum(), 1)).sum())
        l1n = float(np.abs(cap_n / max(cap_n.sum(), 1) - cap_a / max(cap_a.sum(), 1)).sum())
        # 块结构变化
        try:
            b0 = build_blocks(pl, al)
            b1 = build_blocks(pl2, al)
            cv0, cv1 = b0["diag"]["svc_cv"], b1["diag"]["svc_cv"]
            nb0, nb1 = b0["diag"]["svc_blocks"], b1["diag"]["svc_blocks"]
            cp0, cp1 = b0["diag"]["svc_compact"], b1["diag"]["svc_compact"]
        except Exception:
            cv0 = cv1 = nb0 = nb1 = cp0 = cp1 = None
        rows.append({"line": lid, "stores": n, "changed": changed,
                     "base_hit": round(float(np.mean(base_hit)), 3), "new_hit": round(float(np.mean(new_hit)), 3),
                     "cap_L1_old": round(l1o, 3), "cap_L1_new": round(l1n, 3),
                     "blocks_old": nb0, "blocks_new": nb1, "cv_old": cv0, "cv_new": cv1,
                     "compact_old": cp0, "compact_new": cp1})
    d = pd.DataFrame(rows)
    outdir = ROOT / "output/rep_behavior"
    outdir.mkdir(parents=True, exist_ok=True)
    d.to_csv(outdir / "service_day_calibration.csv", index=False)
    print(f"线数 {len(d)} | 参与校验门店合计 {int(d['stores'].sum()):,}")
    print(f"改过服务日的门店占比: 中位 {(d['changed']/d['stores']).median()*100:.1f}%")
    print(f"\n样本外(W3–W4) 星期命中:")
    print(f"  原服务日   中位 {d['base_hit'].median()*100:.1f}%  均值 {d['base_hit'].mean()*100:.1f}%")
    print(f"  校准后     中位 {d['new_hit'].median()*100:.1f}%  均值 {d['new_hit'].mean()*100:.1f}%")
    print(f"  改善的线    {(d['new_hit']>d['base_hit']).mean()*100:.0f}%   持平 {(d['new_hit']==d['base_hit']).mean()*100:.0f}%   变差 {(d['new_hit']<d['base_hit']).mean()*100:.0f}%")
    print(f"  命中≥90%的线: 原 {int((d['base_hit']>=0.9).sum())} → 校准后 {int((d['new_hit']>=0.9).sum())}")
    print(f"\n日容量匹配 L1(越小越贴实际): 原 中位 {d['cap_L1_old'].median():.3f} → 校准后 {d['cap_L1_new'].median():.3f} (改善 {(d['cap_L1_new']<d['cap_L1_old']).mean()*100:.0f}% 的线)")
    if d["cv_old"].notna().any():
        print(f"块结构(服务日×连通): 块数 中位 {d['blocks_old'].median():.0f} → {d['blocks_new'].median():.0f} | "
              f"平衡CV 中位 {d['cv_old'].median():.3f} → {d['cv_new'].median():.3f} | 紧凑度 {d['compact_old'].median():.3f} → {d['compact_new'].median():.3f}")
    print(f"\n明细: {outdir/'service_day_calibration.csv'}")


if __name__ == "__main__":
    main()