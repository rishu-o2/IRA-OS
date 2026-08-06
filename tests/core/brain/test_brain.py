import pytest

from core.brain import (
    BrainContext,
    BrainDecisionType,
    BrainManager,
    BrainModule,
    BrainPipeline,
    BrainRequest,
    BrainRequestCompleted,
    BrainRequestFailed,
    BrainRequestStarted,
    BrainValidationError,
    DecisionEngine,
    ReasoningEngine,
)
from core.config import ConfigurationManager
from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.identity import Identity, IdentityManager, IdentityModule, Role
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.memory import MemoryManager, MemoryModule, MemoryRecord
from core.planner import Goal, PlannerManager, PlannerModule, Task, TaskManager
from core.lifecycle.states import ComponentState


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def build_container() -> Container:
    container = Container()
    config = ConfigurationManager()
    config.load()
    event_bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])

    container.register_instance(ContainerProtocol, container)
    container.register_instance(ConfigurationManager, config)
    container.register_instance(EventBus, event_bus)
    container.register_instance(LoggerFactory, logger_factory)
    container.install(IdentityModule())
    container.install(MemoryModule())
    container.install(PlannerModule())
    container.install(BrainModule())
    return container


async def register_identity(container: Container, identity_id: str = "user-1") -> Identity:
    manager = await container.resolve(IdentityManager)
    identity = Identity(id=identity_id, username=identity_id, display_name=identity_id, roles=(Role.GUEST,))
    await manager.register(identity)
    return identity


async def create_planner_fixture(container: Container, goal_id: str = "goal-1") -> None:
    planner = await container.resolve(PlannerManager)
    task_manager = await container.resolve(TaskManager)
    await planner.create_goal(Goal(id=goal_id, title=f"Goal {goal_id}"))
    task_manager.create(Task(id=f"{goal_id}-task-1", goal_id=goal_id, name="Prepare"))
    task_manager.create(
        Task(
            id=f"{goal_id}-task-2",
            goal_id=goal_id,
            name="Finish",
            dependencies=(f"{goal_id}-task-1",),
        )
    )


async def store_memory(container: Container, owner_id: str = "user-1") -> None:
    memory = await container.resolve(MemoryManager)
    await memory.remember(
        MemoryRecord(
            id="memory-1",
            owner_id=owner_id,
            namespace="brain-test",
            title="Build report context",
            content={"text": "report context for memory retrieval"},
            tags=("brain",),
            importance=2,
        )
    )


def make_request(request_id: str = "request-1", goal_id: str = "goal-1", user_id: str = "user-1", extra_metadata: dict = None) -> BrainRequest:
    metadata = {
        "goal_id": goal_id,
        "memory_query": "report context",
        "memory_namespace": "brain-test",
        "memory_tags": ("brain",),
        "conversation_context": [{"role": "user", "content": "previous turn"}],
        "intent": "coordinate",
    }
    if extra_metadata:
        metadata.update(extra_metadata)
        
    return BrainRequest(
        request_id=request_id,
        user_id=user_id,
        payload="Build the report",
        metadata=metadata,
    )


@pytest.mark.anyio
async def test_brain_request_validation():
    with pytest.raises(BrainValidationError):
        BrainRequest(request_id="", user_id="user-1", payload="hello")

    with pytest.raises(BrainValidationError):
        BrainRequest(request_id="request-1", user_id="", payload="hello")

    with pytest.raises(BrainValidationError):
        BrainRequest(request_id="request-1", user_id="user-1", payload=None)


@pytest.mark.anyio
async def test_context_creation_is_immutable():
    request = make_request()
    context = BrainContext.from_request(request)

    updated = context.with_metadata(stage="test")

    assert context.metadata["request_id"] == "request-1"
    assert "stage" not in context.metadata
    assert updated.metadata["stage"] == "test"
    with pytest.raises(TypeError):
        updated.metadata["stage"] = "changed"


