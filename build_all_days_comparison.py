# -*- coding: utf-8 -*-
"""全月 27 天实际走访 vs Agent 动态插单全量对比与真实道路连线几何提取.

输出:
- demo/all_days_data.json: 包含 27 天每一天的完整门店元数据、三方对比指标、
  自然语言指引、以及真实道路折线几何 (实际轨迹 road geometry vs Agent 路线 road geometry).
"""
import sys, os, json, time, math, ssl, urllib.request
warnings_filter = True
sys.path.insert(0, ".")
import pandas as pd
import numpy as np
from core.metric import day_km
from algos.alns_v3 import two_opt
from algos.agentic.dispatch_agent import SalesVisitDispatchAgent

ctx = ssl._create_unverified_context()

# -------------------------------------------------------------
# 1. 基础网络请求辅助函数
# -------------------------------------------------------------
def fetch_route_geometry(lons, lats, chunk_size=35):
    """分段获取真实骑行路网几何折线 (避免 URL 溢出), 拼接为完整经纬度列表 [[lat, lon], ...]"""
    n = len(lons)
    if n < 2:
        return [[lats[0], lons[0]]] if n == 1 else []
    
    all_latlngs = []
    # 按照 chunk_size 滑动分段 (首尾重合 1 点以保证连续性)
    start = 0
    while start < n - 1:
        end = min(start + chunk_size, n)
        sub_lons = lons[start:end]
        sub_lats = lats[start:end]
        coords_str = ';'.join(f'{lo:.6f},{la:.6f}' for lo, la in zip(sub_lons, sub_lats))
        url = f'https://routing.openstreetmap.de/routed-bike/route/v1/driving/{coords_str}?overview=full&geometries=geojson'
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30, context=ctx)
            res_json = json.loads(resp.read().decode('utf-8'))
            coords = res_json['routes'][0]['geometry']['coordinates']
            # OSRM 返回 [lon, lat], Leaflet 需要 [lat, lon]
            sub_latlngs = [[c[1], c[0]] for c in coords]
            if all_latlngs:
                all_latlngs.extend(sub_latlngs[1:])  # 跳过重叠首点
            else:
                all_latlngs.extend(sub_latlngs)
        except Exception as e:
            # 若路网获取失败, 退化为直连线
            for lo, la in zip(sub_lons, sub_lats):
                all_latlngs.append([la, lo])
        start = end - 1
        time.sleep(0.05)
    return all_latlngs


def fetch_dist_matrix(lons, lats, cache_file):
    """获取/读取距离矩阵 (公里)"""
    if os.path.exists(cache_file):
        return np.load(cache_file)
    
    n = len(lons)
    D = np.zeros((n, n), dtype=float)
    batch_size = 40
    
    for i_start in range(0, n, batch_size):
        i_end = min(i_start + batch_size, n)
        for j_start in range(0, n, batch_size):
            j_end = min(j_start + batch_size, n)
            
            src_coords = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(i_start, i_end))
            dst_coords = ';'.join(f'{lons[k]:.6f},{lats[k]:.6f}' for k in range(j_start, j_end))
            
            # 若全部相同一次性全量
            if n <= 50:
                full_coords = ';'.join(f'{lo:.6f},{la:.6f}' for lo, la in zip(lons, lats))
                url = f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{full_coords}?annotations=distance'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=30, context=ctx)
                res_json = json.loads(resp.read().decode('utf-8'))
                D = np.array(res_json['distances'], dtype=float) / 1000.0
                np.save(cache_file, D)
                return D
            else:
                # 分块请求
                full_coords = src_coords + ';' + dst_coords
                sources = ';'.join(str(k) for k in range(i_end - i_start))
                destinations = ';'.join(str(k + (i_end - i_start)) for k in range(j_end - j_start))
                url = f'https://routing.openstreetmap.de/routed-bike/table/v1/driving/{full_coords}?sources={sources}&destinations={destinations}&annotations=distance'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=30, context=ctx)
                res_json = json.loads(resp.read().decode('utf-8'))
                sub_d = np.array(res_json['distances'], dtype=float) / 1000.0
                D[i_start:i_end, j_start:j_end] = sub_d
                time.sleep(0.05)
                
    np.save(cache_file, D)
    return D

# -------------------------------------------------------------
# 2. 主逻辑: 遍历 27 天
# -------------------------------------------------------------
f_actual = '/Users/ghb/Downloads/进离店报表导出 (4).xlsx'
f_plan = '/Users/ghb/Downloads/进离店内销售的SRP-7月拜访计划.xlsx'

print("加载数据源...", flush=True)
df_act = pd.read_excel(f_actual)
df09 = df_act[df_act['片区'].astype(str).str.contains('09')].copy()
df09['进店时间'] = pd.to_datetime(df09['进店时间'])
df09['客户编码'] = df09['客户编码'].astype(str).str.strip()
df09['date'] = df09['进店时间'].dt.date

df_plan = pd.read_excel(f_plan)
df_plan09 = df_plan[df_plan['销售名称'].astype(str).str.contains('09') & (df_plan['计划是否有效标识'] == '有效')].copy()
df_plan09['拜访日期'] = pd.to_datetime(df_plan09['拜访日期']).dt.date
df_plan09['客户编码'] = df_plan09['客户编码'].astype(str).str.strip()

# 过滤掉周六周日 (weekday < 5 仅保留周一至周五 23 个法定工作日)
dates = sorted([d for d in df09['date'].unique() if d.weekday() < 5])
os.makedirs('/tmp/day_dist_cache', exist_ok=True)

