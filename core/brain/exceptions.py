class BrainError(Exception):
    """Base exception for Brain errors."""


class BrainValidationError(BrainError):
    """Raised when a Brain request or model is invalid."""


class BrainIdentityResolutionError(BrainError):
    """Raised when Identity cannot resolve the request identity."""


class BrainMemoryError(BrainError):
    """Raised when Memory cannot provide request context."""


class BrainPlannerError(BrainError):
    """Raised when Planner cannot produce a plan for the request."""


class BrainDecisionError(BrainError):
    """Raised when the Brain cannot produce a decision."""


class BrainProcessingError(BrainError):
    """Raised when Brain request processing fails."""
