"""
Tests for the Mutation Lifecycle Framework (Milestone 16.1).
Updated for Milestone 16.1.5: MutationManager now receives a ProtectedDispatcher.
"""
import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.container import Container, ContainerProtocol
from core.events import Event, EventBus
from core.execution.contracts import ProtectedDispatcher
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.interfaces import CapabilityRegistry
from core.runtime.models import CapabilityMetadata

from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider, MutatingCapability
from core.mutation.events import (
    AuditRecorded,
    MutationCompleted,
    MutationConfirmed,
    MutationRejected,
    MutationRequested,
    MutationRolledBack,
    MutationStarted,
    RollbackFailed,
)
from core.mutation.exceptions import AuditError
from core.mutation.manager import DefaultMutationManager
from core.mutation.models import ConfirmationLevel, MutationContext, MutationMetadata, MutationState
from core.mutation.mutation_module import MutationModule
from core.mutation.policy import ExecuteImmediatelyPolicy, RejectPolicy, RequireConfirmationPolicy


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_delegate(succeed: bool = True, error: str = "fail"):
    """Build an async callable delegate that ExecutionService would supply."""
    async def delegate(command: ExecutionCommand) -> ExecutionOutcome:
        if succeed:
            return ExecutionOutcome(
                command_id=command.command_id, capability_id=command.capability_id,
                status=ExecutionOutcomeStatus.SUCCEEDED, result_data="ok"
            )
        else:
            return ExecutionOutcome(
                command_id=command.command_id, capability_id=command.capability_id,
                status=ExecutionOutcomeStatus.FAILED, error=error
            )
    return delegate


def _build_deps(delegate=None):
    bus = EventBus()
    logger = LoggerFactory(sinks=[NullSink()]).get("test")

    registry = MagicMock(spec=CapabilityRegistry)

    audit_mgr = AuditManager(logger)
    audit_mgr.register_sink(InMemoryAuditSink())

    conf_mgr = ConfirmationManager(logger)

    manager = DefaultMutationManager(
        capability_registry=registry,
        confirmation_manager=conf_mgr,
        audit_manager=audit_mgr,
        event_bus=bus,
        logger=logger,
    )
    _delegate = delegate or _make_delegate()
    return manager, bus, registry, _delegate, conf_mgr, audit_mgr


# ──────────────────────────────────────────────────────────
# 1. Import Safety
# ──────────────────────────────────────────────────────────

def test_import_safety_no_forbidden():
    import sys
    import core.mutation
    import core.mutation.manager
    import core.mutation.contracts

    forbidden = ["core.android", "core.brain", "core.identity", "core.memory"]
    mutation_modules = [k for k in sys.modules if k.startswith("core.mutation")]

    for mod_name in mutation_modules:
        mod = sys.modules[mod_name]
        path = getattr(mod, "__file__", None)
        if path and path.endswith(".py"):
            with open(path, encoding="utf-8") as f:
                src = f.read()
            for forb in forbidden:
                assert forb not in src, f"Forbidden import '{forb}' found in {mod_name}"


def test_mutation_manager_does_not_import_runtime():
    """MutationManager must have ZERO knowledge of Runtime, Security, or Bridges."""
    import core.mutation.manager as mgr_mod
    with open(mgr_mod.__file__, encoding="utf-8") as f:
        src = f.read()
    forbidden = ["core.runtime.manager", "core.security.manager", "core.android", "SecurityManager", "RuntimeManager"]
    for forb in forbidden:
        assert forb not in src, \
            f"MutationManager must not reference '{forb}'. It is platform-agnostic."


# ──────────────────────────────────────────────────────────
# 2. Immutable Models & Contracts
# ──────────────────────────────────────────────────────────

def test_models_are_frozen():
    assert MutationContext.__dataclass_params__.frozen
    assert MutationMetadata.__dataclass_params__.frozen

def test_events_are_frozen():
    assert MutationRequested.__dataclass_params__.frozen

def test_contracts_are_abstract():
    assert inspect.isabstract(MutatingCapability)


# ──────────────────────────────────────────────────────────
# 3. Successful Lifecycle (No Confirmation)
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_successful_mutation_no_confirmation():
    mgr, bus, reg, dispatcher, _, _ = _build_deps()

    cap = MagicMock()
    mutation_meta = MutationMetadata(confirmation_level=ConfirmationLevel.NONE, audit_required=True)
    cap.metadata = CapabilityMetadata(id="test.cap", name="Test", description="", version="1", mutation=mutation_meta)
    reg.lookup.return_value = cap

    events = []
    bus.subscribe(Event, lambda e: events.append(e))

    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await mgr.process_mutation(cmd, dispatcher)

    assert outcome.succeeded

    event_types = {type(e) for e in events}
    assert MutationRequested in event_types
    assert MutationStarted in event_types
    assert MutationCompleted in event_types
    assert AuditRecorded in event_types
    assert MutationConfirmed not in event_types


