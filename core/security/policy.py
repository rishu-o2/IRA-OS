from typing import Dict, Optional

from .contracts import PolicyEvaluator
from .events import PolicyLoaded
from .exceptions import PolicyEvaluationError, PolicyNotFoundError
from .models import (
    PermissionDecision,
    PermissionPolicy,
    PermissionRequest,
    PermissionState,
    PermissionRequirement,
    TrustLevel,
)


class DefaultPolicyEvaluator(PolicyEvaluator):
    """
    In-memory policy evaluator scaffold.

    Loads policies and evaluates PermissionRequests against them.
    Does NOT implement real policy logic — scaffolded for Milestone 12.2.

    Default behavior: GRANT all requests unless a policy explicitly
    demands user approval or a higher trust level than the context provides.
    """

    def __init__(self) -> None:
        self._policies: Dict[str, PermissionPolicy] = {}

    def load_policy(self, policy: PermissionPolicy) -> None:
        if not policy or not policy.policy_id:
            raise PolicyEvaluationError("Policy must have a valid policy_id.")
        self._policies[policy.policy_id] = policy

    def evaluate(self, request: PermissionRequest) -> PermissionDecision:
        # Find applicable requirement for this capability
        requirement = self._find_requirement(request.capability_id)

        # Default: grant if no policy constrains this capability
        if requirement is None:
            return PermissionDecision(
                permission_id=request.permission_id,
                capability_id=request.capability_id,
                state=PermissionState.GRANTED,
                trust_level=request.context.trust_level,
                requires_user_approval=False,
            )

        # Evaluate trust level sufficiency
        if not self._trust_sufficient(request.context.trust_level, requirement.required_trust_level):
            return PermissionDecision(
                permission_id=request.permission_id,
                capability_id=request.capability_id,
                state=PermissionState.DENIED,
                trust_level=request.context.trust_level,
                denial_reason=(
                    f"Insufficient trust level. Required: {requirement.required_trust_level.value}, "
                    f"provided: {request.context.trust_level.value}."
                ),
            )

        # Evaluate user approval requirement
        if requirement.requires_user_approval:
            return PermissionDecision(
                permission_id=request.permission_id,
                capability_id=request.capability_id,
                state=PermissionState.REQUIRES_APPROVAL,
                trust_level=request.context.trust_level,
                requires_user_approval=True,
            )

        return PermissionDecision(
            permission_id=request.permission_id,
            capability_id=request.capability_id,
            state=PermissionState.GRANTED,
            trust_level=request.context.trust_level,
        )

    def _find_requirement(self, capability_id: str) -> Optional[PermissionRequirement]:
        for policy in self._policies.values():
            for req in policy.requirements:
                if req.capability_id == capability_id:
                    return req
        return None

    @staticmethod
    def _trust_sufficient(provided: TrustLevel, required: TrustLevel) -> bool:
        order = [
            TrustLevel.UNTRUSTED,
            TrustLevel.LOW,
            TrustLevel.MEDIUM,
            TrustLevel.HIGH,
            TrustLevel.CRITICAL,
        ]
        return order.index(provided) >= order.index(required)
