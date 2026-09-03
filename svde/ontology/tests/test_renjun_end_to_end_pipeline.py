"""Phase 6 Tests: Renjun June Human-in-the-Loop Decision Pipeline.

Verifies:
1. End-to-End HITL Flow:
   Raw Data -> WorldState -> Rep-Specific PlanningIntent -> Candidate Plan & Audit Report
   -> Explicit Human Sign-off -> DecisionArtifact
2. Human authorization is strictly enforced before DecisionArtifact is published
3. Published schedule strictly contains all 83 visits across 36 stores
4. NT23 (人民中路, Key store) visited exactly 4 times with strict cadence
"""
from datetime import datetime as _asm_dt, timezone as _asm_tz
_ASSEMBLED_AT = _asm_dt(2026, 8, 1, tzinfo=_asm_tz.utc)  # 测试固定确定性组装时刻 (tz-aware)
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "svde" / "ontology" / "src"))
sys.path.insert(0, str(ROOT))

from prism_ontology.real_data.world_state_assembler import WorldStateAssembler
from prism_ontology.contracts.planning_io import (
    PlanningIntent, PlanningCapabilityType, DecisionArtifact, CandidatePlan, PlanAuditReport
)
from prism_ontology.engine.decision_pipeline import DecisionPipelineRunner

DATA_FILE = ROOT / "ontology" / "tests" / "data" / "fmcg_visit_history_with_geo.xlsx"


def test_renjun_june_hitl_pipeline_success():
    if not DATA_FILE.exists():
        pytest.skip(f"Data file missing: {DATA_FILE}")
        
    # 1. Assemble WorldState from raw Excel
    world_state = WorldStateAssembler.assemble_from_excel(DATA_FILE, assembled_at=_ASSEMBLED_AT)
    assert len(world_state.customer_universe) == 246
    assert "仁军" in world_state.resources
    
    # 2. Formulate Renjun's Context-Specific PlanningIntent
    intent = PlanningIntent(
        intent_id="INT_RENJUN_JUNE_2026_HITL",
        capability_type=PlanningCapabilityType.PERIODIC_VISIT_PLANNING,
        target_rep_id="仁军",
        target_horizon_label="2026-06",
        working_days=tuple(f"2026-06-{d:02d}" for d in range(1, 27) if d not in [6, 7, 13, 14, 20, 21]),
        max_daily_stops=6,
        max_daily_workload_min=480.0,
        same_weekday_required=True
    )
    
    # 3. Generate Candidate Plan and Independent 3D Audit Report
    candidate_plan, audit_report = DecisionPipelineRunner.generate_candidate_and_audit(
        world_state=world_state,
        intent=intent
    )
    
    assert candidate_plan.total_scheduled_visits == 83
    assert audit_report.cadence_compliance_rate == 100.0
    
    # 4. Attempt to publish without approver must FAIL (HITL safety guard)
    with pytest.raises(ValueError, match="Explicit human approver_id is required"):
        DecisionPipelineRunner.human_approve_and_publish(
            candidate_plan=candidate_plan,
            audit_report=audit_report,
            approver_id=""
        )
        
    # 5. Explicit Human Sign-off by Project Director
    artifact: DecisionArtifact = DecisionPipelineRunner.human_approve_and_publish(
        candidate_plan=candidate_plan,
        audit_report=audit_report,
        approver_id="PROJECT_DIRECTOR_GHB",
        approval_notes="Approved with long-distance tolerance for Haian/Rudong days."
    )
    
    assert artifact.status == "APPROVED_FOR_EXECUTION"
    assert artifact.approved_by == "PROJECT_DIRECTOR_GHB"
    assert "DECISION_ART_仁军_2026-06" in artifact.artifact_id
    
    # Verify all 83 visits are in published schedule
    tot_visits = sum(len(codes) for codes in artifact.published_schedule.values())
    assert tot_visits == 83
    
    # Verify Key store NT23 (00006798) is in schedule exactly 4 times
    nt23_count = sum(codes.count("00006798") for codes in artifact.published_schedule.values())
    assert nt23_count == 4
