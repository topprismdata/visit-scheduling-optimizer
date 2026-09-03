"""Cadence Compliance Auditor — Core Diagnostic Operator for SVDE.

Strictly adheres to the Three Iron Rules:
1. Customer Universe Baseline: Evaluates all assigned stores (never filter by executed rows alone)
2. Four-Quadrant Classification: EXACT_COMPLIANT, UNDER_SERVICED, ZERO_VISITED, OVER_SERVICED
3. Critical Incident Guard: Raises immediate alert when Key / REQUIRED stores are under-serviced or zero-visited
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from collections import Counter, defaultdict


class ComplianceStatus(str, Enum):
    EXACT_COMPLIANT = "EXACT_COMPLIANT"    # 严格按频次履约
    UNDER_SERVICED = "UNDER_SERVICED"      # 频次不足 (实际 > 0 但 < 规定)
    ZERO_VISITED = "ZERO_VISITED"          # 彻底脱访 (实际 == 0)
    OVER_SERVICED = "OVER_SERVICED"        # 超频过度拜访 (实际 > 规定)


class IncidentSeverity(str, Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    CRITICAL_INCIDENT = "CRITICAL_INCIDENT" # Key/REQUIRED 门店脱访或严重欠访


@dataclass(frozen=True)
class StoreCadenceAuditResult:
    store_code: str
    store_name: str
    tier: str
    ka_name: str
    district: str
    planned_frequency: int
    actual_visits_count: int
    frequency_gap: int                      # actual - planned
    status: ComplianceStatus
    visit_dates: list[str] = field(default_factory=list)
    severity: IncidentSeverity = IncidentSeverity.NONE
    violation_message: Optional[str] = None


@dataclass
class RepPeriodCadenceReport:
    rep_id: str
    period_label: str
    total_assigned_stores: int
    total_planned_visits: int
    total_actual_visits: int
    exact_compliant_count: int
    under_serviced_count: int
    zero_visited_count: int
    over_serviced_count: int
    compliance_rate: float                 # exact_compliant / total_assigned
    critical_incidents: list[StoreCadenceAuditResult] = field(default_factory=list)
    store_results: list[StoreCadenceAuditResult] = field(default_factory=list)


class CadenceComplianceAuditor:
    """Production-grade Cadence Compliance Auditor for Sales Visit Decision Engine."""

    @staticmethod
    def audit_rep_period(
        rep_id: str,
        period_label: str,
        assigned_stores: Dict[str, Dict[str, Any]],
        execution_records: List[Dict[str, Any]]
    ) -> RepPeriodCadenceReport:
        """
        Audit a sales rep's actual visit executions against their full assigned store universe.
        
        :param rep_id: ID/name of the sales representative
        :param period_label: e.g. "2026-06"
        :param assigned_stores: Dict of all stores assigned to this rep (Customer Universe)
               { store_code: { 'name': str, 'tier': str, 'planned_freq': int, 'ka': str, 'district': str } }
        :param execution_records: Raw list of execution rows for this rep in this period
        """
        # 1. Aggregate actual visits per store
        actual_visits_counter = Counter()
        visit_dates_map = defaultdict(list)
        
        for rec in execution_records:
            code = rec.get("store_code") or rec.get("主数据_门店编码")
            d_val = rec.get("date") or rec.get("拜访日期")
            d_str = str(d_val)[:10] if d_val else ""
            if code:
                actual_visits_counter[code] += 1
                if d_str and d_str not in visit_dates_map[code]:
                    visit_dates_map[code].append(d_str)

        # 2. Iterate over FULL CUSTOMER UNIVERSE (Iron Rule 1)
        store_results: List[StoreCadenceAuditResult] = []
        critical_incidents: List[StoreCadenceAuditResult] = []
        
        exact_cnt = 0
        under_cnt = 0
        zero_cnt = 0
        over_cnt = 0
        tot_planned = 0
        tot_actual = sum(actual_visits_counter.values())

        for code, info in assigned_stores.items():
            st_name = info.get("name") or info.get("store_name", "UNKNOWN")
            tier = info.get("tier") or "STANDARD"
            ka = info.get("ka") or info.get("ka_name", "UNKNOWN")
            dist = info.get("district", "UNKNOWN")
            planned_f = int(info.get("planned_freq", info.get("planned_frequency", 0)))
            tot_planned += planned_f
            
            actual_cnt = actual_visits_counter.get(code, 0)
            gap = actual_cnt - planned_f
            dates = sorted(visit_dates_map.get(code, []))

            # Determine compliance status
            if actual_cnt == planned_f:
                status = ComplianceStatus.EXACT_COMPLIANT
                exact_cnt += 1
                sev = IncidentSeverity.NONE
                msg = None
            elif actual_cnt == 0:
                status = ComplianceStatus.ZERO_VISITED
                zero_cnt += 1
                if tier in ["Key", "STRATEGIC", "A", "CORE"] or planned_f >= 3:
                    sev = IncidentSeverity.CRITICAL_INCIDENT
                    msg = f"CRITICAL: Key/High-frequency store completely missed for entire period! (Planned: {planned_f}, Actual: 0)"
                else:
                    sev = IncidentSeverity.WARNING
                    msg = f"WARNING: Store zero-visited (Planned: {planned_f})"
            elif actual_cnt < planned_f:
                status = ComplianceStatus.UNDER_SERVICED
                under_cnt += 1
                if tier in ["Key", "STRATEGIC"] and gap <= -2:
                    sev = IncidentSeverity.CRITICAL_INCIDENT
                    msg = f"CRITICAL: Key store severely under-serviced! (Planned: {planned_f}, Actual: {actual_cnt})"
                else:
                    sev = IncidentSeverity.WARNING
                    msg = f"WARNING: Store under-serviced (Planned: {planned_f}, Actual: {actual_cnt})"
            else:
                status = ComplianceStatus.OVER_SERVICED
                over_cnt += 1
                sev = IncidentSeverity.WARNING
                msg = f"NOTE: Store over-serviced (Planned: {planned_f}, Actual: {actual_cnt}, +{gap})"

            res = StoreCadenceAuditResult(
                store_code=code,
                store_name=st_name,
                tier=tier,
                ka_name=ka,
                district=dist,
                planned_frequency=planned_f,
                actual_visits_count=actual_cnt,
                frequency_gap=gap,
                status=status,
                visit_dates=dates,
                severity=sev,
                violation_message=msg
            )
            store_results.append(res)
            if sev == IncidentSeverity.CRITICAL_INCIDENT:
                critical_incidents.append(res)

        total_stores = len(assigned_stores)
        comp_rate = (exact_cnt / total_stores * 100.0) if total_stores > 0 else 0.0

        return RepPeriodCadenceReport(
            rep_id=rep_id,
            period_label=period_label,
            total_assigned_stores=total_stores,
            total_planned_visits=tot_planned,
            total_actual_visits=tot_actual,
            exact_compliant_count=exact_cnt,
            under_serviced_count=under_cnt,
            zero_visited_count=zero_cnt,
            over_serviced_count=over_cnt,
            compliance_rate=comp_rate,
            critical_incidents=critical_incidents,
            store_results=store_results
        )
