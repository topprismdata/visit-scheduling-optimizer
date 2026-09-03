"""Phase 0 Unit Tests — Governance 7-State Lifecycle."""
import pytest
from prism_ontology.governance.lifecycle import (
    LifecycleState,
    LifecycleManager,
    InvalidTransitionError,
    ALLOWED_TRANSITIONS
)


def test_valid_lifecycle_forward_chain():
    mgr = LifecycleManager()
    state = LifecycleState.EXTRACTED
    
    state = mgr.transition(state, LifecycleState.EVIDENCE_PENDING)
    assert state == LifecycleState.EVIDENCE_PENDING
    
    state = mgr.transition(state, LifecycleState.CANDIDATE)
    assert state == LifecycleState.CANDIDATE
    
    state = mgr.transition(state, LifecycleState.DOMAIN_REVIEW)
    assert state == LifecycleState.DOMAIN_REVIEW
    
    state = mgr.transition(state, LifecycleState.BUSINESS_APPROVED)
    assert state == LifecycleState.BUSINESS_APPROVED
    
    state = mgr.transition(state, LifecycleState.FROZEN)
    assert state == LifecycleState.FROZEN
    assert mgr.is_frozen(state) is True


def test_illegal_lifecycle_skip():
    mgr = LifecycleManager()
    # Cannot jump from EXTRACTED to BUSINESS_APPROVED directly
    with pytest.raises(InvalidTransitionError):
        mgr.transition(LifecycleState.EXTRACTED, LifecycleState.BUSINESS_APPROVED)


def test_illegal_lifecycle_regression():
    mgr = LifecycleManager()
    # Cannot regress from FROZEN back to CANDIDATE
    with pytest.raises(InvalidTransitionError):
        mgr.transition(LifecycleState.FROZEN, LifecycleState.CANDIDATE)


def test_deprecation_and_retirement():
    mgr = LifecycleManager()
    state = LifecycleState.FROZEN
    
    state = mgr.transition(state, LifecycleState.DEPRECATED)
    assert state == LifecycleState.DEPRECATED
    
    state = mgr.transition(state, LifecycleState.RETIRED)
    assert state == LifecycleState.RETIRED
    assert mgr.is_terminal(state) is True
