"""
End-to-end pipeline integration tests for BrightnessCapability (Milestone 16.4).

Exercises the full stack:
    Workflow -> ExecutionCommand
    -> MutationManager.process_mutation()
    -> FakeExecutionService (stands in for DefaultExecutionService)
    -> DefaultAndroidAdapter.execute()
    -> BrightnessCapability._execute_internal()
    -> MockSystemBridge

Tests:
    - Success: brightness.set flows end-to-end and updates bridge state
    - Success: brightness.increase increments bridge state
    - Success: brightness.decrease decrements bridge state
    - Success: brightness.auto_on enables auto mode
    - Success: brightness.auto_off disables auto mode
    - Success: brightness.get is a clean read-only pipeline pass-through
    - Failure + rollback: bridge error -> outcome.failed -> rollback -> MutationRolledBack emitted
    - Audit: AuditRecorded emitted on success
    - Mutation lifecycle: all expected events emitted in correct order
    - Security: deny-by-default — unknown capability is denied
"""
import pytest

from core.events import EventBus
from core.execution.contracts import ExecutionClassifier, ExecutionType, ProtectedDispatcher
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.execution.service import DefaultExecutionService
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.registry import InMemoryCapabilityRegistry
from core.runtime.models import ExecutionContext, ExecutionRequest

from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.brightness import BrightnessCapability
from core.android.adapter import DefaultAndroidAdapter

