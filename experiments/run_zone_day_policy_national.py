# -*- coding: utf-8 -*-
"""ZoneDayPolicy 全国学习 + 出厂质检器校准复验 (v0.3 S1).

输入: UFS-demo 8月 实际打卡 CSV + 系统规划 xlsx
输出: output/experience/zone_day_policy_2026-08.json
     (979 实际线模板 + 547 计划线一致度/预测执行率/实际执行率)

复验: argmax 一致度 vs 同日执行率 相关应 ≈ 0.82 (2026-09-21 研究锚点)。
"""
import json
import sys
from pathlib import Path

import h3
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestration.experience import alignment_score, learn_zone_day_policy, predict_compliance

ACT_PATH = "/Users/ghb/UFS-demo/8月实际走访数据-了解实际情况.csv"
PLAN_PATH = "/Users/ghb/UFS-demo/8月规划结果-调整.xlsx"
OUT = Path("output/experience/zone_day_policy_2026-08.json")


def main():
    act = pd.read_csv(ACT_PATH, encoding="gbk",
                      usecols=["call_date", "customer_code", "salesperson_code"])
    act["customer_code"] = act["customer_code"].astype(str)
    act["call_date"] = pd.to_datetime(act["call_date"]).dt.normalize()
    plan = pd.read_excel(PLAN_PATH)
    plan["customer_code"] = plan["customer_code"].astype(str)
    plan["plan_day"] = pd.to_datetime(plan["plan_day"]).dt.normalize()
    plan["wd"] = plan["plan_day"].dt.dayofweek

    crd = plan.dropna(subset=["lat", "lng"]).drop_duplicates("customer_code")
    cell_map = {r.customer_code: h3.latlng_to_cell(r.lat, r.lng, 7) for r in crd.itertuples()}
    print(f"店→res7格: {len(cell_map)} | 实际线 {act['salesperson_code'].nunique()} | 计划线 {plan['sales_line_code'].nunique()}")

    # ---- 学习 (全部实际线, 含无计划线 — 模板本身不依赖计划) ----
    tpl = learn_zone_day_policy(act, cell_map)
    print(f"模板学习: {len(tpl)} 线")

    # ---- 质检: 计划线一致度 vs 实际执行 ----
    code2day = {}
    for r in plan.itertuples():
        code2day[(r.customer_code, r.wd)] = 1
    rows = []
    for lid, gg in plan.groupby("sales_line_code"):
        t = tpl.get(str(lid))
        if t is None or gg["customer_code"].map(cell_map).isna().mean() > 0.5:
            continue
        gp = gg.dropna(subset=["lat", "lng"]).copy()
        gp["cell"] = gp["customer_code"].map(cell_map)
        sc = alignment_score(gp[["plan_day", "customer_code", "cell"]], t)
        ah = act[act["salesperson_code"] == lid]
        if len(ah) < 10:
            continue
        same = np.mean([code2day.get((c, w), 0) == 1
                        for c, w in zip(ah["customer_code"], ah["call_date"].dt.dayofweek)])
        rows.append({"line": str(lid), "argmax一致": sc["argmax"], "likelihood": sc["likelihood"],
                     "预测执行": predict_compliance(sc["argmax"]), "实际同日执行": round(float(same), 3),
                     "模板support": t.support})
    df = pd.DataFrame(rows)
    corr = df["argmax一致"].corr(df["实际同日执行"])
    calib_err = (df["预测执行"] - df["实际同日执行"]).abs().median()
    print(f"\n质检线数: {len(df)} | 一致→执行 相关: {corr:.2f} (锚点 0.82) | 预测中位绝对误差: {calib_err:.2f}")
    print("\n芜湖三线:")
    print(df[df["line"].isin(["NP8800295", "000707342", "NP0011193"])].to_string(index=False))
    print("\n一致度最低 5 线 (出厂就该拦):")
    print(df.nsmallest(5, "argmax一致").to_string(index=False))

    # ---- 落盘 ----
    OUT.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema": "zone_day_policy/v1", "month": "2026-08", "res": 7,
        "note": "LEARNED_PREFERENCE — 不得直接作硬约束 (v0.3 §3)",
        "templates": {lid: {"support": t.support, "top_cell": {str(k): v for k, v in t.top_cell.items()},
                            "confidence": {str(k): v for k, v in t.confidence.items()}}
                      for lid, t in tpl.items()},
        "qc": df.to_dict(orient="records"),
        "validation": {"corr_argmax_compliance": round(float(corr), 3), "n_lines": len(df)},
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=1))
    print(f"\n产物: {OUT} ({OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
