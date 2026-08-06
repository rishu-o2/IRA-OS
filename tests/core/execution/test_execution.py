"""
Comprehensive tests for the Execution Service Kernel (Milestone 16.0).

Covers: contracts, models, events, exceptions, DI wiring, import safety,
canonical pipeline (success, denied, runtime-failure), event publication,
and Workflow-cannot-bypass-ExecutionService constraint.
"""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.interfaces import CapabilityRegistry, Dispatcher, Executor
from core.runtime.models import CapabilityMetadata, ExecutionContext, ExecutionRequest
from core.security.contracts import PermissionManager
from core.security.models import PermissionResult, PermissionState, TrustLevel

from core.execution.contracts import ExecutionService
from core.execution.events import (
    ExecutionAuthorized,
    ExecutionDenied,
    ExecutionDispatched,
    ExecutionFailed,
    ExecutionRequested,
    ExecutionSucceeded,
)
from core.execution.exceptions import (
    ExecutionPermissionDeniedError,
    ExecutionRuntimeError,
    ExecutionServiceError,
    ExecutionValidationError,
)
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.execution.service import DefaultExecutionService
from core.execution.execution_module import ExecutionModule


# ──────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_granted_result(cap_id: str) -> PermissionResult:
    return PermissionResult(
        permission_id="perm-1",
        capability_id=cap_id,
        granted=True,
        state=PermissionState.GRANTED,
    )


def _make_denied_result(cap_id: str, reason: str = "Denied.") -> PermissionResult:
    return PermissionResult(
        permission_id="perm-1",
        capability_id=cap_id,
        granted=False,
        state=PermissionState.DENIED,
        denial_reason=reason,
    )


def _make_mock_capability(cap_id: str):
    cap = MagicMock()
    cap.metadata = CapabilityMetadata(id=cap_id, name=cap_id, description="", version="1.0")
    cap.execute = AsyncMock(return_value={"result": "ok"})
    return cap


def _build_service(
    granted: bool = True,
    runtime_raises: Exception = None,
    cap_id: str = "test.cap",
) -> tuple:
    """Build a DefaultExecutionService with mocked dependencies."""
    bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])
    logger = logger_factory.get("test")

    perm_manager = AsyncMock(spec=PermissionManager)
    if granted:
        perm_manager.check_permission.return_value = _make_granted_result(cap_id)
    else:
        perm_manager.check_permission.return_value = _make_denied_result(cap_id, "Policy: Deny-by-Default.")

    cap = _make_mock_capability(cap_id)
    if runtime_raises:
        cap.execute = AsyncMock(side_effect=runtime_raises)

    registry = MagicMock(spec=CapabilityRegistry)
    dispatcher = MagicMock(spec=Dispatcher)
    dispatcher.dispatch.return_value = cap

    executor = MagicMock(spec=Executor)
    if runtime_raises:
        executor.execute = AsyncMock(side_effect=runtime_raises)
    else:
        executor.execute = AsyncMock(return_value={"result": "ok"})

    svc = DefaultExecutionService(
        permission_manager=perm_manager,
        registry=registry,
        dispatcher=dispatcher,
        executor=executor,
        event_bus=bus,
        logger=logger,
    )
    return svc, bus


# ──────────────────────────────────────────────────────────
# 1. Import Safety
# ──────────────────────────────────────────────────────────

def test_import_safety_no_forbidden():
    import sys
    import core.execution
    import core.execution.service
    import core.execution.contracts

    forbidden = ["core.android", "core.brain", "core.identity", "core.memory"]
    execution_modules = [k for k in sys.modules if k.startswith("core.execution")]

    for mod_name in execution_modules:
        mod = sys.modules[mod_name]
        path = getattr(mod, "__file__", None)
        if path and path.endswith(".py"):
            with open(path, encoding="utf-8") as f:
                src = f.read()
            for forb in forbidden:
                assert forb not in src, f"Forbidden import '{forb}' found in {mod_name}"


# ──────────────────────────────────────────────────────────
# 2. Contracts
# ──────────────────────────────────────────────────────────

def test_execution_service_is_abstract():
    assert inspect.isabstract(ExecutionService)

def test_execution_service_has_execute_method():
    abstract_methods = {
        name for name, m in inspect.getmembers(ExecutionService)
        if getattr(m, "__isabstractmethod__", False)
    }
    assert "execute" in abstract_methods


# ──────────────────────────────────────────────────────────
# 3. Models
# ──────────────────────────────────────────────────────────

def test_models_are_frozen():
    for cls in [ExecutionCommand, ExecutionOutcome]:
        assert cls.__dataclass_params__.frozen

def test_execution_outcome_properties():
    s = ExecutionOutcome(command_id="c", capability_id="cap", status=ExecutionOutcomeStatus.SUCCEEDED)
    d = ExecutionOutcome(command_id="c", capability_id="cap", status=ExecutionOutcomeStatus.DENIED)
    f = ExecutionOutcome(command_id="c", capability_id="cap", status=ExecutionOutcomeStatus.FAILED)
    assert s.succeeded and not s.denied and not s.failed
    assert d.denied and not d.succeeded and not d.failed
    assert f.failed and not f.succeeded and not f.denied

