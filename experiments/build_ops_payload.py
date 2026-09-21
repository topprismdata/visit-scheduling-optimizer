# -*- coding: utf-8 -*-
"""Operations Workspace 原型数据载荷: 芜湖三线 计划×实际×模板 (v0.3 S3).

诚实口径: 计划=虚线路由(visit_num序), 实际=点(打卡时间序不可信, 不画顺序);
坐标一律主数据/规划坐标; 状态 same/shift/miss/extra 由 日期×店集合 推导。
"""
import json
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestration.experience import alignment_score, learn_zone_day_policy, predict_compliance

LINES = {"NP8800295": "三山线·8800295", "000707342": "外围县市线·707342", "NP0011193": "城区线·0011193"}
PLAN = pd.read_excel("/Users/ghb/UFS-demo/更新后的8月规划.xlsx")
PLAN["customer_code"] = PLAN["customer_code"].astype(str)
PLAN["plan_day"] = pd.to_datetime(PLAN["plan_day"]).dt.normalize()
ACT = pd.read_csv("/Users/ghb/UFS-demo/8月实际走访数据-了解实际情况.csv", encoding="gbk",
                  usecols=["call_date", "customer_code", "salesperson_code"])
ACT["customer_code"] = ACT["customer_code"].astype(str)
ACT["call_date"] = pd.to_datetime(ACT["call_date"]).dt.normalize()

crd = PLAN.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
cell_map = {r.customer_code: h3.latlng_to_cell(r.lat, r.lng, 7) for r in crd.itertuples()}
name_map = crd.set_index("customer_code")["customer_name"].to_dict()
addr_map = crd.set_index("customer_code")["customer_address"].to_dict()
otm_map = crd.set_index("customer_code")["otm_level"].to_dict()
svc_map = PLAN.drop_duplicates("customer_code").set_index("customer_code")["服务日"].to_dict()
# 主数据兜底 (计划外店坐标/名称)
MST = pd.read_excel("/Users/ghb/UFS-demo/芜湖客户清单--检测数据质量用.xlsx")
MST["code"] = MST["客户编码"].astype(str)
MST = MST.dropna(subset=["lat", "lng"]).drop_duplicates("code")
for r in MST.itertuples():
    if r.code not in cell_map:
        cell_map[r.code] = h3.latlng_to_cell(r.lat, r.lng, 7)
        name_map[r.code] = r.customer_name
        otm_map[r.code] = getattr(r, "OTM等级", "")
coords = {**{r.customer_code: (float(r.lat), float(r.lng)) for r in crd.itertuples()},
          **{r.code: (float(r.lat), float(r.lng)) for r in MST.itertuples()}}
tpl_all = learn_zone_day_policy(ACT[ACT["customer_code"].isin(cell_map)], cell_map)

payload = {"month": "2026-08", "res": 7, "lines": {}, "meta": {
    "note": "计划=虚线(visit_num序) 实际=点(时间序不可信) 坐标=规划/主数据",
    "generated": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}}

for lid, label in LINES.items():
    pl = PLAN[PLAN["sales_line"] == lid].copy()
    ac = ACT[ACT["salesperson_code"] == lid].copy()
    t = tpl_all.get(lid)
    sc = alignment_score(pl.assign(cell=pl["customer_code"].map(cell_map))[
        ["plan_day", "customer_code", "cell"]], t) if t else None
    # 店→实际执行日集合
    adates = ac.groupby("customer_code")["call_date"].apply(set).to_dict()
    pdates = pl.groupby("customer_code")["plan_day"].apply(set).to_dict()
    # 每线 zone 短名 (按频次 A,B,C...)
    zones = sorted(set(pl["customer_code"].map(cell_map).dropna()),
                   key=lambda z: -pl["customer_code"].map(cell_map).value_counts().get(z, 0))
    def _zn(i):  # A..Z, 超出用序号
        return chr(65 + i) if i < 26 else "z" + str(i)
    zname = {z: _zn(i) for i, z in enumerate(zones)}
    days = []
    for d in sorted(pl["plan_day"].unique()):
        g = pl[pl["plan_day"] == d].sort_values("visit_num")
        a_day = ac[ac["call_date"] == d]
        wd = int(pd.Timestamp(d).dayofweek)
        planned, actual = [], []
        for r in g.itertuples():
            cell = cell_map.get(r.customer_code)
            st = "same" if d in adates.get(r.customer_code, set()) else (
                "shift" if r.customer_code in adates else "miss")
            planned.append({"c": r.customer_code, "n": name_map.get(r.customer_code, ""),
                            "lat": round(float(r.lat), 5), "lng": round(float(r.lng), 5),
                            "z": zname.get(cell, "?"), "seq": int(r.visit_num), "s": st,
                            "otm": str(otm_map.get(r.customer_code, "")),
                            "svc": int(svc_map.get(r.customer_code, 0))})
        for c in set(a_day["customer_code"]):
            if c not in coords:
                continue
            cell = cell_map.get(c)
            st = "same" if c in set(g["customer_code"]) else (
                "shift" if c in pdates else "extra")
            actual.append({"c": c, "n": name_map.get(c, ""),
                           "lat": round(coords[c][0], 5), "lng": round(coords[c][1], 5),
                           "z": zname.get(cell, "?"), "s": st})
        def chain_km(seq):
            pts = [(r["lat"], r["lng"]) for r in sorted(seq, key=lambda x: x["seq"])]
            return round(sum(np.linalg.norm(np.diff(pts, axis=0), axis=1) * 111), 1) if len(pts) > 1 else 0
        top_z = pd.Series([p["z"] for p in planned]).value_counts().index[0] if planned else None
        days.append({"d": str(pd.Timestamp(d).date()), "wd": wd,
                     "planned": planned, "actual": actual,
                     "pkm": chain_km(planned),
                     "tpl_z": zname.get(t.top_cell.get(wd, ""), None) if t else None,
                     "tpl_conf": (t.confidence.get(wd) if t else None)})
    cov = len(set(ac["customer_code"]) & set(pl["customer_code"])) / pl["customer_code"].nunique()
    same = sum(1 for dd in days for p in dd["planned"] if p["s"] == "same")
    payload["lines"][lid] = {
        "label": label, "zones": zname,
        "kpi": {"stores": int(pl["customer_code"].nunique()), "visits": int(len(pl)),
                "days": int(pl["plan_day"].nunique()),
                "coverage": round(cov, 3),
                "same_day": round(same / len(pl), 3),
                "alignment": sc["argmax"] if sc else None,
                "predicted": predict_compliance(sc["argmax"]) if sc else None,
                "support": t.support if t else 0},
        "days": days}

out = Path("output/experience/ops_workspace_payload.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, ensure_ascii=False))
print("payload:", out, f"{out.stat().st_size/1024:.0f} KB")
for lid in LINES:
    k = payload["lines"][lid]["kpi"]
    print(lid, k)
