# -*- coding: utf-8 -*-
"""义务合规率 KPI — 计划版本可选 (默认《更新后的8月规划》, 业代真正执行的那一版).

用法: [PLAN_XLSX=...] python experiments/kpi_compliance.py
"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestration.experience.compliance import store_compliance, phase_hit  # noqa: E402

UFS = Path("/Users/ghb/UFS-demo")
PLAN_XLSX = Path(os.environ.get("PLAN_XLSX", str(UFS / "更新后的8月规划.xlsx")))
KPI = pd.read_excel(UFS / "采纳执行-8月.xlsx")
OK = set(KPI["sales_line_code"].astype(str))
plan = pd.read_excel(PLAN_XLSX)
plan["customer_code"] = plan["customer_code"].astype(str)
plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
plan["ph"] = (((plan["plan_day"].dt.day - 1) // 7 + 1) % 2)
act = pd.read_csv(UFS / "8月实际走访数据-了解实际情况.csv", encoding="gbk",
                  usecols=["call_date", "customer_code", "salesperson_code"])
act["customer_code"] = act["customer_code"].astype(str)
act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
act["ph"] = (((act["call_date"].dt.day - 1) // 7 + 1) % 2)

comp, ph, sameday, cov = [], [], [], []
for lid, g in plan.groupby("sales_line_code"):
    lid = str(lid)
    if lid not in OK:
        continue
    a = act[act["salesperson_code"] == lid]
    pc = g.groupby("customer_code").size().to_dict()
    ac = a.groupby("customer_code").size().to_dict()
    pp = g.drop_duplicates("customer_code").set_index("customer_code")["ph"].to_dict()
    ap = a.groupby("customer_code")["ph"].apply(set).to_dict()
    comp.append(store_compliance(pc, ac)); ph.append(phase_hit(pp, ap))
    ps = set(zip(g["customer_code"], g["plan_day"])); as_ = set(zip(a["customer_code"], a["call_date"]))
    if ps:
        sameday.append(len(ps & as_) / len(ps))
    cov.append(len(set(g["customer_code"]) & set(a["customer_code"])) / max(g["customer_code"].nunique(), 1))

print(f"计划版本: {PLAN_XLSX.name} | 线 {len(comp)}")
print(f"义务合规率  均值 {np.mean(comp):.3f} 中位 {np.median(comp):.3f}")
print(f"相位合规率  均值 {np.mean(ph):.3f} 中位 {np.median(ph):.3f}")
print(f"严格同日执行 均值 {np.mean(sameday):.3f} 中位 {np.median(sameday):.3f}")
print(f"门店覆盖    均值 {np.mean(cov):.3f} 中位 {np.median(cov):.3f}")
sd = float(np.std(comp, ddof=1)); n = len(comp); za, zb = 1.96, 0.8416
print(f"\n线间 σ(合规率) = {sd:.3f} | 可用线 {n}")
for delta in (0.03, 0.05, 0.08, 0.10):
    per = 2*(za+zb)**2*sd**2/delta**2
    print(f"  检出 Δ={delta:.2f} 需每臂 {per:,.0f} 线 {'✅' if per <= n/2 else '❌'}")
mde = (2*(za+zb)**2*sd**2/(n/2))**0.5
print(f"  每臂 {n//2} 线 → 最小可检出 Δ = {mde:.3f}")
