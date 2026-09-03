"""Task 1 E2E: 单条命令跑完 Case → Profile 四维画像"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from svdebench.core import load_case_yaml
from svdebench.agents.baseline import PureSolverMockAgent, SemanticAwareAgent, FullDecisionAgent
from svdebench.oracle.cpsat import CPSATExactOracle
from svdebench.runner.pipeline import run_case_pipeline

BENCH = Path(__file__).resolve().parents[2]

def test_e2e_full_pipeline_golden_case_001():
    case_path = BENCH / "svdebench/datasets/public/cases/CASE-001-DELIVERY-RECOVERY.yaml"
    case = load_case_yaml(str(case_path))
    
    oracle_ref = CPSATExactOracle().solve(case)
    assert oracle_ref.solver_status == 'OPTIMAL'
    
    profiles = {}
    for AgentCls in [PureSolverMockAgent, SemanticAwareAgent, FullDecisionAgent]:
        report = run_case_pipeline(case, AgentCls())
        prof = report['evaluation_profile']
        mem = prof.get('memory') or {}
        profiles[AgentCls.__name__] = {
            'semantic': prof['semantic']['overall_pass'],
            'feasibility': prof['feasibility']['feasibility_status'],
            'commitment_survival': prof['runtime']['commitment_survival_rate'],
            'memory': (mem.get('promotion_status') if isinstance(mem, dict) else None) if mem else None
        }
    
    for name, p in profiles.items():
        assert p['semantic'] is not None
        assert p['feasibility'] is not None
        assert p['commitment_survival'] is not None
        # Memory: PureSolverMockAgent 设计上不产生 memory_patch (None 是正确行为)
        if name != 'PureSolverMockAgent':
            assert p['memory'] is not None
    
    # 验证 Decision Feasibility vs Solution Feasibility 区分度
    assert profiles['PureSolverMockAgent']['semantic'] == False
    assert profiles['PureSolverMockAgent']['commitment_survival'] == 0.0
    assert profiles['SemanticAwareAgent']['commitment_survival'] == 1.0
    assert profiles['SemanticAwareAgent']['semantic'] == True

def test_e2e_pipeline_emits_valid_profile_json():
    profile_path = BENCH / "reports/profiles/CASE-001-DELIVERY-RECOVERY.json"
    data = json.loads(profile_path.read_text())
    for k in ['case_id', 'domain', 'oracle', 'agents']:
        assert k in data, f"Missing key: {k}"
    assert data['oracle']['status'] in ['OPTIMAL', 'FEASIBLE', 'INFEASIBLE']

def test_e2e_full_10_cases_pipeline():
    summary = json.loads((BENCH / "reports/profiles/SUMMARY.json").read_text())
    assert summary['total_cases'] == 10
    assert summary['summary_metrics']['oracle_optimal_count'] == 10
