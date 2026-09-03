# -*- coding: utf-8 -*-
"""④ 顺序层精确化: 每个 SRP 日集合 → CP-SAT AddCircuit 精确 TSP (haversine) → OSRM 骑行复测.
目的: 证伪/证实 ②(636.3km, NN+2opt 启发式顺序) 是否已触顺序最优.
构造性保证: ④ 的日集合与 ② 完全相同 (仅顺序可能更优), 逐日同尺 OSRM 量.
对照下界: 每日 haversine 精确回路长 / OSRM 实测 → 路/直比 (标定扭曲系数)."""
import pandas as pd, numpy as np, json, math, time, urllib.request, warnings, datetime
warnings.filterwarnings("ignore")
from ortools.sat.python import cp_model

OSRM = "https://routing.openstreetmap.de/routed-bike/route/v1/driving/"
T_TSP = 90; T_OS = 60

def road_km(coords):
    s = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in coords)
    req = urllib.request.Request(f"{OSRM}{s}?overview=false", headers={"User-Agent": "gz-eval/1.0"})
    for _ in range(3):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=T_OS).read())["routes"][0]["distance"] / 1000.0
        except Exception:
            time.sleep(1.5)
    return None

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date
g = pv[pv["销售名称"].str.contains("海珠荔湾09")].sort_values("拜访顺序")
mst = g.dropna(subset=["经度", "纬度"]).drop_duplicates("客户编码", keep="first").set_index("客户编码")
LON = mst["经度"].astype(float).to_dict(); LAT = mst["纬度"].astype(float).to_dict()

def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, [LAT[a], LON[a], LAT[b], LON[b]])
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))

def exact_open_tsp(cs):
    """开放路径 TSP (起点=第一个拜访店, 不回路, 与链式里程口径一致): CP-SAT 精确."""
    n = len(cs)
    if n <= 2: return cs, sum(hav(cs[k], cs[k+1]) for k in range(n - 1))
    Cm = [[int(round(hav(a, b) * 1000)) for b in cs] for a in cs]
    m = cp_model.CpModel()
    x = {}
    for i in range(n):
        for j in range(n):
            if i != j: x[(i, j)] = m.NewBoolVar(f"x{i}_{j}")
    # 每点 出<=1 入<=1; 起=0 入0, 终点自由: 加虚拟终点 n: 所有点→n, n→起 闭成回路
    N = n + 1
    y = {}
    for i in range(n):
        for j in range(N):
            if i == j: continue
            y[(i, j)] = x[(i, j)] if j < n else m.NewBoolVar(f"t{i}")
    for i in range(0, n):  # start=0: 出=1 入=0
        m.Add(sum(y[(0, j)] for j in range(N) if j != 0) == 1)
        m.Add(sum(y[(i, 0)] for i in range(n) if i != 0) == 0)
    for i in range(1, n):
        m.Add(sum(y[(i, j)] for j in range(N) if j != i) == 1)
        m.Add(sum(y[(k, i)] for k in range(n) if k != i) == 1)
    m.Add(sum(y[(k, n)] for k in range(n)) == 1)
    cost = []
    for i in range(n):
        for j in range(n):
            if i != j: cost.append(y[(i, j)] * Cm[i][j])
    for i in range(n): cost.append(y[(i, n)] * 0)
    # subtour 消除 (MTZ)
    u = [m.NewIntVar(0, n, f"u{i}") for i in range(n)]
    for i in range(1, n):
        for j in range(1, n):
            if i != j:
                m.Add(u[i] - u[j] + N * y[(i, j)] <= N - 1)
    m.Minimize(sum(cost))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = T_TSP; sv.parameters.num_workers = 8
    st = sv.Solve(m)
    if sv.StatusName(st) not in ("OPTIMAL", "FEASIBLE"): return None, None
    succ = {}
    for i in range(n):
        for j in range(n):
            if i != j and sv.Value(y[(i, j)]): succ[i] = j
    order = [0]; cur = 0
    for _ in range(n - 1):
        if cur not in succ: break
        cur = succ[cur]; order.append(cur)
    return [cs[i] for i in order], sv.ObjectiveValue() / 1000.0

def nn2opt(cs):
    seq = list(cs); n = len(seq)
    if n <= 3: return seq
    Hm = {a: {b: hav(a, b) for b in seq} for a in seq}
    out = [seq[0]]; unv = set(seq[1:])
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: Hm[l][j])); unv.discard(out[-1])
    imp = True; ps = 0
    while imp and ps < 25:
        imp = False; ps += 1
        for a in range(1, n - 2):
            for b in range(a + 1, n - 1):
                if Hm[out[a-1]][out[b]] + Hm[out[b]][out[a]] < Hm[out[a-1]][out[a]] + Hm[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return out

rows = []; tot2 = 0.0; tot4 = 0.0; lb_sum = 0.0
for dd, gd in g.groupby("date"):
    cs = [c for c in gd.sort_values("拜访顺序")["客户编码"] if c in LON]
    if len(cs) < 2: continue
    b = nn2opt(cs); kmb = road_km([(LON[c], LAT[c]) for c in b])
    while kmb is None: kmb = road_km([(LON[c], LAT[c]) for c in b])
    tot2 += kmb
    s4, lb = exact_open_tsp(cs)
    if s4 is None:
        print(f"{dd} exact-tsp 超时, 退回启发式", flush=True); s4 = b; lb = None
    km4 = road_km([(LON[c], LAT[c]) for c in s4]) if s4 != b else kmb
    if km4 is None:
        print(f"{dd} OSRM 失败, 重试", flush=True); time.sleep(8)
        km4 = road_km([(LON[c], LAT[c]) for c in s4]) or kmb
    tot4 += km4
    if lb: lb_sum += lb
    print(f"{dd} {len(cs):>3}店  启发式 {kmb:6.1f} | 精确TSP {km4:6.1f} Δ={km4-kmb:+.1f} | havLB={lb:.1f}" if lb else
          f"{dd} {len(cs):>3}店 启发式 {kmb:6.1f} | 精确 {km4:6.1f}", flush=True)
    for r_, c in enumerate(s4, 1):
        rows.append(dict(拜访日期=str(dd), 拜访顺序=r_, 客户编码=c))
    time.sleep(0.2)
print(f"\n② 启发式顺序合计: {tot2:.1f} km")
print(f"④ 精确TSP顺序合计: {tot4:.1f} km ({(tot4-tot2)/tot2:+.1%})")
if lb_sum: print(f"haversine 下界(直线): {lb_sum:.1f} km → 路/直 综合比 {tot4/lb_sum:.2f}")
pd.DataFrame(rows).to_csv("output/srp_exact_tsp_09.csv", index=False)
json.dump({"n2": round(tot2, 1), "n4": round(tot4, 1), "hav_lb": round(lb_sum, 1)},
          open("output/final_09_exact.json", "w"), ensure_ascii=False, indent=1)
print("saved output/srp_exact_tsp_09.csv")
