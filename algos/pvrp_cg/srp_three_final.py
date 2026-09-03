# -*- coding: utf-8 -*-
"""09区三数终版 (apple-to-apple):
宇宙 = SRP 有效计划 163 店 / 686 次, 星期锁定 (计划自带 100% 规则), 次数逐店 = 计划
尺   = OSM 骑行路网距离矩阵 (FOSSGIS, 一次抓取, ①②③ 共用)
① 原始规划距离     : 日集合按计划, 顺序按计划打印顺序
② 原始规划重新排序 : 日集合按计划不动, 每日顺序 NN+2-opt 最优化 (路网矩阵)
③ 重新规划         : ② 的日集合做同星期组内"店↔日"交换搜索 (次数/星期全锁), 仅收改进,
                     每日顺序再 2-opt 收尾 → 结构性 ≤ ②
最终 OSRM 骑行 route 服务复测 ②③ (抽查全月)."""
import sys, json, math, time, random, urllib.request
import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")

REP = sys.argv[1] if len(sys.argv) > 1 else "09"
ROOT = "/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer"
G = json.load(open(f"{ROOT}/output/road_groups_09.json"))
blocks = {int(k): v for k, v in G["blocks"].items()}
codes_all = G["codes"]

# ---------- 载入 SRP 计划 (09) ----------
plan = pd.read_excel("/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx")
pv = plan[plan["计划是否有效标识"] == "有效"].copy()
pv["客户编码"] = pv["客户编码"].astype(str)
pv["拜访日期"] = pd.to_datetime(pv["拜访日期"]); pv["date"] = pv["拜访日期"].dt.date
g = pv[pv["销售名称"] == f"海珠荔湾{REP}"].sort_values("拜访顺序")

# 每个星期组的本地索引: 全局 code → (组号, 组内序)
loc_of = {}
for w, b in blocks.items():
    for k, c in enumerate(b["codes"]):
        loc_of[c] = (w, k)

def day_seq_from(df):
    out = []
    for c in df["客户编码"]:
        out.append(loc_of[c][1] if c in loc_of else None)
    return [k for k in out if k is not None]

def chain_len(w, seq):
    return 0.0 if len(seq) < 2 else float(sum(blocks[w]["M"][seq[k]][seq[k+1]] for k in range(len(seq)-1)))

def nn2opt(w, seq):
    seq = list(seq); n = len(seq)
    if n <= 3: return seq
    M = np.array(blocks[w]["M"])
    sub = M[np.ix_(seq, seq)]
    out = [0]; unv = set(range(1, n))
    while unv:
        l = out[-1]; out.append(min(unv, key=lambda j: sub[l][j])); unv.discard(out[-1])
    def L(o): return sum(sub[o[k]][o[k+1]] for k in range(len(o)-1))
    imp = True; ps = 0
    while imp and ps < 40:
        imp = False; ps += 1
        for a in range(1, n-2):
            for b in range(a+1, n-1):
                if sub[out[a-1]][out[b]] + sub[out[b]][out[a]] < sub[out[a-1]][out[a]] + sub[out[b]][out[b+1]] - 1e-9:
                    out[a:b+1] = out[a:b+1][::-1]; imp = True
    return [seq[i] for i in out]

# ---------- ① 计划原样 ----------
DATES = sorted(g["date"].unique())
day_cols = {}
for dd, gd in g.groupby("date"):
    di = DATES.index(dd)
    day_cols[di] = day_seq_from(gd)
n1 = sum(chain_len(w, day_cols[di]) for di, w in
         ((di, DATES[di].weekday()) for di in sorted(day_cols)))

# ---------- ② 计划重排序 ----------
w_of_day = {di: DATES[di].weekday() for di in day_cols}
day_cols2 = {}
for di, s in day_cols.items():
    day_cols2[di] = nn2opt(w_of_day[di], s)
n2 = sum(chain_len(w_of_day[di], day_cols2[di]) for di in day_cols)

print(f"① 原始规划(计划顺序): {n1:8.1f} km")
print(f"② 原始规划重新排序:   {n2:8.1f} km  ({(n1-n2)/n1:+.1%})", flush=True)

# ---------- ③ 换日交换搜索 (同星期组内, 次数/星期锁死, 仅收改进) ----------
import copy
cur = {di: list(day_cols2[di]) for di in day_cols}
load = {di: len(cur[di]) for di in cur}
dates_by_wd = {}
for di in cur: dates_by_wd.setdefault(w_of_day[di], []).append(di)

def try_swap(di, dj):
    """在同星期两组间找最优 1-1 交换 (保每店次数: 每店在组内只有一份)."""
    best = None
    Si, Sj = cur[di], cur[dj]
    for a_i, a in enumerate(Si):
        for b_i, b in enumerate(Sj):
            ni = Si[:a_i] + [b] + Si[a_i+1:]
            nj = Sj[:b_i] + [a] + Sj[b_i+1:]
            d = chain_len(w_of_day[di], ni) + chain_len(w_of_day[dj], nj) \
                - chain_len(w_of_day[di], Si) - chain_len(w_of_day[dj], Sj)
            if best is None or d < best[0]:
                best = (d, ni, nj, a, b)
    return best

moves = 0
for rounds in range(15):
    improved = False
    for w, dlist in sorted(dates_by_wd.items()):
        if len(dlist) < 2: continue
        for x in range(len(dlist)):
            for y in range(x+1, len(dlist)):
                di, dj = dlist[x], dlist[y]
                r = try_swap(di, dj)
                if r and r[0] < -1e-6:
                    _, cur[di], cur[dj], _, _ = r
                    improved = True; moves += 1
    # 收尾 2-opt
    for di in cur:
        cur[di] = nn2opt(w_of_day[di], cur[di])
    n3 = sum(chain_len(w_of_day[di], cur[di]) for di in cur)
    print(f"  轮 {rounds}: {n3:.1f} km", flush=True)
    if not improved: break

n3 = sum(chain_len(w_of_day[di], cur[di]) for di in cur)
print(f"\n== 三数 (骑行路网矩阵, apple-to-apple) ==")
print(f"① 原始规划距离     : {n1:8.1f} km")
print(f"② 原始规划重新排序 : {n2:8.1f} km  ({(n1-n2)/n1:+.1%})")
print(f"③ 重新规划         : {n3:8.1f} km  ({(n1-n3)/n1:+.1%})   ③ vs ② {(n3-n2)/max(n2,1):+.1%}")
json.dump({"n1": round(n1,1), "n2": round(n2,1), "n3": round(n3,1), "moves": moves},
          open(f"output/three_final_{REP}.json", "w"), ensure_ascii=False, indent=1)
# 落盘 ③ 计划
rows = []
for di, seq in sorted(cur.items()):
    for r_, c in enumerate(seq, 1):
        rows.append(dict(拜访日期=DATES[di].isoformat(), 拜访顺序=r_, 客户编码=codes_all[c]))
pd.DataFrame(rows).to_csv(f"output/three_final_{REP}.csv", index=False)
print("saved output/three_final_"+REP+".{json,csv}")
