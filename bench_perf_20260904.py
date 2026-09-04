# -*- coding: utf-8 -*-
"""性能实测 2026-09-04: 场景A 首次完整规划 / 场景B 基于v3微调 / 场景C 当天插单.
逐条 append 写 output/bench_20260904.csv (带时间戳, 可中断续看).
固定 seed 同时对比 seed 变化, 区分时间预算与实际结束时间.
"""
import sys, json, time, os, csv, platform, math, random
sys.path.insert(0, '.')
from data.loader import load_plan, load_line, ALL_LINE_IDS
from data.road import load_cached
from core.metric import day_km, total_km, check_freq
from algos.registry import get
import algos.impl, algos.sdr_exact, algos.alns_v3, algos.mo_alns_v4
from algos.mo_alns_v4 import MOALNSv4
from algos.tsp_engine import _exact_open_tsp
from algos.agentic.corridor_insertion import CorridorDynamicInsertionTool

OUT = 'output/bench_20260904.csv'
FIELDS = ['ts','scenario','algo','line','seed','budget_s','wall_s','km','changed',
          'freq_ok','iters','extra','machine']

def machine():
    try:
        ncpu = os.cpu_count()
        mem = subprocess_mem()
        return f"{platform.machine()}|py{platform.python_version()}|cpu{ncpu}|mem{mem}"
    except Exception:
        return platform.machine()

def subprocess_mem():
    try:
        import subprocess
        r = subprocess.run(['sysctl','-n','hw.memsize'], capture_output=True, text=True)
        return f"{int(r.stdout.strip())/2**30:.0f}GB"
    except Exception:
        return '?'

