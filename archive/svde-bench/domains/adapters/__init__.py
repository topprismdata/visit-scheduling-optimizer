"""domains.adapters package."""
from domains.adapters.base_adapter import BaseDomainAdapter
from domains.adapters.delivery_adapter import DeliveryDomainAdapter
from domains.adapters.visit_adapter import VisitDomainAdapter
from domains.adapters.registry import DomainAdapterRegistry, ADAPTER_REGISTRY

__all__ = [
    "BaseDomainAdapter",
    "DeliveryDomainAdapter",
    "VisitDomainAdapter",
    "DomainAdapterRegistry",
    "ADAPTER_REGISTRY",
]
