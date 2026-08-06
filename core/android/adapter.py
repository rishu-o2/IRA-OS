from typing import Any
from core.runtime.interfaces import Capability
from core.runtime.models import CapabilityMetadata, ExecutionContext
from .contracts import AndroidAdapter, AndroidCapability
from .exceptions import AndroidAdapterError


class DefaultAndroidAdapter(AndroidAdapter):
    """
    Translates Tool Runtime ExecutionContext into AndroidCapability arguments.
    Bridging layer between the two subsystems.
    """

    def __init__(self, android_capability: AndroidCapability):
        self._android_capability = android_capability
        descriptor = android_capability.descriptor
        self._metadata = CapabilityMetadata(
            id=descriptor.id,
            name=descriptor.name,
            description=descriptor.description,
            version=descriptor.version,
        )

    def get_android_capability(self) -> AndroidCapability:
        return self._android_capability

    @property
    def metadata(self) -> CapabilityMetadata:
        return self._metadata

    async def execute(self, context: ExecutionContext) -> Any:
        # In the future, this might check CapabilityState before executing
        try:
            return await self._android_capability.execute_action(context.request.arguments)
        except Exception as exc:
            raise AndroidAdapterError(f"Adapter failed to execute Android capability: {exc}") from exc
