# -*- coding: utf-8 -*-
"""09区 三数对比 (全部以 SRP 计划为基线与对手, 同一张 OSM 骑行路网矩阵):
① 计划原样   : 店→日 + 拜访顺序 全按 SRP
② 计划重排序 : 店→日按 SRP 不动, 每日顺序最优化 (精确TSP)
③ 重新规划   : 次数/星期按 SRP 锁定, 店→周内哪天 可重排, 每日顺序最优化
               (以②为起点, 只接受改进 → 数学上 ≤ ②)
口径: 开放链 (首店→末店), 无仓库绕行, 与拜访动线一致."""
import sys, json, math, time, random, itertools
import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer")
from ortools.sat.python import cp_model

REP = sys.argv[1] if len(sys.argv) > 1 else "09"
mx = json.load(open(f"output/road_matrix_{REP}.json"))
codes = mx["codes"]; idx = {c: i for i, c in enumerate(codes)}
Dm = np.array([[np.nan if v is None else v for v in row] for row in mx["D"]])
Dm[np.isnan(Dm)] = Dm.max() / 2  # 不可达兜底

plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date
g = pv[pv["销售名称"].str.contains("海珠荔湾" + REP)].sort_values("拜访顺序")
freq = g.groupby("客户编码").size()
wmode = g.groupby("客户编码")["拜访日期"].apply(lambda s: int(s.dt.weekday.value_counts().index[0]))
DATES = sorted(g["date"].unique())
DAYS = len(DATES)
wd_of = {dd: dd.weekday() for dd in DATES}
slots_by_wd = {}
for i, dd in enumerate(DATES): slots_by_wd.setdefault(wd_of[dd], []).append(i)

def chain(seq):
    return 0.0 if len(seq) < 2 else float(sum(Dm[seq[k], seq[k+1]] for k in range(len(seq)-1)))

def exact_tsp(cs):
    """开放链精确 TSP (起点自由=回路破最边). cs: list of matrix idx."""
    n = len(cs)
    if n <= 2: return list(cs), chain(cs)
    C = Dm[np.ix_(cs, cs)]
    m = cp_model.CpModel()
    N = n + 1
    y = {}
    for i in range(n):
        for j in range(N):
            if i != j: y[(i, j)] = m.NewBoolVar(f"y{i}_{j}")
    for i in range(n):
        m.Add(sum(y[(i, j)] for j in range(N) if j != i) == 1)
        m.Add(sum(y[(j, i)] for j in range(n) if j != i) == 1)
    m.Add(sum(y[(i, n)] for i in range(n)) == 1)
    u = [m.NewIntVar(0, n, f"u{i}") for i in range(n)]
    for i in range(1, n):
        for j in range(1, n):
            if i != j: m.Add(u[i] - u[j] + N * y[(i, j)] <= N - 1)
    cost = [y[(i, j)] * int(round(C[i][j] * 1000)) for i in range(n) for j in range(n) if i != j]
    for i in range(n): cost.append(y[(i, n)] * 0)
    m.Minimize(sum(cost))
    sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = 90; sv.parameters.num_workers = 8
    st = sv.Solve(m)
    if sv.StatusName(st) not in ("OPTIMAL", "FEASIBLE"): return list(cs), chain(cs)
    succ = {i: j for i in range(n) for j in range(n) if i != j and sv.Value(y[(i, j)])}
    start = min(succ, key=lambda i: C[[j for j in succ if succ[j] == i][0] if i in [v for v in succ.values()] else 0][0] if False else 0)
    srcs = [i for i in range(n) if i not in succ.values()]
    cur = srcs[0] if srcs else 0
    order = [cur]
    for _ in range(n - 1):
        if cur == n or cur not in succ: break
        cur = succ[cur]
        if cur == n: break
        order.append(cur)
    order = order + [x for x in range(n) if x not in order]
    out = [cs[i] for i in order]
    return out, chain(out)

# ---------- ① 计划原样 ----------
plan_days = {i: [] for i in range(DAYS)}
for dd, gd in g.groupby("date"):
    plan_days[DATES.index(dd)] = [idx[c] for c in gd.sort_values("拜访顺序")["客户编码"] if c in idx]
