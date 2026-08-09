"""
Unit tests for Pack C: Contacts Capabilities
Tests descriptor correctness, CRUD action handling, security/confirmation levels,
rollback for create/update/delete.
"""
import pytest
from core.android.bridge.telephony import MockContactsBridge
from core.android.capabilities.contacts import ContactsReadCapability, ContactsWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def contacts_bridge():
    return MockContactsBridge()

@pytest.fixture
def read_cap(contacts_bridge):
    return ContactsReadCapability(contacts_bridge)

@pytest.fixture
def write_cap(contacts_bridge):
    return ContactsWriteCapability(contacts_bridge)


# ── Descriptor Tests ───────────────────────────────────────────────────────────

def test_read_descriptor_id(read_cap):
    assert read_cap.descriptor.id == "android.communication.contacts.read"

def test_read_is_not_mutation(read_cap):
    assert read_cap.descriptor.is_mutation is False

def test_read_security_normal(read_cap):
    assert read_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_read_confirmation_none(read_cap):
    assert read_cap.descriptor.confirmation_level == ConfirmationLevel.NONE

def test_write_descriptor_id(write_cap):
    assert write_cap.descriptor.id == "android.communication.contacts.write"

def test_write_is_mutation(write_cap):
    assert write_cap.descriptor.is_mutation is True

def test_write_supports_rollback_descriptor(write_cap):
    assert write_cap.descriptor.supports_rollback is True

def test_write_security_normal(write_cap):
    assert write_cap.descriptor.security_level == SecurityLevel.NORMAL

def test_write_confirmation_user(write_cap):
    assert write_cap.descriptor.confirmation_level == ConfirmationLevel.USER

def test_write_audit_required(write_cap):
    assert write_cap.descriptor.audit_required is True

def test_write_supported_actions(write_cap):
    actions = set(write_cap.descriptor.supported_actions)
    assert "telephony.contacts.create" in actions
    assert "telephony.contacts.update" in actions
    assert "telephony.contacts.delete" in actions


# ── Read Action Handling ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_read_all_contacts(read_cap, contacts_bridge):
    result = await read_cap.execute_action({"action": "telephony.contacts.read"})
    assert result.success
    assert len(result.data) == 2

@pytest.mark.anyio
async def test_read_single_contact(read_cap, contacts_bridge):
    result = await read_cap.execute_action({"action": "telephony.contacts.read", "contact_id": "c-001"})
    assert result.success
    assert result.data["name"] == "Alice"

@pytest.mark.anyio
async def test_search_contacts(read_cap, contacts_bridge):
    result = await read_cap.execute_action({"action": "telephony.contacts.search", "query": "bob"})
    assert result.success
    assert any(c["name"] == "Bob" for c in result.data)


# ── Write Action Handling ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_create_contact(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.create", "name": "Charlie", "number": "+3333333333"})
    assert result.success
    assert len(contacts_bridge._contacts) == 3

@pytest.mark.anyio
async def test_create_contact_missing_name(write_cap):
    result = await write_cap.execute_action({"action": "telephony.contacts.create", "number": "+3333333333"})
    assert not result.success

@pytest.mark.anyio
async def test_update_contact(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.update", "contact_id": "c-001", "name": "Alicia"})
    assert result.success
    assert contacts_bridge._contacts["c-001"]["name"] == "Alicia"

@pytest.mark.anyio
async def test_delete_contact(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.delete", "contact_id": "c-001"})
    assert result.success
    assert "c-001" not in contacts_bridge._contacts


# ── Rollback Tests ─────────────────────────────────────────────────────────────

def test_all_write_actions_support_rollback(write_cap):
    for action in ("telephony.contacts.create", "telephony.contacts.update", "telephony.contacts.delete"):
        assert write_cap.supports_rollback({"action": action}) is True

@pytest.mark.anyio
async def test_create_rollback_removes_contact(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.create", "name": "Temp", "number": "+0000"})
    assert result.success
    contact_id = result.data["contact_id"]
    assert contact_id in contacts_bridge._contacts

    await write_cap.rollback({"action": "telephony.contacts.create"}, result.data)
    assert contact_id not in contacts_bridge._contacts

@pytest.mark.anyio
async def test_update_rollback_restores_previous_name(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.update", "contact_id": "c-001", "name": "Alicia"})
    assert result.success
    assert contacts_bridge._contacts["c-001"]["name"] == "Alicia"

    await write_cap.rollback({"action": "telephony.contacts.update"}, result.data)
    assert contacts_bridge._contacts["c-001"]["name"] == "Alice"

@pytest.mark.anyio
async def test_delete_rollback_restores_contact(write_cap, contacts_bridge):
    result = await write_cap.execute_action({"action": "telephony.contacts.delete", "contact_id": "c-002"})
    assert result.success
    assert "c-002" not in contacts_bridge._contacts

    await write_cap.rollback({"action": "telephony.contacts.delete"}, result.data)
    assert "c-002" in contacts_bridge._contacts
    assert contacts_bridge._contacts["c-002"]["name"] == "Bob"
