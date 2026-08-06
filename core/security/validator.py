from .contracts import PermissionValidator
from .exceptions import PermissionValidationError
from .models import PermissionRequest


class DefaultPermissionValidator(PermissionValidator):
    """
    Validates the shape and semantics of a PermissionRequest before pipeline execution.
    Does not perform policy evaluation.
    """

    def __init__(self) -> None:
        pass

    def validate(self, request: PermissionRequest) -> None:
        if not request:
            raise PermissionValidationError("PermissionRequest cannot be None.")
        if not isinstance(request, PermissionRequest):
            raise PermissionValidationError("Request must be a PermissionRequest instance.")
        if not getattr(request, "permission_id", None):
            raise PermissionValidationError("PermissionRequest.permission_id must be provided.")
        if not getattr(request, "capability_id", None):
            raise PermissionValidationError("PermissionRequest.capability_id must be provided.")
        if request.context is None:
            raise PermissionValidationError("PermissionRequest.context must be provided.")
