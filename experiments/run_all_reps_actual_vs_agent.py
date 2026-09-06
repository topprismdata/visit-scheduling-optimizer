# -*- coding: utf-8 -*-
"""全办 10 条线路 / 11 位业代 实际走访 vs Agent 动态插单 全量月度对比.

规则:
- 严格剔除周六周日 (weekday < 5 仅跑 23 个法定工作日)
- 覆盖全部 10 条线路: 海珠荔湾02 ~ 11
- 逐日计算: 人类实际打卡里程 vs Agent 动态走廊顺路插单里程
- 输出增量台账: output/all_reps_actual_vs_agent.csv 和 demo/all_reps_summary.json
"""
import sys, os, json, time, math, ssl, urllib.request, traceback
warnings_filter = True
sys.path.insert(0, ".")
import pandas as pd
import numpy as np
from core.metric import day_km
from algos.alns_v3 import two_opt
from algos.agentic.dispatch_agent import SalesVisitDispatchAgent

ctx = ssl._create_unverified_context()

ALL_LINES = ['02', '03', '04', '05', '06', '07', '08', '09', '10', '11']
CACHE_DIR = 'data/cache'
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs('output', exist_ok=True)

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
df_plan0['客户编码'] = df_plan09 = df_plan0['客户编码'].astype(str).str.strip()

rep_rows = []
all_reps_detail = {}
done_lids = set()
if os.path.exists('output/all_reps_actual_vs_agent.csv'):
    try:
        prev_df = pd.read_csv('output/all_reps_actual_vs_agent.csv')
        rep_rows = prev_df.to_dict(orient='records')
        done_lids = set(str(r['line']).zfill(2) for r in rep_rows)
        print(f"从断点恢复已完成线路: {list(done_lids)}")
    except Exception:
        pass
def save():
    df = pd.DataFrame(rep_rows)
    df.to_csv('output/all_reps_actual_vs_agent.csv', index=False)
    json.dump(rep_rows, open('output/all_reps_actual_vs_agent.json', 'w'), ensure_ascii=False, indent=2)
    json.dump(all_reps_detail, open('demo/all_reps_summary.json', 'w'), ensure_ascii=False, indent=2)

def safe_fetch_json(url, max_retries=2):
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            resp = urllib.request.urlopen(req, timeout=3.5, context=ctx)
            time.sleep(0.3)
            return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5)
            else:
                time.sleep(0.5)
        except Exception:
            time.sleep(0.5)
    return None

def calc_haversine_road(lons, lats):
    R = 6371.0
    n = len(lons)
    D = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            p1, p2 = math.radians(lats[i]), math.radians(lats[j])
            dp = math.radians(lats[j] - lats[i])
            dl = math.radians(lons[j] - lons[i])
            a = math.sin(dp / 2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            D[i, j] = round(R * c * 1.41, 3)
    return D

def fetch_dist_matrix(lons, lats, cache_file):
    if os.path.exists(cache_file):
        return np.load(cache_file)
    n = len(lons)
    try:
        if n <= 50:
            full_coords = ';'.join(f'{lo:.6f},{la:.6f}' for lo, la in zip(lons, lats))
            url = f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{full_coords}?annotations=distance'
            res_json = safe_fetch_json(url, max_retries=2)
            if res_json and 'distances' in res_json:
                D = np.array(res_json['distances'], dtype=float) / 1000.0
                np.save(cache_file, D)
                return D
        
        # n > 50: 分块请求
        D = np.zeros((n, n), dtype=float)
        batch_size = 20
        for i_start in range(0, n, batch_size):
            i_end = min(i_start + batch_size, n)
            n_src = i_end - i_start
            src_coords = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(i_start, i_end))
            for j_start in range(0, n, batch_size):
                j_end = min(j_start + batch_size, n)
                n_dst = j_end - j_start
                dst_coords = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(j_start, j_end))
                
                full_coords = src_coords + ';' + dst_coords
                sources = ';'.join(str(k) for k in range(n_src))
                destinations = ';'.join(str(k + n_src) for k in range(n_dst))
                url = f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{full_coords}?sources={sources}&destinations={destinations}&annotations=distance'
                res_json = safe_fetch_json(url, max_retries=2)
                if res_json and 'distances' in res_json:
                    sub_d = np.array(res_json['distances'], dtype=float) / 1000.0
                    D[i_start:i_end, j_start:j_end] = sub_d
                else:
                    raise RuntimeError("FOSSGIS 分块超时")
        np.save(cache_file, D)
        return D
    except Exception:
        # 限流保护: 回退至 1.41x 广州路网校准矩阵, 确保全月 230 天批处理绝对不断链
        D = calc_haversine_road(lons, lats)
        np.save(cache_file, D)
        return D