def test_execution_command_immutability():
    cmd = ExecutionCommand(command_id="c1", capability_id="cap.test")
    with pytest.raises(Exception):
        cmd.command_id = "mutated"  # type: ignore


# ──────────────────────────────────────────────────────────
# 4. Events
# ──────────────────────────────────────────────────────────

def test_events_are_frozen_dataclasses():
    for cls in [
        ExecutionRequested, ExecutionAuthorized, ExecutionDispatched,
        ExecutionSucceeded, ExecutionDenied, ExecutionFailed,
    ]:
        assert issubclass(cls, Event)
        assert cls.__dataclass_params__.frozen


# ──────────────────────────────────────────────────────────
# 5. Exceptions
# ──────────────────────────────────────────────────────────

def test_exceptions_hierarchy():
    assert issubclass(ExecutionValidationError, ExecutionServiceError)
    assert issubclass(ExecutionPermissionDeniedError, ExecutionServiceError)
    assert issubclass(ExecutionRuntimeError, ExecutionServiceError)
    assert issubclass(ExecutionServiceError, Exception)


# ──────────────────────────────────────────────────────────
# 6. Successful Execution Pipeline
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_successful_execution_returns_succeeded_outcome():
    svc, bus = _build_service(granted=True)
    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.succeeded
    assert outcome.result_data == {"result": "ok"}
    assert outcome.denial_reason is None
    assert outcome.error is None


@pytest.mark.anyio
async def test_successful_execution_publishes_all_events():
    svc, bus = _build_service(granted=True)
    received = []
    bus.subscribe(Event, lambda e: received.append(e))

    cmd = ExecutionCommand(command_id="cmd-ev", capability_id="test.cap")
    await svc.execute(cmd)

    event_types = {type(e) for e in received}
    assert ExecutionRequested in event_types
    assert ExecutionAuthorized in event_types
    assert ExecutionDispatched in event_types
    assert ExecutionSucceeded in event_types
    assert ExecutionDenied not in event_types
    assert ExecutionFailed not in event_types


# ──────────────────────────────────────────────────────────
# 7. Permission Denied
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_denied_execution_returns_denied_outcome():
    svc, bus = _build_service(granted=False)
    cmd = ExecutionCommand(command_id="cmd-deny", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.denied
    assert outcome.denial_reason is not None
    assert not outcome.succeeded


@pytest.mark.anyio
async def test_denied_execution_publishes_denied_event_not_authorized():
    svc, bus = _build_service(granted=False)
    received = []
    bus.subscribe(Event, lambda e: received.append(e))

    cmd = ExecutionCommand(command_id="cmd-deny-ev", capability_id="test.cap")
    await svc.execute(cmd)

    event_types = {type(e) for e in received}
    assert ExecutionRequested in event_types
    assert ExecutionDenied in event_types
    assert ExecutionAuthorized not in event_types
    assert ExecutionSucceeded not in event_types


# ──────────────────────────────────────────────────────────
# 8. Runtime Failure
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_runtime_failure_returns_failed_outcome():
    svc, bus = _build_service(granted=True, runtime_raises=RuntimeError("Crash!"))
    cmd = ExecutionCommand(command_id="cmd-fail", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.failed
    assert "Crash!" in outcome.error
    assert not outcome.succeeded


@pytest.mark.anyio
async def test_runtime_failure_publishes_failed_event():
    svc, bus = _build_service(granted=True, runtime_raises=RuntimeError("Crash!"))
    received = []
    bus.subscribe(Event, lambda e: received.append(e))

    cmd = ExecutionCommand(command_id="cmd-fail-ev", capability_id="test.cap")
    await svc.execute(cmd)

    event_types = {type(e) for e in received}
    assert ExecutionFailed in event_types
    assert ExecutionSucceeded not in event_types


# ──────────────────────────────────────────────────────────
# 9. Validation
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_invalid_command_raises_validation_error():
    svc, _ = _build_service()
    with pytest.raises(ExecutionValidationError):
        await svc.execute(None)  # type: ignore


# ──────────────────────────────────────────────────────────
# 10. Architectural Constraint — Workflow cannot bypass ExecutionService
# ──────────────────────────────────────────────────────────

def test_workflow_executor_does_not_import_runtime_manager():
    import core.workflow.executor as wf_executor_mod
    with open(wf_executor_mod.__file__, encoding="utf-8") as f:
        src = f.read()
    assert "RuntimeManager" not in src, \
        "WorkflowExecutor must not import or reference RuntimeManager directly."

def test_workflow_executor_does_not_import_android():
    import core.workflow.executor as wf_executor_mod
    with open(wf_executor_mod.__file__, encoding="utf-8") as f:
        src = f.read()
    assert "core.android" not in src, \
        "WorkflowExecutor must not import Android subsystems."

def test_workflow_executor_uses_execution_service():
    import core.workflow.executor as wf_executor_mod
    with open(wf_executor_mod.__file__, encoding="utf-8") as f:
        src = f.read()
    assert "ExecutionService" in src, \
        "WorkflowExecutor must depend on the ExecutionService contract."
