class MutationError(Exception):
    """Base exception for the Mutation Lifecycle Framework."""
    pass


class ConfirmationRequired(MutationError):
    """Raised when a mutation cannot proceed without explicit confirmation."""
    pass


class MutationRejectedError(MutationError):
    """Raised when a mutation is explicitly rejected (e.g., user denied, policy rejected)."""
    pass


class RollbackError(MutationError):
    """Raised when a rollback operation fails."""
    pass


class AuditError(MutationError):
    """Raised when writing an audit record fails for a required-audit mutation."""
    pass
