"""Real Data Replay #2: 广州办 SFA 进离店报表 (2026-07) → 清洗 → MVP → Shadow 对比.

链路 (完整穿过 Shadow 工具链, 不绕过任何闸门):
  SFA 进离店 xlsx
    → SFACheckinIngestor (L0 实例化 + R1-R4 可信度清洗)
    → materialize_planned_frequency (policy -> customer, v2 投影; 修 A 策略根因)
    → 目标 rep 子宇宙截断 (可规划店, 按观测频次取 Top-N, 保证 solver 可解)
    → derive_lifecycle (execution facts -> lifecycle records)
    → run_replay(projection=...) (InputSnapshot -> DataPrecheck -> Gate -> MVP
       -> ReplayMetrics -> BaselineComparator)

红线:
- 源 xlsx 只读 (不写回)
- MVP 主流程 / runner / precheck / guard 全部零修改 (projection 注入是 runner 既有入口)
- UNMAPPED (GPS 全不可信) 客户不进规划宇宙 — canonical 门禁
- 子宇宙截断的 coverage 缺口如实写入 notes, 不做粉饰

用法:
  python -m prism_ontology.shadow.replay_guangzhou_07 \
      [--xlsx /path/进离店报表导出 (4).xlsx] [--rep 梁健满] [--max-stops 30]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from prism_ontology.real_data.sfa_checkin_ingestor import (
    SFACheckinIngestor, CleaningParams, EventFlag, CleaningStats,
)
from prism_ontology.shadow.planning_input import (
    materialize_planned_frequency, _derive_lifecycle_into,
)
from prism_ontology.shadow.runner import run_replay

DEFAULT_XLSX = "/Users/ghb/Downloads/进离店报表导出 (4).xlsx"
PERIOD = "2026-07"
ASSEMBLED_AT = datetime.datetime(2026, 8, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)


def july_working_days_2026() -> List[str]:
    """2026-07 的工作日 (周一..周五), 取前 20 个 = solver 4周x5天槽位."""
    out = []
    d = datetime.date(2026, 7, 1)
    while d.month == 7:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out[:20]


def build_projection(xlsx: str, rep_id: str, max_stops: int):
    """L0 实例化 + 清洗 + 投影. 返回 (projection, ws, stats, flags, subset_info)."""
    ws, flags, stats = SFACheckinIngestor.assemble_from_excel(
        xlsx, assembled_at=ASSEMBLED_AT,
        params=CleaningParams(), snapshot_id="SNAP_SFA_GZ_2026_07")

    if rep_id not in ws.resources:
        raise ValueError(f"rep '{rep_id}' 不在报表中; 可选: {sorted(ws.resources)}")

    # policy -> planned_frequency (v2 投影: 修 A 策略注入不生效根因)
    p1 = materialize_planned_frequency(ws, rep_id=rep_id)
    ws1 = p1.worldstate

    # 子宇宙: 该 rep 的可规划 (planned_frequency 已物化) 客户, 按观测频次降序取 Top-N
    rep = ws1.resources[rep_id]
    plannable = [c for c in rep.assigned_store_codes
                 if ws1.customers.get(c) and ws1.customers[c].planned_frequency is not None]
    plannable.sort(key=lambda c: (-ws1.customers[c].planned_frequency, c))
    subset = plannable[:max_stops]
    dropped = len(rep.assigned_store_codes) - len(subset)

    ws2 = replace(ws1, resources={
        **ws1.resources,
        rep_id: replace(rep, assigned_store_codes=tuple(subset)),
    })

    # replay 宇宙 = 目标 rep 子宇宙: 同步裁剪 ownership/policies,
    # 否则频次达成率分母会混入全辖区 3023 家店
    subset_set = set(subset)
    ws2 = replace(ws2, policies=replace(
        ws2.policies,
        operational_policies={c: p for c, p in ws2.policies.operational_policies.items()
                              if c in subset_set},
        ownership_map={c: o for c, o in ws2.policies.ownership_map.items()
                       if c in subset_set}))
    p2 = _derive_lifecycle_into(ws2, rep_id, PERIOD)

    subset_info = {
        "rep_assigned_total": len(rep.assigned_store_codes),
        "plannable_after_clean": len(plannable),
        "subset_size": len(subset),
        "dropped_for_solvability": dropped,
        "observed_freq_mean": round(mean(
            [ws2.customers[c].planned_frequency for c in subset]), 2) if subset else 0,
        "materialize_confidence": p1.confidence,
    }
    return p2, ws, stats, flags, subset_info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", default=DEFAULT_XLSX)
    ap.add_argument("--rep", default="梁健满")
    ap.add_argument("--max-stops", type=int, default=30)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    print("=" * 72)
    print(f"Real Data Replay #2: SFA 进离店报表 → 清洗 → MVP (rep={args.rep}, {PERIOD})")
    print("=" * 72)

    # [1] 清洗 + 投影
    projection, ws_raw, stats, flags, subset_info = build_projection(
        args.xlsx, args.rep, args.max_stops)
    print(f"\n[1] L0 实例化 + R1-R4 清洗:")
    print(f"    原始事件: {stats.raw_events} | 有效(credit>0): {stats.effective_events} "
          f"| 可信率: {stats.reliability_rate:.1%}")
    print(f"    R1 时长截断: {stats.r1_truncated} | R2 连批降权: {stats.r2_suspects} "
          f"| R3 GPS不可信: {stats.r3_gps_bad}")
    print(f"    R4 坐标漂移店: {stats.r4_drift_customers}/{stats.r4_total_customers} "
          f"| 完全不可定位店: {stats.unmapped_customers}")
    print(f"    子宇宙: {subset_info}")

    # [2] Shadow 全链路 (runner 自带 snapshot/precheck/gate; projection 注入既有入口)
    run_params = {
        "target_rep_id": args.rep,
        "period_label": PERIOD,
        "working_days": july_working_days_2026(),
        "scenario_id": "REAL_DATA_GZ_07_CLEANED",
        "description": "SFA 进离店真实数据 (R1-R4 清洗后) shadow replay",
        "unavailable_rep_ids": [],
        "run_timestamp": ASSEMBLED_AT,
        "schema_version": "sfa_checkin_v1.0",
    }
    report = run_replay(args.xlsx, run_params, projection=projection)

    print(f"\n[2] ShadowReplayRunner:")
    print(f"    snapshot={report.snapshot_id} worldstate={report.worldstate_id}")
    print(f"    precheck={report.precheck_status} (E={report.precheck_error_count} "
          f"W={report.precheck_warning_count}) | invariants_held={report.invariants_held}")
    if report.metrics:
        m = report.metrics
        print(f"    plan: routes={m.total_routes} stops={m.total_stops} "
              f"unique_cust={m.unique_customers_visited}")
    if report.comparison:
        c = report.comparison
        print(f"    compare: plan={c.plan_total_stops} actual={c.actual_total_stops} "
              f"diff={c.stop_diff} match_rate={c.match_rate:.3f} status={c.status}")
        for n in c.notes[:6]:
            print(f"      - {n}")
    for n in report.notes:
        print(f"    note: {n}")
    print(f"    elapsed={report.elapsed_seconds:.1f}s")

    # [3] 有效基线 vs 名义基线 (世界模型口径差异)
    by_rep = defaultdict(lambda: [0, 0])  # rep -> [nominal, effective]
    for e in ws_raw.execution_fact_stream:
        by_rep[e.rep_id][0] += 1
        if "R2:batch_suspect" not in e.summary and "R3:gps_dev" not in e.summary:
            by_rep[e.rep_id][1] += 1
    print(f"\n[3] 名义 vs 有效拜访 (按 rep, 全宇宙):")
    for rep_id, (nom, eff) in sorted(by_rep.items(), key=lambda kv: -kv[1][0]):
        print(f"    {rep_id}: {nom} -> {eff} ({eff/nom:.0%})")

    result = {
        "stats": {"raw": stats.raw_events, "effective": stats.effective_events,
                  "reliability": round(stats.reliability_rate, 4),
                  "r1": stats.r1_truncated, "r2": stats.r2_suspects,
                  "r3": stats.r3_gps_bad, "r4_drift": stats.r4_drift_customers,
                  "unmapped": stats.unmapped_customers},
        "subset": subset_info,
        "precheck": report.precheck_status,
        "invariants_held": report.invariants_held,
        "metrics": (None if not report.metrics else {
            "routes": report.metrics.total_routes, "stops": report.metrics.total_stops,
            "unique_customers": report.metrics.unique_customers_visited}),
        "comparison": (None if not report.comparison else {
            "plan": report.comparison.plan_total_stops,
            "actual": report.comparison.actual_total_stops,
            "match_rate": report.comparison.match_rate,
            "status": report.comparison.status}),
        "notes": report.notes,
        "flags_sample": [vars(f) for f in flags[:50]],
        "flags_total": len(flags),
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n[4] JSON 报告 -> {args.json_out}")
    return 0 if report.invariants_held else 1


if __name__ == "__main__":
    raise SystemExit(main())
