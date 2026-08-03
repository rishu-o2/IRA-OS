import pytest
import asyncio
from typing import List
from core.lifecycle import (
    LifecycleManager,
    ComponentRegistration,
    Bootstrap,
    LifecycleError,
    StartupError,
    ShutdownError,
    RegistrationError,
    ComponentState
)

@pytest.fixture
def anyio_backend():
    return 'asyncio'

# Test dummies
class DummyComponent:
    def __init__(self):
        self.log = []

    async def before_boot(self): self.log.append("before_boot")
    async def boot(self): self.log.append("boot")
    async def after_boot(self): self.log.append("after_boot")
    
    async def before_start(self): self.log.append("before_start")
    async def start(self): self.log.append("start")
    async def after_start(self): self.log.append("after_start")
    
    async def before_stop(self): self.log.append("before_stop")
    async def stop(self): self.log.append("stop")
    async def after_stop(self): self.log.append("after_stop")
    
    async def before_shutdown(self): self.log.append("before_shutdown")
    async def shutdown(self): self.log.append("shutdown")
    async def after_shutdown(self): self.log.append("after_shutdown")


class FailingComponent(DummyComponent):
    async def start(self):
        self.log.append("start_failed")
        raise ValueError("Failed to start")


class SlowComponent(DummyComponent):
    async def start(self):
        await asyncio.sleep(0.5)
        self.log.append("start")


@pytest.fixture
def manager():
    return LifecycleManager()


# ─── Registration Tests ───────────────────────────────────────────────

def test_registration(manager: LifecycleManager):
    comp = DummyComponent()
    manager.register("Comp1", comp, priority=1)
    
    assert manager._registry.contains("Comp1")
    assert manager.state("Comp1") == ComponentState.CREATED

def test_duplicate_registration(manager: LifecycleManager):
    comp = DummyComponent()
    manager.register("Comp1", comp)
    with pytest.raises(RegistrationError):
        manager.register("Comp1", comp)

def test_update_registration(manager: LifecycleManager):
    comp = DummyComponent()
    manager.register("Comp1", comp, priority=1)
    manager.update("Comp1", priority=10, enabled=False)
    
    reg = manager._registry.get("Comp1")
    assert reg.priority == 10
    assert reg.enabled is False
    
def test_update_missing_field(manager: LifecycleManager):
    comp = DummyComponent()
    manager.register("Comp1", comp)
    with pytest.raises(RegistrationError):
        manager.update("Comp1", unknown_field=True)


# ─── Orchestration Order Tests ────────────────────────────────────────

@pytest.mark.anyio
async def test_dependency_ordering(manager: LifecycleManager):
    c1 = DummyComponent()
    c2 = DummyComponent()
    c3 = DummyComponent()
    
    # C3 depends on C2 which depends on C1.
    # We register them in reverse order to ensure it sorts correctly.
    manager.register("C3", c3, dependencies=["C2"])
    manager.register("C2", c2, dependencies=["C1"])
    manager.register("C1", c1)
    
    report = await manager.start()
    assert report.success
    # Order should be C1 -> C2 -> C3
    assert report.started_components == ["C1", "C2", "C3"]

@pytest.mark.anyio
async def test_priority_ordering(manager: LifecycleManager):
    c1 = DummyComponent()
    c2 = DummyComponent()
    c3 = DummyComponent()
    
    # No dependencies, should order by priority
    manager.register("C3", c3, priority=3)
    manager.register("C1", c1, priority=1)
    manager.register("C2", c2, priority=2)
    
    report = await manager.start()
    assert report.success
    assert report.started_components == ["C1", "C2", "C3"]

@pytest.mark.anyio
async def test_circular_dependency(manager: LifecycleManager):
    c1 = DummyComponent()
    c2 = DummyComponent()
    
    manager.register("C1", c1, dependencies=["C2"])
    manager.register("C2", c2, dependencies=["C1"])
    
    report = await manager.start()
    assert not report.success
    assert "Circular dependency" in report.error_details

@pytest.mark.anyio
async def test_missing_dependency(manager: LifecycleManager):
    c1 = DummyComponent()
    manager.register("C1", c1, dependencies=["Unknown"])
    
    report = await manager.start()
    assert not report.success
    assert "depends on unknown component" in report.error_details


# ─── Execution Tests ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_lifecycle_hooks(manager: LifecycleManager):
    c1 = DummyComponent()
    manager.register("C1", c1)
    
    await manager.boot()
    assert c1.log == ["before_boot", "boot", "after_boot"]
    
    await manager.start()
    assert c1.log == ["before_boot", "boot", "after_boot", "before_start", "start", "after_start"]

    await manager.stop()
    assert c1.log == ["before_boot", "boot", "after_boot", "before_start", "start", "after_start", "before_stop", "stop", "after_stop"]

@pytest.mark.anyio
async def test_startup_failure_rollback(manager: LifecycleManager):
    c1 = DummyComponent()
    c2 = FailingComponent()
    c3 = DummyComponent()
    
    manager.register("C1", c1, priority=1)
    manager.register("C2", c2, priority=2)
    manager.register("C3", c3, priority=3)
    
    report = await manager.start()
    assert not report.success
    assert report.failed_component == "C2"
    
    # C1 should have started, then been stopped (rolled back)
    assert "start" in c1.log
    assert "stop" in c1.log
    
    # C2 should have tried to start and failed
    assert "start_failed" in c2.log
    
    # C3 should not have started at all
    assert len(c3.log) == 0

@pytest.mark.anyio
async def test_non_critical_failure(manager: LifecycleManager):
    c1 = FailingComponent()
    c2 = DummyComponent()
    
    manager.register("C1", c1, priority=1, critical=False)
    manager.register("C2", c2, priority=2)
    
    report = await manager.start()
    # It should still be considered a successful startup for the system
    assert report.success
    assert report.started_components == ["C2"]

@pytest.mark.anyio
async def test_startup_timeout(manager: LifecycleManager):
    c1 = SlowComponent()
    
    # 0.1s timeout, component takes 0.5s
    manager.register("C1", c1, startup_timeout=0.1)
    
    report = await manager.start()
    assert not report.success
    assert "timed out" in report.error_details

@pytest.mark.anyio
async def test_restart(manager: LifecycleManager):
    c1 = DummyComponent()
    manager.register("C1", c1)
    
    await manager.start()
    c1.log.clear() # Clear to track restart
    
    res = await manager.restart()
    assert res is True
    assert c1.log == ["before_stop", "stop", "after_stop", "before_start", "start", "after_start"]


# ─── Health Tests ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_updates(manager: LifecycleManager):
    c1 = DummyComponent()
    manager.register("C1", c1)
    
    assert manager.state("C1") == ComponentState.CREATED
    
    await manager.boot()
    assert manager.state("C1") == ComponentState.BOOTED
    
    await manager.start()
    assert manager.state("C1") == ComponentState.RUNNING
    
    await manager.stop()
    assert manager.state("C1") == ComponentState.STOPPED


# ─── Bootstrap Tests ──────────────────────────────────────────────────

def test_bootstrap():
    manager = Bootstrap.build()
    
    assert isinstance(manager, LifecycleManager)
    
    # Check that basic kernel components are registered
    assert manager._registry.contains("Configuration")
    assert manager._registry.contains("Logging")
    assert manager._registry.contains("Container")
    assert manager._registry.contains("EventBus")
    
    # Check dependencies
    log_reg = manager._registry.get("Logging")
    assert "Configuration" in log_reg.dependencies
