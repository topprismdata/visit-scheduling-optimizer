# -*- coding: utf-8 -*-
"""基线审判: 人类 GPS 实际走法 vs 计划打印顺序 vs 同日集合重排.
若 实际/实际重排 ≈ 1 → 人类自发重排, 打印顺序是稻草人基线 (真正的对手=实际里程).
若 实际/实际重排 >> 1 → 人类照打印顺序走, 1,116 基线成立."""
import pandas as pd, json, math, time, urllib.request, warnings
warnings.filterwarnings("ignore")
OSRM = "https://routing.openstreetmap.de/routed-bike/route/v1/driving/"
def road_km(coords):
    s = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in coords)
    req = urllib.request.Request(f"{OSRM}{s}?overview=false", headers={"User-Agent":"gz-eval/1.0"})
    for k in range(5):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=45).read())["routes"][0]["distance"]/1000.0
        except Exception:
            time.sleep(2+k)
    return None

act = pd.read_excel("/Users/ghb/Downloads/进离店报表导出 (4).xlsx")
act["进店时间"] = pd.to_datetime(act["进店时间"])
act["日期"] = act["进店时间"].dt.date
liang = act[act["人员名称"]=="梁健满"].sort_values("进店时间")
DAYS = [pd.Timestamp(f"2026-07-{d}").date() for d in (6,7,8,9,10)]

def nn2opt(cs):
    if len(cs) <= 3: return cs
    def d(a,b):
        la1,lo1,la2,lo2 = map(math.radians,[a[1],a[0],b[1],b[0]])
        x = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
        return 2*6371*math.asin(math.sqrt(x))
    H = {a: {b: d(a,b) for b in cs} for a in cs}
    out = [cs[0]]; unv = set(cs[1:])
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: H[l][j])); unv.discard(out[-1])
    imp = True; ps = 0
    while imp and ps < 25:
        imp = False; ps += 1
        for a in range(1, len(out)-2):
            for b in range(a+1, len(out)-1):
                if H[out[a-1]][out[b]] + H[out[b]][out[a]] < H[out[a-1]][out[a]] + H[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return out

print(f"{'日期':<12}{'实际店':>5}{'实际走法km':>10}{'重排km':>8}{'实际/重排':>9}")
t_act = t_opt = 0.0
for dd in DAYS:
    gd = liang[liang["日期"]==dd].sort_values("进店时间")
    # 每次停店取首个可信点坐标; 保留人类经过的全部停点顺序
    pts = {}
    for _, r in gd.iterrows():
        c = str(r["客户编码"])
        if c not in pts:
            pts[c] = (float(r["进店经度"]), float(r["进店纬度"]))
    seq_act = []
    for _, r in gd.iterrows():
        c = str(r["客户编码"]); p = pts[c]
        if not seq_act or seq_act[-1] != p:
            seq_act.append(p)
    uniq = list(dict.fromkeys(seq_act))
    opt = nn2opt(uniq)
    k_act = road_km(seq_act); time.sleep(0.25)
    k_opt = road_km(opt) if opt != uniq else k_act; time.sleep(0.25)
    if k_act is None or k_opt is None: continue
    t_act += k_act; t_opt += k_opt
    print(f"{str(dd):<12}{len(uniq):>5}{k_act:>10.1f}{k_opt:>8.1f}{k_act/max(k_opt,0.1):>9.2f}")
print(f"\n5日合计: 人类实际走法 {t_act:.1f} km | 同日集合重排最优 {t_opt:.1f} km | 比值 {t_act/max(t_opt,1):.2f}")
print(f"参照: 计划打印/重排 比值 = 1116/636 = 1.75 (全月)")
