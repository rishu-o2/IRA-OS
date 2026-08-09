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
def base_execution_service(flashlight_adapter, event_bus):
    from core.execution.contracts import ProtectedDispatcher, ExecutionClassifier, ExecutionType
    class FakeProtectedDispatcher(ProtectedDispatcher):
        async def dispatch(self, command: ExecutionCommand) -> ExecutionOutcome:
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
                if hasattr(result, 'success') and not result.success:
                    return ExecutionOutcome(
                        command_id=command.command_id, capability_id=command.capability_id,
                        status=ExecutionOutcomeStatus.FAILED, error=getattr(result, 'error_message', 'Unknown error')
                    )
                return ExecutionOutcome(
                    command_id=command.command_id, capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.SUCCEEDED, result_data=result
                )
            except Exception as e:
                return ExecutionOutcome(
                    command_id=command.command_id, capability_id=command.capability_id,
                    status=ExecutionOutcomeStatus.FAILED, error=str(e)
                )

    class AllMutationClassifier(ExecutionClassifier):
        def classify(self, command): return ExecutionType.MUTATION

    return FakeProtectedDispatcher(), AllMutationClassifier(), event_bus


@pytest.fixture
async def execution_service(event_bus, logger, registry, base_execution_service, flashlight_adapter):
    await registry.register(flashlight_adapter)
    
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
    protected_dispatcher, classifier, _ = base_execution_service
    from core.execution.service import DefaultExecutionService
    return DefaultExecutionService(
        classifier=classifier,
        protected_dispatcher=protected_dispatcher,
        mutation_manager=mgr,
        event_bus=event_bus,
        logger=logger,
    )

@pytest.mark.anyio
async def test_flashlight_integration_success(execution_service, mock_bridge):
    cmd = ExecutionCommand(
        command_id="cmd-1",
        capability_id="android.hardware.flashlight",
        arguments={"action": "system.flashlight.on"}
    )
    outcome = await execution_service.execute(cmd)
    
    assert outcome.succeeded is True
    assert outcome.result_data.data["enabled"] is True
    assert mock_bridge._flashlight_on is True

@pytest.mark.anyio
async def test_flashlight_integration_failure_and_rollback(execution_service, mock_bridge, event_bus):
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
    
    outcome = await execution_service.execute(cmd)
    
    assert outcome.failed is True
    assert "Bridge error" in outcome.error
    assert mock_bridge._flashlight_on is False
    assert len(events) == 1