@pytest.mark.anyio
async def test_brain_process_request_integrates_identity_memory_planner_and_decision():
    container = await build_container()
    await register_identity(container)
    await create_planner_fixture(container)
    await store_memory(container)

    manager = await container.resolve(BrainManager)
    await manager.start()

    result = await manager.process_request(make_request())

    assert result.success is True
    assert result.decision is not None
    assert result.decision.user_id == "user-1"
    assert result.decision.decision_type == BrainDecisionType.PLAN_READY
    assert result.decision.plan_summary.goal_id == "goal-1"
    assert result.decision.plan_summary.task_ids == ("goal-1-task-1", "goal-1-task-2")
    assert result.decision.memory_count == 1


@pytest.mark.anyio
async def test_brain_publishes_started_and_completed_events():
    container = await build_container()
    await register_identity(container)
    await create_planner_fixture(container)
    await store_memory(container)
    event_bus = await container.resolve(EventBus)
    events = []

    async def handler(event: Event):
        events.append(event)

    event_bus.subscribe(Event, handler)
    manager = await container.resolve(BrainManager)

    result = await manager.process_request(make_request())

    assert result.success is True
    assert [event.name for event in events if event.name.startswith("Brain")] == [
        "BrainRequestStarted",
        "BrainRequestCompleted",
    ]
    assert isinstance(events[-1], BrainRequestCompleted)


@pytest.mark.anyio
async def test_brain_publishes_failed_event_and_returns_consistent_failure():
    container = await build_container()
    await register_identity(container)
    planner = await container.resolve(PlannerManager)
    await planner.create_goal(Goal(id="empty-goal", title="Empty Goal"))
    event_bus = await container.resolve(EventBus)
    events = []

    async def handler(event: Event):
        events.append(event)

    event_bus.subscribe(Event, handler)
    manager = await container.resolve(BrainManager)

    result = await manager.process_request(make_request(goal_id="empty-goal"))

    assert result.success is False
    assert result.error == "Brain request processing failed."
    assert [event.name for event in events if event.name.startswith("Brain")] == [
        "BrainRequestStarted",
        "BrainRequestFailed",
    ]
    assert isinstance(events[-1], BrainRequestFailed)


@pytest.mark.anyio
async def test_identity_resolution_failure_does_not_authenticate_or_execute():
    container = await build_container()
    await create_planner_fixture(container)
    manager = await container.resolve(BrainManager)

    result = await manager.process_request(make_request())

    assert result.success is False
    assert result.error == "Brain request processing failed."


@pytest.mark.anyio
async def test_brain_lifecycle_is_idempotent_and_health_reflects_state():
    container = await build_container()
    manager = await container.resolve(BrainManager)

    stopped = await manager.health_check()
    await manager.start()
    await manager.start()
    running = await manager.health_check()
    await manager.shutdown()
    await manager.shutdown()
    stopped_again = await manager.health_check()

    assert stopped.state == ComponentState.STOPPED
    assert running.state == ComponentState.RUNNING
    assert stopped_again.state == ComponentState.STOPPED


@pytest.mark.anyio
async def test_brain_module_registers_services_without_circular_dependencies():
    container = await build_container()

    pipeline = await container.resolve(BrainPipeline)
    manager = await container.resolve(BrainManager)
    reasoning = await container.resolve(ReasoningEngine)
    decision = await container.resolve(DecisionEngine)

    assert isinstance(pipeline, BrainPipeline)
    assert isinstance(manager, BrainManager)
    assert isinstance(reasoning, ReasoningEngine)
    assert isinstance(decision, DecisionEngine)
    assert len(container.validate()) == 0


@pytest.mark.anyio
async def test_pipeline_processing_is_stateless_between_requests():
    container = await build_container()
    await register_identity(container)
    await create_planner_fixture(container, "goal-a")
    await create_planner_fixture(container, "goal-b")
    await store_memory(container)
    manager = await container.resolve(BrainManager)

    first = await manager.process_request(make_request(request_id="request-a", goal_id="goal-a"))
    second = await manager.process_request(make_request(request_id="request-b", goal_id="goal-b"))

    assert first.success is True
    assert second.success is True
    assert first.decision is not None
    assert second.decision is not None
    assert first.decision.request_id == "request-a"
    assert second.decision.request_id == "request-b"
    assert first.decision.plan_summary.goal_id == "goal-a"
    assert second.decision.plan_summary.goal_id == "goal-b"


