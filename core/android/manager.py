from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent
from core.lifecycle.models import ComponentHealth
from core.logging import Logger

from .contracts import AndroidRegistry, AndroidRuntime
from .events import AndroidRuntimeStarted, AndroidRuntimeStopped
from .health import AndroidHealthTracker
from .models import AndroidRuntimeStatus


class AndroidRuntimeManager(AndroidRuntime, LifecycleComponent):
    """
    Lifecycle orchestrator for the Android Runtime subsystem.
    """

    def __init__(
        self,
        registry: AndroidRegistry,
        health_tracker: AndroidHealthTracker,
        event_bus: EventBus,
        logger: Logger,
        capabilities: list = None,
    ):
        self._registry = registry
        self._health_tracker = health_tracker
        self._event_bus = event_bus
        self._logger = logger
        self._capabilities = capabilities or []
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self._logger.info("Starting Android Runtime Manager.")
        await self._health_tracker.update_status(AndroidRuntimeStatus.INITIALIZING, "Starting up...")

        # In the future, capability discovery/loading might happen here
        from .exceptions import AndroidCapabilityRegistrationError
        for cap in self._capabilities:
            try:
                await self._registry.register(cap)
            except AndroidCapabilityRegistrationError as e:
                # Log and gracefully continue (e.g. for legacy duplicate aliases)
                self._logger.warning(f"Skipping registration for duplicate capability: {e}")
            except Exception as e:
                self._logger.error(f"Failed to register capability: {e}")

        self._started = True
        await self._health_tracker.update_status(AndroidRuntimeStatus.RUNNING, "Started successfully.")

        await self._event_bus.publish(
            AndroidRuntimeStarted(
                payload={},
                source="AndroidRuntimeManager"
            )
        )

    async def shutdown(self) -> None:
        if not self._started:
            return

        self._logger.info("Shutting down Android Runtime Manager.")
        self._started = False
        await self._health_tracker.update_status(AndroidRuntimeStatus.STOPPED, "Shut down successfully.")

        await self._event_bus.publish(
            AndroidRuntimeStopped(
                payload={},
                source="AndroidRuntimeManager"
            )
        )

    async def health_check(self) -> ComponentHealth:
        """Delegates to the health tracker for a lightweight, deterministic check."""
        return await self._health_tracker.health_check()
