"""SFA 进离店报表适配器契约测试 (广州真实导出 schema).

覆盖:
- R1 跨午夜/挂机时长截断 (在店>=cap 或 自动离店)
- R2 原地连批打卡识别 (同坐标 + 间隔<=5min + 在店<=2min)
- R3 GPS 偏差降权 (偏差>100m -> 事件保留, 位置不参与估计)
- R4 同客户坐标漂移 -> 聚类质心保留可规划性
- manifest sha256 与源文件字节一致 (InputSnapshot 契约)
- 观察频次 -> OperationalVisitPolicy (approved_by=DERIVED_FROM_OBSERVATION)
"""
import datetime
import hashlib
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # svde/ontology/src

import openpyxl
import pytest

from prism_ontology.real_data.sfa_checkin_ingestor import (
    CleaningParams, SFACheckinIngestor, TZ_CN, EventFlag,
)

ASSEMBLED_AT = datetime.datetime(2026, 8, 1, tzinfo=datetime.timezone.utc)

COLS = ["大区", "办事处", "片区", "人员编码", "人员名称", "客户编码", "客户名称",
        "客户类型", "进店时间", "离店时间", "在店时长(分钟)", "进店地址",
        "省", "市", "进店经度", "进店纬度", "偏差(米)", "打卡状态", "自动离店"]
_ALIAS = {"在店时长": "在店时长(分钟)", "偏差": "偏差(米)"}
def _row(**kw):
    base = {
        "大区": "华南区", "办事处": "广州", "片区": "测试片区",
        "人员编码": "R001", "人员名称": "测试员",
        "客户编码": "C0001", "客户名称": "测试门店", "客户类型": "门店",
        "进店时间": "2026-07-01 09:00:00", "离店时间": "2026-07-01 09:10:00",
        "在店时长(分钟)": 10.0, "进店地址": "测试地址1号",
        "省": "广东省", "市": "广州市",
        "进店经度": 113.27, "进店纬度": 23.10, "偏差(米)": 5.0,
        "打卡状态": "正常", "自动离店": "否",
    }
    base.update({_ALIAS.get(k, k): v for k, v in kw.items()})
    return [base.get(c, "") for c in COLS]


def _write(tmp_path, rows, name="sfa.xlsx"):
    p = tmp_path / name
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(COLS)
    for r in rows:
        ws.append(r)
    wb.save(p)
    return str(p)


def _ingest(path):
    return SFACheckinIngestor.assemble_from_excel(path, assembled_at=ASSEMBLED_AT)


def test_r1_checkout_inflation_truncated(tmp_path):
    p = _write(tmp_path, [_row(在店时长=348.0, 进店时间="2026-07-01 18:09:57",
                               离店时间="2026-07-01 23:58:56"),
                          _row(自动离店="是", 在店时长=200.0)])
    ws, flags, stats = _ingest(p)
    assert stats.r1_truncated == 2
    assert all(e.service_duration_min <= CleaningParams().r1_cap_min
               for e in ws.execution_fact_stream)
    assert any(f.code == "R1_CHECKOUT_INFLATION" for f in flags)
    # 审计痕迹落在 summary/action_notes, 不静默
    e = ws.execution_fact_stream[0]
    assert "R1" in (e.summary or "") or e.actions


