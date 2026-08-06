"""
Comprehensive regression tests for the Android Runtime subsystem (Milestone 11).
Covers: lifecycle, registry, adapter, health, events, DI, public API, import safety.
"""
import inspect
import pytest

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.lifecycle.states import ComponentState
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.interfaces import CapabilityRegistry as ToolCapabilityRegistry
from core.runtime.models import CapabilityMetadata, ExecutionContext, ExecutionRequest

from core.android.contracts import AndroidAdapter, AndroidCapability, AndroidRegistry, AndroidRuntime
from core.android.models import AndroidRuntimeStatus, CapabilityDescriptor, CapabilityState, SecurityLevel
from core.android.events import (
    AndroidCapabilityRegistered,
    AndroidCapabilityRemoved,
    AndroidHealthChanged,
    AndroidRuntimeStarted,
    AndroidRuntimeStopped,
)
from core.android.exceptions import AndroidAdapterError, AndroidCapabilityRegistrationError, AndroidRuntimeError
from core.android.adapter import DefaultAndroidAdapter
from core.android.registry import InMemoryAndroidRegistry
from core.android.health import AndroidHealthTracker
from core.android.manager import AndroidRuntimeManager
from core.android.android_module import AndroidModule
from core.runtime.registry import InMemoryCapabilityRegistry
from core.runtime.runtime_module import RuntimeModule


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


class ConcreteAndroidCapability(AndroidCapability):
    """Minimal concrete capability for testing."""

    def __init__(self, cap_id: str = "test-cap", should_fail: bool = False):
        self._descriptor = CapabilityDescriptor(
            id=cap_id,
            name=f"Test {cap_id}",
            description="Test capability",
            version="1.0", security_level=SecurityLevel.LOW,
        )
        self._should_fail = should_fail

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return self._descriptor

    async def check_state(self) -> CapabilityState:
        return CapabilityState.AVAILABLE

    async def execute_action(self, arguments):
        if self._should_fail:
            raise RuntimeError("Intentional failure")
        return {"result": "ok", "args": dict(arguments)}


async def build_container() -> Container:
    container = Container()
    event_bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])

    container.register_instance(ContainerProtocol, container)
    container.register_instance(EventBus, event_bus)
    container.register_instance(LoggerFactory, logger_factory)

    container.install(RuntimeModule())
    container.install(AndroidModule())
    return container


async def make_registry(container: Container) -> InMemoryAndroidRegistry:
    event_bus = await container.resolve(EventBus)
    tool_registry = await container.resolve(ToolCapabilityRegistry)
    return InMemoryAndroidRegistry(event_bus, tool_registry)


# ─────────────────────────────────────────────
# Import Safety — no forbidden deps
# ─────────────────────────────────────────────

def test_import_safety_no_brain():
    import core.android
    import core.android.contracts
    import core.android.manager
    import core.android.registry
    import core.android.health
    import core.android.adapter
    import core.android.events
    import core.android.models
    import core.android.exceptions
    import core.android.android_module
    # No exception means import chain is clean

def test_no_forbidden_imports_in_android_package():
    import importlib, sys
    forbidden = ["core.brain", "core.planner", "core.memory", "core.identity"]
    android_modules = [k for k in sys.modules.keys() if k.startswith("core.android")]

    for mod_name in android_modules:
        mod = sys.modules[mod_name]
        mod_file = getattr(mod, "__file__", None)
        if mod_file and mod_file.endswith(".py"):
            src = open(mod_file).read()
            for f in forbidden:
                assert f not in src, f"Forbidden import '{f}' found in {mod_name}"


# ─────────────────────────────────────────────
# Contract Verification
# ─────────────────────────────────────────────

def test_android_runtime_contract_is_abstract():
    assert inspect.isabstract(AndroidRuntime), \
        "AndroidRuntime must be abstract (isabstract must return True)"

def test_android_capability_contract_is_abstract():
    assert inspect.isabstract(AndroidCapability)

def test_android_registry_contract_is_abstract():
    assert inspect.isabstract(AndroidRegistry)

def test_android_adapter_contract_is_abstract():
    assert inspect.isabstract(AndroidAdapter)

def test_android_runtime_abstract_methods():
    abstract = {
        name for name, method in inspect.getmembers(AndroidRuntime)
        if getattr(method, "__isabstractmethod__", False)
    }
    assert "start" in abstract
    assert "shutdown" in abstract
    assert "health_check" in abstract

