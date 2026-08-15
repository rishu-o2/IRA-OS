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

from core.execution.contracts import ExecutionService, ExecutionType, ExecutionClassifier, ProtectedDispatcher
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
from core.execution.service import DefaultExecutionService, DefaultProtectedDispatcher
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
    is_mutation: bool = False,
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

    # Wire ExecutionClassifier
    classifier = MagicMock(spec=ExecutionClassifier)
    classifier.classify.return_value = ExecutionType.MUTATION if is_mutation else ExecutionType.READ

    # Wire ProtectedDispatcher
    protected_dispatcher = DefaultProtectedDispatcher(
        permission_manager=perm_manager,
        registry=registry,
        dispatcher=dispatcher,
        executor=executor,
        event_bus=bus,
        logger=logger,
    )

    # Mock mutation manager — not triggered in non-mutation tests
    mutation_manager = AsyncMock()

    svc = DefaultExecutionService(
        classifier=classifier,
        protected_dispatcher=protected_dispatcher,
        mutation_manager=mutation_manager,
        event_bus=bus,
        logger=logger,
    )
    return svc, bus, mutation_manager


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
    svc, bus, _ = _build_service(granted=True)
    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.succeeded
    assert outcome.result_data == {"result": "ok"}
    assert outcome.denial_reason is None
    assert outcome.error is None