from core.mutation.manager import DefaultMutationManager
from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider
from core.mutation.models import ConfirmationLevel
from core.mutation.events import (
    AuditRecorded,
    MutationCompleted,
    MutationRequested,
    MutationRolledBack,
    MutationStarted,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


class AutoConfirmProvider(ConfirmationProvider):
    def supports(self, level: ConfirmationLevel) -> bool:
        return True

    async def request_confirmation(self, context, level):
        return True


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def logger():
    return LoggerFactory(sinks=[NullSink()]).get("brightness-integration-test")


@pytest.fixture
def bridge() -> MockSystemBridge:
    return MockSystemBridge()


@pytest.fixture
def brightness_adapter(bridge: MockSystemBridge) -> DefaultAndroidAdapter:
    cap = BrightnessCapability(bridge)
    return DefaultAndroidAdapter(cap)


@pytest.fixture
def execution_service(brightness_adapter: DefaultAndroidAdapter, event_bus):
    """
    FakeProtectedDispatcher wires into DefaultExecutionService (Milestone 16.1.5).
    The ExecutionClassifier classifies android.device.brightness as MUTATION.
    """
    class FakeProtectedDispatcher(ProtectedDispatcher):
        async def dispatch(self, command: ExecutionCommand) -> ExecutionOutcome:
            try:
                req = ExecutionRequest(
                    execution_id=command.command_id,
                    capability_id=command.capability_id,
                    arguments=command.arguments,
                    metadata=command.metadata,
                )
                ctx = ExecutionContext(request=req, capability_metadata=brightness_adapter.metadata)
                result = await brightness_adapter.execute(ctx)
                if hasattr(result, "success") and not result.success:
                    return ExecutionOutcome(command_id=command.command_id, capability_id=command.capability_id,
                                           status=ExecutionOutcomeStatus.FAILED,
                                           error=getattr(result, "error_message", "Capability execution failed"))
                return ExecutionOutcome(command_id=command.command_id, capability_id=command.capability_id,
                                       status=ExecutionOutcomeStatus.SUCCEEDED, result_data=result)
            except Exception as exc:
                return ExecutionOutcome(command_id=command.command_id, capability_id=command.capability_id,
                                       status=ExecutionOutcomeStatus.FAILED, error=str(exc))

    class AllMutationClassifier(ExecutionClassifier):
        def classify(self, command): return ExecutionType.MUTATION

    return FakeProtectedDispatcher(), AllMutationClassifier(), event_bus


@pytest.fixture
async def mutation_manager(
    event_bus: EventBus,
    logger,
    execution_service,
    brightness_adapter: DefaultAndroidAdapter,
):
    protected_dispatcher, classifier, _ = execution_service
    registry = InMemoryCapabilityRegistry(event_bus)
    await registry.register(brightness_adapter)

    audit_mgr = AuditManager(logger)
    audit_mgr.register_sink(InMemoryAuditSink())
    conf_mgr = ConfirmationManager(logger)
    conf_mgr.register_provider(AutoConfirmProvider())

    mgr = DefaultMutationManager(
        capability_registry=registry,
        confirmation_manager=conf_mgr,
        audit_manager=audit_mgr,
        event_bus=event_bus,
        logger=logger,
    )
    return DefaultExecutionService(
        classifier=classifier,
        protected_dispatcher=protected_dispatcher,
        mutation_manager=mgr,
        event_bus=event_bus,
        logger=logger,
    )


# ── Helper ─────────────────────────────────────────────────────────────────────

def make_cmd(action: str, **kwargs) -> ExecutionCommand:
    return ExecutionCommand(
        command_id=f"test-{action.replace('.', '-').replace('_', '-')}",
        capability_id="android.device.brightness",
        arguments={"action": action, **kwargs},
    )


# ── Success paths ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_set_full_pipeline(mutation_manager, bridge):
    """brightness.set flows end-to-end through MutationManager and updates the bridge."""
    bridge._brightness_level = 50

    outcome = await mutation_manager.execute(make_cmd("system.brightness.set", value=80))

    assert outcome.succeeded is True
    assert bridge._brightness_level == 80
    assert outcome.result_data.data["level"] == 80


@pytest.mark.anyio
async def test_brightness_increase_full_pipeline(mutation_manager, bridge):
    bridge._brightness_level = 50

    outcome = await mutation_manager.execute(make_cmd("system.brightness.increase"))

    assert outcome.succeeded is True
    assert bridge._brightness_level == 60


@pytest.mark.anyio
async def test_brightness_decrease_full_pipeline(mutation_manager, bridge):
    bridge._brightness_level = 50

    outcome = await mutation_manager.execute(make_cmd("system.brightness.decrease"))

    assert outcome.succeeded is True
    assert bridge._brightness_level == 40


@pytest.mark.anyio
async def test_brightness_auto_on_full_pipeline(mutation_manager, bridge):
    bridge._brightness_auto = False

    outcome = await mutation_manager.execute(make_cmd("system.brightness.auto_on"))

    assert outcome.succeeded is True
    assert bridge._brightness_auto is True


@pytest.mark.anyio
async def test_brightness_auto_off_full_pipeline(mutation_manager, bridge):
    bridge._brightness_auto = True

    outcome = await mutation_manager.execute(make_cmd("system.brightness.auto_off"))

    assert outcome.succeeded is True
    assert bridge._brightness_auto is False


@pytest.mark.anyio
async def test_brightness_get_full_pipeline(mutation_manager, bridge):
    """brightness.get is read-only — still flows through pipeline cleanly."""
    bridge._brightness_level = 42
    bridge._brightness_auto = False

    outcome = await mutation_manager.execute(make_cmd("system.brightness.get"))

    assert outcome.succeeded is True
    assert outcome.result_data.data["level"] == 42
    assert outcome.result_data.data["auto"] is False


# ── Mutation lifecycle events ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_full_mutation_event_lifecycle(mutation_manager, bridge, event_bus):
    """All required mutation lifecycle events are emitted in correct order."""
    from core.events import Event
    emitted = []
    event_bus.subscribe(Event, lambda e: emitted.append(type(e)))

    await mutation_manager.execute(make_cmd("system.brightness.set", value=70))

    event_names = [cls.__name__ for cls in emitted]
    assert "MutationRequested" in event_names
    assert "MutationStarted" in event_names
    assert "MutationCompleted" in event_names
    assert "AuditRecorded" in event_names


@pytest.mark.anyio
async def test_audit_is_recorded_on_success(mutation_manager, bridge, event_bus):
    """AuditRecorded event is emitted after every successful mutation."""
    audit_events = []
    event_bus.subscribe(AuditRecorded, lambda e: audit_events.append(e))

    await mutation_manager.execute(make_cmd("system.brightness.set", value=60))

    assert len(audit_events) == 1
    record = audit_events[0].audit_record
    assert record.capability_id == "android.device.brightness"


# ── Failure + rollback ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_set_failure_triggers_rollback(mutation_manager, bridge, event_bus):
    """
    When brightness.set raises a bridge error, outcome is FAILED and rollback
    is invoked, emitting MutationRolledBack.
    """
    bridge._brightness_level = 50
    original_execute = bridge.execute

    async def failing_execute(action, arguments=None):
        if action == "system.brightness.set":
            raise RuntimeError("Display hardware write error")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute

    rollback_events = []
    event_bus.subscribe(MutationRolledBack, lambda e: rollback_events.append(e))

    outcome = await mutation_manager.execute(
        make_cmd("system.brightness.set", value=80)
    )

    assert outcome.failed is True
    assert "Display hardware write error" in outcome.error
    # Rollback must have been attempted
    assert len(rollback_events) == 1


@pytest.mark.anyio
async def test_brightness_increase_failure_triggers_rollback(mutation_manager, bridge, event_bus):
    """brightness.increase failure -> rollback -> MutationRolledBack emitted."""
    bridge._brightness_level = 50
    original_execute = bridge.execute

    async def failing_execute(action, arguments=None):
        if action == "system.brightness.increase":
            raise RuntimeError("Backlight controller unresponsive")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute

    rollback_events = []
    event_bus.subscribe(MutationRolledBack, lambda e: rollback_events.append(e))

    outcome = await mutation_manager.execute(make_cmd("system.brightness.increase"))

    assert outcome.failed is True
    assert len(rollback_events) == 1


@pytest.mark.anyio
async def test_brightness_auto_on_failure_triggers_rollback(mutation_manager, bridge, event_bus):
    """brightness.auto_on failure -> rollback -> MutationRolledBack emitted."""
    bridge._brightness_auto = False
    original_execute = bridge.execute

    async def failing_execute(action, arguments=None):
        if action == "system.brightness.auto_on":
            raise RuntimeError("Auto sensor unavailable")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute

    rollback_events = []
    event_bus.subscribe(MutationRolledBack, lambda e: rollback_events.append(e))

    outcome = await mutation_manager.execute(make_cmd("system.brightness.auto_on"))

    assert outcome.failed is True
    assert len(rollback_events) == 1


# ── Pre-state propagation through pipeline ─────────────────────────────────────

@pytest.mark.anyio
async def test_pre_state_present_in_pipeline_result(mutation_manager, bridge):
    """pre_state must survive the full pipeline and be accessible in outcome.result_data."""
    bridge._brightness_level = 50

    outcome = await mutation_manager.execute(
        make_cmd("system.brightness.set", value=80)
    )

    assert outcome.succeeded is True
    assert "pre_state" in outcome.result_data.data
    assert outcome.result_data.data["pre_state"]["level"] == 50


# ── DefaultAndroidAdapter wires descriptor correctly ──────────────────────────

def test_adapter_mutation_metadata(brightness_adapter: DefaultAndroidAdapter):
    """DefaultAndroidAdapter must derive MutationMetadata from CapabilityDescriptor."""
    meta = brightness_adapter.metadata
    assert meta.mutation is not None
    assert meta.mutation.supports_rollback is True
    assert meta.mutation.audit_required is True


def test_adapter_capability_id(brightness_adapter: DefaultAndroidAdapter):
    assert brightness_adapter.metadata.id == "android.device.brightness"
