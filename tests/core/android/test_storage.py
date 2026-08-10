import pytest
from core.android.bridge.storage import MockStorageBridge
from core.android.capabilities.storage import StorageReadCapability, StorageWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockStorageBridge()

@pytest.fixture
def read_cap(bridge):
    return StorageReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return StorageWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.storage.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.storage.write"
    assert desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL
    assert desc.confirmation_level == ConfirmationLevel.USER

@pytest.mark.anyio
async def test_storage_clear_cache(write_cap, bridge):
    res = await write_cap.execute_action({"action": "storage.clear_cache"})
    assert res.success
    assert bridge._cache == 0

def test_irreversible(write_cap):
    assert not write_cap.supports_rollback({"action": "storage.format"})
    assert not write_cap.supports_rollback({"action": "storage.clear_cache"})
