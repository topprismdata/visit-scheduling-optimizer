# -*- coding: utf-8 -*-
"""SRP 月计划重优化 — 业务→数学→引擎 全链路 (广州办 2026-07 真实数据).

业务层 (输入: SRP 有效计划 6564 行 + 进离店实际执行 9760 行):
  - 计划宇宙: 每销售编码的有效计划客户 (含主数据经纬度)
  - 月频次:   每店有效计划次数 (2..5)
  - 服务时长: SRP 逐店服务时长
  - 工作日历: 2026-07 周一~周五 (23 天)
  - 日工时上限: 480 min (业务容量, 替代奶制品竖线的 6 店/日默认)
数学层: 周期性 PVRP 集合划分 — 列=可行日计划, 主问题 one-column-per-day
  + 覆盖==freq + 最小重访间隔 + 日工时上限; 对偶引导定价; CP-SAT 终解; 均衡二次分配.
引擎层: algos.pvrp_cg.solver (solve_time_cg) + calibration.build_time_matrix
  (区县 min/km 用实际执行数据拟合 — 历史里程即标定源).
"""
import sys, json, time
from datetime import date
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")

import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")

from algos.pvrp_cg import solver
from algos.pvrp_cg.calibration import build_time_matrix
from algos.pvrp_cg.policy import PlanningPolicy
from algos.pvrp_cg.solver_adapter import solve_to_plan

SRP = "/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx"
ACT = "/Users/ghb/Downloads/进离店报表导出 (4).xlsx"
ONLY = sys.argv[1] if len(sys.argv) > 1 else None   # 传片区号可单线试跑

# ---------- 业务层: 装载 ----------
plan = pd.read_excel(SRP)
pv = plan[plan["计划是否有效标识"] == "有效"].copy()      # 失效行不参与
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date

act = pd.read_excel(ACT)
act["客户编码"] = act["客户编码"].astype(str)
act["进店时间"] = pd.to_datetime(act["进店时间"]); act["离店时间"] = pd.to_datetime(act["离店时间"])
act = act.dropna(subset=["进店时间", "进店经度", "进店纬度"])
act["wd"] = act["进店时间"].dt.weekday
act_wd = act[act["wd"] < 5].copy()                        # 周一~周五口径

# 标定样本: 实际执行的 door-to-door 分钟 (next_entry - prev_entry - prev_svc)
segments = []
for (zw, dd), g in act_wd.sort_values("进店时间").groupby(["组织架构编码", act_wd["进店时间"].dt.date]):
    g = g.sort_values("进店时间")
    rows = g.to_dict("records")
    for a, b in zip(rows, rows[1:]):
        t = (b["进店时间"] - a["进店时间"]).total_seconds() / 60 - float(a["在店时长(分钟)"] or 0)
        if 0.5 < t <= 150:
            segments.append((a["进店纬度"], a["进店经度"], b["进店纬度"], b["进店经度"], t,
                             b.get("district_name", "广州市")))
print(f"标定样本: {len(segments)} 条实测 door-to-door 腿", flush=True)

def hav_chain(lons, lats):
    R = 6371.0; tot = 0.0
    for i in range(len(lons) - 1):
        la1, lo1, la2, lo2 = map(np.radians, [lats[i], lons[i], lats[i + 1], lons[i + 1]])
        a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
        tot += 2 * R * np.arcsin(np.sqrt(a))
    return float(tot)

