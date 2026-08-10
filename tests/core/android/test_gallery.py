import pytest
from core.android.bridge.gallery import MockGalleryBridge
from core.android.capabilities.gallery import GalleryReadCapability, GalleryWriteCapability
from core.android.models import SecurityLevel, ConfirmationLevel

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def bridge():
    return MockGalleryBridge()

@pytest.fixture
def read_cap(bridge):
    return GalleryReadCapability(bridge)

@pytest.fixture
def write_cap(bridge):
    return GalleryWriteCapability(bridge)

def test_read_descriptor(read_cap):
    desc = read_cap.descriptor
    assert desc.id == "android.device.gallery.read"
    assert not desc.is_mutation
    assert not desc.supports_rollback

def test_write_descriptor(write_cap):
    desc = write_cap.descriptor
    assert desc.id == "android.device.gallery.write"
    assert desc.is_mutation
    assert desc.supports_rollback
    assert desc.security_level == SecurityLevel.HIGH
    assert desc.confirmation_level == ConfirmationLevel.USER

@pytest.mark.anyio
async def test_gallery_add_and_rollback(write_cap, bridge):
    res = await write_cap.execute_action({"action": "gallery.add"})
    assert res.success
    asset_id = res.data["asset_id"]
    assert asset_id in bridge._assets

    await write_cap.rollback({"action": "gallery.add"}, res.data)
    assert asset_id not in bridge._assets

@pytest.mark.anyio
async def test_gallery_delete_and_rollback(write_cap, bridge):
    bridge._assets["img-1"] = {"id": "img-1", "type": "image"}
    res = await write_cap.execute_action({"action": "gallery.delete", "asset_id": "img-1"})
    assert res.success
    assert "img-1" not in bridge._assets

    await write_cap.rollback({"action": "gallery.delete"}, res.data)
    assert "img-1" in bridge._assets
