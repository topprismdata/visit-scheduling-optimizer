"""Tests for CadenceComplianceAuditor Operator.

Verifies:
1. Four-quadrant classification (EXACT, UNDER, ZERO, OVER)
2. Customer Universe Left-Join logic (ensures zero-visited stores are captured)
3. Critical Incident Alert on Key store zero-visits (e.g. NT23 in Renjun June data)
4. Real FMCG data benchmark on sales rep Renjun (June 2026)
"""
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

import openpyxl
from prism_ontology.diagnostics.cadence_auditor import (
    CadenceComplianceAuditor, ComplianceStatus, IncidentSeverity
)

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


@pytest.fixture(scope="module")
def renjun_june_data():
    """Extract Renjun's assigned store universe and June 2026 execution records."""
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
    
    wb = openpyxl.load_workbook(DATA_FILE, read_only=True, data_only=True)
    sheet = wb["历史拜访总表"]
    rows = list(sheet.iter_rows(values_only=True))
    header = list(rows[0])
    data = list(rows[1:])
    
    rep_idx = header.index('门店负责人')
    date_idx = header.index('拜访日期')
    store_name_idx = header.index('门店名称')
    store_code_idx = header.index('主数据_门店编码')
    tier_idx = header.index('门店级别')
    freq_idx = header.index('拜访频率')
    ka_idx = header.index('主数据_KA名称')
    district_idx = header.index('主数据_行政区县名称')

    # 1. Assigned store universe for Renjun
    assigned_stores = {}
    for r in data:
        if r[rep_idx] == '仁军':
            code = r[store_code_idx]
            if code and code not in assigned_stores:
                assigned_stores[code] = {
                    'name': r[store_name_idx],
                    'tier': r[tier_idx] or 'STANDARD',
                    'planned_freq': int(r[freq_idx]) if r[freq_idx] is not None and str(r[freq_idx]).isdigit() else 0,
                    'ka': r[ka_idx] or '独立店',
                    'district': r[district_idx] or '未知'
                }

    # 2. June 2026 execution records
    executions = []
    for r in data:
        if r[rep_idx] == '仁军':
            d_val = r[date_idx]
            if d_val and '-06-' in str(d_val):
                executions.append({
                    'store_code': r[store_code_idx],
                    'store_name': r[store_name_idx],
                    'date': d_val
                })

    return assigned_stores, executions


# ============================================================================
# Unit Tests on Mock Data
# ============================================================================

def test_auditor_detects_zero_visited_store_even_with_empty_executions():
    assigned = {
        "STORE_001": {"name": "Test Key Store", "tier": "Key", "planned_freq": 4, "ka": "KA1", "district": "D1"}
    }
    executions = [] # no visits at all
    
    report = CadenceComplianceAuditor.audit_rep_period("REP_A", "2026-06", assigned, executions)
    
    assert report.total_assigned_stores == 1
    assert report.zero_visited_count == 1
    assert report.compliance_rate == 0.0
    assert len(report.critical_incidents) == 1
    assert report.critical_incidents[0].store_code == "STORE_001"
    assert report.critical_incidents[0].severity == IncidentSeverity.CRITICAL_INCIDENT


def test_auditor_four_quadrants():
    assigned = {
        "S1": {"name": "Exact", "tier": "A", "planned_freq": 2, "ka": "KA", "district": "D"},
        "S2": {"name": "Under", "tier": "B", "planned_freq": 4, "ka": "KA", "district": "D"},
        "S3": {"name": "Zero", "tier": "C", "planned_freq": 1, "ka": "KA", "district": "D"},
        "S4": {"name": "Over", "tier": "D", "planned_freq": 1, "ka": "KA", "district": "D"},
    }
    executions = [
        {"store_code": "S1", "date": "2026-06-01"},
        {"store_code": "S1", "date": "2026-06-15"},
        {"store_code": "S2", "date": "2026-06-01"}, # 1 visit, planned 4
        # S3 is 0 visits
        {"store_code": "S4", "date": "2026-06-01"},
        {"store_code": "S4", "date": "2026-06-10"}, # 2 visits, planned 1
    ]
    
    report = CadenceComplianceAuditor.audit_rep_period("REP_B", "2026-06", assigned, executions)
    
    assert report.exact_compliant_count == 1
    assert report.under_serviced_count == 1
    assert report.zero_visited_count == 1
    assert report.over_serviced_count == 1
    assert report.compliance_rate == 25.0


# ============================================================================
# Real Data Benchmark: Renjun June 2026 Audit
# ============================================================================

def test_renjun_june_real_audit_exact_numbers(renjun_june_data):
    assigned_stores, executions = renjun_june_data
    
    report = CadenceComplianceAuditor.audit_rep_period("仁军", "2026-06", assigned_stores, executions)
    
    # 1. Total universe must be 36 assigned stores
    assert report.total_assigned_stores == 36
    assert report.total_actual_visits == 71
    
    # 2. Four quadrant exact counts
    assert report.exact_compliant_count == 20
    assert report.under_serviced_count == 7
    assert report.zero_visited_count == 4
    assert report.over_serviced_count == 5
    assert pytest.approx(report.compliance_rate, 0.1) == 55.6
    
    # 3. Critical Incident must catch Key store NT23 (人民中路店)
    zero_codes = {r.store_code for r in report.store_results if r.status == ComplianceStatus.ZERO_VISITED}
    assert "00006798" in zero_codes # NT23 code
    
    critical_codes = {r.store_code for r in report.critical_incidents}
    assert "00006798" in critical_codes
    
    nt23_res = [r for r in report.critical_incidents if r.store_code == "00006798"][0]
    assert nt23_res.tier == "Key"
    assert nt23_res.planned_frequency == 4
    assert nt23_res.actual_visits_count == 0
    assert "CRITICAL" in nt23_res.violation_message