def log(rows, **kw):
    kw['ts'] = time.strftime('%Y-%m-%d %H:%M:%S')
    kw['machine'] = machine()
    if rows is not None: rows.append(kw)
    new = not os.path.exists(OUT)
    with open(OUT, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow({k: kw.get(k,'') for k in FIELDS})
    print(f"[{kw['scenario']}/{kw['algo']}/{kw['line']}] wall={kw['wall_s']}s "
          f"km={kw.get('km')} freq_ok={kw.get('freq_ok')} {kw.get('extra','')}", flush=True)

def run_algo(cls_name, data, D, budget, seed, scenario, line, extra='', **kw):
    algo = get(cls_name)()
    t0 = time.time()
    r = algo.solve(data, D, time_budget=budget, **kw)
    wall = time.time() - t0
    ok = check_freq(r.days, data.codes, data.freq)
    dm = {}
    log(None, scenario=scenario, algo=cls_name, line=line, seed=seed, budget_s=budget,
        wall_s=round(wall,2), km=round(r.km,1), changed=r.metadata.get('delta',''),
        freq_ok=ok, iters=r.metadata.get('iters', r.metadata.get('generations','')), extra=extra)
    return r, wall

def main():
    print("machine:", machine(), flush=True)
    pv = load_plan()
    data = load_line(pv, '09')
    dates = list(data.dates)

    # ---- A0: 矩阵缓存读取 ----
    t0=time.time(); D = load_cached('09').tolist(); load_s=time.time()-t0
    log(None, scenario='A0-matrix-cache-hit', algo='road.load_cached', line='09', seed='',
        budget_s=0, wall_s=round(load_s,3), km='', changed='', freq_ok='', iters='',
        extra=f'{len(D)}x{len(D)} from output/road_dist_09.npy')

    # ---- A1: nn2opt ----
    t0=time.time()
    r = get('nn2opt')().solve(data, D, time_budget=10)
    log(None, scenario='A-first-full', algo='nn2opt', line='09', seed='det', budget_s=10,
        wall_s=round(time.time()-t0,3), km=round(r.km,1), changed='', freq_ok=check_freq(r.days,data.codes,data.freq),
        iters='', extra='deterministic')

    # ---- A2: CP-SAT 日内 x1 (budget 300 全线路) ----
    for i in range(1):
        t0=time.time()
        r = get('cpsat_route')().solve(data, D, time_budget=300)
        w=time.time()-t0
        log(None, scenario='A-first-full', algo='cpsat_route', line='09', seed='det', budget_s=300,
            wall_s=round(w,2), km=round(r.km,1), changed='', freq_ok=check_freq(r.days,data.codes,data.freq),
            iters='', extra=f'per_day={w/len(dates):.2f}s x {len(dates)}days')

    # ---- A3: ALNS v3 x3 (budget 300) ----
    for i,(seed,tag) in enumerate([(42,'fixed'),(7,'vary'),(123,'vary')]):
        t0=time.time()
        r = get('alns_v3')().solve(data, D, time_budget=300, seed=seed)
        log(None, scenario='A-first-full', algo='alns_v3', line='09', seed=seed, budget_s=300,
            wall_s=round(time.time()-t0,2), km=round(r.km,1), changed='',
            freq_ok=check_freq(r.days,data.codes,data.freq), iters=r.metadata.get('iters',''),
            extra=f'run{i+1} seed={tag}')

    # ---- A4: MO-ALNS v4 x3 (base=v3 日级结果 + CP-SAT 锚点) ----
    v3w = json.load(open('output/v3_09_weekly.json'))
    dbs = {str(dd): dd for dd in dates}
    v3_base = {dbs[e['date']]: e['seq_alns_v3'] for dd_, days in v3w.items() for e in days.values()}
    t0=time.time()
    cpsat_seed = {dd: _exact_open_tsp(list(data.days_orig[dd]), D, 10) for dd in dates}
    cpsat_s = time.time()-t0
    mo = MOALNSv4()
    for i,(seed,tag) in enumerate([(42,'fixed'),(7,'vary'),(123,'vary')]):
        t0=time.time()
        r = mo.solve(data, D, time_budget=60, seed=seed, base=v3_base,
                     extra_seeds={'cpsat_exact': cpsat_seed})
        log(None, scenario='A-first-full', algo='mo_alns_v4', line='09', seed=seed, budget_s=60,
            wall_s=round(time.time()-t0,2), km=round(r.km,1), changed=r.metadata['front_size'],
            freq_ok=all(v['freq_ok'] for v in r.metadata['presets'].values()),
            iters=r.metadata['generations'],
            extra=f'run{i+1} seed={tag}; cpsat_anchor_build={cpsat_s:.1f}s; front={r.metadata["front_size"]}sol')

    # ---- A5: ensemble_sp + sdr_exact x1 (budget deep) ----
    t0=time.time()
    r = get('ensemble_sp')().solve(data, D, time_budget=300)
    log(None, scenario='A-first-full', algo='ensemble_sp', line='09', seed='det', budget_s=300,
        wall_s=round(time.time()-t0,2), km=round(r.km,1), changed='',
        freq_ok=check_freq(r.days,data.codes,data.freq), iters='', extra='pool rebuilt internally')

    t0=time.time()
    r = get('sdr_exact')().solve(data, D, time_budget=600, warm_start=r.days)
    md = r.metadata or {}
    log(None, scenario='A-first-full', algo='sdr_exact', line='09', seed='det', budget_s=600,
        wall_s=round(time.time()-t0,2), km=round(r.km,1), changed='',
        freq_ok=check_freq(r.days,data.codes,data.freq), iters='',
        extra=f"gen_s={md.get('gen_s')} sp_s={md.get('sp_s')} lp_s={md.get('lp_s')} gap={md.get('gap')}")

    # ---- B: 基于 v3 的小范围微调 (唯一有 base 的是 V4; V3 无起点参数=全量重初始化, 实测对照) ----
    for K in (1,3,5,16):
        rng = random.Random(42)
        base_k = {dd: list(seq) for dd, seq in v3_base.items()}
        allstores = [s for seq in base_k.values() for s in seq]
        for c in rng.sample(sorted(set(allstores)), K):
            d1 = [dd for dd,seq in base_k.items() if c in seq][0]
            same_wd = [dd for dd in dates if dd.weekday()==d1.weekday() and dd!=d1]
            if same_wd:
                d2 = rng.choice(same_wd); base_k[d1].remove(c); base_k[d2].append(c)
        t0=time.time()
        r = mo.solve(data, D, time_budget=30, seed=42, base=base_k)
        w=time.time()-t0
        dm={}
        for dd,seq in r.days.items():
            for s in seq: dm.setdefault(s,set()).add(dd)
        bdm={}
        for dd,seq in base_k.items():
            for s in seq: bdm.setdefault(s,set()).add(dd)
        moved = sum(1 for s in set(list(dm)+list(bdm)) if dm.get(s,set())!=bdm.get(s,set()))
        aff = sum(1 for dd in dates if sorted(base_k.get(dd,[]))!=sorted(v3_base.get(dd,[]))
                  or sorted(r.days.get(dd,[]))!=sorted(base_k.get(dd,[])))
        log(None, scenario=f'B-finetune-K{K}', algo='mo_alns_v4', line='09', seed=42, budget_s=30,
            wall_s=round(w,2), km=round(r.km,1), changed=moved,
            freq_ok=check_freq(r.days,data.codes,data.freq), iters=r.metadata['generations'],
            extra=f'perturbed {K} stores, affected_days={aff}')

    # ---- B对照: V3 无法增量 (签名无起点参数), 短预算重跑=全量重初始化 ----
    t0=time.time()
    r = get('alns_v3')().solve(data, D, time_budget=30)
    log(None, scenario='B-finetune-V3control', algo='alns_v3', line='09', seed=42, budget_s=30,
        wall_s=round(time.time()-t0,2), km=round(r.km,1), changed='',
        freq_ok=check_freq(r.days,data.codes,data.freq), iters=r.metadata.get('iters',''),
        extra='NO base/start param in signature: full re-init from days_orig, 30s gives worse km')

    # ---- C: 当天临时插单 (09线 7/1: 23计划+13临时; 及 1/3/5 合成) ----
    tool = CorridorDynamicInsertionTool()
    import pandas as pd
    df_act = pd.read_excel('/Users/ghb/Downloads/进离店报表导出 (4).xlsx')
    d0 = load_line(pv,'09')
    day1 = df_act[(df_act['片区'].astype(str).str.contains('09'))].copy()
    day1['进店时间']=pd.to_datetime(day1['进店时间'])
    day1=day1[day1['进店时间'].dt.date==pd.Timestamp('2026-07-01').date()].drop_duplicates('客户编码')
    codes_l = list(d0.codes)
    day_lons=[float(x) for x in day1['进店经度']]; day_lats=[float(x) for x in day1['进店纬度']]
    Dday = load_cached('09')  # use full line matrix indices for planned; simpler: rebuild with per-day
    from data.road import fetch_matrix
    import numpy as np
    cache = f"data/cache/dist_09_2026-07-01_{len(day1)}.npy"
    if os.path.exists(cache):
        Dd = np.load(cache).tolist()
    else:
        Dd = fetch_matrix(list(day1['客户编码'].astype(str).str.strip()), day_lons, day_lats).tolist()
    seq = [codes_l.index(c) if c in codes_l else i for i,c in enumerate(day_lons)]  # unused
    p_codes = [c for c in day1['客户编码'].astype(str).str.strip()]
    # planned 23 from SRP for that date:
    plan = load_plan()
    p09 = plan[plan['销售名称'].str.contains('海珠荔湾09') & (plan['date']==pd.Timestamp('2026-07-01').date())]
    planned_codes = set(p09['客户编码'].astype(str))
    idx = list(range(len(p_codes)))
    planned = [i for i in idx if p_codes[i] in planned_codes]
    adhoc   = [i for i in idx if i not in planned]
    route = MOALNSv4.__name__ and None
    from algos.alns_v3 import two_opt
    morning = two_opt(planned, Dd, 20)
    for K in (1,3,5):
        for rep in range(3):
            sel = adhoc if K==99 else rng_adhoc(rep,K,adhoc)
            t0=time.perf_counter()
            res = tool.insert_adhoc_batch(list(morning), sel, Dd, visited_prefix_len=6)
            us=(time.perf_counter()-t0)*1e6
            log(None, scenario='C-adhoc-insert', algo='CorridorDynamicInsertionTool', line='09/7-1',
                seed=rep, budget_s=0, wall_s=round(us/1e6,4), km=round(res['new_km'],2), changed=len(sel),
                freq_ok='', iters='', extra=f'K={len(sel)} route={len(res["new_route"])}stores latency_us={us:.0f}')
    # 真实 13 家全量
    t0=time.perf_counter()
    res = tool.insert_adhoc_batch(list(morning), adhoc, Dd, visited_prefix_len=6)
    us=(time.perf_counter()-t0)*1e6
    log(None, scenario='C-adhoc-insert', algo='CorridorDynamicInsertionTool', line='09/7-1',
        seed='real13', budget_s=0, wall_s=round(us/1e6,4), km=round(res['new_km'],2), changed=len(adhoc),
        freq_ok='', iters='', extra=f'REAL day K={len(adhoc)} latency_us={us:.0f}')

    # ---- D: 全 10 线轻量扫描 (nn2opt + v3@60s, 生产默认300s另计) ----
    for lid in ALL_LINE_IDS:
        try:
            dl = load_line(pv, lid); Dl = load_cached(lid)
            if Dl is None: 
                log(None, scenario='D-10lines', algo='skip', line=lid, seed='', budget_s=0,
                    wall_s=0, km='', changed='', freq_ok='', iters='', extra='no matrix cache')
                continue
            Dl = Dl.tolist()
            t0=time.time(); rn = get('nn2opt')().solve(dl, Dl, time_budget=10)
            log(None, scenario='D-10lines', algo='nn2opt', line=lid, seed='det', budget_s=10,
                wall_s=round(time.time()-t0,3), km=round(rn.km,1), changed='',
                freq_ok=check_freq(rn.days,dl.codes,dl.freq), iters='', extra=f'stores={dl.stores}')
            t0=time.time(); rv = get('alns_v3')().solve(dl, Dl, time_budget=60)
            log(None, scenario='D-10lines', algo='alns_v3@60s', line=lid, seed=42, budget_s=60,
                wall_s=round(time.time()-t0,2), km=round(rv.km,1), changed='',
                freq_ok=check_freq(rv.days,dl.codes,dl.freq), iters=rv.metadata.get('iters',''),
                extra='budget60 NOT production 300')
        except Exception as e:
            log(None, scenario='D-10lines', algo='ERROR', line=lid, seed='', budget_s=0,
                wall_s=0, km='', changed='', freq_ok='', iters='', extra=str(e)[:120])
    print("=== ALL DONE ===", flush=True)

def rng_adhoc(rep,K,pool):
    rr = random.Random(100+rep)
    return rr.sample(pool, min(K,len(pool)))

if __name__ == '__main__':
    main()
