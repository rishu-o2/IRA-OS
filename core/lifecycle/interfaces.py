from typing import Protocol, runtime_checkable
from .models import ComponentHealth


@runtime_checkable
class Bootable(Protocol):
    async def before_boot(self) -> None: ...
    async def boot(self) -> None: ...
    async def after_boot(self) -> None: ...


@runtime_checkable
class Startable(Protocol):
    async def before_start(self) -> None: ...
    async def start(self) -> None: ...
    async def after_start(self) -> None: ...


@runtime_checkable
class Stoppable(Protocol):
    async def before_stop(self) -> None: ...
    async def stop(self) -> None: ...
    async def after_stop(self) -> None: ...


@runtime_checkable
class DisposableComponent(Protocol):
    async def before_shutdown(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def after_shutdown(self) -> None: ...


@runtime_checkable
class Restartable(Protocol):
    async def restart(self) -> None: ...


@runtime_checkable
class HealthCheckable(Protocol):
    async def health_check(self) -> ComponentHealth: ...


class LifecycleComponent(
    Bootable,
    Startable,
    Stoppable,
    DisposableComponent,
    Restartable,
    HealthCheckable,
    Protocol
):
    """
    A comprehensive protocol combining all lifecycle hooks.
    Most components will implement a subset of these interfaces.
    """
    pass
