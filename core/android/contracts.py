from abc import ABC, abstractmethod
from typing import Any, Mapping, Tuple
from core.runtime.interfaces import Capability
from core.lifecycle.models import ComponentHealth
from .models import CapabilityDescriptor, CapabilityState


class AndroidCapability(ABC):
    """
    Abstract contract for a platform-specific Android Capability.
    Does not depend on the Tool Runtime's ExecutionContext directly.
    """

    @property
    @abstractmethod
    def descriptor(self) -> CapabilityDescriptor:
        """Returns the immutable descriptor for this capability."""
        pass

    @abstractmethod
    async def check_state(self) -> CapabilityState:
        """Returns the current availability state of this capability."""
        pass

    @abstractmethod
    async def execute_action(self, arguments: Mapping[str, Any]) -> Any:
        """Executes the Android-specific action with the provided arguments."""
        pass


class AndroidAdapter(Capability):
    """
    Translates Tool Runtime Capability requests into Android Capability calls.
    Implements core.runtime.interfaces.Capability.
    """
    @abstractmethod
    def get_android_capability(self) -> AndroidCapability:
        pass


class AndroidRegistry(ABC):
    """
    Abstract contract for discovering, registering, and querying Android Capabilities.
    Never executes them.
    """

    @abstractmethod
    async def register(self, capability: AndroidCapability) -> None:
        pass

    @abstractmethod
    async def unregister(self, capability_id: str) -> None:
        pass

    @abstractmethod
    def lookup(self, capability_id: str) -> AndroidCapability:
        pass

    @abstractmethod
    def get_all(self) -> Tuple[AndroidCapability, ...]:
        pass


class AndroidRuntime(ABC):
    """
    Abstract contract for the Android Runtime Manager.
    Integrates with the lifecycle and orchestrates the Android subsystem components.

    Any implementation must provide start, shutdown, and health_check.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start the Android Runtime. Must be idempotent."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the Android Runtime. Must be idempotent."""
        pass

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Return the current health state of the Android Runtime."""
        pass
