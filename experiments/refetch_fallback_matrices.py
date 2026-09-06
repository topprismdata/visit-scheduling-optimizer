# -*- coding: utf-8 -*-
"""重刷 Haversine 回退污染的日级路网矩阵 (2026-09-05).

Phase 1 (--phase refetch):
  逐 (线路, 工作日) 装配坐标 -> 检测缓存是否 == 1.41xHaversine 校准矩阵
  -> 命中则移入 data/cache/fallback_backup_<ts>/ 并从 FOSSGIS 耐心重抓
  -> 抓取失败不回退 (fail loud), 记入 pending, 可重复执行直至清零

Phase 2 (--phase ledger):
  纯 CPU, 零网络: 用干净矩阵重算全办台账
  -> output/all_reps_actual_vs_agent_road.csv + demo/all_reps_summary_road.json
  (验证 09 线应复现 ~1234.7 -> 592.2, 即干净基线一致性检查)
"""
import sys, os, json, time, math, ssl, shutil, urllib.request
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from core.metric import day_km
from algos.alns_v3 import two_opt
from algos.agentic.dispatch_agent import SalesVisitDispatchAgent

PHASE = sys.argv[sys.argv.index('--phase') + 1] if '--phase' in sys.argv else 'refetch'
BACKUP = f'data/cache/fallback_backup_20260905'
ALL_LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
CACHE_DIR = 'data/cache'
ctx = ssl._create_unverified_context()

f_act = '/Users/ghb/Downloads/进离店报表导出 (4).xlsx'
f_plan = '/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx'

print("加载数据源...", flush=True)
df_act = pd.read_excel(f_act)
df_plan = pd.read_excel(f_plan)
df_act['进店时间'] = pd.to_datetime(df_act['进店时间'])
df_act['客户编码'] = df_act['客户编码'].astype(str).str.strip()
df_act['date'] = df_act['进店时间'].dt.date
df_plan0 = df_plan[df_plan['计划是否有效标识'] == '有效'].copy()
df_plan0['拜访日期'] = pd.to_datetime(df_plan0['拜访日期']).dt.date
df_plan0['客户编码'] = df_plan0['客户编码'].astype(str).str.strip()

def day_rows(lid):
    """(date, n, lons, lats, cache_file) 列表, 与 run_all_reps 装配完全一致."""
    act_sub = df_act[df_act['片区'].astype(str).str.contains(lid)].copy()
    out = []
    for d in sorted([x for x in act_sub['date'].unique() if x.weekday() < 5]):
        day_df = act_sub[act_sub['date'] == d].sort_values('进店时间').drop_duplicates(subset=['客户编码'])
        n = len(day_df)
        if n <= 1:
            continue
        out.append((d, n, list(day_df['进店经度']), list(day_df['进店纬度']),
                    f"{CACHE_DIR}/dist_{lid}_{str(d)}_{n}.npy"))
    return out

def calc_haversine_road(lons, lats):
    R = 6371.0
    n = len(lons)
    D = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            p1, p2 = math.radians(lats[i]), math.radians(lats[j])
            dp = math.radians(lats[j] - lats[i]); dl = math.radians(lons[j] - lons[i])
            a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
            D[i, j] = round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)) * 1.41, 3)
    return D

def fetch(url, retries=8):
    """耐心抓取: 429 退避 12s, 其余 3s, 全失败抛异常 (禁止回退)."""
    for att in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            resp = urllib.request.urlopen(req, timeout=25, context=ctx)
            time.sleep(1.5)  # 礼貌限流
            return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    429, 退避 12s ({att+1}/{retries})", flush=True)
                time.sleep(12)
            else:
                time.sleep(3)
        except Exception:
            time.sleep(3)
    raise RuntimeError(f"抓取失败: {url[:80]}")

BATCH = 40
def fetch_matrix(lons, lats):
    n = len(lons)
    if n <= 50:
        coords = ';'.join(f'{lo:.6f},{la:.6f}' for lo, la in zip(lons, lats))
        r = fetch(f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{coords}?annotations=distance')
        return np.array(r['distances'], dtype=float) / 1000.0
    D = np.zeros((n, n), dtype=float)
    for i0 in range(0, n, BATCH):
        i1 = min(i0 + BATCH, n)
        src = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(i0, i1))
        for j0 in range(0, n, BATCH):
            j1 = min(j0 + BATCH, n)
            dst = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(j0, j1))
            url = (f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{src};{dst}'
                   f'?sources={";".join(str(k) for k in range(i1-i0))}'
                   f'&destinations={";".join(str(k) for k in range(j1-j0))}&annotations=distance')
            r = fetch(url)
            D[i0:i1, j0:j1] = np.array(r['distances'], dtype=float) / 1000.0
    return D