def test_android_runtime_manager_satisfies_contract():
    assert issubclass(AndroidRuntimeManager, AndroidRuntime)
    # Must not itself be abstract — must implement all methods
    assert not inspect.isabstract(AndroidRuntimeManager)


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

def test_capability_descriptor_is_immutable():
    d = CapabilityDescriptor(id="id", name="n", description="d", version="1", security_level=SecurityLevel.LOW)
    with pytest.raises((AttributeError, TypeError)):
        d.id = "changed"  # type: ignore

def test_android_runtime_status_enum_values():
    assert AndroidRuntimeStatus.STOPPED.value == "STOPPED"
    assert AndroidRuntimeStatus.RUNNING.value == "RUNNING"
    assert AndroidRuntimeStatus.INITIALIZING.value == "INITIALIZING"
    assert AndroidRuntimeStatus.DEGRADED.value == "DEGRADED"

def test_capability_state_enum_values():
    assert CapabilityState.AVAILABLE.value == "AVAILABLE"
    assert CapabilityState.UNAVAILABLE.value == "UNAVAILABLE"
    assert CapabilityState.PERMISSION_DENIED.value == "PERMISSION_DENIED"


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────

def test_events_are_frozen_dataclasses():
    for cls in [
        AndroidRuntimeStarted, AndroidRuntimeStopped,
        AndroidCapabilityRegistered, AndroidCapabilityRemoved,
        AndroidHealthChanged,
    ]:
        assert hasattr(cls, "__dataclass_params__")
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"

def test_events_inherit_from_event():
    for cls in [
        AndroidRuntimeStarted, AndroidRuntimeStopped,
        AndroidCapabilityRegistered, AndroidCapabilityRemoved,
        AndroidHealthChanged,
    ]:
        assert issubclass(cls, Event), f"{cls.__name__} must inherit from Event"


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

def test_exception_hierarchy():
    assert issubclass(AndroidAdapterError, AndroidRuntimeError)
    assert issubclass(AndroidCapabilityRegistrationError, AndroidRuntimeError)
    assert issubclass(AndroidRuntimeError, Exception)


# ─────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_registry_register_and_lookup():
    container = await build_container()
    registry = await make_registry(container)
    cap = ConcreteAndroidCapability("cap-1")
    await registry.register(cap)
    result = registry.lookup("cap-1")
    assert result is cap

@pytest.mark.anyio
async def test_registry_duplicate_raises():
    container = await build_container()
    registry = await make_registry(container)
    cap = ConcreteAndroidCapability("cap-dup")
    await registry.register(cap)
    with pytest.raises(AndroidCapabilityRegistrationError):
        await registry.register(cap)

@pytest.mark.anyio
async def test_registry_unregister():
    container = await build_container()
    registry = await make_registry(container)
    cap = ConcreteAndroidCapability("cap-rm")
    await registry.register(cap)
    await registry.unregister("cap-rm")
    with pytest.raises(AndroidCapabilityRegistrationError):
        registry.lookup("cap-rm")

@pytest.mark.anyio
async def test_registry_unknown_lookup_raises():
    container = await build_container()
    registry = await make_registry(container)
    with pytest.raises(AndroidCapabilityRegistrationError):
        registry.lookup("nonexistent")

@pytest.mark.anyio
async def test_registry_unknown_unregister_raises():
    container = await build_container()
    registry = await make_registry(container)
    with pytest.raises(AndroidCapabilityRegistrationError):
        await registry.unregister("nonexistent")

@pytest.mark.anyio
async def test_registry_get_all():
    container = await build_container()
    registry = await make_registry(container)
    cap1 = ConcreteAndroidCapability("cap-a")
    cap2 = ConcreteAndroidCapability("cap-b")
    await registry.register(cap1)
    await registry.register(cap2)
    all_caps = registry.get_all()
    assert len(all_caps) == 2
    assert cap1 in all_caps
    assert cap2 in all_caps

@pytest.mark.anyio
async def test_registry_never_executes():
    """Registry must only manage registration — never execute capabilities."""
    container = await build_container()
    registry = await make_registry(container)
    # Confirm no execute() or execute_action() method on the registry
    assert not hasattr(InMemoryAndroidRegistry, "execute")
    assert not hasattr(InMemoryAndroidRegistry, "execute_action")

