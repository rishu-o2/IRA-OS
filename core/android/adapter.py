from typing import Any
from core.runtime.interfaces import Capability
from core.runtime.models import CapabilityMetadata, ExecutionContext
from .contracts import AndroidAdapter, AndroidCapability
from .exceptions import AndroidAdapterError


from core.mutation.contracts import MutatingCapability
from core.mutation.models import MutationMetadata

class DefaultAndroidAdapter(AndroidAdapter, MutatingCapability):
    """
    Translates Tool Runtime ExecutionContext into AndroidCapability calls.
    Bridging layer between the two subsystems.
    Implements MutatingCapability to naturally integrate with Mutation Framework.
    """

    def __init__(self, android_capability: AndroidCapability):
        self._android_capability = android_capability
        descriptor = android_capability.descriptor
        
        mutation_meta = None
        if getattr(descriptor, 'is_mutation', False):
            from core.mutation.models import ConfirmationLevel as MutConfirm
            conf_level = getattr(descriptor, 'confirmation_level', None)
            if conf_level:
                conf_level = MutConfirm(conf_level.value)
            else:
                conf_level = MutConfirm.NONE
                
            mutation_meta = MutationMetadata(
                is_destructive=False,
                supports_rollback=getattr(descriptor, 'supports_rollback', False),
                audit_required=getattr(descriptor, 'audit_required', False),
                confirmation_level=conf_level,
                idempotent=getattr(descriptor, 'idempotent', False)
            )

        self._metadata = CapabilityMetadata(
            id=descriptor.id,
            name=descriptor.name,
            description=descriptor.description,
            version=descriptor.version,
            mutation=mutation_meta
        )

    def get_android_capability(self) -> AndroidCapability:
        return self._android_capability

    @property
    def metadata(self) -> CapabilityMetadata:
        return self._metadata

    async def execute(self, context: ExecutionContext) -> Any:
        try:
            return await self._android_capability.execute_action(context.request.arguments)
        except Exception as exc:
            raise AndroidAdapterError(f"Adapter failed to execute Android capability: {exc}") from exc

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        if hasattr(self._android_capability, "supports_rollback"):
            return self._android_capability.supports_rollback(arguments)
        return False

    async def rollback(self, arguments: Mapping[str, Any], original_result: Any) -> None:
        if hasattr(self._android_capability, "rollback"):
            await self._android_capability.rollback(arguments, original_result)
        else:
            raise NotImplementedError("Underlying capability does not support rollback")