n1 = sum(chain(s) for s in plan_days.values())

# ---------- ② 计划重排序 (逐日精确 TSP) ----------
d2 = {}
tot2 = 0.0
for di, s in plan_days.items():
    seq, km = exact_tsp(s)
    d2[di] = seq; tot2 += km
print(f"① {n1:.1f} | ② {tot2:.1f}  (-{(n1-tot2)/n1*100:.1f}%)", flush=True)

# ---------- ③ 重新规划: 星期锁定+次数精确, 换日搜索(仅收改进) ----------
rng = random.Random(7)
cur_days = dict(d2)
tot3 = tot2
day_lists = {di: list(v) for di, v in d2.items()}
where = {}
for di, s in day_lists.items():
    for c in s: where.setdefault(c, []).append(di)
caps_lo = {di: max(1, len(day_lists[di]) - 6) for di in range(DAYS)}
changed = True; rounds = 0
while changed and rounds < 40:
    changed = False; rounds += 1
    for di in sorted(day_lists):
        for dj in sorted(day_lists):
            if di >= dj or wd_of[DATES[di]] != wd_of[DATES[dj]]: continue
            for a in list(day_lists[di]):
                for b in list(day_lists[dj]):
                    if a == b: continue
                    si = [x for x in day_lists[di] if x != a] + [b]
                    sj = [x for x in day_lists[dj] if x != b] + [a]
                    if len(si) < caps_lo[di] or len(sj) < caps_lo[dj]: continue
                    ci = chain(nn2opt(si)) if False else exact_or_greedy(si)
                    cj = exact_or_greedy(sj)
                    old = chain(day_lists[di]) + chain(day_lists[dj])
                    if ci + cj < old - 1e-6:
                        day_lists[di], day_lists[dj] = si, sj
                        where[a] = [d for d in where[a] if d != di] + [dj]
                        where[b] = [d for d in where[b] if d != dj] + [di]
                        tot3 -= (old - (ci + cj)); changed = True
print("(③ 交换搜索完成)" if rounds else "", flush=True)

def exact_or_greedy(seq):
    if len(seq) > 12:
        s, km = nn_greedy(seq); return km
    _, km = exact_tsp(seq); return km

def nn_greedy(cs):
    out = [cs[0]]; unv = set(cs[1:])
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: Dm[l][j])); unv.discard(out[-1])
    imp = True; ps = 0
    while imp and ps < 25:
        imp = False; ps += 1
        for a in range(1, len(out)-2):
            for b in range(a+1, len(out)-1):
                if Dm[out[a-1]][out[b]] + Dm[out[b]][out[a]] < Dm[out[a-1]][out[a]] + Dm[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return out, chain(out)

# ③ 重新逐日精确做序后定稿
tot3 = 0.0
rows = []
for di, s in day_lists.items():
    seq, km = (exact_tsp(s) if len(s) <= 40 else nn_greedy(s))
    tot3 += km
    for r_, c in enumerate(seq, 1):
        rows.append(dict(拜访日期=str(DATES[di]), 拜访顺序=r_, 客户编码=codes[c]))
cnt = pd.Series([c for s in day_lists.values() for c in s]).value_counts()
assert all(cnt.get(codes[i], 0) == int(freq[codes[i]]) for i in range(len(codes))), "③ 次数被破坏!"
print(f"③ 重新规划: {tot3:.1f} km (≤②={tot2:.1f}: {'✓' if tot3 <= tot2 + 1e-6 else '✗'})")
print(f"\n== 三数 (09区, 骑行路网矩阵, 同一把尺) ==")
print(f"① 原始规划距离     : {n1:8.1f} km")
print(f"② 原始规划重新排序 : {tot2:8.1f} km  ({(n1-tot2)/n1:+.1%})")
print(f"③ 重新规划         : {tot3:8.1f} km  ({(n1-tot3)/n1:+.1%})")
pd.DataFrame(rows).to_csv(f"output/three_{REP}_plan3.csv", index=False)
json.dump({"n1": round(n1,1), "n2": round(tot2,1), "n3": round(tot3,1)},
          open(f"output/three_numbers_{REP}.json", "w"), ensure_ascii=False, indent=1)
print("saved")
