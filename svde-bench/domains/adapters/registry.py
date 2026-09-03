"""Domain Adapter Registry for SVDE-Bench v0.5."""
from typing import Dict, Any, Optional
from domains.adapters.base_adapter import BaseDomainAdapter
from domains.adapters.delivery_adapter import DeliveryDomainAdapter
from domains.adapters.visit_adapter import VisitDomainAdapter


class DomainAdapterRegistry:
    """Registry managing domain-specific adapters for seamless canonical translation."""
    def __init__(self):
        self._adapters: Dict[str, BaseDomainAdapter] = {
            "delivery": DeliveryDomainAdapter(),
            "visit": VisitDomainAdapter(),
        }

    def register_adapter(self, adapter: BaseDomainAdapter):
        self._adapters[adapter.domain_name] = adapter

    def get_adapter(self, domain_name: str) -> BaseDomainAdapter:
        adapter = self._adapters.get(domain_name.lower())
        if not adapter:
            # Default fallback to delivery adapter if domain unknown
            return self._adapters["delivery"]
        return adapter


# Global singleton
ADAPTER_REGISTRY = DomainAdapterRegistry()
