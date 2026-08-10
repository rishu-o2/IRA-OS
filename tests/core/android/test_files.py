import pytest
from core.android.bridge.files import MockFileBridge
from core.android.capabilities.files import FilesReadCapability, FilesWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockFileBridge()

@pytest.fixture
def read_cap(bridge):
    return FilesReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return FilesWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.files.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.files.write"
    assert desc.is_mutation
    assert desc.supports_rollback
    assert desc.security_level == SecurityLevel.HIGH
    assert desc.confirmation_level == ConfirmationLevel.USER

@pytest.mark.anyio
async def test_files_create_and_rollback(write_cap, bridge):
    # Create
    res = await write_cap.execute_action({"action": "files.create", "path": "/test.txt", "content": "hello"})
    assert res.success
    assert "/test.txt" in bridge._fs

    # Rollback
    await write_cap.rollback({"action": "files.create"}, res.data)
    assert "/test.txt" not in bridge._fs

@pytest.mark.anyio
async def test_files_write_and_rollback(write_cap, bridge):
    bridge._fs["/test.txt"] = {"content": "hello"}
    # Write
    res = await write_cap.execute_action({"action": "files.write", "path": "/test.txt", "content": "world"})
    assert res.success
    assert bridge._fs["/test.txt"]["content"] == "world"

    # Rollback
    await write_cap.rollback({"action": "files.write"}, res.data)
    assert bridge._fs["/test.txt"]["content"] == "hello"

@pytest.mark.anyio
async def test_files_delete_and_rollback(write_cap, bridge):
    bridge._fs["/test.txt"] = {"content": "hello"}
    # Delete
    res = await write_cap.execute_action({"action": "files.delete", "path": "/test.txt"})
    assert res.success
    assert "/test.txt" not in bridge._fs

    # Rollback
    await write_cap.rollback({"action": "files.delete"}, res.data)
    assert "/test.txt" in bridge._fs
    assert bridge._fs["/test.txt"]["content"] == "hello"

@pytest.mark.anyio
async def test_files_rename_and_rollback(write_cap, bridge):
    bridge._fs["/test.txt"] = {"content": "hello"}
    # Rename
    res = await write_cap.execute_action({"action": "files.rename", "source": "/test.txt", "destination": "/new.txt"})
    assert res.success
    assert "/test.txt" not in bridge._fs
    assert "/new.txt" in bridge._fs

    # Rollback
    await write_cap.rollback({"action": "files.rename"}, res.data)
    assert "/new.txt" not in bridge._fs
    assert "/test.txt" in bridge._fs

def test_supports_rollback(write_cap):
    assert write_cap.supports_rollback({"action": "files.create"})
    assert write_cap.supports_rollback({"action": "files.delete"})