if PHASE == 'refetch':
    os.makedirs(BACKUP, exist_ok=True)
    stat = {'clean': 0, 'fallback': 0, 'refetched': 0, 'missing': 0, 'pending': 0}
    pending = []
    for lid in ALL_LINES:
        for d, n, lons, lats, cf in day_rows(lid):
            if not os.path.exists(cf):
                stat['missing'] += 1
                pending.append((lid, str(d), 'MISSING'))
                continue
            D = np.load(cf)
            H = calc_haversine_road(lons, lats)
            if float(np.abs(D - H).max()) < 0.5:
                stat['fallback'] += 1
                try:
                    newD = fetch_matrix(lons, lats)
                    if float(np.abs(newD - H).max()) < 0.5:
                        raise RuntimeError("新矩阵仍疑似回退, 拒绝写入")
                    shutil.move(cf, f"{BACKUP}/{os.path.basename(cf)}")
                    np.save(cf, newD)
                    stat['refetched'] += 1
                    print(f"  线{lid} {d} n={n}: 回退->实测 (maxΔ={float(np.abs(newD-H).max()):.1f}km)", flush=True)
                except Exception as e:
                    stat['pending'] += 1
                    pending.append((lid, str(d), str(e)[:60]))
                    print(f"  线{lid} {d} n={n}: 失败 {str(e)[:60]}", flush=True)
            else:
                stat['clean'] += 1
        print(f"线 {lid} 扫完: {stat}", flush=True)
    json.dump(pending, open('output/refetch_pending.json', 'w'), ensure_ascii=False, indent=1)
    print(f"\n=== Phase1 完成: {stat} | pending 详情 output/refetch_pending.json ===", flush=True)

elif PHASE == 'ledger':
    rep_rows, all_reps_detail = [], {}
    for lid in ALL_LINES:
        plan_sub = df_plan0[df_plan0['销售名称'].astype(str).str.contains(lid)].copy()
        act_sub = df_act[df_act['片区'].astype(str).str.contains(lid)].copy()
        rep_name = act_sub['人员名称'].iloc[0] if len(act_sub) else f'业代_{lid}'
        dates = sorted([x for x in act_sub['date'].unique() if x.weekday() < 5])
        la_km = ag_km = 0.0; tv = ip = ad = 0; daily = []
        for d in dates:
            day_df = act_sub[act_sub['date'] == d].sort_values('进店时间').drop_duplicates(subset=['客户编码']).copy()
            plan_set = set(plan_sub[plan_sub['拜访日期'] == d]['客户编码'])
            day_df['is_planned'] = day_df['客户编码'].isin(plan_set)
            n = len(day_df); tv += n
            ip += int(day_df['is_planned'].sum()); ad += n - int(day_df['is_planned'].sum())
            if n <= 1: continue
            D = np.load(f"{CACHE_DIR}/dist_{lid}_{str(d)}_{n}.npy")
            H = calc_haversine_road(list(day_df['进店经度']), list(day_df['进店纬度']))
            assert not np.array_equal(np.round(D, 3), H), f"线{lid} {d} 仍是回退矩阵!"
            actual_km = round(float(day_km(list(range(n)), D)), 2)
            p_idx = [k for k, p in enumerate(day_df['is_planned']) if p]
            a_idx = [k for k, p in enumerate(day_df['is_planned']) if not p]
            morning = two_opt(p_idx, D, max_pass=20) if p_idx else []
            vc = min(6, len(morning)//2) if len(morning) >= 4 else 0
            sdict = {k: {'code': c, 'name': nm, 'address': str(a) if pd.notna(a) else ''}
                     for k, (c, nm, a) in enumerate(zip(day_df['客户编码'], day_df['客户名称'], day_df['进店地址']))}
            agent = SalesVisitDispatchAgent(rep_name, str(d), morning, D, sdict)
            for s in morning[:vc]:
                agent.record_checkin(s)
            dec = agent.handle_adhoc_request(a_idx)
            day_ag = round(float(dec['new_km']), 2)
            ag_km += float(dec['new_km'])
            la_km += actual_km
            daily.append({'date': str(d), 'total_stores': n, 'in_plan': len(p_idx), 'adhoc': len(a_idx),
                          'actual_km': actual_km, 'agent_km': day_ag})
        saved = round(la_km - ag_km, 1)
        row = {'line': lid, 'rep_name': rep_name, 'days': len(dates), 'total_visits': tv,
               'in_plan_visits': ip, 'adhoc_visits': ad,
               'adhoc_pct': round(ad/tv*100, 1) if tv else 0.0,
               'actual_km': round(la_km, 1), 'agent_km': round(ag_km, 1),
               'saved_km': saved, 'saved_pct': round(saved/la_km*100, 1) if la_km else 0.0}
        rep_rows.append(row)
        all_reps_detail[lid] = {'summary': row, 'daily': daily}
        print(f"线 {lid} ({rep_name}): {row['actual_km']} -> {row['agent_km']} (-{row['saved_pct']}%)", flush=True)
    pd.DataFrame(rep_rows).to_csv('output/all_reps_actual_vs_agent_road.csv', index=False)
    json.dump(rep_rows, open('output/all_reps_actual_vs_agent_road.json', 'w'), ensure_ascii=False, indent=2)
    json.dump(all_reps_detail, open('demo/all_reps_summary_road.json', 'w'), ensure_ascii=False, indent=2)
    tot_a = round(sum(r['actual_km'] for r in rep_rows), 1); tot_g = round(sum(r['agent_km'] for r in rep_rows), 1)
    print(f"\n=== 全办(实测口径): {tot_a} -> {tot_g} (-{round((tot_a-tot_g)/tot_a*100,1)}%) ===", flush=True)