@pytest.mark.anyio
async def test_registry_publishes_capability_registered_event():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidCapabilityRegistered):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await registry.register(ConcreteAndroidCapability("cap-ev"))
    assert len(events) == 1
    assert events[0].capability_id == "cap-ev"

@pytest.mark.anyio
async def test_registry_publishes_capability_removed_event():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)

    await registry.register(ConcreteAndroidCapability("cap-rm-ev"))

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidCapabilityRemoved):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await registry.unregister("cap-rm-ev")
    assert len(events) == 1
    assert events[0].capability_id == "cap-rm-ev"


# ─────────────────────────────────────────────
# Adapter
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_adapter_translates_metadata():
    cap = ConcreteAndroidCapability("adapter-cap")
    adapter = DefaultAndroidAdapter(cap)
    assert adapter.metadata.id == "adapter-cap"
    assert adapter.metadata.name == "Test adapter-cap"

@pytest.mark.anyio
async def test_adapter_executes_action():
    cap = ConcreteAndroidCapability("adapter-ok")
    adapter = DefaultAndroidAdapter(cap)
    req = ExecutionRequest(execution_id="ex-1", capability_id="adapter-ok", arguments={"x": 1})
    ctx = ExecutionContext(request=req, capability_metadata=adapter.metadata)
    result = await adapter.execute(ctx)
    assert result == {"result": "ok", "args": {"x": 1}}

@pytest.mark.anyio
async def test_adapter_normalizes_exception():
    cap = ConcreteAndroidCapability("adapter-fail", should_fail=True)
    adapter = DefaultAndroidAdapter(cap)
    req = ExecutionRequest(execution_id="ex-fail", capability_id="adapter-fail")
    ctx = ExecutionContext(request=req, capability_metadata=adapter.metadata)
    with pytest.raises(AndroidAdapterError):
        await adapter.execute(ctx)

@pytest.mark.anyio
async def test_adapter_exposes_tool_runtime_capability_interface():
    from core.runtime.interfaces import Capability
    cap = ConcreteAndroidCapability("iface-test")
    adapter = DefaultAndroidAdapter(cap)
    assert isinstance(adapter, Capability)

@pytest.mark.anyio
async def test_adapter_get_android_capability():
    cap = ConcreteAndroidCapability("get-cap")
    adapter = DefaultAndroidAdapter(cap)
    assert adapter.get_android_capability() is cap


# ─────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_stopped_when_not_started():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)
    tracker = AndroidHealthTracker(event_bus, registry)
    health = await tracker.health_check()
    assert health.state == ComponentState.STOPPED

@pytest.mark.anyio
async def test_health_running_after_start():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)
    tracker = AndroidHealthTracker(event_bus, registry)
    await tracker.update_status(AndroidRuntimeStatus.RUNNING, "started")
    health = await tracker.health_check()
    assert health.state == ComponentState.RUNNING

@pytest.mark.anyio
async def test_health_reflects_capability_count():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)
    await registry.register(ConcreteAndroidCapability("h-cap"))
    tracker = AndroidHealthTracker(event_bus, registry)
    await tracker.update_status(AndroidRuntimeStatus.RUNNING, "started")
    health = await tracker.health_check()
    assert "1 capabilities" in health.details

@pytest.mark.anyio
async def test_health_changed_event_published():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)
    tracker = AndroidHealthTracker(event_bus, registry)

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidHealthChanged):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await tracker.update_status(AndroidRuntimeStatus.RUNNING, "up")
    assert len(events) == 1
    assert events[0].previous_status == AndroidRuntimeStatus.STOPPED
    assert events[0].current_status == AndroidRuntimeStatus.RUNNING

@pytest.mark.anyio
async def test_health_no_duplicate_event_on_same_status():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    registry = await make_registry(container)
    tracker = AndroidHealthTracker(event_bus, registry)

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidHealthChanged):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await tracker.update_status(AndroidRuntimeStatus.STOPPED, "still stopped")
    assert len(events) == 0  # no change, no event


# ─────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_manager_start_and_shutdown():
    container = await build_container()
    manager = await container.resolve(AndroidRuntime)
    await manager.start()
    health = await manager.health_check()
    assert health.state == ComponentState.RUNNING
    await manager.shutdown()
    health2 = await manager.health_check()
    assert health2.state == ComponentState.STOPPED

@pytest.mark.anyio
async def test_manager_start_is_idempotent():
    container = await build_container()
    manager = await container.resolve(AndroidRuntime)
    await manager.start()
    await manager.start()  # must not raise or double-publish
    health = await manager.health_check()
    assert health.state == ComponentState.RUNNING

