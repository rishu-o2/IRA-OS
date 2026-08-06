"""
Comprehensive tests for the Task & Workflow Engine (Milestone 13).
"""
import inspect
import pytest

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.lifecycle.states import ComponentState
from core.logging import LoggerFactory
from core.logging.sinks import NullSink

from core.workflow.contracts import (
    WorkflowExecutor,
    WorkflowManager,
    WorkflowQueue,
    WorkflowScheduler,
)
from core.workflow.events import (
    RetryScheduled,
    TaskCompleted,
    TaskFailed,
    TaskQueued,
    TaskStarted,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowFailed,
    WorkflowPaused,
    WorkflowResumed,
    WorkflowStarted,
)
from core.workflow.exceptions import (
    TaskExecutionError,
    WorkflowCancelledError,
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from core.workflow.models import (
    ExecutionHistory,
    RetryPolicy,
    Schedule,
    TaskPriority,
    WorkflowContext,
    WorkflowRequest,
    WorkflowResult,
    WorkflowState,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTask,
)
from core.workflow.executor import DefaultWorkflowExecutor
from core.workflow.manager import WorkflowManagerImpl
from core.workflow.queue import InMemoryWorkflowQueue
from core.workflow.scheduler import DefaultWorkflowScheduler
from core.workflow.workflow_module import WorkflowModule


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

    container.install(WorkflowModule())
    return container


def make_request(wf_id: str = "wf-test") -> WorkflowRequest:
    return WorkflowRequest(
        workflow_id=wf_id,
        target_capability="test.cap",
        arguments={"x": 1}
    )


# ─────────────────────────────────────────────
# Import Safety
# ─────────────────────────────────────────────

def test_import_safety_no_forbidden():
    import sys
    import core.workflow
    import core.workflow.manager
    import core.workflow.scheduler
    import core.workflow.queue
    import core.workflow.executor
    
    forbidden = ["core.brain", "core.memory", "core.identity", "core.android"]
    workflow_modules = [k for k in sys.modules.keys() if k.startswith("core.workflow")]

    for mod_name in workflow_modules:
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
    assert inspect.isabstract(WorkflowManager)
    assert inspect.isabstract(WorkflowScheduler)
    assert inspect.isabstract(WorkflowQueue)
    assert inspect.isabstract(WorkflowExecutor)

def test_contract_abstract_methods():
    def get_abstract_methods(cls):
        return {name for name, method in inspect.getmembers(cls)
                if getattr(method, "__isabstractmethod__", False)}

    assert "start" in get_abstract_methods(WorkflowManager)
    assert "submit" in get_abstract_methods(WorkflowManager)
    assert "cancel" in get_abstract_methods(WorkflowManager)
    assert "schedule" in get_abstract_methods(WorkflowScheduler)
    assert "enqueue" in get_abstract_methods(WorkflowQueue)
    assert "dispatch" in get_abstract_methods(WorkflowExecutor)


# ─────────────────────────────────────────────
# Models & Enums
# ─────────────────────────────────────────────

def test_models_are_frozen():
    for cls in [
        WorkflowRequest, WorkflowResult, WorkflowTask, WorkflowStep,
        WorkflowContext, RetryPolicy, Schedule, ExecutionHistory
    ]:
        assert hasattr(cls, "__dataclass_params__")
        assert cls.__dataclass_params__.frozen

def test_enums():
    assert WorkflowStatus.PENDING.value == "PENDING"
    assert WorkflowState.EXECUTING.value == "EXECUTING"
    assert TaskPriority.HIGH.value == "HIGH"


# ─────────────────────────────────────────────
# Events
# ─────────────────────────────────────────────

def test_events_inherit_event():
    for cls in [
        WorkflowStarted, WorkflowCompleted, WorkflowFailed,
        WorkflowCancelled, WorkflowPaused, WorkflowResumed,
        TaskQueued, TaskStarted, TaskCompleted, TaskFailed, RetryScheduled
    ]:
        assert issubclass(cls, Event)
        assert getattr(cls, "__dataclass_params__").frozen


# ─────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────

def test_exceptions():
    assert issubclass(WorkflowError, Exception)
    assert issubclass(WorkflowValidationError, WorkflowError)
    assert issubclass(WorkflowNotFoundError, WorkflowError)
    assert issubclass(TaskExecutionError, WorkflowError)
    assert issubclass(WorkflowCancelledError, WorkflowError)


# ─────────────────────────────────────────────
# DI Wiring
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_di_wiring():
    container = await build_container()
    
    manager = await container.resolve(WorkflowManager)
    scheduler = await container.resolve(WorkflowScheduler)
    queue = await container.resolve(WorkflowQueue)
    executor = await container.resolve(WorkflowExecutor)
    
    assert isinstance(manager, WorkflowManagerImpl)
    assert isinstance(scheduler, DefaultWorkflowScheduler)
    assert isinstance(queue, InMemoryWorkflowQueue)
    assert isinstance(executor, DefaultWorkflowExecutor)
    
    m2 = await container.resolve(WorkflowManager)
    assert manager is m2, "Manager should be singleton"


# ─────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_lifecycle_and_health():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    
    h1 = await manager.health_check()
    assert h1.state == ComponentState.STOPPED
    
    await manager.start()
    await manager.start() # idempotent
    h2 = await manager.health_check()
    assert h2.state == ComponentState.RUNNING
    
    await manager.shutdown()
    h3 = await manager.health_check()
    assert h3.state == ComponentState.STOPPED


# ─────────────────────────────────────────────
# Scheduler & Queue
# ─────────────────────────────────────────────

def test_scheduler_creates_task():
    sched = DefaultWorkflowScheduler()
    req = make_request("sched-test")
    task = sched.schedule(req)
    
    assert isinstance(task, WorkflowTask)
    assert task.workflow_id == "sched-test"
    assert task.status == WorkflowStatus.PENDING

def test_queue_enqueue_dequeue():
    q = InMemoryWorkflowQueue()
    task = WorkflowTask(task_id="t1", workflow_id="w1", target_capability="c", arguments={}, priority=TaskPriority.NORMAL)
    
    assert q.peek() is None
    q.enqueue(task)
    assert q.peek() is task
    assert q.lookup("t1") is task
    assert q.status()["queued_tasks"] == 1
    
    popped = q.dequeue()
    assert popped is task
    assert q.peek() is None
    assert q.lookup("t1") is None
    assert q.status()["queued_tasks"] == 0

def test_queue_remove():
    q = InMemoryWorkflowQueue()
    task = WorkflowTask(task_id="t2", workflow_id="w2", target_capability="c", arguments={}, priority=TaskPriority.NORMAL)
    
    q.enqueue(task)
    assert q.remove("t2") is True
    assert q.peek() is None


# ─────────────────────────────────────────────
# Workflow Pipeline
# ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_manager_pipeline_success():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    bus = await container.resolve(EventBus)
    
    events = []
    bus.subscribe(Event, lambda e: events.append(e))
    
    req = make_request("wf-pipeline")
    res = await manager.submit(req)
    
    assert res.success is True
    assert res.status == WorkflowStatus.COMPLETED
    assert res.workflow_id == "wf-pipeline"
    
    event_types = [type(e) for e in events]
    assert TaskQueued in event_types
    assert WorkflowStarted in event_types
    assert TaskStarted in event_types
    assert TaskCompleted in event_types
    assert WorkflowCompleted in event_types

@pytest.mark.anyio
async def test_manager_status():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    
    with pytest.raises(WorkflowNotFoundError):
        await manager.status("not-found")
        
    req = make_request("wf-status")
    await manager.submit(req)
    
    stat = await manager.status("wf-status")
    assert stat == WorkflowStatus.COMPLETED

@pytest.mark.anyio
async def test_manager_cancel():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    
    req = make_request("wf-cancel")
    await manager.submit(req)
    
    await manager.cancel("wf-cancel")
    assert await manager.status("wf-cancel") == WorkflowStatus.CANCELLED

@pytest.mark.anyio
async def test_manager_pause_resume():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    
    req = make_request("wf-pause")
    await manager.submit(req)
    
    await manager.pause("wf-pause")
    assert await manager.status("wf-pause") == WorkflowStatus.PAUSED
    
    await manager.resume("wf-pause")
    assert await manager.status("wf-pause") == WorkflowStatus.RUNNING

@pytest.mark.anyio
async def test_manager_validation():
    container = await build_container()
    manager = await container.resolve(WorkflowManager)
    
    with pytest.raises(WorkflowValidationError):
        await manager.submit(None)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def test_public_api():
    import core.workflow as wf
    
    expected = [
        "WorkflowModule",
        "WorkflowManager", "WorkflowScheduler", "WorkflowQueue", "WorkflowExecutor",
        "WorkflowRequest", "WorkflowResult", "WorkflowTask", "WorkflowStep", "WorkflowContext",
        "RetryPolicy", "Schedule", "WorkflowStatus", "ExecutionHistory", "TaskPriority", "WorkflowState",
        "WorkflowStarted", "WorkflowCompleted", "WorkflowFailed", "WorkflowCancelled", "WorkflowPaused",
        "WorkflowResumed", "TaskQueued", "TaskStarted", "TaskCompleted", "TaskFailed", "RetryScheduled",
        "WorkflowError", "WorkflowValidationError", "WorkflowNotFoundError", "TaskExecutionError", "WorkflowCancelledError"
    ]
    
    for exp in expected:
        assert exp in wf.__all__
        assert hasattr(wf, exp)
        
    forbidden = ["WorkflowManagerImpl", "DefaultWorkflowScheduler", "InMemoryWorkflowQueue", "DefaultWorkflowExecutor"]
    for forb in forbidden:
        assert forb not in wf.__all__
