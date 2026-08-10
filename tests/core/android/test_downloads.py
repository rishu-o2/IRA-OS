import pytest
from core.android.bridge.downloads import MockDownloadBridge
from core.android.capabilities.downloads import DownloadsReadCapability, DownloadsWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockDownloadBridge()

@pytest.fixture
def read_cap(bridge):
    return DownloadsReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return DownloadsWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.downloads.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.downloads.write"
    assert desc.is_mutation
    assert desc.supports_rollback
    assert desc.security_level == SecurityLevel.NORMAL
    assert desc.confirmation_level == ConfirmationLevel.USER

@pytest.mark.anyio
async def test_downloads_pause_and_rollback(write_cap, bridge):
    bridge._downloads["dl-1"] = {"id": "dl-1", "url": "http", "status": "downloading"}
    res = await write_cap.execute_action({"action": "downloads.pause", "download_id": "dl-1"})
    assert res.success
    assert bridge._downloads["dl-1"]["status"] == "paused"

    await write_cap.rollback({"action": "downloads.pause"}, res.data)
    assert bridge._downloads["dl-1"]["status"] == "downloading"

def test_irreversible(write_cap):
    assert not write_cap.supports_rollback({"action": "downloads.start"})
    assert not write_cap.supports_rollback({"action": "downloads.cancel"})
    assert not write_cap.supports_rollback({"action": "downloads.delete"})
    assert write_cap.supports_rollback({"action": "downloads.pause"})
    assert write_cap.supports_rollback({"action": "downloads.resume"})
