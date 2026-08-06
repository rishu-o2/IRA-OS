from typing import Any

from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState
from core.logging import Logger

from .contracts import PermissionAuthorizer, PermissionManager, PolicyEvaluator, PermissionValidator
from .events import (
    PermissionDenied,
    PermissionGranted,
    PermissionRequested,
    PolicyEvaluationCompleted,
)
from .exceptions import SecurityError, PermissionValidationError
from .models import (
    PermissionRequest,
    PermissionResult,
    PermissionState,
)


class SecurityManager(PermissionManager, LifecycleComponent):
    """
    Orchestrates the canonical Permission Kernel pipeline:

    1. Validate Request
    2. Load Applicable Policies
    3. Evaluate Policy
    4. Determine Trust Requirement
    5. Authorize / Enforce Denial
    6. Publish Security Event
    7. Permission Result
    """

    def __init__(
        self,
        validator: PermissionValidator,
        policy_evaluator: PolicyEvaluator,
        authorizer: PermissionAuthorizer,
        event_bus: EventBus,
        logger: Logger,
    ):
        self._validator = validator
        self._policy_evaluator = policy_evaluator
        self._authorizer = authorizer
        self._event_bus = event_bus
        self._logger = logger
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._logger.info("SecurityManager starting.")
        self._started = True

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._logger.info("SecurityManager shutting down.")
        self._started = False

    async def health_check(self) -> ComponentHealth:
        if not self._started:
            return ComponentHealth(state=ComponentState.STOPPED, details="Security kernel is stopped.")

        missing = []
        if self._validator is None:
            missing.append("Validator")
        if self._policy_evaluator is None:
            missing.append("PolicyEvaluator")
        if self._authorizer is None:
            missing.append("Authorizer")
        if self._event_bus is None:
            missing.append("EventBus")

        if missing:
            return ComponentHealth(
                state=ComponentState.DEGRADED,
                details=f"Security kernel missing dependencies: {', '.join(missing)}.",
            )

        return ComponentHealth(state=ComponentState.RUNNING, details="Security kernel is available.")

    async def check_permission(self, request: Any) -> PermissionResult:
        """
        Canonical permission pipeline:
        1. Validate Request
        2. Publish PermissionRequested
        3. Evaluate Policy
        4. Publish PolicyEvaluationCompleted
        5. Authorize
        6. Publish PermissionGranted / PermissionDenied
        7. Return PermissionResult
        """
        perm_id = getattr(request, "permission_id", "unknown")

        try:
            # 1. Validate
            if not isinstance(request, PermissionRequest):
                raise PermissionValidationError("Request is not a PermissionRequest.")
            self._validator.validate(request)

            # 2. Publish PermissionRequested
            await self._event_bus.publish(
                PermissionRequested(
                    payload={"permission_id": request.permission_id},
                    source="SecurityManager",
                    permission_id=request.permission_id,
                    capability_id=request.capability_id,
                )
            )

            # 3. Evaluate Policy
            decision = self._policy_evaluator.evaluate(request)

            # 4. Publish PolicyEvaluationCompleted
            await self._event_bus.publish(
                PolicyEvaluationCompleted(
                    payload={"permission_id": request.permission_id, "state": decision.state.value},
                    source="SecurityManager",
                    permission_id=request.permission_id,
                    capability_id=request.capability_id,
                    state=decision.state,
                )
            )

            # 5. Authorize
            result = self._authorizer.authorize(decision)

            # 6. Publish outcome event
            if result.granted:
                await self._event_bus.publish(
                    PermissionGranted(
                        payload={"permission_id": result.permission_id},
                        source="SecurityManager",
                        permission_id=result.permission_id,
                        capability_id=result.capability_id,
                        trust_level=decision.trust_level,
                    )
                )
            else:
                await self._event_bus.publish(
                    PermissionDenied(
                        payload={"permission_id": result.permission_id, "reason": result.denial_reason or ""},
                        source="SecurityManager",
                        permission_id=result.permission_id,
                        capability_id=result.capability_id,
                        denial_reason=result.denial_reason or "Permission denied.",
                    )
                )

            # 7. Return result
            return result

        except SecurityError as exc:
            return await self._deny(perm_id, getattr(request, "capability_id", "unknown"), str(exc))
        except Exception:
            return await self._deny(perm_id, getattr(request, "capability_id", "unknown"), "Permission check failed.")

    async def _deny(self, permission_id: str, capability_id: str, reason: str) -> PermissionResult:
        self._logger.error(reason, permission_id=permission_id)
        await self._event_bus.publish(
            PermissionDenied(
                payload={"permission_id": permission_id, "reason": reason},
                source="SecurityManager",
                permission_id=permission_id,
                capability_id=capability_id,
                denial_reason=reason,
            )
        )
        return PermissionResult(
            permission_id=permission_id,
            capability_id=capability_id,
            granted=False,
            state=PermissionState.DENIED,
            denial_reason=reason,
        )
