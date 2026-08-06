import pytest
from core.container import Container, ContainerProtocol
from core.events import EventBus, Event
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.lifecycle.states import ComponentState

from core.runtime import (
    RuntimeModule, RuntimeManager, CapabilityRegistry, Dispatcher, Executor, Validator,
    ExecutionRequest, ExecutionResult, ExecutionStatus, CapabilityMetadata, ExecutionContext,
    Capability, CapabilityRegistered, CapabilityUnregistered, ExecutionStarted, ExecutionCompleted, ExecutionFailed,
    RuntimeSubsystemError, ValidationError, CapabilityNotFoundError, ExecutionFailedError
)

class DummyCapability(Capability):
    def __init__(self, metadata: CapabilityMetadata, should_fail: bool = False):
        self._metadata = metadata
        self._should_fail = should_fail
        
    @property
    def metadata(self) -> CapabilityMetadata:
        return self._metadata
        
    async def execute(self, context: ExecutionContext):
        if self._should_fail:
            raise ValueError("Intentional dummy failure")
        return {"action": "success", "arg": context.request.arguments.get("arg")}

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
    
    container.install(RuntimeModule())
    return container

@pytest.mark.anyio
async def test_di_integration():
    container = await build_container()
    
    manager = await container.resolve(RuntimeManager)
    registry = await container.resolve(CapabilityRegistry)
    dispatcher = await container.resolve(Dispatcher)
    executor = await container.resolve(Executor)
    validator = await container.resolve(Validator)
    
    assert isinstance(manager, RuntimeManager)
    assert isinstance(registry, CapabilityRegistry)
    assert isinstance(dispatcher, Dispatcher)
    assert isinstance(executor, Executor)
    assert isinstance(validator, Validator)

@pytest.mark.anyio
async def test_validation_malformed_request():
    container = await build_container()
    manager = await container.resolve(RuntimeManager)
    
    # invalid request object
    result1 = await manager.execute(None)
    assert result1.success is False
    assert result1.status == ExecutionStatus.FAILED
    assert "ExecutionRequest cannot be None" in result1.error or "Request is not an ExecutionRequest" in result1.error
    
    # missing execution_id or malformed request
    class BadReq:
        pass
    result2 = await manager.execute(BadReq())
    assert result2.success is False
    assert result2.status == ExecutionStatus.FAILED
    assert "Request is not an ExecutionRequest" in result2.error
    
    # valid request format but missing capability
    req2 = ExecutionRequest(execution_id="1", capability_id="missing")
    result3 = await manager.execute(req2)
    assert result3.success is False
    assert "not found" in result3.error

@pytest.mark.anyio
async def test_registry_register_unregister_lookup():
    container = await build_container()
    registry = await container.resolve(CapabilityRegistry)
    
    cap = DummyCapability(CapabilityMetadata(id="cap-1", name="Cap 1", description="desc", version="1"))
    
    # register
    await registry.register(cap)
    
    # lookup
    found = registry.lookup("cap-1")
    assert found is cap
    
    # duplicate
    with pytest.raises(ValidationError):
        await registry.register(cap)
        
    # get all
    assert len(registry.get_all()) == 1
    
    # unregister
    await registry.unregister("cap-1")
    with pytest.raises(CapabilityNotFoundError):
        registry.lookup("cap-1")
        
    # unknown unregister
    with pytest.raises(CapabilityNotFoundError):
        await registry.unregister("cap-1")

@pytest.mark.anyio
async def test_execution_success_and_events():
    container = await build_container()
    manager = await container.resolve(RuntimeManager)
    registry = await container.resolve(CapabilityRegistry)
    event_bus = await container.resolve(EventBus)
    
    events = []
    async def handler(event: Event):
        if type(event) in (ExecutionStarted, ExecutionCompleted, ExecutionFailed):
            events.append(event)
    event_bus.subscribe(Event, handler)
    
    cap = DummyCapability(CapabilityMetadata(id="cap-ok", name="OK", description="D", version="1"))
    await registry.register(cap)
    
    req = ExecutionRequest(execution_id="exec-1", capability_id="cap-ok", arguments={"arg": 42})
    result = await manager.execute(req)
    
    assert result.success is True
    assert result.status == ExecutionStatus.COMPLETED
    assert result.result_data == {"action": "success", "arg": 42}
    
    assert len(events) == 2
    assert isinstance(events[0], ExecutionStarted)
    assert events[0].execution_id == "exec-1"
    
    assert isinstance(events[1], ExecutionCompleted)
    assert events[1].execution_id == "exec-1"
    assert events[1].result_data == result.result_data

@pytest.mark.anyio
async def test_execution_failure_normalization():
    container = await build_container()
    manager = await container.resolve(RuntimeManager)
    registry = await container.resolve(CapabilityRegistry)
    event_bus = await container.resolve(EventBus)
    
    events = []
    async def handler(event: Event):
        if type(event) in (ExecutionStarted, ExecutionCompleted, ExecutionFailed):
            events.append(event)
    event_bus.subscribe(Event, handler)
    
    cap = DummyCapability(CapabilityMetadata(id="cap-fail", name="Fail", description="D", version="1"), should_fail=True)
    await registry.register(cap)
    
    req = ExecutionRequest(execution_id="exec-fail", capability_id="cap-fail")
    result = await manager.execute(req)
    
    assert result.success is False
    assert result.status == ExecutionStatus.FAILED
    assert "Capability execution failed: ValueError" in result.error
    
    assert len(events) == 2
    assert isinstance(events[1], ExecutionFailed)
    assert events[1].execution_id == "exec-fail"

@pytest.mark.anyio
async def test_lifecycle_and_health():
    container = await build_container()
    manager = await container.resolve(RuntimeManager)
    
    health = await manager.health_check()
    assert health.state == ComponentState.STOPPED
    
    await manager.start()
    health2 = await manager.health_check()
    assert health2.state == ComponentState.RUNNING
    
    await manager.shutdown()
    health3 = await manager.health_check()
    assert health3.state == ComponentState.STOPPED
