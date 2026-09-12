# -*- coding: utf-8 -*-
"""全部.xlsx -> per-line problem JSON (广州 svc_golden 同构) + 合同普查."""
import os, json, hashlib
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSX = os.environ.get("NW_XLSX", "/Users/ghb/Downloads/全部.xlsx")
OUT = os.path.join(ROOT, "output", "nationwide", "specs")
os.makedirs(OUT, exist_ok=True)


MIN_VISITS, MIN_DAYS = 5, 2  # 数据健全性门: 3行/1行的噪声编码无法形成日路线

def fname(line):
    return hashlib.sha1(line.encode()).hexdigest()[:12] + ".json"


def main():
    df = pd.read_excel(XLSX)
    df["客户编码"] = df["客户编码"].astype(str)
    df["date"] = pd.to_datetime(df["拜访日期"]).dt.strftime("%Y-%m-%d")
    census = {}
    for line, ln in df.groupby("销售编码"):
        if len(ln) < MIN_VISITS:
            census[line] = dict(excluded="too_few_visits", n_visits=len(ln))
            continue
        sd = ln.groupby("客户编码")[["lng", "lat"]].first()
        stores = []
        for i, (code, r) in enumerate(sd.iterrows()):
            v = int((ln["客户编码"] == code).sum())
            stores.append(dict(id=i, code=code, lon=float(r["lng"]), lat=float(r["lat"]),
                               frequency=dict(horizon=None, visits=v)))
        c2i = {s["code"]: s["id"] for s in stores}
        days = sorted(ln["date"].unique())
        assign = {d: [c2i[c] for c in
                      ln[ln["date"] == d].sort_values("拜访顺序")["客户编码"]]
                  for d in days}
        sw = ln["服务周"].astype(str).value_counts().to_dict()
        prov = str(ln["province"].iloc[0]).strip()
        spec = dict(
            schema="nationwide-sweep/1", version="1",
            inputs_hash=hashlib.sha1(
                (line + str(len(stores)) + str(len(ln))).encode()).hexdigest()[:12],
            line_id=line,
            cycle=dict(n_days=len(days), dates=days),
            stores=stores,
            original_assignment_idx=assign,
            meta=dict(province=prov, n_stores=len(stores), n_visits=len(ln),
                      burned=(prov == "110000"),
                      service_week_census=sw,
                      k_workdays=len(days)))
        with open(os.path.join(OUT, fname(line)), "w") as f:
            json.dump(spec, f, ensure_ascii=False)
        census[line] = dict(province=prov, burned=spec["meta"]["burned"],
                            file=fname(line), n=len(stores), V=len(ln), K=len(days),
                            f=round(len(ln) / len(stores), 3), service_weeks=sw)
    with open(os.path.join(ROOT, "output", "nationwide", "census.json"), "w") as f:
        json.dump(census, f, ensure_ascii=False, indent=1)
    ok = [c for c in census.values() if not c.get("excluded")]
    skipped = [k for k, c in census.items() if c.get("excluded")]
    k1 = sum(1 for c in ok if c["K"] == 1)
    print(f"specs: {len(ok)} lines (SKIP {len(skipped)}: {skipped}); "
          f"burned={sum(c['burned'] for c in ok)}; f_max={max(c['f'] for c in ok):.2f}; "
          f"K=1 lines={k1}")


if __name__ == "__main__":
    main()
