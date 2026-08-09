"""
Pack A Integration Tests — Milestone 16.1.5 Hardened.

All mutations now enter through ExecutionService, not MutationManager directly.
MutationManager is wired as an internal component of ExecutionService.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.events import EventBus
from core.execution.contracts import ExecutionClassifier, ExecutionType, ProtectedDispatcher
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.execution.service import DefaultExecutionService
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.registry import InMemoryCapabilityRegistry
from core.runtime.models import ExecutionContext, ExecutionRequest
from core.android.bridge.system import MockSystemBridge
from core.android.adapter import DefaultAndroidAdapter
from core.mutation.manager import DefaultMutationManager
from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider
from core.mutation.models import ConfirmationLevel
from core.mutation.events import MutationRolledBack

from core.android.capabilities.vibrate import VibrateCapability
from core.android.capabilities.do_not_disturb import DoNotDisturbCapability
from core.android.capabilities.rotation import RotationCapability
from core.android.capabilities.screen_timeout import ScreenTimeoutCapability

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
    return LoggerFactory(sinks=[NullSink()]).get("pack-a-integration")

@pytest.fixture
def bridge() -> MockSystemBridge:
    return MockSystemBridge()

@pytest.fixture
async def execution_service(event_bus, logger, bridge):
    vibrate_cap = VibrateCapability(bridge)
    dnd_cap = DoNotDisturbCapability(bridge)
    rotation_cap = RotationCapability(bridge)
    timeout_cap = ScreenTimeoutCapability(bridge)

    registry = InMemoryCapabilityRegistry(event_bus)
    for cap in [vibrate_cap, dnd_cap, rotation_cap, timeout_cap]:
        await registry.register(DefaultAndroidAdapter(cap))

    # ProtectedDispatcher: executes through the real capability adapters
    class FakeProtectedDispatcher(ProtectedDispatcher):
        async def dispatch(self, command: ExecutionCommand) -> ExecutionOutcome:
            try:
                req = ExecutionRequest(
                    execution_id=command.command_id,
                    capability_id=command.capability_id,
                    arguments=command.arguments,
                    metadata=command.metadata,
                )
                adapter = registry.lookup(command.capability_id)
                ctx = ExecutionContext(request=req, capability_metadata=adapter.metadata)
                result = await adapter.execute(ctx)

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

    # ExecutionClassifier: all android.device.* capabilities are mutations
    class FakeClassifier(ExecutionClassifier):
        def classify(self, command: ExecutionCommand) -> ExecutionType:
            adapter = registry.lookup(command.capability_id)
            if adapter:
                mutation_meta = getattr(getattr(adapter, "metadata", None), "mutation", None)
                if mutation_meta and getattr(mutation_meta, "is_mutation", False):
                    return ExecutionType.MUTATION
            return ExecutionType.READ

    audit_mgr = AuditManager(logger)
    audit_mgr.register_sink(InMemoryAuditSink())
    conf_mgr = ConfirmationManager(logger)
    conf_mgr.register_provider(AutoConfirmProvider())

    execution_service = DefaultMutationManager(
        capability_registry=registry,
        confirmation_manager=conf_mgr,
        audit_manager=audit_mgr,
        event_bus=event_bus,
        logger=logger,
    )

    return DefaultExecutionService(
        classifier=FakeClassifier(),
        protected_dispatcher=FakeProtectedDispatcher(),
        mutation_manager=execution_service,
        event_bus=event_bus,
        logger=logger,
    )

def make_cmd(cap_id: str, action: str, **kwargs) -> ExecutionCommand:
    return ExecutionCommand(
        command_id=f"test-{action.replace('.', '-')}",
        capability_id=cap_id,
        arguments={"action": action, **kwargs},
    )

# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_vibrate_integration(execution_service, bridge):
    outcome = await execution_service.execute(
        make_cmd("android.device.vibrate", "system.vibrate.start", duration_ms=200)
    )
    assert outcome.succeeded is True
    assert bridge._is_vibrating is True

    outcome = await execution_service.execute(
        make_cmd("android.device.vibrate", "system.vibrate.cancel")
    )
    assert outcome.succeeded is True
    assert bridge._is_vibrating is False

@pytest.mark.anyio
async def test_dnd_integration(execution_service, bridge):
    bridge._dnd_mode = "NORMAL"
    outcome = await execution_service.execute(
        make_cmd("android.device.dnd", "system.dnd.set", mode="ALARMS")
    )
    assert outcome.succeeded is True
    assert bridge._dnd_mode == "ALARMS"
    assert outcome.result_data.data["pre_state"]["mode"] == "NORMAL"

@pytest.mark.anyio
async def test_rotation_integration(execution_service, bridge):
    outcome = await execution_service.execute(
        make_cmd("android.device.rotation", "system.rotation.lock", orientation="LANDSCAPE")
    )
    assert outcome.succeeded is True
    assert bridge._rotation_locked is True
    assert bridge._rotation_orientation == "LANDSCAPE"

@pytest.mark.anyio
async def test_screen_timeout_integration(execution_service, bridge):
    bridge._screen_timeout_ms = 60000
    outcome = await execution_service.execute(
        make_cmd("android.device.screen_timeout", "system.screen_timeout.set", duration_ms=120000)
    )
    assert outcome.succeeded is True
    assert bridge._screen_timeout_ms == 120000

    # Test Rollback on Failure
    original_execute = bridge.execute
    async def failing_execute(action, arguments=None):
        if action == "system.screen_timeout.set":
            raise RuntimeError("Fake HW Error")
        return await original_execute(action, arguments)

    bridge.execute = failing_execute
    outcome_fail = await execution_service.execute(
        make_cmd("android.device.screen_timeout", "system.screen_timeout.set", duration_ms=300000)
    )
    assert outcome_fail.failed is True
    assert bridge._screen_timeout_ms == 120000



