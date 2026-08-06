"""
Comprehensive tests for the Plugin Framework (Milestone 14).
"""
import inspect
import pytest

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.lifecycle.states import ComponentState
from core.logging import LoggerFactory
from core.logging.sinks import NullSink

from core.plugins.contracts import (
    PluginHealthTracker,
    PluginLoader,
    PluginManager,
    PluginRegistry,
    PluginValidator,
)
from core.plugins.events import (
    PluginDisabled,
    PluginDiscovered,
    PluginEnabled,
    PluginLoaded,
    PluginRegistered,
    PluginRemoved,
    PluginUnloaded,
    PluginValidationFailed,
)
from core.plugins.exceptions import (
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    PluginStateError,
    PluginValidationError,
)
from core.plugins.models import (
    PluginCapability,
    PluginContext,
    PluginDependency,
    PluginDescriptor,
    PluginManifest,
    PluginMetadata,
    PluginRequest,
    PluginResult,
    PluginState,
    PluginStatus,
    PluginType,
)
from core.plugins.health import DefaultPluginHealthTracker
from core.plugins.loader import DefaultPluginLoader
from core.plugins.manager import PluginManagerImpl
from core.plugins.registry import InMemoryPluginRegistry
from core.plugins.validator import DefaultPluginValidator
from core.plugins.plugin_module import PluginModule


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"

async def build_container() -> Container:
    container = Container()
    event_bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])

    container.register_instance(ContainerProtocol, container)
    container.register_instance(EventBus, event_bus)
    container.register_instance(LoggerFactory, logger_factory)

    container.install(PluginModule())
    return container


def make_valid_metadata(plugin_id="test.plugin") -> PluginMetadata:
    manifest = PluginManifest(
        id=plugin_id,
        name="Test",
        version="1.0",
        author="Test",
        description="Test desc",
        type=PluginType.LOCAL,
    )
    return PluginMetadata(manifest, "/path/to", "hash")


# ─────────────────────────────────────────────
# Import Safety
# ─────────────────────────────────────────────

def test_import_safety_no_forbidden():
    import sys
    import core.plugins
    import core.plugins.manager
    import core.plugins.loader
    import core.plugins.registry
    import core.plugins.validator
    
    forbidden = ["core.brain", "core.memory", "core.identity", "core.workflow", "core.runtime", "core.android"]
    plugin_modules = [k for k in sys.modules.keys() if k.startswith("core.plugins")]

    for mod_name in plugin_modules:
        mod = sys.modules[mod_name]
        mod_file = getattr(mod, "__file__", None)
        if mod_file and mod_file.endswith(".py"):
            with open(mod_file, encoding="utf-8") as f:
                src = f.read()
            for forb in forbidden:
                assert forb not in src, f"Forbidden import '{forb}' in {mod_name}"


# ─────────────────────────────────────────────
# Contracts
# ─────────────────────────────────────────────

def test_contracts_are_abstract():
    assert inspect.isabstract(PluginManager)
    assert inspect.isabstract(PluginLoader)
    assert inspect.isabstract(PluginRegistry)
    assert inspect.isabstract(PluginValidator)
    assert inspect.isabstract(PluginHealthTracker)


def test_contract_abstract_methods():
    def get_abstract_methods(cls):
        return {name for name, method in inspect.getmembers(cls)
                if getattr(method, "__isabstractmethod__", False)}

    assert "start" in get_abstract_methods(PluginManager)
    assert "discover" in get_abstract_methods(PluginManager)
    assert "enable" in get_abstract_methods(PluginManager)
    assert "discover" in get_abstract_methods(PluginLoader)
    assert "register" in get_abstract_methods(PluginRegistry)
    assert "validate" in get_abstract_methods(PluginValidator)
    assert "check_health" in get_abstract_methods(PluginHealthTracker)


# ─────────────────────────────────────────────
# Models & Enums
# ─────────────────────────────────────────────

def test_models_are_frozen():
    for cls in [
        PluginManifest, PluginMetadata, PluginDescriptor,
        PluginRequest, PluginResult, PluginDependency,
        PluginCapability, PluginContext
    ]:
        assert hasattr(cls, "__dataclass_params__")
        assert cls.__dataclass_params__.frozen

def test_enums():
    assert PluginState.DISCOVERED.value == "DISCOVERED"
    assert PluginType.BUILTIN.value == "BUILTIN"
    assert PluginStatus.HEALTHY.value == "HEALTHY"


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────

def test_events_inherit_event():
    for cls in [
        PluginDiscovered, PluginLoaded, PluginEnabled,
        PluginDisabled, PluginUnloaded, PluginRegistered,
        PluginRemoved, PluginValidationFailed
    ]:
        assert issubclass(cls, Event)
        assert getattr(cls, "__dataclass_params__").frozen


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

def test_exceptions():
    assert issubclass(PluginError, Exception)
    assert issubclass(PluginValidationError, PluginError)
    assert issubclass(PluginLoadError, PluginError)
    assert issubclass(PluginNotFoundError, PluginError)
    assert issubclass(PluginStateError, PluginError)


