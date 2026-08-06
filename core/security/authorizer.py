from .contracts import PermissionAuthorizer
from .models import PermissionDecision, PermissionResult, PermissionState


class DefaultPermissionAuthorizer(PermissionAuthorizer):
    """
    Converts a PermissionDecision into a final, immutable PermissionResult.
    Applies no additional logic — faithfully reflects the policy decision.
    """

    def __init__(self) -> None:
        pass

    def authorize(self, decision: PermissionDecision) -> PermissionResult:
        granted = decision.state == PermissionState.GRANTED

        return PermissionResult(
            permission_id=decision.permission_id,
            capability_id=decision.capability_id,
            granted=granted,
            state=decision.state,
            denial_reason=decision.denial_reason,
        )
