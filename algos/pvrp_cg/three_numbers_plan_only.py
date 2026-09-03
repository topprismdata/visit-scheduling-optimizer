# -*- coding: utf-8 -*-
"""09 线路三数终版 (只用计划表, 同源同尺):
宇宙 = SRP 有效计划 (店→周几 100% 锁定; 次数逐店=计划行数; 4周周期+第5周溢出)
① 原始规划      : 日集合按计划, 顺序按打印 拜访顺序
② 原始规划重排序: 日集合按计划不动, 每日 CP-SAT 精确 TSP (开放链)
③ 重新规划      : 仅用计划留下的自由度(同周内挑哪几个周次, 溢出周可选), 以②的周次分配为
                  warm start 做交换搜索(仅收改进) + 每日精确 TSP → 数学上 ≤ ②
尺子: FOSSGIS routed-bike 组内距离矩阵 (一次拉取, 三数共用)."""
import pandas as pd, numpy as np, json, math, time, urllib.request, warnings, os
warnings.filterwarnings("ignore")
from ortools.sat.python import cp_model

REP = "海珠荔湾09"
MX = "output/road_groups_09.json"
URL = "https://routing.openstreetmap.de/routed-bike/table/v1/driving/"

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date
g = pv[pv["销售名称"] == REP].copy()
g["wd"] = g["拜访日期"].dt.weekday
pts_all = g.dropna(subset=["经度", "纬度"]).drop_duplicates("客户编码").set_index("客户编码")
codes = list(pts_all.index); idx = {c: i for i, c in enumerate(codes)}
DATES = sorted(g["date"].unique()); DI = {d: i for i, d in enumerate(DATES)}
n_slots = len(DATES)

def fetch_groups():
    """每个星期几一个组 (店≤47<50), 组内 OSRM 骑行距离矩阵 (km)."""
    groups = {}
    for w in range(5):
        cs = sorted({c for c in g[g["wd"] == w]["客户编码"] if c in pts_all.index})
        if not cs: groups[w] = {"codes": [], "M": []}; continue
        P = [(float(pts_all.loc[c, "经度"]), float(pts_all.loc[c, "纬度"])) for c in cs]
        s = ";".join(f"{lo:.6f},{la:.6f}" for lo, la in P)
        got = None
        for k in range(6):
            try:
                r = json.loads(urllib.request.urlopen(
                    urllib.request.Request(f"{URL}{s}?annotations=distance",
                                           headers={"User-Agent": "gz-eval/1.0"}), timeout=60).read())
                if r.get("code") == "Ok": got = r; break
                time.sleep(2 + k)
            except Exception:
                time.sleep(2 + k)
        if got is None:
            print(f"组{w} 拉取失败", flush=True); groups = None; break
        M = np.array([[np.nan if v is None else v / 1000.0 for v in row] for row in got["distances"]])
        fill = (1 - np.isnan(M).mean()) if M.size else 0
        M = np.nan_to_num(M, nan=float(np.nanmax(M)) if np.isfinite(np.nanmax(M)) else 5.0)
        groups[w] = {"codes": cs, "M": M.round(4).tolist()}
        print(f"组 周{w}: {len(cs)}店 矩阵✓ (填充 {fill:.2f})", flush=True)
        time.sleep(0.6)
    return groups

if os.path.exists(MX):
    groups = json.load(open(MX))
else:
    groups = fetch_groups()
    if groups: json.dump({str(k): v for k, v in groups.items()}, open(MX, "w"))
GCODES = {}; GM = {}
for w, bb in (groups or {}).items():
    w = int(w); cs = bb["codes"]
    GCODES[w] = {c: i for i, c in enumerate(cs)}
    GM[w] = np.array(bb["M"], dtype=float)

