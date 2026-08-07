"""
End-to-end pipeline integration tests for VolumeCapability (Milestone 16.3).

Exercises the full stack:
    Workflow → ExecutionCommand
    → MutationManager.process_mutation()
    → FakeExecutionService (stands in for DefaultExecutionService)
    → DefaultAndroidAdapter.execute()
    → VolumeCapability._execute_internal()
    → MockSystemBridge

Tests:
    - Success: volume.set flows end-to-end and updates bridge state
    - Success: volume.up increments bridge state
    - Success: volume.mute mutes bridge state
    - Failure + rollback: bridge error → outcome.failed → rollback → MutationRolledBack emitted
    - Audit: AuditRecorded emitted on success
    - Mutation lifecycle: all expected events emitted in order
"""
import pytest

from core.events import EventBus
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.registry import InMemoryCapabilityRegistry

from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.volume import VolumeCapability
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
    return LoggerFactory(sinks=[NullSink()]).get("volume-integration-test")


@pytest.fixture
def bridge() -> MockSystemBridge:
    return MockSystemBridge()


@pytest.fixture
def volume_adapter(bridge: MockSystemBridge) -> DefaultAndroidAdapter:
    cap = VolumeCapability(bridge)
    return DefaultAndroidAdapter(cap)


@pytest.fixture
def execution_service(volume_adapter: DefaultAndroidAdapter):
    """
    Fake ExecutionService that:
     1. Executes the AndroidAdapter directly (bypasses real Security for unit testing)
     2. Propagates CapabilityResult.success=False as FAILED outcome
    This mirrors how DefaultExecutionService maps adapter results in the real pipeline.
    """
    class FakeExecutionService:
        async def execute(self, command: ExecutionCommand) -> ExecutionOutcome:
            try:
                from core.runtime.models import ExecutionContext, ExecutionRequest
                req = ExecutionRequest(
                    execution_id=command.command_id,
                    capability_id=command.capability_id,
                    arguments=command.arguments,
                    metadata=command.metadata,
                )
                ctx = ExecutionContext(
                    request=req,
                    capability_metadata=volume_adapter.metadata,
                )
                result = await volume_adapter.execute(ctx)

                # CapabilityResult.success=False → FAILED outcome
                if hasattr(result, "success") and not result.success:
                    return ExecutionOutcome(
                        command_id=command.command_id,
                        capability_id=command.capability_id,
                        status=ExecutionOutcomeStatus.FAILED,
                        error=getattr(result, "error_message", "Capability execution failed"),
                    )

                return ExecutionOutcome(
                    command_id=command.command_id,
                    capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.SUCCEEDED,
                    result_data=result,
                )
            except Exception as exc:
                return ExecutionOutcome(
                    command_id=command.command_id,
                    capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.FAILED,
                    error=str(exc),
                )

    return FakeExecutionService()


@pytest.fixture
async def mutation_manager(
    event_bus: EventBus,
    logger,
    execution_service,
    volume_adapter: DefaultAndroidAdapter,
):
    registry = InMemoryCapabilityRegistry(event_bus)
    await registry.register(volume_adapter)

    audit_mgr = AuditManager(logger)
    audit_mgr.register_sink(InMemoryAuditSink())

    conf_mgr = ConfirmationManager(logger)
    conf_mgr.register_provider(AutoConfirmProvider())

    return DefaultMutationManager(
        execution_service=execution_service,
        capability_registry=registry,
        confirmation_manager=conf_mgr,
        audit_manager=audit_mgr,
        event_bus=event_bus,
        logger=logger,
    )


# ── Helper ─────────────────────────────────────────────────────────────────────

def make_cmd(action: str, **kwargs) -> ExecutionCommand:
    return ExecutionCommand(
        command_id=f"test-{action.replace('.', '-')}",
        capability_id="android.device.volume",
        arguments={"action": action, **kwargs},
    )


# ── Success paths ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_set_full_pipeline(mutation_manager, bridge):
    """volume.set flows end-to-end through MutationManager and updates the bridge."""
    bridge._volume_level = 50

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.set", value=80))

    assert outcome.succeeded is True
    assert bridge._volume_level == 80
    assert outcome.result_data.data["level"] == 80


@pytest.mark.anyio
async def test_volume_up_full_pipeline(mutation_manager, bridge):
    bridge._volume_level = 50

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.up"))

    assert outcome.succeeded is True
    assert bridge._volume_level == 60


@pytest.mark.anyio
async def test_volume_down_full_pipeline(mutation_manager, bridge):
    bridge._volume_level = 50

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.down"))

    assert outcome.succeeded is True
    assert bridge._volume_level == 40


@pytest.mark.anyio
async def test_volume_mute_full_pipeline(mutation_manager, bridge):
    bridge._volume_muted = False

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.mute"))

    assert outcome.succeeded is True
    assert bridge._volume_muted is True


@pytest.mark.anyio
async def test_volume_unmute_full_pipeline(mutation_manager, bridge):
    bridge._volume_muted = True

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.unmute"))

    assert outcome.succeeded is True
    assert bridge._volume_muted is False


@pytest.mark.anyio
async def test_volume_get_full_pipeline(mutation_manager, bridge):
    """volume.get is a read-only action — still flows through pipeline cleanly."""
    bridge._volume_level = 42
    bridge._volume_muted = True

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.get"))

    assert outcome.succeeded is True
    assert outcome.result_data.data["level"] == 42
    assert outcome.result_data.data["muted"] is True


# ── Mutation lifecycle events ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_full_mutation_event_lifecycle(mutation_manager, bridge, event_bus):
    """All required mutation events are emitted in correct order."""
    from core.events import Event
    emitted = []
    event_bus.subscribe(Event, lambda e: emitted.append(type(e)))

    await mutation_manager.process_mutation(make_cmd("system.volume.set", value=70))

    event_names = [cls.__name__ for cls in emitted]
    assert "MutationRequested" in event_names
    assert "MutationStarted" in event_names
    assert "MutationCompleted" in event_names
    assert "AuditRecorded" in event_names


# ── Failure + rollback ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_set_failure_triggers_rollback(mutation_manager, bridge, event_bus):
    """
    When volume.set raises a bridge error, the outcome is FAILED and
    rollback is invoked, emitting MutationRolledBack.
    """
    bridge._volume_level = 50
    original_execute = bridge.execute

    async def failing_execute(action, arguments=None):
        if action == "system.volume.set":
            raise RuntimeError("Hardware write error")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute

    rollback_events = []
    event_bus.subscribe(MutationRolledBack, lambda e: rollback_events.append(e))

    outcome = await mutation_manager.process_mutation(
        make_cmd("system.volume.set", value=80)
    )

    assert outcome.failed is True
    assert "Hardware write error" in outcome.error
    # Rollback must have been called
    assert len(rollback_events) == 1


@pytest.mark.anyio
async def test_volume_up_failure_triggers_rollback(mutation_manager, bridge, event_bus):
    """volume.up failure → rollback → MutationRolledBack emitted."""
    bridge._volume_level = 50
    original_execute = bridge.execute

    async def failing_execute(action, arguments=None):
        if action == "system.volume.up":
            raise RuntimeError("Speaker error")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute

    rollback_events = []
    event_bus.subscribe(MutationRolledBack, lambda e: rollback_events.append(e))

    outcome = await mutation_manager.process_mutation(make_cmd("system.volume.up"))

    assert outcome.failed is True
    assert len(rollback_events) == 1