@pytest.mark.anyio
async def test_processing_is_deterministic_for_same_request_shape():
    container = await build_container()
    await register_identity(container)
    await create_planner_fixture(container)
    await store_memory(container)
    manager = await container.resolve(BrainManager)

    first = await manager.process_request(make_request(request_id="request-1"))
    second = await manager.process_request(make_request(request_id="request-2"))

    assert first.success is True
    assert second.success is True
    assert first.decision is not None
    assert second.decision is not None
    assert first.decision.plan_summary.task_ids == second.decision.plan_summary.task_ids
    assert first.decision.memory_count == second.decision.memory_count == 1


@pytest.mark.anyio
async def test_brain_health_check_dependency_degradation():
    from core.brain.manager import BrainManager
    from core.logging import LoggerFactory
    from core.logging.sinks import NullSink
    
    logger = LoggerFactory(sinks=[NullSink()]).get("core.brain")
    
    # Missing dependencies
    manager = BrainManager(pipeline=None, logger=logger)
    await manager.start()
    health = await manager.health_check()
    
    assert health.state == ComponentState.FAILED
    assert "Pipeline" in health.details
    assert "Identity" in health.details
    assert "Memory" in health.details
    assert "Planner" in health.details
    assert "Event Bus" in health.details
    
    # Stopped Brain
    await manager.shutdown()
    health = await manager.health_check()
    assert health.state == ComponentState.STOPPED


@pytest.mark.anyio
async def test_brain_boundary_validation_malformed_input():
    container = await build_container()
    manager = await container.resolve(BrainManager)
    
    event_bus = await container.resolve(EventBus)
    events = []
    async def handler(event: Event):
        events.append(event)
    event_bus.subscribe(Event, handler)
    
    # Completely invalid input
    result1 = await manager.process_request(None)
    assert result1.success is False
    assert result1.request_id == "unknown"
    assert isinstance(events[-1], BrainRequestFailed)
    assert events[-1].request_id == "unknown"
    
    # Malformed request-like object without request_id
    class BadObject:
        pass
        
    result2 = await manager.process_request(BadObject())
    assert result2.success is False
    assert result2.request_id == "unknown"
    
    # Malformed with some request_id
    class FakeRequest:
        request_id = "fake-123"
        
    result3 = await manager.process_request(FakeRequest())
    assert result3.success is False
    assert result3.request_id == "fake-123"


@pytest.mark.anyio
async def test_brain_pipeline_execution_order_and_stages():
    container = await build_container()
    pipeline = await container.resolve(BrainPipeline)
    
    stage_names = [stage.name for stage in pipeline.stages]
    
    # Ensure there's exactly one canonical pipeline and exact order
    expected_stages = [
        "validate_request",
        "conversation_context",
        "resolve_identity",
        "analyze_request",
        "retrieve_memory",
        "build_planner_input",
        "invoke_planner",
        "make_decision",
    ]
    
    assert stage_names == expected_stages


@pytest.mark.anyio
async def test_brain_inactive_identity():
    container = await build_container()
    identity_manager = await container.resolve(IdentityManager)
    identity = Identity(id="user-inactive", username="user-inactive", display_name="user-inactive", roles=(Role.GUEST,), active=False)
    await identity_manager.register(identity)
    
    manager = await container.resolve(BrainManager)
    
    request = make_request(user_id="user-inactive")
    result = await manager.process_request(request)
    
    assert result.success is False
    assert result.error == "Brain request processing failed."


@pytest.mark.anyio
async def test_brain_invalid_memory_limit():
    container = await build_container()
    await register_identity(container)
    manager = await container.resolve(BrainManager)
    
    request = make_request(extra_metadata={"memory_limit": "not-an-int"})
    result = await manager.process_request(request)
    
    assert result.success is False
    assert result.error == "Brain request processing failed."


@pytest.mark.anyio
async def test_brain_missing_planner_goal():
    container = await build_container()
    await register_identity(container)
    await store_memory(container)
    manager = await container.resolve(BrainManager)
    
    request = make_request(goal_id="nonexistent-goal")
    result = await manager.process_request(request)
    
    assert result.success is False
    assert result.error == "Brain request processing failed."

