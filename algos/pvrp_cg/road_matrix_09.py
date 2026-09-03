# -*- coding: utf-8 -*-
"""为 09 区计划的 163 个门店构建 OSM 骑行路网距离矩阵 (一次抓取, 之后 ①②③ 全部同源).
FOSSGIS table 服务: 每个 source 一次请求 (含全部 destinations)."""
import pandas as pd, numpy as np, json, time, urllib.request, warnings
from concurrent.futures import ThreadPoolExecutor
warnings.filterwarnings("ignore")
URL = "https://routing.openstreetmap.de/routed-bike/table/v1/driving/"

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
g09 = pv[pv["销售名称"].str.contains("海珠荔湾09")]
mst = g09.dropna(subset=["经度", "纬度"]).drop_duplicates("客户编码", keep="first").reset_index(drop=True)
codes = mst["客户编码"].tolist()
pts = [(float(a), float(b)) for a, b in zip(mst["经度"], mst["纬度"])]
n = len(codes)
print("门店数:", n, flush=True)
coord_str = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in pts)

def row_for(src):
    url = f"{URL}{coord_str}?sources={src}&annotations=distance"
    req = urllib.request.Request(url, headers={"User-Agent": "gz-eval/1.0"})
    for k in range(6):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if r.get("code") != "Ok":
                raise RuntimeError(r.get("message"))
            d = r["durations"][0]
            return src, [np.nan if x is None else x / 1000.0 for x in
                         [v for v in r["distances"][0]]]
        except Exception as e:
            time.sleep(2 + k)
    return src, None

D = np.full((n, n), np.nan)
with ThreadPoolExecutor(max_workers=4) as ex:
    for src, row in ex.map(row_for, range(n)):
        if row is None:
            print("FAIL row", src, codes[src], flush=True); continue
        D[src, :] = row
print("矩阵填充率:", round((~np.isnan(D)).mean(), 3), flush=True)
json.dump({"codes": codes, "pts": pts, "D": [[None if np.isnan(v) else round(v, 4) for v in row] for row in D]},
          open("output/road_matrix_09.json", "w"))
print("saved output/road_matrix_09.json")
