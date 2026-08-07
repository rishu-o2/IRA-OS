import pytest
from unittest.mock import AsyncMock

from core.events import EventBus
from core.execution.models import ExecutionCommand, ExecutionOutcome, ExecutionOutcomeStatus
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.runtime.registry import InMemoryCapabilityRegistry

from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.flashlight import FlashlightCapability
from core.android.adapter import DefaultAndroidAdapter

from core.mutation.manager import DefaultMutationManager
from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider
from core.mutation.models import ConfirmationLevel
from core.mutation.events import MutationRolledBack

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
    return LoggerFactory(sinks=[NullSink()]).get("test")

@pytest.fixture
def mock_bridge():
    return MockSystemBridge()

@pytest.fixture
def flashlight_adapter(mock_bridge):
    cap = FlashlightCapability(mock_bridge)
    return DefaultAndroidAdapter(cap)

@pytest.fixture
def registry(event_bus, flashlight_adapter):
    reg = InMemoryCapabilityRegistry(event_bus)
    # The register method is async
    return reg

@pytest.fixture
def execution_service(flashlight_adapter):
    class FakeExecutionService:
        async def execute(self, command: ExecutionCommand) -> ExecutionOutcome:
            try:
                from core.runtime.models import ExecutionContext, ExecutionRequest
                req = ExecutionRequest(
                    execution_id=command.command_id,
                    capability_id=command.capability_id,
                    arguments=command.arguments,
                    metadata=command.metadata
                )
                ctx = ExecutionContext(request=req, capability_metadata=flashlight_adapter.metadata)
                result = await flashlight_adapter.execute(ctx)
                
                # Check for CapabilityResult wrapper
                if hasattr(result, "success") and not result.success:
                    return ExecutionOutcome(
                        command_id=command.command_id,
                        capability_id=command.capability_id,
                        status=ExecutionOutcomeStatus.FAILED,
                        error=getattr(result, "error_message", "Unknown capability error")
                    )
                    
                return ExecutionOutcome(
                    command_id=command.command_id,
                    capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.SUCCEEDED,
                    result_data=result
                )
            except Exception as e:
                return ExecutionOutcome(
                    command_id=command.command_id,
                    capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.FAILED,
                    error=str(e)
                )
    return FakeExecutionService()

@pytest.fixture
async def mutation_manager(event_bus, logger, registry, execution_service, flashlight_adapter):
    await registry.register(flashlight_adapter)
    
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

@pytest.mark.anyio
async def test_flashlight_integration_success(mutation_manager, mock_bridge):
    cmd = ExecutionCommand(
        command_id="cmd-1",
        capability_id="android.hardware.flashlight",
        arguments={"action": "system.flashlight.on"}
    )
    outcome = await mutation_manager.process_mutation(cmd)
    
    assert outcome.succeeded is True
    assert outcome.result_data.data["enabled"] is True
    assert mock_bridge._flashlight_on is True

@pytest.mark.anyio
async def test_flashlight_integration_failure_and_rollback(mutation_manager, mock_bridge, execution_service, event_bus):
    original_execute = mock_bridge.execute
    
    async def failing_execute(action, arguments=None):
        if action == "system.flashlight.on":
            raise RuntimeError("Bridge error")
        return await original_execute(action, arguments)
    
    mock_bridge.execute = failing_execute
    mock_bridge._flashlight_on = True
    
    events = []
    event_bus.subscribe(MutationRolledBack, lambda e: events.append(e))

    cmd = ExecutionCommand(
        command_id="cmd-fail",
        capability_id="android.hardware.flashlight",
        arguments={"action": "system.flashlight.on"}
    )
    
    outcome = await mutation_manager.process_mutation(cmd)
    
    assert outcome.failed is True
    assert "Bridge error" in outcome.error
    assert mock_bridge._flashlight_on is False
    assert len(events) == 1
