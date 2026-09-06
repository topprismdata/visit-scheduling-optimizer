"""WorldState Contract Adapter Layer (DTO & Backward-Compatibility).

Re-exports the Canonical OperationalDecisionWorldState from world_model.state_snapshot
as the single source of truth for the entire codebase.
"""
from prism_ontology.world_model.state_snapshot import (
    CognitiveCategory, FulfillmentClass, GeoQualityStatus, ChannelTier,
    InStoreActionType, LifecycleStatus, BitemporalPeriod, GeoCoordinate,
    DerivedDepotEstimate, AccountHierarchyEntity, ProductLineScopeEntity,
    SupplyNodeEntity, InStoreActionFact, MerchandisingComplianceFact,
    OperationalCustomer, CustomerEntity, OperationalResource, ResourceEntity,
    CadenceRule, OperationalVisitPolicy, OperationalCommitment,
    OwnershipConflictRecord, PolicyRegistry, OperationalVisitLifecycleRecord,
    ActualVisitEvent, SourceManifest, OperationalDecisionWorldState,
    WorldState, WorldStateSnapshot
)

__all__ = [
    "CognitiveCategory", "FulfillmentClass", "GeoQualityStatus", "ChannelTier",
    "InStoreActionType", "LifecycleStatus", "BitemporalPeriod", "GeoCoordinate",
    "DerivedDepotEstimate", "AccountHierarchyEntity", "ProductLineScopeEntity",
    "SupplyNodeEntity", "InStoreActionFact", "MerchandisingComplianceFact",
    "OperationalCustomer", "CustomerEntity", "OperationalResource", "ResourceEntity",
    "CadenceRule", "OperationalVisitPolicy", "OperationalCommitment",
    "OwnershipConflictRecord", "PolicyRegistry", "OperationalVisitLifecycleRecord",
    "ActualVisitEvent", "SourceManifest", "OperationalDecisionWorldState",
    "WorldState", "WorldStateSnapshot"
]
