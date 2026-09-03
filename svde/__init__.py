"""SVDE Core Decision Engine Entrypoint.

Gap 1 Fix: Automatically runs DataPrecheckValidator on incoming DecisionRequest.
Fails closed with CompilationError if precheck discovers fatal data errors.
"""
from typing import Optional, List, Dict, Any
from svde.contracts import DecisionRequest, DecisionArtifact, CompilationError
from svde.compiler import DecisionCompiler
from svde.planning import DecisionPlanner
from svde.runtime import RuntimeOrchestrator
from svde.verification import DecisionAuditor
from svde.verification.data_precheck import DataPrecheckValidator
from svde.memory import MemoryStore


class DecisionEngine:
    """SVDE Core Decision Engine orchestrating precheck -> compile -> plan -> execute -> audit."""
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        self.memory_store = memory_store or MemoryStore()
        self.precheck_validator = DataPrecheckValidator()
        self.compiler = DecisionCompiler()
        self.planner = DecisionPlanner()
        self.orchestrator = RuntimeOrchestrator()
        self.auditor = DecisionAuditor()

    def _retrieve_governed_principles(self, context) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Retrieves and matches governed principles at Runtime based on declarative boundary checks."""
        promoted = self.memory_store.get_promoted_principles()
        activated = []
        rejected = []

        for p in promoted:
            # Declarative boundary evaluation
            if "zero_locked_commitments" in p.invalidation_boundaries and not context.has_hard_commitments:
                rejected.append({"id": p.principle_id, "name": p.name, "reason": "zero_locked_commitments boundary verified"})
                continue
            if "homogeneous_general_cargo" in p.invalidation_boundaries and not context.has_competency_constraints:
                rejected.append({"id": p.principle_id, "name": p.name, "reason": "homogeneous_general_cargo boundary verified"})
                continue

            is_triggered = False
            if p.principle_id == "CORE-PRIN-001" and context.has_hard_commitments:
                is_triggered = True
            elif p.principle_id == "CORE-PRIN-002" and context.has_competency_constraints:
                is_triggered = True
            elif p.principle_id == "CORE-PRIN-003" and context.has_resource_failure:
                is_triggered = True

            if is_triggered:
                activated.append(p.to_dict())
            else:
                rejected.append({"id": p.principle_id, "name": p.name, "reason": "Trigger conditions not met"})

        activated.sort(key=lambda x: x.get("precedence_tier", 1), reverse=True)
        return activated, rejected

    def decide(
        self,
        request: DecisionRequest,
        preferred_capability: Optional[str] = None,
        skip_precheck: bool = False
    ) -> DecisionArtifact:
        # 1. Pre-flight Data Validation (Gap 1 Fix: Automated Precheck Ingestion)
        if not skip_precheck:
            report = self.precheck_validator.validate(request)
            if not report.is_valid:
                error_msgs = [f"{e.field}: {e.message}" for e in report.errors]
                raise CompilationError(f"Pre-flight data validation failed with {len(report.errors)} errors: {'; '.join(error_msgs)}")

        # 2. Compile Request -> DecisionSpec (Pure semantic mapping, zero memory coupling)
        spec = self.compiler.compile(request)

        # 3. Retrieve Governed Principles in Runtime Layer
        activated_principles, rejected_principles = self._retrieve_governed_principles(spec.context)
        spec.governing_principles = activated_principles

        # 4. Plan & Route by structural capability requirement (Strict fail-closed)
        plan = self.planner.plan(spec, preferred_capability=preferred_capability)

        # 5. Execute Plan via Capability Adapter (Forwards principles to solver/engine)
        raw_result = self.orchestrator.execute(spec, plan)

        # 6. Audit & Verify Output with segregated evidence
        artifact = self.auditor.audit(spec, raw_result)
        artifact.rejected_principles = rejected_principles
        artifact.evidence.rejected_principles = rejected_principles

        return artifact


_GLOBAL_ENGINE = DecisionEngine()


def decide(
    request: DecisionRequest,
    preferred_capability: Optional[str] = None,
    skip_precheck: bool = False
) -> DecisionArtifact:
    return _GLOBAL_ENGINE.decide(request, preferred_capability=preferred_capability, skip_precheck=skip_precheck)


__all__ = [
    "DecisionEngine",
    "decide",
    "DecisionRequest",
    "DecisionArtifact",
]
