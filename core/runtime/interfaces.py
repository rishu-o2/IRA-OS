from abc import ABC, abstractmethod
from typing import Any, Tuple

from .models import CapabilityMetadata, ExecutionContext, ExecutionRequest


class Capability(ABC):
    """Abstract interface for a registered platform capability."""

    @property
    @abstractmethod
    def metadata(self) -> CapabilityMetadata:
        """Returns the immutable metadata for this capability."""
        pass

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Executes the capability given the execution context."""
        pass


class CapabilityRegistry(ABC):
    """Abstract registry for discovering and managing capabilities."""

    @abstractmethod
    async def register(self, capability: Capability) -> None:
        """Registers a capability."""
        pass

    @abstractmethod
    async def unregister(self, capability_id: str) -> None:
        """Unregisters a capability by ID."""
        pass

    @abstractmethod
    def lookup(self, capability_id: str) -> Capability:
        """Looks up a capability by ID."""
        pass

    @abstractmethod
    def get_all(self) -> Tuple[Capability, ...]:
        """Returns all registered capabilities."""
        pass


class Dispatcher(ABC):
    """Abstract dispatcher for routing requests."""

    @abstractmethod
    def dispatch(self, request: ExecutionRequest, registry: CapabilityRegistry) -> Capability:
        """Determines the appropriate capability for the request."""
        pass


class Executor(ABC):
    """Abstract executor for invoking capabilities."""

    @abstractmethod
    async def execute(self, capability: Capability, context: ExecutionContext) -> Any:
        """Invokes the capability and handles normalization of its result."""
        pass


class Validator(ABC):
    """Abstract validator for execution requests."""

    @abstractmethod
    def validate_request(self, request: ExecutionRequest) -> None:
        """Validates the execution request shape and semantics."""
        pass

    @abstractmethod
    def validate_arguments(self, capability: Capability, request: ExecutionRequest) -> None:
        """Validates the request arguments against the capability's requirements."""
        pass
