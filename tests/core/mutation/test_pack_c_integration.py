"""
Pack C Integration Tests — Milestone 16.1.5 Hardened.

All mutations enter through ExecutionService.execute().
MutationManager is an internal component — never called directly.
Verifies the full pipeline: ExecutionService -> MutationManager -> Security -> Runtime -> Capability -> Bridge
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
from core.android.adapter import DefaultAndroidAdapter
from core.mutation.manager import DefaultMutationManager
from core.mutation.audit import AuditManager, InMemoryAuditSink
from core.mutation.confirmation import ConfirmationManager
from core.mutation.contracts import ConfirmationProvider
from core.mutation.models import ConfirmationLevel

from core.android.bridge.telephony import MockCallBridge, MockSMSBridge, MockContactsBridge
from core.android.bridge.notification import MockNotificationBridge
from core.android.capabilities.call import PhoneReadCapability, PhoneWriteCapability
from core.android.capabilities.sms import SmsReadCapability, SmsWriteCapability
from core.android.capabilities.contacts import ContactsReadCapability, ContactsWriteCapability
from core.android.capabilities.notification import NotificationReadCapability, NotificationWriteCapability


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
    return LoggerFactory(sinks=[NullSink()]).get("pack-c-integration")

@pytest.fixture
def call_bridge():
    return MockCallBridge()

@pytest.fixture
def sms_bridge():
    return MockSMSBridge()

@pytest.fixture
def contacts_bridge():
    return MockContactsBridge()

@pytest.fixture
def notif_bridge():
    return MockNotificationBridge()


def _build_service(event_bus, logger, capabilities):
    """Build a complete hardened ExecutionService with given capabilities."""

    async def _build():
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

        mutation_mgr = DefaultMutationManager(
            capability_registry=registry,
            confirmation_manager=conf_mgr,
            audit_manager=audit_mgr,
            event_bus=event_bus,
            logger=logger,
        )

        return DefaultExecutionService(
            classifier=FakeClassifier(),
            protected_dispatcher=FakeProtectedDispatcher(),
            mutation_manager=mutation_mgr,
            event_bus=event_bus,
            logger=logger,
        )

    return _build


def make_cmd(cap_id: str, action: str, **kwargs) -> ExecutionCommand:
    return ExecutionCommand(
        command_id=f"test-{action.replace('.', '-')}",
        capability_id=cap_id,
        arguments={"action": action, **kwargs},
    )


# ── Call Integration ───────────────────────────────────────────────────────────

@pytest.fixture
async def call_service(event_bus, logger, call_bridge):
    caps = [PhoneReadCapability(call_bridge), PhoneWriteCapability(call_bridge)]
    return await _build_service(event_bus, logger, caps)()

@pytest.mark.anyio
async def test_phone_status_read_path(call_service, call_bridge):
    """Read-only: must NOT enter MutationManager."""
    outcome = await call_service.execute(make_cmd("android.communication.phone.read", "telephony.phone.status"))
    assert outcome.succeeded
    assert outcome.result_data.data["status"] == "idle"

@pytest.mark.anyio
async def test_make_call_mutation_path(call_service, call_bridge):
    """Mutation: must enter MutationManager -> Security -> Capability."""
    outcome = await call_service.execute(make_cmd("android.communication.phone.write", "telephony.phone.call", number="+9999999999"))
    assert outcome.succeeded
    assert call_bridge._status == "active"

@pytest.mark.anyio
async def test_end_call_mutation_path(call_service, call_bridge):
    call_bridge._status = "active"
    call_bridge._current_number = "+9999999999"
    outcome = await call_service.execute(make_cmd("android.communication.phone.write", "telephony.phone.end"))
    assert outcome.succeeded
    assert call_bridge._status == "ended"

@pytest.mark.anyio
async def test_reject_call_mutation_path(call_service, call_bridge):
    call_bridge._status = "ringing"
    outcome = await call_service.execute(make_cmd("android.communication.phone.write", "telephony.phone.reject"))
    assert outcome.succeeded
    assert call_bridge._status == "idle"


# ── SMS Integration ────────────────────────────────────────────────────────────

@pytest.fixture
async def sms_service(event_bus, logger, sms_bridge):
    caps = [SmsReadCapability(sms_bridge), SmsWriteCapability(sms_bridge)]
    return await _build_service(event_bus, logger, caps)()

@pytest.mark.anyio
async def test_sms_read_path(sms_service, sms_bridge):
    """Read-only: bypasses MutationManager."""
    outcome = await sms_service.execute(make_cmd("android.communication.sms.read", "telephony.sms.read"))
    assert outcome.succeeded

@pytest.mark.anyio
async def test_sms_search_path(sms_service, sms_bridge):
    outcome = await sms_service.execute(make_cmd("android.communication.sms.read", "telephony.sms.search", query="hello"))
    assert outcome.succeeded

@pytest.mark.anyio
async def test_sms_send_mutation_path(sms_service, sms_bridge):
    """Mutation: enters MutationManager."""
    outcome = await sms_service.execute(make_cmd("android.communication.sms.write", "telephony.sms.send", number="+1111111111", body="Hi IRA"))
    assert outcome.succeeded
    assert len(sms_bridge._sent) == 1

@pytest.mark.anyio
async def test_sms_delete_mutation_and_rollback(sms_service, sms_bridge):
    """Delete is a mutation, and rollback must restore the message."""
    outcome = await sms_service.execute(make_cmd("android.communication.sms.write", "telephony.sms.delete", message_id="msg-001"))
    assert outcome.succeeded
    assert "msg-001" not in sms_bridge._inbox

    # Rollback
    from core.android.capabilities.sms import SmsWriteCapability
    cap = SmsWriteCapability(sms_bridge)
    await cap.rollback({"action": "telephony.sms.delete"}, outcome.result_data)
    assert "msg-001" in sms_bridge._inbox


# ── Contacts Integration ───────────────────────────────────────────────────────

@pytest.fixture
async def contacts_service(event_bus, logger, contacts_bridge):
    caps = [ContactsReadCapability(contacts_bridge), ContactsWriteCapability(contacts_bridge)]
    return await _build_service(event_bus, logger, caps)()

@pytest.mark.anyio
async def test_contacts_read_path(contacts_service, contacts_bridge):
    outcome = await contacts_service.execute(make_cmd("android.communication.contacts.read", "telephony.contacts.read"))
    assert outcome.succeeded

@pytest.mark.anyio
async def test_contacts_create_mutation_path(contacts_service, contacts_bridge):
    outcome = await contacts_service.execute(make_cmd("android.communication.contacts.write", "telephony.contacts.create", name="Eve", number="+5555555555"))
    assert outcome.succeeded
    assert len(contacts_bridge._contacts) == 3

@pytest.mark.anyio
async def test_contacts_create_rollback(contacts_service, contacts_bridge):
    outcome = await contacts_service.execute(make_cmd("android.communication.contacts.write", "telephony.contacts.create", name="Temp", number="+0000000000"))
    assert outcome.succeeded
    contact_id = outcome.result_data.data["contact_id"]
    assert contact_id in contacts_bridge._contacts

    from core.android.capabilities.contacts import ContactsWriteCapability
    cap = ContactsWriteCapability(contacts_bridge)
    await cap.rollback({"action": "telephony.contacts.create"}, outcome.result_data)
    assert contact_id not in contacts_bridge._contacts

@pytest.mark.anyio
async def test_contacts_update_rollback(contacts_service, contacts_bridge):
    outcome = await contacts_service.execute(make_cmd("android.communication.contacts.write", "telephony.contacts.update", contact_id="c-001", name="Alicia"))
    assert outcome.succeeded
    assert contacts_bridge._contacts["c-001"]["name"] == "Alicia"

    from core.android.capabilities.contacts import ContactsWriteCapability
    cap = ContactsWriteCapability(contacts_bridge)
    await cap.rollback({"action": "telephony.contacts.update"}, outcome.result_data)
    assert contacts_bridge._contacts["c-001"]["name"] == "Alice"

@pytest.mark.anyio
async def test_contacts_delete_rollback(contacts_service, contacts_bridge):
    outcome = await contacts_service.execute(make_cmd("android.communication.contacts.write", "telephony.contacts.delete", contact_id="c-002"))
    assert outcome.succeeded
    assert "c-002" not in contacts_bridge._contacts

    from core.android.capabilities.contacts import ContactsWriteCapability
    cap = ContactsWriteCapability(contacts_bridge)
    await cap.rollback({"action": "telephony.contacts.delete"}, outcome.result_data)
    assert "c-002" in contacts_bridge._contacts
    assert contacts_bridge._contacts["c-002"]["name"] == "Bob"


# ── Notification Integration ───────────────────────────────────────────────────

@pytest.fixture
async def notif_service(event_bus, logger, notif_bridge):
    caps = [NotificationReadCapability(notif_bridge), NotificationWriteCapability(notif_bridge)]
    return await _build_service(event_bus, logger, caps)()

@pytest.mark.anyio
async def test_notification_read_path(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.read", "notification.read"))
    assert outcome.succeeded

@pytest.mark.anyio
async def test_notification_dismiss_mutation_path(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.write", "notification.dismiss", notification_id="n-001"))
    assert outcome.succeeded
    assert "n-001" not in notif_bridge._active

@pytest.mark.anyio
async def test_notification_dismiss_rollback(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.write", "notification.dismiss", notification_id="n-002"))
    assert outcome.succeeded
    assert "n-002" not in notif_bridge._active

    from core.android.capabilities.notification import NotificationWriteCapability
    cap = NotificationWriteCapability(notif_bridge)
    await cap.rollback({"action": "notification.dismiss"}, outcome.result_data)
    assert "n-002" in notif_bridge._active

@pytest.mark.anyio
async def test_notification_clear_mutation_path(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.write", "notification.clear"))
    assert outcome.succeeded
    assert len(notif_bridge._active) == 0

@pytest.mark.anyio
async def test_notification_clear_rollback(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.write", "notification.clear"))
    assert outcome.succeeded
    assert len(notif_bridge._active) == 0

    from core.android.capabilities.notification import NotificationWriteCapability
    cap = NotificationWriteCapability(notif_bridge)
    await cap.rollback({"action": "notification.clear"}, outcome.result_data)
    assert len(notif_bridge._active) == 3

@pytest.mark.anyio
async def test_notification_reply_irreversible(notif_service, notif_bridge):
    outcome = await notif_service.execute(make_cmd("android.communication.notification.write", "notification.reply", notification_id="n-003", text="OK"))
    assert outcome.succeeded
    # No rollback attempt needed; covered by unit test supports_rollback=False
