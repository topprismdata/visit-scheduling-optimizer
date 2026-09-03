# -*- coding: utf-8 -*-
"""09区 apple-to-apple 终测: 三方案同一把尺 (OSM 骑行路网, 23 工作日, 686 次).
① SRP 原顺序  ② SRP 日集合+NN/2-opt 重排  ③ warm-ALNS 改进 (次数逐店精确)"""
import pandas as pd, json, math, time, urllib.request, warnings
warnings.filterwarnings("ignore")
OSRM = "https://routing.openstreetmap.de/routed-bike/route/v1/driving/"

def road_km(coords):
    s = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in coords)
    req = urllib.request.Request(f"{OSRM}{s}?overview=false", headers={"User-Agent": "gz-eval/1.0"})
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return r["routes"][0]["distance"] / 1000.0
        except Exception:
            time.sleep(1.5)
    return None

def nn2opt(seq, H):
    seq = list(seq)
    if len(seq) <= 2:
        return seq
    n = len(seq)
    out = [seq[0]]; unv = set(seq[1:])
    while unv:
        last = out[-1]
        out.append(min(unv, key=lambda j: H[last][j])); unv.discard(out[-1])
    def L(o): return sum(H[o[k]][o[k+1]] for k in range(len(o)-1))
    imp = True; ps = 0
    while imp and ps < 25:
        imp = False; ps += 1
        for a in range(1, n-2):
            for b in range(a+1, n-1):
                if H[out[a-1]][out[b]] + H[out[b]][out[a]] < H[out[a-1]][out[a]] + H[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return out

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date
g = pv[pv["销售名称"].str.contains("海珠荔湾09")].sort_values("拜访顺序")
mst = g.dropna(subset=["经度", "纬度"]).drop_duplicates("客户编码", keep="first").set_index("客户编码")
codes = list(mst.index)
LON = mst["经度"].astype(float).to_dict(); LAT = mst["纬度"].astype(float).to_dict()

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [LAT[a], LON[a], LAT[b], LON[b]])
    x = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371*math.asin(math.sqrt(x))
H = {a: {b: hav(a, b) for b in codes} for a in codes}

def pts(cs): return [(LON[c], LAT[c]) for c in cs]

# ---- ① 原顺序 ----
t1 = 0.0; v1 = 0
for dd, gd in g.groupby("date"):
    cs = [c for c in gd.sort_values("拜访顺序")["客户编码"] if c in LON]
    if len(cs) < 2: continue
    t1 += road_km(pts(cs)); v1 += len(cs); time.sleep(0.25)

# ---- ② SRP 日集合 + NN/2-opt 重排 ----
t2 = 0.0; v2 = 0
for dd, gd in g.groupby("date"):
    cs = [c for c in gd.sort_values("拜访顺序")["客户编码"] if c in LON]
    if len(cs) < 2: continue
    t2 += road_km(pts(nn2opt(cs, H))); v2 += len(cs); time.sleep(0.25)

# ---- ③ warm-ALNS 改进 (次数逐店精确) ----
opt = pd.read_csv("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/srp_alns_09.csv")
opt["客户编码"] = opt["客户编码"].astype(str)
t3 = 0.0; v3 = 0; cnt3 = opt["客户编码"].value_counts().to_dict()
for dd, gd in opt.groupby("拜访日期"):
    cs = [c for c in gd.sort_values("拜访顺序")["客户编码"] if c in LON]
    if len(cs) < 2: continue
    t3 += road_km(pts(cs)); v3 += len(cs); time.sleep(0.25)

print(f"{'方案':<34}{'拜访次数':>8}{'骑行路网km':>12}{'km/次':>8}")
for nm, t, v in (("① SRP 原计划(原顺序)", t1, v1),
                 ("② SRP 日集合+顺序重排", t2, v2),
                 ("③ warm-ALNS 改进(不劣化保底)", t3, v3)):
    print(f"{nm:<34}{v:>8}{t:>12.1f}{t/max(v,1):>8.3f}")
print()
print(f"② vs ①: -{(t1-t2)/t1:.1%}   ③ vs ①: -{(t1-t3)/t1:.1%}   ③ vs ②: {(t3-t2)/t2:+.1%}")
# 次数校验: ③ vs SRP 逐店
cnt_srp = g["客户编码"].value_counts().to_dict()
bad = [c for c in cnt_srp if cnt_srp[c] != cnt3.get(c, 0)] + [c for c in cnt3 if c not in cnt_srp]
print(f"③ 次数逐店一致: {'✓ 全部一致' if not bad else '✗ 差异 '+str(bad[:5])}  (①{v1} ②{v2} ③{v3})")
json.dump({"n1": round(t1,1), "n2": round(t2,1), "n3": round(t3,1),
           "v": [v1, v2, v3], "count_exact": not bad},
          open("/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/output/final_09_apple.json", "w"),
          ensure_ascii=False, indent=1)
