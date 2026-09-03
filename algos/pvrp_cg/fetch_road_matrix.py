# -*- coding: utf-8 -*-
"""获取 163 店完整骑行路网距离矩阵 (OSM FOSSGIS, 分块请求)."""
import pandas as pd, numpy as np, json, math, time, urllib.request, warnings
warnings.filterwarnings("ignore")
URL = "https://routing.openstreetmap.de/routed-bike/table/v1/driving/"

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"]=="有效"].copy(); pv["客户编码"]=pv["客户编码"].astype(str)
pv["拜访日期"]=pd.to_datetime(pv["拜访日期"])
g = pv[pv["销售名称"]=="海珠荔湾09"]
pts = g.dropna(subset=["经度","纬度"]).drop_duplicates("客户编码",keep="first").set_index("客户编码")
codes = pts.index.tolist()
LON=pts["经度"].astype(float).tolist(); LAT=pts["纬度"].astype(float).tolist()
n=len(codes)
print(f"获取 {n} 店的骑行路网距离矩阵...")

coord_str = ";".join(f"{lo:.6f},{la:.6f}" for lo,la in zip(LON,LAT))

# FOSSGIS table 限制单次 50 个坐标, 用 sources 参数分批请求
D = np.full((n,n), np.nan)
batch = 40
for src_start in range(0, n, batch):
    src_end = min(src_start+batch, n)
    srcs = ";".join(str(i) for i in range(src_start, src_end))
    url = f"{URL}{coord_str}?sources={srcs}&annotations=distance"
    req = urllib.request.Request(url, headers={"User-Agent":"gz-eval/1.0"})
    for attempt in range(5):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if r.get("code") == "Ok":
                dists = r["distances"]
                for li, row in enumerate(dists):
                    gi = src_start + li
                    for j in range(n):
                        v = row[j]
                        if v is not None:
                            D[gi][j] = v / 1000.0
                print(f"  rows {src_start}-{src_end-1} ✓ ({len(dists)} rows)", flush=True)
                break
            else:
                print(f"  code={r.get('code')}", flush=True); time.sleep(2)
        except Exception as e:
            print(f"  attempt {attempt+1} fail: {e}", flush=True); time.sleep(3)
    time.sleep(0.3)

fill = (~np.isnan(D)).mean()
print(f"矩阵填充率: {fill:.1%}")
np.save("output/road_dist_09.npy", D)
json.dump({"codes": codes}, open("output/road_codes_09.json","w"))
print("saved output/road_dist_09.npy")
