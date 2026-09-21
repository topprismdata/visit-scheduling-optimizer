# -*- coding: utf-8 -*-
"""芜湖 000707342 · 8月覆盖制规划 — 三层框架全链路首次完整执行 (Phase D 验收跑).

数据基准: /Users/ghb/UFS-demo/更新后的8月规划.xlsx (老板 2026-09-21 裁定为现行基准)
口径: 覆盖制 (coverage dialect) — 每店全月 1 访, 17 个工作日与基线持平, 走廊 [5,12]

链路: LineData(覆盖口径) → L1 coverage spec → L2 VisitPlanningInstance
      → L3 R2ALNS 多seed + SP 精磨 → L2 MathValidator 独立验解 → Decision Episode
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date

from core.base import LineData
from orchestration.episode import emit_episode
from visit_math_api import SolverConfig, SolveResult
from visit_math_api import episode_hash
from visit_ir.compiler import COMPILER_VERSION
from visit_semantic_api import (
    CompilerProfile, ContractType, PlanningHorizon, SemanticObjectivePolicy,
    SourceMetadata, VisitContract, VisitSemanticSpec, WorkloadCorridorPolicy,
)
from visitmodel import MathCompiler, MathValidator

XLSX = "/Users/ghb/UFS-demo/更新后的8月规划.xlsx"
LINE = sys.argv[1] if len(sys.argv) > 1 else "000707342"
SEEDS = [42, 7, 137]
BUDGET_S = 40.0


def hav_mat(lat, lng):
    lat = np.radians(np.asarray(lat)); lng = np.radians(np.asarray(lng))
    p1, p2 = lat[:, None], lat[None, :]
    dp = p2 - p1
    dl = lng[:, None] - lng[None, :]
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def load_coverage_line() -> tuple[LineData, pd.DataFrame, dict]:
    df = pd.read_excel(XLSX)
    df['plan_day'] = pd.to_datetime(df['plan_day'])
    d = df[df['sales_line'] == LINE].copy()
    svc_wd = d.groupby(d['customer_code'].astype(str))['服务日'].apply(
        lambda x: frozenset(int(v) for v in x.dropna())).to_dict()
    d = d.sort_values(['plan_day', 'visit_num'])
    codes = d['customer_code'].drop_duplicates().tolist()
    idx = {c: i for i, c in enumerate(codes)}
    dates = sorted(d['plan_day'].unique())
    days_orig = {dd: [idx[c] for c in g['customer_code']] for dd, g in d.groupby('plan_day')}
    freq = d.groupby('customer_code').size().to_dict()  # 覆盖制: 义务=基线实际次数
    lens = [len(v) for v in days_orig.values()]
    line = LineData(
        line_id=LINE, line_name="芜湖覆盖线342",
        codes=codes, lon=d.drop_duplicates('customer_code')['lng'].astype(float).tolist(),
        lat=d.drop_duplicates('customer_code')['lat'].astype(float).tolist(),
        dates=dates, days_orig=days_orig, freq=freq,
        stores=len(codes), visits=len(d),
        min_daily_capacity=min(lens), max_daily_capacity=max(lens),
    )
    return line, d, svc_wd


def coverage_spec(line: LineData, svc_wd: dict) -> VisitSemanticSpec:
    """覆盖方言 v2 (coverage_v2): 义务=基线次数, legal_dates 锁定服务日星期几.

    习惯结构 (2026-09-21 老板洞察 + 数据证实): 业代的日簇习惯单位是
    星期几×圈层 (342: 周一~三城区, 周四五郊区), 不是具体日期。
    优化自由度 = 同星期几内选哪一周 + 当日内路线序; 跨星期几禁止。
    C3 成员检查即 σ 锁。
    """
    contracts = tuple(
        VisitContract(
            customer_code=c, contract_type=ContractType.WEEKLY, phase=None,
            sigma=min(svc_wd.get(str(c), {1})) - 1, legal_slot_indices=(0,),
            obligation=int(line.freq[c]),
            legal_dates=tuple(sorted(
                dd for dd in line.dates
                if dd.weekday() + 1 in svc_wd.get(str(c), {dd.weekday() + 1})
            )),
        )
        for c in line.codes
    )
    corridor = WorkloadCorridorPolicy(
        k_min=line.min_daily_capacity, k_max=line.max_daily_capacity,
        source="historical_baseline", derivation="min/max(original_daily_counts)",
        approved=True, approved_by="boss-2026-09-21",
    )
    horizon = PlanningHorizon(
        start_date=min(line.dates), end_date=max(line.dates),
        timezone="Asia/Shanghai", calendar_id="wuhu_aug2026",
        anchor_week=min(line.dates).isocalendar()[1], phase_period=2,
    )
    import hashlib, json
    payload = json.dumps({
        "codes": sorted(str(c) for c in line.codes),
        "corridor": [corridor.k_min, corridor.k_max],
        "workdays": sorted(str(x) for x in line.dates),
    }, sort_keys=True, ensure_ascii=False)
    meta = SourceMetadata(
        schema_version="coverage_v2",
        content_hash=hashlib.sha256(payload.encode()).hexdigest(),
        source_snapshot_id=f"ufs-demo-8yue-{LINE}",
        compiler_version=COMPILER_VERSION,
        compiled_at=pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
    )
    return VisitSemanticSpec(
        horizon=horizon, contracts=contracts, corridor=corridor,
        objective_policy=SemanticObjectivePolicy(),
        metadata=meta,
    )


def main():
    line, plan_df, svc_wd = load_coverage_line()
    D = hav_mat(line.lat, line.lon)
    dates = list(line.dates)
    kmc = lambda seq: float(sum(D[seq[k]][seq[k + 1]] for k in range(len(seq) - 1)))

    # ---- L1: 覆盖方言编译 ----
    spec = coverage_spec(line, svc_wd)
    print(f"[L1] coverage spec: {len(spec.contracts)} 合同 义务Σ="
          f"{sum(c.obligation for c in spec.contracts)} 走廊=[{spec.corridor.k_min},{spec.corridor.k_max}] "
          f"hash={spec.metadata.content_hash[:8]} dialect={spec.metadata.schema_version}")

    # ---- L2: 数学实例 ----
    inst = MathCompiler().compile(spec)
    print(f"[L2] instance: {len(inst.customers)} 客户 {len(inst.workdays)} 工作日 "
          f"走廊={inst.day_corridor} 目标项={[t.metric for t in inst.objective_terms]}")

    # ---- 基线里程 ----
    base_days = {dd: list(seq) for dd, seq in line.days_orig.items()}
    base_km = sum(kmc(s) for s in base_days.values())

    # ---- L3: R2ALNS 多 seed → SP 精磨 ----
    from algos.r2_alns import R2ALNS
    best_days, best_km = None, float("inf")
    for seed in SEEDS:
        r = R2ALNS().solve(line, D, time_budget=BUDGET_S, seed=seed)
        print(f"[L3] R2ALNS seed={seed}: km={r.km:.2f} iters={r.metadata.get('iters')}")
        if r.km < best_km:
            best_km, best_days = r.km, {dd: list(v) for dd, v in r.days.items()}

    # σ 锁视图: legal = 每店服务日日期集 (coverage_v2)
    legal_idx = {i: frozenset(spec.contract_of(c).legal_dates)
                 for i, c in enumerate(line.codes)}
    view = {"legal": legal_idx, "fw": None}
    from algos.sp_matheuristic import SPMatheuristic
    def _legal_cols(days):
        return [(dd, list(v), kmc(v)) for dd, seq in days.items()
                for v in [seq] if all(dd in legal_idx[i] for i in v)]
    pool = _legal_cols(best_days) + _legal_cols(base_days)
    sp = SPMatheuristic().solve(line, D, time_budget=60, pool=pool, rounds=2,
                                sa_burst=8.0, r2_prime=False, view=view)
    print(f"[L3] SP 精磨: km={sp.km:.2f} (rmp_lp={sp.metadata.get('rmp_lp')})")

    final_days, final_km = sp.days, sp.km

    # ---- L2: 独立验解 (Solver 不自证合法) ----
    solution = {dd: tuple(line.codes[i] for i in final_days[dd]) for dd in dates}
    report = MathValidator().validate(inst, solution)
    print(f"[L2] MathValidator: ok={report.ok} 违例={[(v.constraint_id, v.detail) for v in report.violations[:5]]}")

    # 覆盖断言: 每店次数 == 义务 (双访线不是排列, 是计数)
    from collections import Counter
    cnt = Counter(i for dd in dates for i in final_days[dd])
    bad = [(line.codes[i], cnt.get(i, 0), line.freq[c]) for i, c in enumerate(line.codes)
           if cnt.get(i, 0) != line.freq[c]]
    assert not bad, f"义务不守恒: {bad[:5]}"
    print(f"[ASSERT] {len(line.codes)} 店义务守恒: ✓")
    # 习惯保持率: 解的星期几 ⊆ 服务日 (σ 锁验收)
    viol_sigma = sum(1 for dd, seq in final_days.items() for i in seq
                     if dd not in legal_idx[i])
    print(f"[ASSERT] σ 锁 (服务日) 违例: {viol_sigma} 次拜访 → 习惯保持率 "
          f"{(1 - viol_sigma / max(sum(len(s) for s in final_days.values()), 1)) * 100:.0f}%")

    # ---- Episode ----
    solve_result = SolveResult(
        status="FEASIBLE" if report.ok else "INFEASIBLE",
        assignments={dd: tuple(solution[dd]) for dd in dates},
        objective_vector=(round(final_km, 3),),
        termination_reason="r2alns3seed+sp-polish",
        instance_hash=dict(inst.metadata).get("content_hash", ""),
    )
    episode = emit_episode(spec, inst, solve_result,
                           SolverConfig(backend="r2alns+sp", time_limit_s=BUDGET_S * len(SEEDS) + 60,
                                        seed=SEEDS[0]),
                           solver_version="phase-d-run1")
    print(f"[EP] episode={episode.episode_id[:8]} hash={episode_hash(episode)[:8]}")

    # ---- 对比报告 ----
    print("\n===== 基线 vs 三层框架 =====")
    print(f"基线(更新后规划) : {base_km:8.2f} km")
    print(f"框架最优         : {final_km:8.2f} km   ({(final_km - base_km) / base_km * 100:+.1f}%)")
    print(f"日负载: 基线 {[len(base_days[dd]) for dd in dates]}")
    print(f"        框架 {[len(final_days[dd]) for dd in dates]}")
    per_day = pd.DataFrame({
        "基线km": [round(kmc(base_days[dd]), 2) for dd in dates],
        "框架km": [round(kmc(final_days[dd]), 2) for dd in dates],
    }, index=[str(dd.date()) for dd in dates])
    print(per_day.to_string())

    # ---- 导出优化版规划 + 飞点店去向 ----
    out = []
    for dd in dates:
        for k, i in enumerate(final_days[dd], 1):
            out.append({
                "sales_line": LINE, "plan_day": dd, "visit_num": k,
                "customer_code": line.codes[i],
                "customer_name": plan_df.drop_duplicates('customer_code')
                    .set_index('customer_code')['customer_name'].get(line.codes[i], ""),
                "lng": line.lon[i], "lat": line.lat[i],
                "leg_km": round(D[final_days[dd][k-1]][final_days[dd][k]], 3) if k < len(final_days[dd]) else 0.0,
            })
    out_df = pd.DataFrame(out)
    out_path = f"/Users/ghb/UFS-demo/{LINE}_三层框架_8月规划_优化版.xlsx"
    out_df.to_excel(out_path, index=False)
    print(f"\n优化版规划已导出: {out_path} ({len(out_df)} 行, 总直线 {final_km:.1f} km)")

    fly = set()
    for dd, seq in line.days_orig.items():
        for k in range(len(seq) - 1):
            if D[seq[k]][seq[k + 1]] > 15:
                fly |= {line.codes[seq[k]], line.codes[seq[k + 1]]}
    # 双访店间隔检查 (coverage_v1 方言无间隔约束, 如实报告)
    multi = [c for c in line.codes if line.freq[c] >= 2]
    if multi:
        print(f"双访店间隔检查 ({len(multi)} 家, obligation>=2):")
        day2idx = {str(dd.date()): seq for dd, seq in final_days.items()}
        code2idx = {str(cc): ii for ii, cc in enumerate(line.codes)}
        for c in multi:
            i = code2idx[str(c)]
            days_i = sorted([ds for ds, seq in day2idx.items() if i in seq])
            gaps = [abs((pd.Timestamp(b) - pd.Timestamp(a)).days) for a, b in zip(days_i, days_i[1:])]
            print(f"   {c}: {days_i} 间隔 {gaps}")

    print("飞点店去向 (基线坏腿涉及店 → 框架分配日):")
    seq_by_str = {str(dd.date()): seq for dd, seq in final_days.items()}
    idx2day = {i: str(dd.date()) for dd, seq in final_days.items() for i in seq}
    code2idx = {str(c): i for i, c in enumerate(line.codes)}
    for c in sorted(fly, key=str):
        i = code2idx[str(c)]
        dd = idx2day.get(i, "未排")
        seq = seq_by_str.get(dd, [])
        pos = seq.index(i) if i in seq else -1
        leg_in = D[seq[pos-1]][i] if pos > 0 else 0.0
        leg_out = D[i][seq[pos+1]] if 0 <= pos < len(seq)-1 else 0.0
        print(f"   {c}: {dd} 第{pos+1}站 进腿{leg_in:.1f}km 出腿{leg_out:.1f}km")
    return spec, inst, final_days, report


if __name__ == "__main__":
    main()