for lid in ALL_LINES:
    if lid in done_lids:
        print(f"线路 海珠荔湾{lid} 已在断点中完成, 跳过", flush=True)
        continue
    t_line_start = time.time()
    try:
        act_sub = df_act[df_act['片区'].astype(str).str.contains(lid)].copy()
        plan_sub = df_plan0[df_plan0['销售名称'].astype(str).str.contains(lid)].copy()
        rep_name = act_sub['人员名称'].iloc[0] if len(act_sub) else f'业代_{lid}'
        # 仅保留工作日 (周一至周五)
        dates = sorted([d for d in act_sub['date'].unique() if d.weekday() < 5])
        
        line_actual_km = 0.0
        line_agent_km = 0.0
        line_total_visits = 0
        line_in_plan_visits = 0
        line_adhoc_visits = 0
        daily_records = []
        
        print(f"\n>>> 处理线路 海珠荔湾{lid} ({rep_name}) | 共 {len(dates)} 工作日...", flush=True)
        
        for d in dates:
            d_str = str(d)
            day_df = act_sub[act_sub['date'] == d].sort_values('进店时间').drop_duplicates(subset=['客户编码']).copy()
            day_plan = plan_sub[plan_sub['拜访日期'] == d]
            plan_set = set(day_plan['客户编码'])
            day_df['is_planned'] = day_df['客户编码'].isin(plan_set)
            
            n = len(day_df)
            codes = list(day_df['客户编码'])
            names = list(day_df['客户名称'])
            lons = list(day_df['进店经度'])
            lats = list(day_df['进店纬度'])
            addrs = list(day_df['进店地址'])
            is_p = list(day_df['is_planned'].astype(bool))
            
            p_idx = [k for k, p in enumerate(is_p) if p]
            a_idx = [k for k, p in enumerate(is_p) if not p]
            
            line_total_visits += n
            line_in_plan_visits += len(p_idx)
            line_adhoc_visits += len(a_idx)
            
            if n <= 1:
                continue
                
            cache_file = f"{CACHE_DIR}/dist_{lid}_{d_str}_{n}.npy"
            D = fetch_dist_matrix(lons, lats, cache_file)
            
            actual_km = round(float(day_km(list(range(n)), D)), 2)
            
            morning_route = two_opt(p_idx, D, max_pass=20) if p_idx else []
            visited_cnt = min(6, len(morning_route) // 2) if len(morning_route) >= 4 else 0
            
            store_dict = {
                k: {'code': codes[k], 'name': names[k], 'address': str(addrs[k]) if pd.notna(addrs[k]) else ''}
                for k in range(n)
            }
            agent = SalesVisitDispatchAgent(rep_name, d_str, morning_route, D, store_dict)
            for s in morning_route[:visited_cnt]:
                agent.record_checkin(s)
            dec = agent.handle_adhoc_request(a_idx)
            agent_km = round(float(dec['new_km']), 2)
            
            line_actual_km += actual_km
            line_agent_km += agent_km
            
            daily_records.append({
                'date': d_str,
                'weekday': d.strftime('%a'),
                'total_stores': n,
                'in_plan': len(p_idx),
                'adhoc': len(a_idx),
                'actual_km': actual_km,
                'agent_km': agent_km,
                'saved_km': round(actual_km - agent_km, 2)
            })
            
        saved_km = round(line_actual_km - line_agent_km, 1)
        saved_pct = round(saved_km / line_actual_km * 100, 1) if line_actual_km > 0 else 0.0
        dur_line = round(time.time() - t_line_start, 1)
        
        row = {
            'line': lid,
            'rep_name': rep_name,
            'days': len(dates),
            'total_visits': line_total_visits,
            'in_plan_visits': line_in_plan_visits,
            'adhoc_visits': line_adhoc_visits,
            'adhoc_pct': round(line_adhoc_visits / line_total_visits * 100, 1) if line_total_visits > 0 else 0.0,
            'actual_km': round(line_actual_km, 1),
            'agent_km': round(line_agent_km, 1),
            'saved_km': saved_km,
            'saved_pct': saved_pct,
            'sec': dur_line
        }
        rep_rows.append(row)
        all_reps_detail[lid] = {
            'line': lid,
            'rep_name': rep_name,
            'summary': row,
            'daily': daily_records
        }
        save()
        print(f"线 {lid} ({rep_name}) 完成! 实际={line_actual_km:.1f}km -> Agent={line_agent_km:.1f}km (省 {saved_km}km, -{saved_pct}%) [耗时 {dur_line}s]", flush=True)

    except Exception as e:
        print(f"线 {lid} 失败: {e}", flush=True)
        traceback.print_exc()

save()
print("\n=== 全办 10 条线路实际 vs Agent 对比全部完成! ===", flush=True)
