from __future__ import annotations

from typing import Optional

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
    ):
        self._pipeline = pipeline
        self._logger = logger
        self._event_bus = event_bus
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
        if self._pipeline is None:
            return ComponentHealth(state=ComponentState.FAILED, details="Brain pipeline is unavailable.")
        if not self._pipeline.stages:
            return ComponentHealth(state=ComponentState.FAILED, details="Brain pipeline has no stages.")
        if not self._started:
            return ComponentHealth(state=ComponentState.STOPPED, details="Brain is stopped.")
        return ComponentHealth(state=ComponentState.RUNNING, details="Brain is available.")

    async def process_request(self, request: BrainRequest) -> BrainResult:
        self._logger.info("Brain request received.", request_id=request.request_id, user_id=request.user_id)
        await self._publish_started(request)

        try:
            result = await self._pipeline.execute(request)
            self._logger.info("Brain request completed.", request_id=request.request_id)
            await self._publish_completed(request, result)
            return result
        except BrainError as exc:
            return await self._fail(request, "Brain request processing failed.", exc)
        except Exception as exc:
            return await self._fail(request, "Brain request processing failed.", exc)

    async def _publish_started(self, request: BrainRequest) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            BrainRequestStarted(
                payload={"request_id": request.request_id, "user_id": request.user_id},
                source="BrainManager",
                request_id=request.request_id,
                user_id=request.user_id,
            )
        )

    async def _publish_completed(self, request: BrainRequest, result: BrainResult) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            BrainRequestCompleted(
                payload={"request_id": request.request_id, "success": result.success},
                source="BrainManager",
                request_id=request.request_id,
                success=result.success,
            )
        )

    async def _fail(self, request: BrainRequest, public_message: str, exc: BaseException) -> BrainResult:
        self._logger.error(public_message, exception=exc, request_id=request.request_id)
        if self._event_bus is not None:
            await self._event_bus.publish(
                BrainRequestFailed(
                    payload={"request_id": request.request_id, "error": public_message},
                    source="BrainManager",
                    request_id=request.request_id,
                    error=public_message,
                )
            )
        return BrainResult(success=False, error=public_message, request_id=request.request_id)
