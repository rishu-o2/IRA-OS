from typing import List, Dict, Optional, Any
from .registry import ComponentRegistry
from .health import HealthMonitor
from .orchestrator import LifecycleOrchestrator
from .models import ComponentRegistration, ComponentHealth, StartupReport, ShutdownReport
from .states import ComponentState


class LifecycleManager:
    """
    The public facade for the Lifecycle Management subsystem.
    Delegates component registration to the Registry, health tracking to the
    HealthMonitor, and execution logic to the Orchestrator.
    """
    def __init__(self):
        self._registry = ComponentRegistry()
        self._health = HealthMonitor()
        self._orchestrator = LifecycleOrchestrator(self._registry, self._health)

    def register(
        self,
        name: str,
        instance: Any,
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
        enabled: bool = True,
        critical: bool = True,
        startup_timeout: Optional[float] = None,
        shutdown_timeout: Optional[float] = None
    ) -> None:
        """
        Registers a new lifecycle component.
        """
        registration = ComponentRegistration(
            name=name,
            instance=instance,
            dependencies=dependencies or [],
            priority=priority,
            enabled=enabled,
            critical=critical,
            startup_timeout=startup_timeout,
            shutdown_timeout=shutdown_timeout
        )
        self._registry.register(registration)
        self._health.created(name)

    def remove(self, name: str) -> None:
        """Removes a component from the registry."""
        self._registry.remove(name)

    def update(self, name: str, **kwargs) -> None:
        """Updates metadata of an existing registration."""
        self._registry.update(name, **kwargs)

    def get_health(self, name: str) -> Optional[ComponentHealth]:
        """Gets the health snapshot for a specific component."""
        return self._health.get_health(name)

    def get_all_health(self) -> Dict[str, ComponentHealth]:
        """Gets health snapshots for all components."""
        return self._health.get_all_health()

    def state(self, name: str) -> Optional[ComponentState]:
        """Convenience method to get just the state enum for a component."""
        health = self.get_health(name)
        return health.state if health else None

    async def boot(self) -> StartupReport:
        """Executes the boot phase for all components."""
        return await self._orchestrator.boot()

    async def start(self) -> StartupReport:
        """Executes the start phase for all components."""
        return await self._orchestrator.start()

    async def stop(self) -> ShutdownReport:
        """Executes the stop phase for all components in reverse order."""
        return await self._orchestrator.stop()

    async def shutdown(self) -> ShutdownReport:
        """Executes the shutdown phase for all components in reverse order."""
        return await self._orchestrator.shutdown()

    async def restart(self) -> bool:
        """Restarts the system by stopping and then starting."""
        return await self._orchestrator.restart()