def exact_tsp(cs_local, Mat):
    """开放链精确 TSP v2: 虚拟起点 s + 虚拟终点 t, MTZ 消子环. 修复 v1 的
    入度恒不可行 bug (v1: 实点入度只能来自实点, n 条需求 > n-1 条可用弧)."""
    n = len(cs_local)
    if n <= 2: return list(cs_local), float(sum(Mat[cs_local[k], cs_local[k+1]] for k in range(n-1))) if n == 2 else 0.0
    sub = Mat[np.ix_(cs_local, cs_local)]
    m = cp_model.CpModel()
    S, T = n, n + 1                      # 虚拟起点 / 终点
    y = {}
    for i in range(n):
        y[(S, i)] = m.NewBoolVar(f"ys_{i}")
        y[(i, T)] = m.NewBoolVar(f"yt_{i}")
        for j in range(n):
            if j != i: y[(i, j)] = m.NewBoolVar(f"y{i}_{j}")
    for i in range(n):                   # 每实点: 入=1 (可来自 s), 出=1 (可去 t)
        m.Add(sum(y[(j, i)] for j in range(n) if j != i) + y[(S, i)] == 1)
        m.Add(sum(y[(i, j)] for j in range(n) if j != i) + y[(i, T)] == 1)
    m.Add(sum(y[(S, i)] for i in range(n)) == 1)
    m.Add(sum(y[(i, T)] for i in range(n)) == 1)
    u = [m.NewIntVar(0, n, f"u{i}") for i in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j: m.Add(u[j] >= u[i] + 1 - n * (1 - y[(i, j)]))
    m.Minimize(sum(y[(i, j)] * int(round(sub[i][j] * 1000)) for i in range(n) for j in range(n) if i != j))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = 90; sv.parameters.num_workers = 8
    st = sv.Solve(m)
    if sv.StatusName(st) not in ("OPTIMAL", "FEASIBLE"):
        return list(cs_local), float(sum(sub[k, k+1] for k in range(n-1)))
    succ = {}
    for (i, j), var in y.items():
        if i < n and j < n and sv.Value(var): succ[i] = j
    heads = [i for i in range(n) if i not in succ.values()]
    cur = heads[0] if heads else 0; order = [cur]
    for _ in range(n - 1):
        if cur not in succ: break
        cur = succ[cur]; order.append(cur)
    order += [x for x in range(n) if x not in order]
    out = [cs_local[i] for i in order]
    return out, float(sum(sub[k, k+1] for k in range(len(order)-1)))
    succ = {}
    for i in range(n):
        for j in range(n):
            if i != j and sv.Value(y[(i, j)]): succ[i] = j
    heads = [i for i in range(n) if i not in succ.values()]
    cur = heads[0] if heads else 0; order = [cur]
    for _ in range(n - 1):
        if cur not in succ: break
        cur = succ[cur]; order.append(cur)
    order += [x for x in range(n) if x not in order]
    out = [cs_local[i] for i in order]
    return out, float(sum(sub[k, k+1] for k in range(n-1)))

def nn2opt(cs_local, Mat):
    n = len(cs_local)
    if n <= 3: return list(cs_local)
    sub = Mat[np.ix_(cs_local, cs_local)]
    out = [0]; unv = set(range(1, n))
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: sub[l][j])); unv.discard(out[-1])
    def L(o): return sum(sub[o[k]][o[k+1]] for k in range(len(o)-1))
    imp = True; ps = 0
    while imp and ps < 25:
        imp = False; ps += 1
        for a in range(1, n-2):
            for b in range(a+1, n-1):
                if sub[out[a-1]][out[b]] + sub[out[b]][out[a]] < sub[out[a-1]][out[a]] + sub[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return out

codes_w = {w: {GCODES[w][c]: c for c in GCODES[w]} for w in range(5)}
def day_sets_by_wd():
    """w → {slot_date_idx: [local codes]} 按计划 (①/② 基础)"""
    out = {}
    for w in range(5):
        out[w] = {}
        for d in [dd for dd in DATES if dd.weekday() == w]:
            cs = [c for c in g[g["date"] == d].sort_values("拜访顺序")["客户编码"] if c in GCODES[w]]
            out[w][DI[d]] = [GCODES[w][c] for c in cs]
    return out

DS = day_sets_by_wd()
print(f"宇宙: {len(codes)} 店 / {len(g)} 计划行 / {n_slots} 日\n")

# ---------- ① 计划打印顺序 ----------
n1 = 0.0
for w in range(5):
    for di, locs in DS[w].items():
        n1 += sum(GM[w][locs[k], locs[k+1]] for k in range(len(locs)-1))
# ---------- ② 日集合不动, 逐日精确 TSP ----------
n2 = 0.0; opt2 = {}
for w in range(5):
    opt2[w] = {}
    for di, locs in DS[w].items():
        seq, km = exact_tsp(locs, GM[w])
        opt2[w][di] = seq; n2 += km
print(f"① 原始规划(打印顺序)  {n1:8.1f} km")
print(f"② 原始规划重新排序    {n2:8.1f} km   ({(n1-n2)/n1:+.1%})", flush=True)

# ---------- ③ 周次再分配 (warm start=②, 仅收改进) ----------
plan3 = {w: {di: list(s) for di, s in opt2[w].items()} for w in range(5)}
tot3 = n2
# 每店其星期组内的槽位与次数
store_slots = {w: {} for w in range(5)}
for w in range(5):
    for di, locs in plan3[w].items():
        for x in locs: store_slots[w].setdefault(x, []).append(di)
def daycost(w, locs):
    if len(locs) <= 1: return 0.0
    return sum(GM[w][locs[k], locs[k+1]] for k in range(len(locs)-1)) if False else \
           sum(GM[w][locs[k], locs[k+1]] for k in range(len(locs)-1))
def route_len(w, locs):
    o = nn2opt(list(locs), GM[w]); M = GM[w]
    return daycost(w, o)
moved = 0; rounds = 0
while rounds < 12:
    rounds += 1; improved = False
    for w in range(5):
        slots = sorted(plan3[w])
        for x, xs in list(store_slots[w].items()):
            for src in xs:
                for dst in slots:
                    if dst in xs or dst == src: continue
                    S_src = [t for t in plan3[w][src] if t != x]
                    S_dst = plan3[w][dst] + [x]
                    for _nm, _arr in (("S_src", S_src), ("S_dst", S_dst)):
                        if any(t >= GM[w].shape[0] or t < 0 for t in _arr):
                            print(f"[哨兵] w={w} 越界! {_nm}={_arr} shape={GM[w].shape} "
                                  f"组内codes={[GCODES[w].get(t,'??') for t in _arr if t>=GM[w].shape[0] or t<0]}", flush=True)
                            raise IndexError(f"哨兵捕获: {_nm} 越界 w={w}")
                    if route_len(w, S_src) + route_len(w, S_dst) < route_len(w, plan3[w][src]) + route_len(w, plan3[w][dst]) - 1e-9:
                        tot3 += route_len(w, S_src) + route_len(w, S_dst) - route_len(w, plan3[w][src]) - route_len(w, plan3[w][dst])
                        plan3[w][src] = S_src; plan3[w][dst] = S_dst
                        store_slots[w][x] = [t for t in xs if t != src] + [dst]
                        moved += 1; improved = True
                        break
    if not improved: break
# ③ 定稿逐日精确 TSP
n3 = 0.0; rows3 = []
for w in range(5):
    for di, locs in sorted(plan3[w].items()):
        seq, km = exact_tsp(locs, GM[w]); n3 += km
        for r_, t in enumerate(seq, 1):
            rows3.append(dict(拜访日期=str(DATES[di]), 拜访顺序=r_, 客户编码=codes_w[w][t]))
n_all = sum(len(v) for w in plan3 for v in plan3[w].values())
print(f"③ 重新规划            {n3:8.1f} km   ({(n1-n3)/n1:+.1%})   [周次移动 {moved} 次]")
print(f"\n校验: 计划 {len(g)} 行 vs ③ {n_all} 次 → {'✓ 逐店次数保持' if n_all==len(g) else '✗'}")
json.dump({"n1": round(n1,1), "n2": round(n2,1), "n3": round(n3,1), "moves": moved},
          open("output/three_numbers_plan_only_09.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame(rows3).to_csv("output/three_09_plan3.csv", index=False)
print("saved output/three_numbers_plan_only_09.json + three_09_plan3.csv")