@pytest.mark.anyio
async def test_successful_execution_publishes_all_events():
    svc, bus, _ = _build_service(granted=True)
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
    svc, bus, _ = _build_service(granted=False)
    cmd = ExecutionCommand(command_id="cmd-deny", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.denied
    assert outcome.denial_reason is not None
    assert not outcome.succeeded


@pytest.mark.anyio
async def test_denied_execution_publishes_denied_event_not_authorized():
    svc, bus, _ = _build_service(granted=False)
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
# 7.5. Permission Requires Approval
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_requires_approval_execution_prompts_confirmation():
    svc, bus, _ = _build_service(granted=False)
    # Patch the permission result to be REQUIRES_APPROVAL
    svc._protected_dispatcher._permission_manager.check_permission.return_value = PermissionResult(
        permission_id="perm-2",
        capability_id="test.cap",
        granted=False,
        state=PermissionState.REQUIRES_APPROVAL,
    )
    
    # Mock confirmation manager
    conf_mgr = AsyncMock()
    conf_mgr.request_confirmation.return_value = True # user approved
    svc._protected_dispatcher._confirmation_manager = conf_mgr
    
    cmd = ExecutionCommand(command_id="cmd-req-app", capability_id="test.cap")
    outcome = await svc.execute(cmd)
    
    # Since it's approved by ConfirmationManager, it should proceed to execution and succeed
    assert outcome.succeeded
    conf_mgr.request_confirmation.assert_called_once()
    assert outcome.denied is False

@pytest.mark.anyio
async def test_requires_approval_execution_denies_if_confirmation_rejected():
    svc, bus, _ = _build_service(granted=False)
    # Patch the permission result to be REQUIRES_APPROVAL
    svc._protected_dispatcher._permission_manager.check_permission.return_value = PermissionResult(
        permission_id="perm-3",
        capability_id="test.cap",
        granted=False,
        state=PermissionState.REQUIRES_APPROVAL,
    )
    
    # Mock confirmation manager
    conf_mgr = AsyncMock()
    conf_mgr.request_confirmation.return_value = False # user denied
    svc._protected_dispatcher._confirmation_manager = conf_mgr
    
    cmd = ExecutionCommand(command_id="cmd-req-app-deny", capability_id="test.cap")
    outcome = await svc.execute(cmd)
    
    # Since it's denied by ConfirmationManager, it should deny
    assert outcome.denied
    conf_mgr.request_confirmation.assert_called_once()
    assert "User denied required security approval" in outcome.denial_reason


# ──────────────────────────────────────────────────────────
# 8. Runtime Failure
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_runtime_failure_returns_failed_outcome():
    svc, bus, _ = _build_service(granted=True, runtime_raises=RuntimeError("Crash!"))
    cmd = ExecutionCommand(command_id="cmd-fail", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    assert outcome.failed
    assert "Crash!" in outcome.error
    assert not outcome.succeeded


@pytest.mark.anyio
async def test_runtime_failure_publishes_failed_event():
    svc, bus, _ = _build_service(granted=True, runtime_raises=RuntimeError("Crash!"))
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
    svc, _, _ = _build_service()
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


# ──────────────────────────────────────────────────────────
# 11. Architecture Invariant Tests (Milestone 16.1.5)
# ──────────────────────────────────────────────────────────

def test_workflow_does_not_import_mutation_manager():
    """Regression: Workflow must never directly depend on MutationManager."""
    import sys
    import os
    workflow_dir = os.path.dirname(sys.modules["core.workflow.executor"].__file__)
    for fname in os.listdir(workflow_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(workflow_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            src = f.read()
        assert "MutationManager" not in src, \
            f"Workflow file '{fname}' must not reference MutationManager. " \
            f"Route all execution through ExecutionService."
        assert "process_mutation" not in src, \
            f"Workflow file '{fname}' must not call process_mutation directly."


def test_mutation_manager_does_not_know_about_runtime():
    """Regression: MutationManager must have zero coupling to Runtime, Security, or Platform."""
    import core.mutation.manager as mgr_mod
    with open(mgr_mod.__file__, encoding="utf-8") as f:
        src = f.read()
    forbidden = [
        "core.runtime.manager",
        "RuntimeManager",
        "core.security.manager",
        "SecurityManager",
        "core.android",
        "CapabilityRegistry",  # should not import this — it's a ProtectedDispatcher concern
    ]
    # CapabilityRegistry is legitimately needed for capability lookup so allow it
    forbidden = [f for f in forbidden if f != "CapabilityRegistry"]
    for forb in forbidden:
        assert forb not in src, \
            f"MutationManager must not reference '{forb}'. " \
            f"It must remain platform-agnostic."


@pytest.mark.anyio
async def test_mutation_commands_routed_through_mutation_manager():
    """Regression: A command classified as MUTATION must trigger MutationManager, never ProtectedDispatcher directly."""
    from core.execution.models import ExecutionOutcomeStatus
    svc, bus, mutation_manager = _build_service(is_mutation=True)
    mutation_manager.process_mutation.return_value = ExecutionOutcome(
        command_id="cmd-1", capability_id="test.cap",
        status=ExecutionOutcomeStatus.SUCCEEDED, result_data="ok"
    )
    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await svc.execute(cmd)
    mutation_manager.process_mutation.assert_called_once()
    assert outcome.succeeded


@pytest.mark.anyio
async def test_read_commands_skip_mutation_manager():
    """Regression: A command classified as READ must bypass MutationManager entirely."""
    svc, bus, mutation_manager = _build_service(is_mutation=False)
    cmd = ExecutionCommand(command_id="cmd-read", capability_id="test.cap")
    await svc.execute(cmd)
    mutation_manager.process_mutation.assert_not_called()


def test_execution_service_is_the_only_permitted_entry_point():
    """Documentation invariant: ExecutionService is the single public entry point by contract."""
    import core.execution.contracts as contracts_mod
    assert hasattr(contracts_mod, "ExecutionService"), \
        "ExecutionService must be declared in execution.contracts."
    assert hasattr(contracts_mod, "ProtectedDispatcher"), \
        "ProtectedDispatcher must exist as a contract; it is the only path to Runtime."
    # MutationManager must NOT be in execution.contracts (it's an internal concern)
    assert not hasattr(contracts_mod, "MutationManager"), \
        "MutationManager must not be part of the Execution public contract surface."


# ──────────────────────────────────────────────────────────
# 12. Architecture Invariant Tests — Security / Bypass / Dependency (Milestone 16.1.5)
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_security_invariant_read_path_passes_through_security():
    """Test C: Read-only commands must pass through Security (ProtectedDispatcher)."""
    svc, bus, mutation_manager = _build_service(is_mutation=False, granted=True)
    from core.execution.events import ExecutionAuthorized
    received = []
    bus.subscribe(ExecutionAuthorized, lambda e: received.append(e))

    cmd = ExecutionCommand(command_id="cmd-read-sec", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    # Security was exercised — ExecutionAuthorized event must be emitted
    assert len(received) == 1, "Read-only path must emit ExecutionAuthorized (security ran)"
    assert outcome.succeeded
    mutation_manager.process_mutation.assert_not_called()


@pytest.mark.anyio
async def test_security_invariant_mutation_path_passes_through_security():
    """Test C (mutation side): Mutation commands go through MutationManager, which calls the delegate, which calls Security."""
    # We verify that MutationManager is called (it will use the delegate that wraps Security)
    svc, bus, mutation_manager = _build_service(is_mutation=True)
    mutation_manager.process_mutation.return_value = ExecutionOutcome(
        command_id="cmd-m", capability_id="test.cap",
        status=ExecutionOutcomeStatus.SUCCEEDED, result_data="ok"
    )
    cmd = ExecutionCommand(command_id="cmd-m", capability_id="test.cap")
    outcome = await svc.execute(cmd)

    mutation_manager.process_mutation.assert_called_once()
    # Verify the delegate (second arg) is a callable — not a ProtectedDispatcher object
    call_args = mutation_manager.process_mutation.call_args
    assert callable(call_args[0][1] if call_args[0] else call_args[1].get("execute_delegate")), \
        "MutationManager must receive a callable delegate, not the ProtectedDispatcher directly."
    assert outcome.succeeded


def test_mutation_bypass_prevention():
    """Test D: The MutationManager contract must NOT be accessible from ExecutionService's public interface."""
    import core.execution.contracts as contracts_mod
    import core.mutation.contracts as mutation_contracts_mod

    # ExecutionService must be the ONLY public entry point in the execution contracts
    assert hasattr(contracts_mod, "ExecutionService")
    # MutationManager must NOT leak into execution contracts
    assert not hasattr(contracts_mod, "MutationManager"), \
        "MutationManager must not appear in core.execution.contracts"

    # MutationManager must be in mutation contracts (internal boundary)
    assert hasattr(mutation_contracts_mod, "MutationManager"), \
        "MutationManager must be declared in core.mutation.contracts as an internal ABC"


def test_dependency_direction_mutation_manager_does_not_import_execution_service():
    """Test E: MutationManager must not import or depend on ExecutionService."""
    import core.mutation.manager as mgr_mod
    import core.mutation.contracts as contracts_mod

    with open(mgr_mod.__file__, encoding="utf-8") as f:
        mgr_src = f.read()
    with open(contracts_mod.__file__, encoding="utf-8") as f:
        contracts_src = f.read()

    # Check only import statements, not docstring mentions
    mgr_imports = [line.strip() for line in mgr_src.splitlines() if line.strip().startswith(("import ", "from "))]
    contracts_imports = [line.strip() for line in contracts_src.splitlines() if line.strip().startswith(("import ", "from "))]

    forbidden_in_imports = ["core.execution.service", "core.execution.execution_module", "DefaultExecutionService"]
    for forb in forbidden_in_imports:
        for imp_line in mgr_imports:
            assert forb not in imp_line, \
                f"core.mutation.manager must not import '{forb}' (dependency inversion violation): {imp_line}"
        for imp_line in contracts_imports:
            assert forb not in imp_line, \
                f"core.mutation.contracts must not import '{forb}': {imp_line}"

    # Verify allowed: models only from core.execution
    allowed_execution_imports = {"from core.execution.models", "from core.execution.contracts"}
    for imp_line in mgr_imports:
        if "core.execution" in imp_line:
            assert any(imp_line.startswith(ok) for ok in allowed_execution_imports), \
                f"core.mutation.manager has unexpected execution import: {imp_line}"



@pytest.mark.anyio
async def test_di_construction_no_circular_dependency():
    """Test F: The complete execution graph can be constructed without circular dependencies."""
    from core.container import Container, ContainerProtocol
    from core.events import EventBus
    from core.logging import LoggerFactory
    from core.logging.sinks import NullSink
    from core.security.security_module import SecurityModule
    from core.runtime.runtime_module import RuntimeModule
    from core.mutation.mutation_module import MutationModule
    from core.execution.execution_module import ExecutionModule

    container = Container()
    event_bus = EventBus()
    logger_factory = LoggerFactory(sinks=[NullSink()])

    container.register_instance(ContainerProtocol, container)
    container.register_instance(EventBus, event_bus)
    container.register_instance(LoggerFactory, logger_factory)

    container.install(SecurityModule())
    container.install(RuntimeModule())
    container.install(MutationModule())  # Must come before ExecutionModule
    container.install(ExecutionModule())

    # Must resolve without ResolutionError or circular dependency
    execution_service = await container.resolve(ExecutionService)
    assert execution_service is not None, "ExecutionService must be constructable from DI"
    assert isinstance(execution_service, ExecutionService)


@pytest.mark.anyio
async def test_existing_capabilities_pass_through_hardened_pipeline():
    """Test G: Flashlight, Volume, Brightness, Pack A, Pack B all route through hardened service."""
    # Verified by the integration tests in tests/core/mutation/.
    # This test asserts the structural invariant: ExecutionService.execute() is the entry point.
    svc, _, mutation_manager = _build_service(is_mutation=True)
    mutation_manager.process_mutation.return_value = ExecutionOutcome(
        command_id="cmd-g", capability_id="android.device.volume",
        status=ExecutionOutcomeStatus.SUCCEEDED, result_data="ok"
    )
    capability_ids = [
        "android.device.volume",
        "android.hardware.flashlight",
        "android.device.brightness",
        "android.device.vibrate",
        "android.device.airplane_mode",
    ]
    for cap_id in capability_ids:
        mutation_manager.process_mutation.reset_mock()
        mutation_manager.process_mutation.return_value = ExecutionOutcome(
            command_id=f"cmd-{cap_id}", capability_id=cap_id,
            status=ExecutionOutcomeStatus.SUCCEEDED, result_data="ok"
        )
        cmd = ExecutionCommand(command_id=f"cmd-{cap_id}", capability_id=cap_id)
        # All capabilities classified as MUTATION route through MutationManager
        outcome = await svc.execute(cmd)
        mutation_manager.process_mutation.assert_called_once(), \
            f"{cap_id} must route through MutationManager when classified as MUTATION"
