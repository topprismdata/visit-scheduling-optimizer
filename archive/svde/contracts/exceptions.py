"""SVDE Core Exceptions."""

class SVDEError(Exception):
    """Base exception for all SVDE Core errors."""
    pass


class UnsupportedDomainError(SVDEError):
    """Raised when a DecisionRequest specifies an un-registered domain."""
    pass


class UnsupportedCapabilityError(SVDEError):
    """Raised when DecisionPlanner cannot find a registered capability to fulfill DecisionSpec."""
    pass


class CompilationError(SVDEError):
    """Raised when compiling a DecisionRequest into DecisionSpec fails."""
    pass