# ─────────────────────────────────────────────
# DI Wiring
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_di_wiring():
    container = await build_container()
    
    manager = await container.resolve(PluginManager)
    loader = await container.resolve(PluginLoader)
    registry = await container.resolve(PluginRegistry)
    validator = await container.resolve(PluginValidator)
    health = await container.resolve(PluginHealthTracker)
    
    assert isinstance(manager, PluginManagerImpl)
    assert isinstance(loader, DefaultPluginLoader)
    assert isinstance(registry, InMemoryPluginRegistry)
    assert isinstance(validator, DefaultPluginValidator)
    assert isinstance(health, DefaultPluginHealthTracker)
    
    m2 = await container.resolve(PluginManager)
    assert manager is m2, "Manager should be singleton"


# ─────────────────────────────────────────────
# Lifecycle & Health
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_lifecycle_and_health():
    container = await build_container()
    manager = await container.resolve(PluginManager)
    
    h1 = await manager.health_check()
    assert h1.state == ComponentState.STOPPED
    
    await manager.start()
    h2 = await manager.health_check()
    assert h2.state == ComponentState.RUNNING
    
    await manager.shutdown()
    h3 = await manager.health_check()
    assert h3.state == ComponentState.STOPPED


# ─────────────────────────────────────────────
# Scaffolding Components
# ─────────────────────────────────────────────

def test_loader_scaffold():
    loader = DefaultPluginLoader()
    results = loader.discover()
    assert len(results) == 1
    assert results[0].manifest.id == "core.example.plugin"

def test_registry_scaffold():
    reg = InMemoryPluginRegistry()
    md = make_valid_metadata()
    desc = PluginDescriptor("test", md, PluginState.DISCOVERED, PluginStatus.HEALTHY)
    
    reg.register(desc)
    assert reg.lookup("test") is desc
    assert len(reg.enumerate()) == 1
    
    assert reg.unregister("test") is True
    assert reg.lookup("test") is None
    assert reg.unregister("not_found") is False

def test_validator_success():
    val = DefaultPluginValidator()
    assert val.validate(make_valid_metadata()) is True

def test_validator_failures():
    val = DefaultPluginValidator()
    
    with pytest.raises(PluginValidationError):
        val.validate(None)
        
    with pytest.raises(PluginValidationError, match="Plugin manifest is missing"):
        md = PluginMetadata(None, "", "")
        val.validate(md)


# ─────────────────────────────────────────────
# Pipeline Transitions
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_manager_pipeline():
    container = await build_container()
    manager = await container.resolve(PluginManager)
    
    # 1. Discover
    await manager.discover()
    plugins = await manager.plugins()
    assert len(plugins) == 1
    plugin_id = "core.example.plugin"
    
    assert plugins[0].state == PluginState.DISCOVERED
    assert await manager.status(plugin_id) == PluginStatus.HEALTHY
    
    # 2. Load
    req = PluginRequest(plugin_id=plugin_id)
    res = await manager.load(req)
    assert res.success is True
    assert res.state == PluginState.LOADED
    
    # 3. Enable
    res2 = await manager.enable(plugin_id)
    assert res2.success is True
    assert res2.state == PluginState.ENABLED
    
    # 4. Disable
    res3 = await manager.disable(plugin_id)
    assert res3.success is True
    assert res3.state == PluginState.LOADED
    
    # 5. Unload
    res4 = await manager.unload(plugin_id)
    assert res4.success is True
    assert res4.state == PluginState.DISCOVERED

@pytest.mark.anyio
async def test_manager_state_errors():
    container = await build_container()
    manager = await container.resolve(PluginManager)
    
    await manager.discover()
    plugin_id = "core.example.plugin"
    
    # Cannot enable a DISCOVERED plugin (must be LOADED)
    with pytest.raises(PluginStateError):
        await manager.enable(plugin_id)
        
    # Cannot disable a DISCOVERED plugin (must be ENABLED)
    with pytest.raises(PluginStateError):
        await manager.disable(plugin_id)
        
    await manager.load(PluginRequest(plugin_id=plugin_id))
    
    # Cannot load an already LOADED plugin (must be DISCOVERED/UNLOADED)
    with pytest.raises(PluginStateError):
        await manager.load(PluginRequest(plugin_id=plugin_id))


@pytest.mark.anyio
async def test_manager_not_found():
    container = await build_container()
    manager = await container.resolve(PluginManager)
    
    with pytest.raises(PluginNotFoundError):
        await manager.load(PluginRequest(plugin_id="bad"))
        
    with pytest.raises(PluginNotFoundError):
        await manager.status("bad")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def test_public_api():
    import core.plugins as p
    
    expected = [
        "PluginModule", "PluginManager", "PluginLoader", "PluginRegistry",
        "PluginValidator", "PluginHealthTracker", "PluginManifest", "PluginMetadata",
        "PluginDescriptor", "PluginRequest", "PluginResult", "PluginDependency",
        "PluginCapability", "PluginContext", "PluginState", "PluginType", "PluginStatus",
        "PluginDiscovered", "PluginLoaded", "PluginEnabled", "PluginDisabled",
        "PluginUnloaded", "PluginRegistered", "PluginRemoved", "PluginValidationFailed",
        "PluginError", "PluginValidationError", "PluginLoadError", "PluginNotFoundError",
        "PluginStateError"
    ]
    
    for exp in expected:
        assert exp in p.__all__
        assert hasattr(p, exp)
        
    forbidden = [
        "PluginManagerImpl", "DefaultPluginLoader", "InMemoryPluginRegistry",
        "DefaultPluginValidator", "DefaultPluginHealthTracker"
    ]
    for forb in forbidden:
        assert forb not in p.__all__
