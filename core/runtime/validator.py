from .exceptions import ValidationError
from .interfaces import Capability, Validator
from .models import ExecutionRequest


class RuntimeValidator(Validator):
    """Validates execution requests and capability arguments."""

    def __init__(self) -> None:
        pass

    def validate_request(self, request: ExecutionRequest) -> None:
        if not request:
            raise ValidationError("ExecutionRequest cannot be None.")
        if not getattr(request, "execution_id", None):
            raise ValidationError("ExecutionRequest.execution_id must be provided.")
        if not getattr(request, "capability_id", None):
            raise ValidationError("ExecutionRequest.capability_id must be provided.")
        if not isinstance(request.arguments, dict):
            raise ValidationError("ExecutionRequest.arguments must be a mapping.")

    def validate_arguments(self, capability: Capability, request: ExecutionRequest) -> None:
        # In the future, this can use JSON Schema or Pydantic to validate args.
        pass