@pytest.mark.anyio
async def test_manager_shutdown_is_idempotent():
    container = await build_container()
    manager = await container.resolve(AndroidRuntime)
    await manager.start()
    await manager.shutdown()
    await manager.shutdown()  # must not raise
    health = await manager.health_check()
    assert health.state == ComponentState.STOPPED

@pytest.mark.anyio
async def test_manager_health_check_stopped_before_start():
    container = await build_container()
    manager = await container.resolve(AndroidRuntime)
    health = await manager.health_check()
    assert health.state == ComponentState.STOPPED

@pytest.mark.anyio
async def test_manager_publishes_started_event():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    manager = await container.resolve(AndroidRuntime)

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidRuntimeStarted):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await manager.start()
    assert len(events) == 1

@pytest.mark.anyio
async def test_manager_publishes_stopped_event():
    container = await build_container()
    event_bus = await container.resolve(EventBus)
    manager = await container.resolve(AndroidRuntime)

    events = []
    async def capture(event: Event):
        if isinstance(event, AndroidRuntimeStopped):
            events.append(event)
    event_bus.subscribe(Event, capture)

    await manager.start()
    await manager.shutdown()
    assert len(events) == 1


# ─────────────────────────────────────────────
# Dependency Injection
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_di_resolves_android_runtime():
    container = await build_container()
    manager = await container.resolve(AndroidRuntime)
    assert isinstance(manager, AndroidRuntime)

@pytest.mark.anyio
async def test_di_resolves_android_registry():
    container = await build_container()
    registry = await container.resolve(AndroidRegistry)
    assert isinstance(registry, AndroidRegistry)

@pytest.mark.anyio
async def test_di_resolves_android_health_tracker():
    container = await build_container()
    tracker = await container.resolve(AndroidHealthTracker)
    assert isinstance(tracker, AndroidHealthTracker)

@pytest.mark.anyio
async def test_di_singletons_are_same_instance():
    container = await build_container()
    r1 = await container.resolve(AndroidRuntime)
    r2 = await container.resolve(AndroidRuntime)
    assert r1 is r2

@pytest.mark.anyio
async def test_di_registry_singleton_shared_with_manager():
    container = await build_container()
    registry = await container.resolve(AndroidRegistry)
    cap = ConcreteAndroidCapability("shared-cap")
    await registry.register(cap)

    # The same registry should be visible across resolutions
    registry2 = await container.resolve(AndroidRegistry)
    assert registry2.lookup("shared-cap") is cap


# ─────────────────────────────────────────────
# Public API Surface
# ─────────────────────────────────────────────

def test_public_api_exposes_contracts():
    import core.android as android_pkg
    for sym in ["AndroidCapability", "AndroidRegistry", "AndroidAdapter", "AndroidRuntime", "AndroidModule"]:
        assert sym in android_pkg.__all__, f"{sym} missing from __all__"

def test_public_api_exposes_models_and_events():
    import core.android as android_pkg
    for sym in ["CapabilityDescriptor", "AndroidRuntimeStatus", "CapabilityState",
                "AndroidDeviceInfo", "AndroidRuntimeStarted", "AndroidRuntimeStopped",
                "AndroidCapabilityRegistered", "AndroidCapabilityRemoved", "AndroidHealthChanged"]:
        assert sym in android_pkg.__all__, f"{sym} missing from __all__"

def test_public_api_does_not_expose_implementations():
    import core.android as android_pkg
    for sym in ["AndroidRuntimeManager", "DefaultAndroidAdapter", "InMemoryAndroidRegistry"]:
        assert sym not in android_pkg.__all__, f"Concrete class {sym} must not be in __all__"

def test_capabilities_package_exports_all_interfaces():
    from core.android import capabilities
    expected = [
        "CallCapability", "SmsCapability", "AlarmCapability", "CalendarCapability",
        "NotificationCapability", "CameraCapability", "ContactsCapability", "FilesCapability",
        "MediaCapability", "LocationCapability", "BluetoothCapability", "WifiCapability",
        "ApplicationCapability", "ClipboardCapability", "BatteryCapability", "DeviceCapability",
    ]
    for cls_name in expected:
        assert cls_name in capabilities.__all__, f"{cls_name} missing from capabilities.__all__"
        assert hasattr(capabilities, cls_name), f"{cls_name} not importable from capabilities"
