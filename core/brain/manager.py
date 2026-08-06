from __future__ import annotations

from typing import Any, Optional

from core.events import EventBus
from core.lifecycle.interfaces import HealthCheckable, LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.lifecycle.states import ComponentState
from core.logging import Logger

from .events import BrainRequestCompleted, BrainRequestFailed, BrainRequestStarted
from .exceptions import BrainError
from .models import BrainRequest, BrainResult
from .pipeline import BrainPipeline


class BrainManager(LifecycleComponent, HealthCheckable):
    """Stateless Brain facade and lifecycle boundary."""

    def __init__(
        self,
        pipeline: BrainPipeline,
        logger: Logger,
        event_bus: Optional[EventBus] = None,
        identity_manager: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        planner_manager: Optional[Any] = None,
    ):
        self._pipeline = pipeline
        self._logger = logger
        self._event_bus = event_bus
        self._identity_manager = identity_manager
        self._memory_manager = memory_manager
        self._planner_manager = planner_manager
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._logger.info("BrainManager starting.")
        self._started = True

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._logger.info("BrainManager shutting down.")
        self._started = False

    async def health_check(self) -> ComponentHealth:
        if not self._started:
            return ComponentHealth(state=ComponentState.STOPPED, details="Brain is stopped.")

        missing = []
        if self._pipeline is None or not getattr(self._pipeline, "stages", None):
            missing.append("Pipeline")
        if self._identity_manager is None:
            missing.append("Identity")
        if self._memory_manager is None:
            missing.append("Memory")
        if self._planner_manager is None:
            missing.append("Planner")
        if self._event_bus is None:
            missing.append("Event Bus")

        if missing:
            return ComponentHealth(
                state=ComponentState.FAILED,
                details=f"Missing kernel dependencies: {', '.join(missing)}.",
            )

        return ComponentHealth(state=ComponentState.RUNNING, details="Brain is available.")

    def _get_request_id(self, request: Any) -> str:
        if isinstance(request, BrainRequest) and request.request_id:
            return request.request_id
        return getattr(request, "request_id", "unknown") or "unknown"

    def _get_user_id(self, request: Any) -> str:
        if isinstance(request, BrainRequest) and request.user_id:
            return request.user_id
        return getattr(request, "user_id", "unknown") or "unknown"

    async def process_request(self, request: Any) -> BrainResult:
        request_id = self._get_request_id(request)
        user_id = self._get_user_id(request)

        # Boundary validation happens before logging or pipeline execution
        if not isinstance(request, BrainRequest):
            return await self._fail(
                request_id=request_id,
                public_message="Invalid BrainRequest object.",
                exc=ValueError("Request is not a BrainRequest instance."),
            )

        self._logger.info("Brain request received.", request_id=request_id, user_id=user_id)
        await self._publish_started(request_id, user_id)

        try:
            result = await self._pipeline.execute(request)
            self._logger.info("Brain request completed.", request_id=request_id)
            await self._publish_completed(request_id, result)
            return result
        except BrainError as exc:
            return await self._fail(request_id, "Brain request processing failed.", exc)
        except Exception as exc:
            return await self._fail(request_id, "Brain request processing failed.", exc)

    async def _publish_started(self, request_id: str, user_id: str) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            BrainRequestStarted(
                payload={"request_id": request_id, "user_id": user_id},
                source="BrainManager",
                request_id=request_id,
                user_id=user_id,
            )
        )

    async def _publish_completed(self, request_id: str, result: BrainResult) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            BrainRequestCompleted(
                payload={"request_id": request_id, "success": result.success},
                source="BrainManager",
                request_id=request_id,
                success=result.success,
            )
        )

    async def _fail(self, request_id: str, public_message: str, exc: BaseException) -> BrainResult:
        self._logger.error(public_message, exception=exc, request_id=request_id)
        if self._event_bus is not None:
            await self._event_bus.publish(
                BrainRequestFailed(
                    payload={"request_id": request_id, "error": public_message},
                    source="BrainManager",
                    request_id=request_id,
                    error=public_message,
                )
            )
        return BrainResult(success=False, error=public_message, request_id=request_id)