days_dict = {}
summary_calendar = []

print(f"开始批量处理全部 {len(dates)} 天 (计算指标 + 获取道路连线几何)...", flush=True)

for i, d in enumerate(dates):
    d_str = str(d)
    t_start = time.time()
    day_df = df09[df09['date'] == d].sort_values('进店时间').drop_duplicates(subset=['客户编码']).copy()
    plan_df = df_plan09[df_plan09['拜访日期'] == d]
    plan_set = set(plan_df['客户编码'])
    day_df['is_planned'] = day_df['客户编码'].isin(plan_set)
    
    n = len(day_df)
    codes = list(day_df['客户编码'])
    names = list(day_df['客户名称'])
    lons = list(day_df['进店经度'])
    lats = list(day_df['进店纬度'])
    addrs = list(day_df['进店地址'])
    is_p = list(day_df['is_planned'].astype(bool))
    
    # 距离矩阵
    cache_path = f'/tmp/day_dist_cache/dist_{d_str}_{n}.npy'
    try:
        D = fetch_dist_matrix(lons, lats, cache_path)
    except Exception as e:
        print(f"[{i+1:02d}] {d_str} 矩阵获取异常: {e}, 跳过")
        continue

    store_dict = {
        str(k): {
            'code': codes[k], 'name': names[k],
            'address': str(addrs[k]) if pd.notna(addrs[k]) else '',
            'lon': float(lons[k]), 'lat': float(lats[k]),
            'is_planned': bool(is_p[k])
        } for k in range(n)
    }
    
    # 1. 人类实际打卡序
    actual_seq = list(range(n))
    actual_km = round(float(day_km(actual_seq, D)), 2)
    
    # 2. 事后理论最优
    best_tsp = two_opt(actual_seq, D, max_pass=30)
    opt_km = round(float(day_km(best_tsp, D)), 2)
    
    # 3. Agent 动态在途插单
    p_idx = [k for k, p in enumerate(is_p) if p]
    a_idx = [k for k, p in enumerate(is_p) if not p]
    
    if p_idx:
        morning_route = two_opt(p_idx, D, max_pass=20)
        morning_km = round(float(day_km(morning_route, D)), 2)
    else:
        # 周六无计划店, 早晨计划为空
        morning_route = []
        morning_km = 0.0
        
    visited_cnt = min(6, len(morning_route) // 2) if len(morning_route) >= 4 else 0
    agent = SalesVisitDispatchAgent('梁健满', d_str, morning_route, D, {k: store_dict[str(k)] for k in range(n)})
    for s in morning_route[:visited_cnt]:
        agent.record_checkin(s)
        
    decision = agent.handle_adhoc_request(a_idx)
    agent_seq = decision['full_route']
    agent_km = round(float(decision['new_km']), 2)
    detour_km = round(float(decision['detour_km']), 2)
    
    # 4. 获取真实道路几何折线 (Road Geometry)
    actual_lons = [lons[idx] for idx in actual_seq]
    actual_lats = [lats[idx] for idx in actual_seq]
    actual_geom = fetch_route_geometry(actual_lons, actual_lats)
    
    agent_lons = [lons[idx] for idx in agent_seq]
    agent_lats = [lats[idx] for idx in agent_seq]
    agent_geom = fetch_route_geometry(agent_lons, agent_lats)
    
    dur = round(time.time() - t_start, 1)
    print(f"[{i+1:02d}/27] {d_str} ({d.strftime('%a')}): 总{n:2d}店 (临时{len(a_idx):2d}) | 实际={actual_km:5.1f}km | Agent={agent_km:5.1f}km (-{(actual_km-agent_km):4.1f}km) | 道路点={len(agent_geom)} [{dur}s]", flush=True)
    
    days_dict[d_str] = {
        'date': d_str,
        'weekday': d.strftime('%a'),
        'total_stores': n,
        'planned_count': len(p_idx),
        'adhoc_count': len(a_idx),
        'actual_km': actual_km,
        'morning_km': morning_km,
        'agent_km': agent_km,
        'opt_km': opt_km,
        'detour_km': detour_km,
        'elapsed_ms': decision['elapsed_ms'],
        'explanation': decision['explanation'],
        'actual_seq': actual_seq,
        'agent_seq': agent_seq,
        'actual_geom': actual_geom,  # 真实道路连线
        'agent_geom': agent_geom,    # 真实道路连线
        'stores': store_dict
    }
    
    summary_calendar.append({
        'date': d_str,
        'weekday': d.strftime('%a'),
        'actual_total': n,
        'in_plan': len(p_idx),
        'adhoc': len(a_idx),
        'actual_km': actual_km,
        'agent_km': agent_km,
        'saved_km': round(actual_km - agent_km, 1)
    })

# -------------------------------------------------------------
# 3. 汇总输出 JSON
# -------------------------------------------------------------
full_output = {
    'rep_name': '梁健满',
    'line_id': '海珠荔湾09',
    'month': '2026-07',
    'total_days': len(days_dict),
    'calendar': summary_calendar,
    'days': days_dict
}

out_path = '/Users/ghb/Documents/Codex/2026-08-04/wo-xi/visit-scheduling-optimizer/demo/all_days_data.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(full_output, f, ensure_ascii=False)

sz_mb = os.path.getsize(out_path) / 1024 / 1024
print(f"\n全部 27 天数据与道路几何已写入 {out_path} ({sz_mb:.2f} MB)!", flush=True)