def test_r2_batch_checkin_suspect(tmp_path):
    # 同 rep 同日同坐标: 正常拜访 -> 2分钟后原地秒打卡(2min) -> 正常离店拜访
    p = _write(tmp_path, [
        _row(客户编码="C0001", 进店时间="2026-07-01 09:00:00",
             离店时间="2026-07-01 09:10:00", 在店时长=10.0),
        _row(客户编码="C0002", 进店时间="2026-07-01 09:12:00",
             离店时间="2026-07-01 09:13:00", 在店时长=1.0),
        _row(客户编码="C0003", 进店时间="2026-07-01 10:00:00",
             离店时间="2026-07-01 10:15:00", 在店时长=15.0),
    ])
    ws, flags, stats = _ingest(p)
    assert stats.r2_suspects == 1
    assert any(f.code == "R2_BATCH_CHECKIN_SUSPECT" and "C0002" in f.target for f in flags)
    # 降权事件仍在事实流 (观察事实不删除), 但 credit=0 不进有效频次
    codes = {e.store_code for e in ws.execution_fact_stream}
    assert {"C0001", "C0002", "C0003"} <= codes
    eff = ws.manifest.valid_facts_count
    assert eff == stats.raw_events - stats.r2_suspects


def test_r3_gps_deviance_excluded_from_location(tmp_path):
    p = _write(tmp_path, [
        _row(客户编码="C0001", 偏差=5.0),
        _row(客户编码="C0001", 进店时间="2026-07-02 09:00:00",
             离店时间="2026-07-02 09:05:00", 偏差=3500.0,
             进店经度=113.99, 进店纬度=23.99),
    ])
    ws, flags, stats = _ingest(p)
    assert stats.r3_gps_bad == 1
    loc = ws.customers["C0001"].location
    assert loc.longitude == 113.27 and loc.latitude == 23.10  # 仅可信坐标参与
    assert any(f.code == "R3_GPS_DEVIANCE" for f in flags)


def test_r4_coord_drift_clustered(tmp_path):
    p = _write(tmp_path, [
        _row(客户编码="C0001", 进店时间="2026-07-01 09:00:00",
             离店时间="2026-07-01 09:05:00"),
        _row(客户编码="C0001", 进店时间="2026-07-02 09:00:00",
             离店时间="2026-07-02 09:05:00", 进店经度=113.50, 进店纬度=23.50),
        _row(客户编码="C0001", 进店时间="2026-07-03 09:00:00",
             离店时间="2026-07-03 09:05:00", 进店经度=113.50, 进店纬度=23.50),
    ])
    ws, flags, stats = _ingest(p)
    assert stats.r4_drift_customers == 1
    assert ws.customers["C0001"].geo_quality.name == "EXACT_MATCH"  # 簇质心保留可规划
    assert any(f.code == "R4_STORE_COORD_DRIFT" for f in flags)


def test_unmapped_customer_when_no_trusted_gps(tmp_path):
    p = _write(tmp_path, [_row(偏差=900.0)])
    ws, flags, stats = _ingest(p)
    assert ws.customers["C0001"].geo_quality.name == "UNMAPPED"
    assert stats.unmapped_customers == 1


def test_manifest_hash_matches_file_bytes(tmp_path):
    p = _write(tmp_path, [_row()])
    ws, _flags, _stats = _ingest(p)
    assert ws.manifest.source_file_sha256 == hashlib.sha256(open(p, "rb").read()).hexdigest()


def test_observed_frequency_synthesized_as_policy(tmp_path):
    # C0001 当月有效到店 2 次 -> target_frequency 钳位 [1,4]
    p = _write(tmp_path, [
        _row(客户编码="C0001"),
        _row(客户编码="C0001", 进店时间="2026-07-10 09:00:00",
             离店时间="2026-07-10 09:05:00"),
    ])
    ws, _flags, _stats = _ingest(p)
    pol = ws.policies.operational_policies["C0001"]
    assert pol.target_frequency_per_month == 2
    assert pol.approved_by == "DERIVED_FROM_OBSERVATION"  # 绝不冒充签署政策


def test_required_column_missing_raises(tmp_path):
    p = _write(tmp_path, [_row()])
    import openpyxl as _ox
    wb = _ox.load_workbook(p)
    wb.active.delete_cols(COLS.index("偏差(米)") + 1)
    bad = str(tmp_path / "bad.xlsx")
    wb.save(bad)
    with pytest.raises(ValueError, match="缺少必需列"):
        _ingest(bad)
