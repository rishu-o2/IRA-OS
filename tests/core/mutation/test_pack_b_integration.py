"""
Pack B Integration Tests — Milestone 16.1.5 Hardened.

All mutations now enter through ExecutionService, not MutationManager directly.
MutationManager is wired as an internal component of ExecutionService.
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
from core.android.bridge.network import MockNetworkBridge
from core.android.adapter import DefaultAndroidAdapter
from core.mutation.manager import DefaultMutationManager
from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider
from core.mutation.models import ConfirmationLevel

from core.android.capabilities.wifi import WifiCapability
from core.android.capabilities.bluetooth import BluetoothCapability
from core.android.capabilities.mobile_data import MobileDataCapability
from core.android.capabilities.hotspot import HotspotCapability
from core.android.capabilities.airplane_mode import AirplaneModeCapability

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
    return LoggerFactory(sinks=[NullSink()]).get("pack-b-integration")

@pytest.fixture
def bridge() -> MockNetworkBridge:
    return MockNetworkBridge()

@pytest.fixture
async def execution_service(event_bus, logger, bridge):
    capabilities = [
        WifiCapability(bridge),
        BluetoothCapability(bridge),
        MobileDataCapability(bridge),
        HotspotCapability(bridge),
        AirplaneModeCapability(bridge),
    ]

    registry = InMemoryCapabilityRegistry(event_bus)
    for cap in capabilities:
        await registry.register(DefaultAndroidAdapter(cap))

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

    mutation_manager = DefaultMutationManager(
        capability_registry=registry,
        confirmation_manager=conf_mgr,
        audit_manager=audit_mgr,
        event_bus=event_bus,
        logger=logger,
    )

    return DefaultExecutionService(
        classifier=FakeClassifier(),
        protected_dispatcher=FakeProtectedDispatcher(),
        mutation_manager=mutation_manager,
        event_bus=event_bus,
        logger=logger,
    )

def make_cmd(cap_id: str, action: str, **kwargs) -> ExecutionCommand:
    return ExecutionCommand(
        command_id=f"test-{action.replace('.', '-')}",
        capability_id=cap_id,
        arguments={"action": action, **kwargs},
    )

@pytest.mark.anyio
async def test_airplane_mode_integration(execution_service, bridge):
    outcome = await execution_service.execute(
        make_cmd("android.device.airplane_mode", "network.airplane.enable")
    )
    assert outcome.succeeded is True
    assert bridge._state["wifi"]["enabled"] is False
    assert bridge._state["bluetooth"]["enabled"] is False

@pytest.mark.anyio
async def test_airplane_mode_rollback(execution_service, bridge):
    await bridge.execute("network.wifi.enable")
    assert bridge._state["wifi"]["enabled"] is True

    outcome = await execution_service.execute(
        make_cmd("android.device.airplane_mode", "network.airplane.enable")
    )
    assert outcome.succeeded is True
    assert bridge._state["wifi"]["enabled"] is False

    # Directly test rollback on the adapter
    # This proves the pre_state was captured correctly
    adapter_registry = None
    # We verify cascade state was captured by checking that the bridge has the right WiFi state
    # Rollback restores it from pre_state embedded in result_data
    from core.android.capabilities.airplane_mode import AirplaneModeCapability
    cap = AirplaneModeCapability(bridge)
    await cap.rollback(
        {"action": "network.airplane.enable"},
        outcome.result_data,
    )
    assert bridge._state["wifi"]["enabled"] is True
    assert bridge._state["airplane_mode"]["enabled"] is False