# ---------- 逐片区: 业务→数学→引擎 ----------
only_set = {ONLY} if ONLY else None
summary = []; plan_rows = []
for zw, g in sorted(pv.groupby("销售编码")):
    name = g["销售名称"].iloc[0]
    short = "".join(ch for ch in name.replace("海珠荔湾","") if ch.isdigit()) or name
    if only_set and short not in only_set:
        continue
    master = (g.dropna(subset=["经度", "纬度"])
                .sort_values("拜访日期")
                .drop_duplicates("客户编码", keep="first"))
    n = len(master)
    freq = g.groupby("客户编码").size().reindex(master["客户编码"]).astype(int).tolist()
    svc = master["服务时长"].astype(float).tolist()
    lats = master["纬度"].astype(float).tolist(); lons = master["经度"].astype(float).tolist()
    counties = master["district_name"].tolist()
    depot = (float(np.mean(lats)), float(np.mean(lons)))
    depot_county = master["district_name"].mode().iloc[0]

    # 数学层: 统一约束契约 (业务参数显式入契约)
    policy = PlanningPolicy(
        n_customers=n, frequency_rules={i: int(f) for i, f in enumerate(freq)},
        horizon_days=23, max_visits_per_day=40, max_work_minutes_per_day=480.0,
    )
    # 引擎配置: 契约值注入引擎 (替换奶制品竖线的 6 店/日隐藏常量)
    solver.MAX_PER_DAY = policy.max_visits_per_day
    solver.PASS1_TIME = 90; solver.MIP_TIME = 180; solver.CG_ROUNDS = 1

    t0 = time.time()
    p, visits, ev = solve_to_plan(
        lats=lats, lons=lons, depot=depot, representative_id=f"{name}",
        freq=freq, svc=svc, policy=policy, segments=segments,
        counties=counties, depot_county=depot_county,
        horizon_start=date(2026, 7, 1), time_limit=240, solver_type="time",
        verbose=False,
    )
    elapsed = time.time() - t0

    # 引擎输出 → 路线 km (按 sequence 链)
    if not visits:
        print(f"[{short}] 引擎未返回可行计划, 跳过", flush=True); continue
    vdf = pd.DataFrame([{"date": v.planned_date, "seq": v.sequence,
                         "ci": v.customer_id} for v in visits])
    opt_km = 0.0
    day_load = []
    for dd, gd in vdf.sort_values("seq").groupby("date"):
        idx = [int(x) for x in gd["ci"]]
        opt_km += hav_chain([lons[i] for i in idx], [lats[i] for i in idx])
        day_load.append(len(idx))
    # SRP 现行计划 km (拜访顺序链, 同一宇宙同一频次)
    srp_km = 0.0
    for dd, gd in g.sort_values("拜访顺序").groupby("date"):
        gd = gd[gd["客户编码"].isin(master["客户编码"])]
        if len(gd) < 2: continue
        m2 = master.set_index("客户编码").loc[gd["客户编码"]]
        srp_km += hav_chain(m2["经度"].tolist(), m2["纬度"].tolist())
    total_visits = sum(freq)
    summary.append(dict(
        片区=short, 客户=n, 月拜访=total_visits,
        SRP_km=round(srp_km, 1), 优化km=round(opt_km, 1),
        节省km=round(srp_km - opt_km, 1),
        节省率=f"{(srp_km-opt_km)/max(srp_km,1):.0%}",
        日均店=f"{np.mean(day_load):.1f}", 日最大=max(day_load),
        引擎状态=ev.status, 列数=ev.n_columns, 秒=round(elapsed, 1),
    ))
    for v in visits:
        mrow = master.iloc[int(v.customer_id)]
        plan_rows.append(dict(销售编码=zw, 销售名称=name, 拜访日期=v.planned_date,
                              拜访顺序=v.sequence, 客户编码=mrow["客户编码"],
                              客户名称=mrow["客户名称"], 服务时长=v.estimated_service_minutes))
    print(f"[{short}] n={n} SRP={srp_km:.0f}km opt={opt_km:.0f}km "
          f"({(srp_km-opt_km)/max(srp_km,1):.0%}) status={ev.status} {elapsed:.0f}s", flush=True)

t = pd.DataFrame(summary).sort_values("SRP_km", ascending=False)
pd.set_option("display.width", 220)
print("\n" + t.to_string(index=False))
to, tn = t["SRP_km"].sum(), t["优化km"].sum()
print(f"\n全办: {to:.0f}km -> {tn:.0f}km, 月节省 {to-tn:.0f}km ({(to-tn)/to:.0%})")
import os
os.makedirs("/tmp/gz_gif/opt", exist_ok=True)
if summary:
    t.to_csv(f"/tmp/gz_gif/opt/summary_{short}.csv", index=False)
    pd.DataFrame(plan_rows).to_csv(f"/tmp/gz_gif/opt/plan_{short}.csv", index=False)
print("saved", flush=True)
