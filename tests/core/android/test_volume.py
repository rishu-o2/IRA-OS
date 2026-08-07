"""
Comprehensive unit tests for VolumeCapability (Milestone 16.3).

Covers:
    - Descriptor validation (all metadata fields)
    - Import safety / no forbidden imports
    - Every action (get, set, up, down, mute, unmute)
    - Argument validation (volume.set range enforcement)
    - supports_rollback() for each action
    - rollback() with pre_state present (precise restoration)
    - rollback() with pre_state absent (logical inversion)
    - rollback() of mute/unmute
    - Architecture boundaries (bridge isolation, no Android APIs)
"""
import sys
import inspect
import pytest

from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.volume import VolumeCapability
from core.android.models import ConfirmationLevel, SecurityLevel


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def bridge() -> MockSystemBridge:
    return MockSystemBridge()


@pytest.fixture
def volume(bridge: MockSystemBridge) -> VolumeCapability:
    return VolumeCapability(bridge)


# ── Import safety ──────────────────────────────────────────────────────────────

def test_no_android_sdk_imports():
    """VolumeCapability must not import any Android SDK package."""
    import core.android.capabilities.volume as vol_module
    src = inspect.getsource(vol_module)
    forbidden = ["android.media", "android.os", "import android", "AudioManager"]
    for term in forbidden:
        assert term not in src, f"Forbidden import found: {term}"


def test_no_forbidden_subsystem_imports():
    """VolumeCapability must not import brain, planner, memory, or identity."""
    import core.android.capabilities.volume as vol_module
    src = inspect.getsource(vol_module)
    forbidden = ["core.brain", "core.planner", "core.memory", "core.identity"]
    for term in forbidden:
        assert term not in src, f"Forbidden subsystem import: {term}"


def test_volume_capability_is_exported():
    """VolumeCapability must appear in the capabilities package __all__."""
    from core.android import capabilities
    assert "VolumeCapability" in capabilities.__all__
    assert hasattr(capabilities, "VolumeCapability")


# ── Descriptor ─────────────────────────────────────────────────────────────────

def test_descriptor_id(volume: VolumeCapability):
    assert volume.descriptor.id == "android.device.volume"


def test_descriptor_security_level(volume: VolumeCapability):
    assert volume.descriptor.security_level == SecurityLevel.NORMAL


def test_descriptor_confirmation_level(volume: VolumeCapability):
    assert volume.descriptor.confirmation_level == ConfirmationLevel.NONE


def test_descriptor_mutation_flags(volume: VolumeCapability):
    desc = volume.descriptor
    assert desc.is_mutation is True
    assert desc.supports_rollback is True
    assert desc.audit_required is True
    assert desc.idempotent is False


def test_descriptor_supported_actions(volume: VolumeCapability):
    desc = volume.descriptor
    assert "system.volume.get" in desc.supported_actions
    assert "system.volume.set" in desc.supported_actions
    assert "system.volume.up" in desc.supported_actions
    assert "system.volume.down" in desc.supported_actions
    assert "system.volume.mute" in desc.supported_actions
    assert "system.volume.unmute" in desc.supported_actions


def test_descriptor_is_frozen(volume: VolumeCapability):
    desc = volume.descriptor
    with pytest.raises((AttributeError, TypeError)):
        desc.id = "changed"  # type: ignore


# ── volume.get ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_get_returns_current_state(volume: VolumeCapability, bridge: MockSystemBridge):
    res = await volume.execute_action({"action": "system.volume.get"})
    assert res.success is True
    assert res.data["level"] == 50      # MockSystemBridge default
    assert res.data["muted"] is False


# ── volume.set ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_set(volume: VolumeCapability, bridge: MockSystemBridge):
    res = await volume.execute_action({"action": "system.volume.set", "value": 75})
    assert res.success is True
    assert res.data["level"] == 75
    assert bridge._volume_level == 75


@pytest.mark.anyio
async def test_volume_set_clamps_at_max(volume: VolumeCapability, bridge: MockSystemBridge):
    res = await volume.execute_action({"action": "system.volume.set", "value": 150})
    assert res.success is False  # InvalidArgumentError from capability


@pytest.mark.anyio
async def test_volume_set_clamps_at_min(volume: VolumeCapability, bridge: MockSystemBridge):
    res = await volume.execute_action({"action": "system.volume.set", "value": -10})
    assert res.success is False  # InvalidArgumentError from capability


@pytest.mark.anyio
async def test_volume_set_missing_value(volume: VolumeCapability, bridge: MockSystemBridge):
    res = await volume.execute_action({"action": "system.volume.set"})
    assert res.success is False
    assert "value" in res.error_message


# ── volume.up ──────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_up_default_step(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 50
    res = await volume.execute_action({"action": "system.volume.up"})
    assert res.success is True
    assert bridge._volume_level == 60


