"""Memory Engine exceptions."""

class MemoryError(Exception):
    """Base exception for the Memory Engine."""

class MemoryNotFound(MemoryError):
    """Raised when a memory record cannot be found."""

class DuplicateMemory(MemoryError):
    """Raised when adding a memory record with an existing id."""

class MemoryValidationError(MemoryError):
    """Raised when a memory record violates validation rules."""

class SearchError(MemoryError):
    """Raised when a search query cannot be executed."""