# ──────────────────────────────────────────────────────────
# 4. Confirmation Required (Granted)
# ──────────────────────────────────────────────────────────

class MockProvider(ConfirmationProvider):
    def supports(self, level: ConfirmationLevel) -> bool:
        return True
    async def request_confirmation(self, context, level):
        return True

@pytest.mark.anyio
async def test_confirmation_granted():
    mgr, bus, reg, dispatcher, conf_mgr, _ = _build_deps()
    conf_mgr.register_provider(MockProvider())

    cap = MagicMock()
    mutation_meta = MutationMetadata(confirmation_level=ConfirmationLevel.USER)
    cap.metadata = CapabilityMetadata(id="test.cap", name="Test", description="", version="1", mutation=mutation_meta)
    reg.lookup.return_value = cap

    events = []
    bus.subscribe(Event, lambda e: events.append(e))

    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await mgr.process_mutation(cmd, dispatcher)

    assert outcome.succeeded
    event_types = {type(e) for e in events}
    assert MutationConfirmed in event_types


# ──────────────────────────────────────────────────────────
# 5. Confirmation Required (Denied)
# ──────────────────────────────────────────────────────────

class DenyingProvider(ConfirmationProvider):
    def supports(self, level: ConfirmationLevel) -> bool:
        return True
    async def request_confirmation(self, context, level):
        return False

@pytest.mark.anyio
async def test_confirmation_denied():
    mgr, bus, reg, dispatcher, conf_mgr, _ = _build_deps()
    conf_mgr.register_provider(DenyingProvider())

    cap = MagicMock()
    mutation_meta = MutationMetadata(confirmation_level=ConfirmationLevel.USER)
    cap.metadata = CapabilityMetadata(id="test.cap", name="Test", description="", version="1", mutation=mutation_meta)
    reg.lookup.return_value = cap

    events = []
    bus.subscribe(Event, lambda e: events.append(e))

    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await mgr.process_mutation(cmd, dispatcher)

    assert outcome.denied
    assert "Confirmation denied" in outcome.denial_reason

    event_types = {type(e) for e in events}
    assert MutationRejected in event_types
    assert AuditRecorded in event_types  # Rejections are audited
    assert MutationStarted not in event_types


# ──────────────────────────────────────────────────────────
# 6. Rollback (Success)
# ──────────────────────────────────────────────────────────

class DummyMutatingCap(MutatingCapability):
    def supports_rollback(self, args): return True
    async def rollback(self, args, res): pass
    async def execute(self, ctx): return {"ok": True}
    @property
    def metadata(self): return self._metadata

@pytest.mark.anyio
async def test_rollback_on_failure():
    failing_delegate = _make_delegate(succeed=False, error="fail")
    mgr, bus, reg, _, _, _ = _build_deps()

    cap = DummyMutatingCap()
    cap._metadata = CapabilityMetadata(id="test.cap", name="Test", description="", version="1", mutation=MutationMetadata(supports_rollback=True))
    cap.rollback = AsyncMock()
    reg.lookup.return_value = cap

    events = []
    bus.subscribe(Event, lambda e: events.append(e))

    cmd = ExecutionCommand(command_id="cmd-1", capability_id="test.cap")
    outcome = await mgr.process_mutation(cmd, failing_delegate)

    assert outcome.failed
    cap.rollback.assert_called_once()

    event_types = {type(e) for e in events}
    assert MutationRolledBack in event_types


# ──────────────────────────────────────────────────────────
# 7. Audit Manager
# ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_audit_manager_raises_on_all_failures():
    logger = LoggerFactory(sinks=[NullSink()]).get("test")
    mgr = AuditManager(logger)

    from core.mutation.contracts import AuditSink

    class FailingSink(AuditSink):
        async def record(self, r): raise Exception("db down")

    mgr.register_sink(FailingSink())

    from core.mutation.models import AuditRecord
    from datetime import datetime

    rec = AuditRecord("a", "m", "c", "x", {}, MutationState.COMPLETED, datetime.now())
    with pytest.raises(AuditError):
        await mgr.record(rec)



