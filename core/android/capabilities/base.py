from abc import abstractmethod
from typing import Any, Mapping

from core.android.contracts import AndroidCapability
from core.android.models import CapabilityDescriptor, CapabilityState

from .exceptions import InvalidArgumentError, PlatformExecutionError
from .models import CapabilityResult


class BaseAndroidCapability(AndroidCapability):
    """
    Shared foundation for all Android capabilities.
    Validates arguments and catches raw exceptions.
    Subclasses manage their own bridge dependencies.
    """

    async def check_state(self) -> CapabilityState:
        return CapabilityState.AVAILABLE

    async def execute_action(self, arguments: Mapping[str, Any]) -> CapabilityResult:
        try:
            # 1. Standard Validation
            action = arguments.get("action", "default")
            
            if action not in self.descriptor.supported_actions and action != "default":
                raise InvalidArgumentError(f"Action '{action}' is not supported by {self.descriptor.id}.")

            # 2. Subclass Execution
            result_data = await self._execute_internal(action, arguments)
            
            # 3. Standardized Result
            return CapabilityResult(
                capability_id=self.descriptor.id,
                success=True,
                data=result_data
            )
            
        except Exception as e:
            from .exceptions import CapabilityError
            if isinstance(e, CapabilityError):
                error_cls = e.__class__.__name__
                error_msg = str(e)
            else:
                error_cls = "PlatformExecutionError"
                error_msg = f"Unhandled platform exception: {str(e)}"
                
            return CapabilityResult(
                capability_id=self.descriptor.id,
                success=False,
                error_code=error_cls,
                error_message=error_msg
            )

    @abstractmethod
    async def _execute_internal(self, action: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Implemented by subclasses to perform the actual bridge call.
        """
        pass