@pytest.mark.anyio
async def test_volume_up_custom_step(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 50
    res = await volume.execute_action({"action": "system.volume.up", "step": 25})
    assert res.success is True
    assert bridge._volume_level == 75


@pytest.mark.anyio
async def test_volume_up_clamps_at_max(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 95
    res = await volume.execute_action({"action": "system.volume.up", "step": 10})
    assert res.success is True
    assert bridge._volume_level == 100


# ── volume.down ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_down_default_step(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 50
    res = await volume.execute_action({"action": "system.volume.down"})
    assert res.success is True
    assert bridge._volume_level == 40


@pytest.mark.anyio
async def test_volume_down_clamps_at_min(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 5
    res = await volume.execute_action({"action": "system.volume.down", "step": 10})
    assert res.success is True
    assert bridge._volume_level == 0


# ── volume.mute / unmute ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_mute(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_muted = False
    res = await volume.execute_action({"action": "system.volume.mute"})
    assert res.success is True
    assert res.data["muted"] is True
    assert bridge._volume_muted is True


@pytest.mark.anyio
async def test_volume_unmute(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_muted = True
    res = await volume.execute_action({"action": "system.volume.unmute"})
    assert res.success is True
    assert res.data["muted"] is False
    assert bridge._volume_muted is False


# ── supports_rollback ──────────────────────────────────────────────────────────

def test_supports_rollback_for_mutating_actions(volume: VolumeCapability):
    for action in ("system.volume.set", "system.volume.up", "system.volume.down",
                   "system.volume.mute", "system.volume.unmute"):
        assert volume.supports_rollback({"action": action}) is True


def test_no_rollback_for_get(volume: VolumeCapability):
    assert volume.supports_rollback({"action": "system.volume.get"}) is False


# ── rollback — precise (pre_state present) ────────────────────────────────────

@pytest.mark.anyio
async def test_rollback_set_with_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.set must restore exact previous level."""
    bridge._volume_level = 50

    class FakeResult:
        data = {"level": 75, "muted": False, "pre_state": {"level": 50, "muted": False}}

    await volume.rollback({"action": "system.volume.set", "value": 75}, FakeResult())
    assert bridge._volume_level == 50


@pytest.mark.anyio
async def test_rollback_up_with_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.up must restore exact previous level."""
    bridge._volume_level = 60

    class FakeResult:
        data = {"level": 60, "muted": False, "pre_state": {"level": 50, "muted": False}}

    await volume.rollback({"action": "system.volume.up"}, FakeResult())
    assert bridge._volume_level == 50


@pytest.mark.anyio
async def test_rollback_mute_with_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.mute must unmute if pre_state shows unmuted."""
    bridge._volume_muted = True

    class FakeResult:
        data = {"level": 50, "muted": True, "pre_state": {"level": 50, "muted": False}}

    await volume.rollback({"action": "system.volume.mute"}, FakeResult())
    assert bridge._volume_muted is False


@pytest.mark.anyio
async def test_rollback_unmute_with_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.unmute must re-mute if pre_state shows muted."""
    bridge._volume_muted = False

    class FakeResult:
        data = {"level": 50, "muted": False, "pre_state": {"level": 50, "muted": True}}

    await volume.rollback({"action": "system.volume.unmute"}, FakeResult())
    assert bridge._volume_muted is True


# ── rollback — approximate (no pre_state / failure path) ──────────────────────

@pytest.mark.anyio
async def test_rollback_up_without_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.up without pre_state falls back to volume.down."""
    bridge._volume_level = 60
    await volume.rollback({"action": "system.volume.up", "step": 10}, None)
    assert bridge._volume_level == 50


@pytest.mark.anyio
async def test_rollback_down_without_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.down without pre_state falls back to volume.up."""
    bridge._volume_level = 40
    await volume.rollback({"action": "system.volume.down", "step": 10}, None)
    assert bridge._volume_level == 50


@pytest.mark.anyio
async def test_rollback_mute_without_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    """Rollback of volume.mute without pre_state always unmutes."""
    bridge._volume_muted = True
    await volume.rollback({"action": "system.volume.mute"}, None)
    assert bridge._volume_muted is False


# ── Pre-state in result data ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_volume_set_embeds_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 50
    res = await volume.execute_action({"action": "system.volume.set", "value": 80})
    assert res.success is True
    assert "pre_state" in res.data
    assert res.data["pre_state"]["level"] == 50


@pytest.mark.anyio
async def test_volume_up_embeds_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_level = 50
    res = await volume.execute_action({"action": "system.volume.up"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["level"] == 50


@pytest.mark.anyio
async def test_volume_mute_embeds_pre_state(volume: VolumeCapability, bridge: MockSystemBridge):
    bridge._volume_muted = False
    res = await volume.execute_action({"action": "system.volume.mute"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["muted"] is False
