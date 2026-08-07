"""
Comprehensive unit tests for BrightnessCapability (Milestone 16.4).

Covers:
    - Descriptor validation (all metadata fields)
    - Import safety / no forbidden imports
    - Package export
    - Every action (get, set, increase, decrease, auto_on, auto_off)
    - Argument validation (value range, type enforcement)
    - supports_rollback() for each action
    - rollback() with pre_state present (precise restoration)
    - rollback() with pre_state absent (logical inversion)
    - rollback() of auto_on / auto_off
    - Pre-state embedded in all mutating results
    - Architecture boundaries (bridge isolation, no Android APIs)
"""
import sys
import inspect
import pytest

from core.android.bridge.system import MockSystemBridge
from core.android.capabilities.brightness import BrightnessCapability
from core.android.models import ConfirmationLevel, SecurityLevel


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def bridge() -> MockSystemBridge:
    return MockSystemBridge()


@pytest.fixture
def brightness(bridge: MockSystemBridge) -> BrightnessCapability:
    return BrightnessCapability(bridge)


# ── Import safety ──────────────────────────────────────────────────────────────

def test_no_android_sdk_imports():
    """BrightnessCapability must not import any Android SDK package."""
    import core.android.capabilities.brightness as mod
    src = inspect.getsource(mod)
    forbidden = ["android.media", "android.os", "import android", "AudioManager",
                 "WindowManager", "ContentResolver"]
    for term in forbidden:
        assert term not in src, f"Forbidden import found: {term}"


def test_no_forbidden_subsystem_imports():
    """BrightnessCapability must not import brain, planner, memory, or identity."""
    import core.android.capabilities.brightness as mod
    src = inspect.getsource(mod)
    forbidden = ["core.brain", "core.planner", "core.memory", "core.identity"]
    for term in forbidden:
        assert term not in src, f"Forbidden subsystem import: {term}"


def test_brightness_capability_is_exported():
    """BrightnessCapability must appear in the capabilities package __all__."""
    from core.android import capabilities
    assert "BrightnessCapability" in capabilities.__all__
    assert hasattr(capabilities, "BrightnessCapability")


# ── Descriptor ─────────────────────────────────────────────────────────────────

def test_descriptor_id(brightness: BrightnessCapability):
    assert brightness.descriptor.id == "android.device.brightness"


def test_descriptor_name(brightness: BrightnessCapability):
    assert brightness.descriptor.name == "Brightness Control"


def test_descriptor_version(brightness: BrightnessCapability):
    assert brightness.descriptor.version == "1.0.0"


def test_descriptor_security_level(brightness: BrightnessCapability):
    assert brightness.descriptor.security_level == SecurityLevel.LOW


def test_descriptor_confirmation_level(brightness: BrightnessCapability):
    assert brightness.descriptor.confirmation_level == ConfirmationLevel.NONE


def test_descriptor_mutation_flags(brightness: BrightnessCapability):
    desc = brightness.descriptor
    assert desc.is_mutation is True
    assert desc.supports_rollback is True
    assert desc.audit_required is True
    assert desc.idempotent is False


def test_descriptor_supported_actions(brightness: BrightnessCapability):
    desc = brightness.descriptor
    assert "system.brightness.get" in desc.supported_actions
    assert "system.brightness.set" in desc.supported_actions
    assert "system.brightness.increase" in desc.supported_actions
    assert "system.brightness.decrease" in desc.supported_actions
    assert "system.brightness.auto_on" in desc.supported_actions
    assert "system.brightness.auto_off" in desc.supported_actions


def test_descriptor_is_frozen(brightness: BrightnessCapability):
    """CapabilityDescriptor must be immutable."""
    desc = brightness.descriptor
    with pytest.raises((AttributeError, TypeError)):
        desc.id = "changed"  # type: ignore


# ── brightness.get ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_get_returns_default_state(brightness, bridge):
    """brightness.get returns MockSystemBridge defaults: level=50, auto=True."""
    res = await brightness.execute_action({"action": "system.brightness.get"})
    assert res.success is True
    assert res.data["level"] == 50
    assert res.data["auto"] is True


@pytest.mark.anyio
async def test_brightness_get_reflects_bridge_state(brightness, bridge):
    bridge._brightness_level = 75
    bridge._brightness_auto = False
    res = await brightness.execute_action({"action": "system.brightness.get"})
    assert res.success is True
    assert res.data["level"] == 75
    assert res.data["auto"] is False


# ── brightness.set ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_set(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.set", "value": 80})
    assert res.success is True
    assert res.data["level"] == 80
    assert bridge._brightness_level == 80


@pytest.mark.anyio
async def test_brightness_set_to_zero(brightness, bridge):
    res = await brightness.execute_action({"action": "system.brightness.set", "value": 0})
    assert res.success is True
    assert bridge._brightness_level == 0


@pytest.mark.anyio
async def test_brightness_set_to_max(brightness, bridge):
    res = await brightness.execute_action({"action": "system.brightness.set", "value": 100})
    assert res.success is True
    assert bridge._brightness_level == 100


@pytest.mark.anyio
async def test_brightness_set_rejects_above_100(brightness):
    res = await brightness.execute_action({"action": "system.brightness.set", "value": 150})
    assert res.success is False
    assert "0-100" in res.error_message


@pytest.mark.anyio
async def test_brightness_set_rejects_below_zero(brightness):
    res = await brightness.execute_action({"action": "system.brightness.set", "value": -10})
    assert res.success is False
    assert "0-100" in res.error_message


@pytest.mark.anyio
async def test_brightness_set_rejects_missing_value(brightness):
    res = await brightness.execute_action({"action": "system.brightness.set"})
    assert res.success is False
    assert "value" in res.error_message


@pytest.mark.anyio
async def test_brightness_set_rejects_string_value(brightness):
    """Non-numeric types like 'high' must be rejected before reaching the bridge."""
    res = await brightness.execute_action({"action": "system.brightness.set", "value": "high"})
    assert res.success is False
    assert res.error_message  # any descriptive error is acceptable


@pytest.mark.anyio
async def test_brightness_set_rejects_none_value(brightness):
    res = await brightness.execute_action({"action": "system.brightness.set", "value": None})
    assert res.success is False


# ── brightness.increase ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_increase_default_step(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.increase"})
    assert res.success is True
    assert bridge._brightness_level == 60


@pytest.mark.anyio
async def test_brightness_increase_custom_step(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.increase", "step": 25})
    assert res.success is True
    assert bridge._brightness_level == 75


@pytest.mark.anyio
async def test_brightness_increase_clamps_at_max(brightness, bridge):
    bridge._brightness_level = 95
    res = await brightness.execute_action({"action": "system.brightness.increase", "step": 10})
    assert res.success is True
    assert bridge._brightness_level == 100


@pytest.mark.anyio
async def test_brightness_increase_from_100_stays_at_100(brightness, bridge):
    bridge._brightness_level = 100
    res = await brightness.execute_action({"action": "system.brightness.increase"})
    assert res.success is True
    assert bridge._brightness_level == 100


# ── brightness.decrease ────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_decrease_default_step(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.decrease"})
    assert res.success is True
    assert bridge._brightness_level == 40


@pytest.mark.anyio
async def test_brightness_decrease_custom_step(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.decrease", "step": 20})
    assert res.success is True
    assert bridge._brightness_level == 30


@pytest.mark.anyio
async def test_brightness_decrease_clamps_at_min(brightness, bridge):
    bridge._brightness_level = 5
    res = await brightness.execute_action({"action": "system.brightness.decrease", "step": 10})
    assert res.success is True
    assert bridge._brightness_level == 0


@pytest.mark.anyio
async def test_brightness_decrease_from_zero_stays_at_zero(brightness, bridge):
    bridge._brightness_level = 0
    res = await brightness.execute_action({"action": "system.brightness.decrease"})
    assert res.success is True
    assert bridge._brightness_level == 0


# ── brightness.auto_on / auto_off ──────────────────────────────────────────────

@pytest.mark.anyio
async def test_brightness_auto_on(brightness, bridge):
    bridge._brightness_auto = False
    res = await brightness.execute_action({"action": "system.brightness.auto_on"})
    assert res.success is True
    assert res.data["auto"] is True
    assert bridge._brightness_auto is True


@pytest.mark.anyio
async def test_brightness_auto_off(brightness, bridge):
    bridge._brightness_auto = True
    res = await brightness.execute_action({"action": "system.brightness.auto_off"})
    assert res.success is True
    assert res.data["auto"] is False
    assert bridge._brightness_auto is False


# ── Unsupported action ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_unsupported_action_returns_failure(brightness):
    res = await brightness.execute_action({"action": "system.brightness.strobe"})
    assert res.success is False


# ── supports_rollback ──────────────────────────────────────────────────────────

def test_supports_rollback_for_mutating_actions(brightness):
    for action in (
        "system.brightness.set",
        "system.brightness.increase",
        "system.brightness.decrease",
        "system.brightness.auto_on",
        "system.brightness.auto_off",
    ):
        assert brightness.supports_rollback({"action": action}) is True, \
            f"Expected rollback support for {action}"


def test_no_rollback_for_get(brightness):
    assert brightness.supports_rollback({"action": "system.brightness.get"}) is False


# ── rollback — precise (pre_state present) ─────────────────────────────────────

@pytest.mark.anyio
async def test_rollback_set_with_pre_state(brightness, bridge):
    """Rollback of brightness.set must restore the exact previous level."""
    bridge._brightness_level = 50

    class FakeResult:
        data = {"level": 80, "auto": True, "pre_state": {"level": 50, "auto": True}}

    await brightness.rollback({"action": "system.brightness.set", "value": 80}, FakeResult())
    assert bridge._brightness_level == 50


@pytest.mark.anyio
async def test_rollback_increase_with_pre_state(brightness, bridge):
    """Rollback of brightness.increase must restore the exact previous level."""
    bridge._brightness_level = 60

    class FakeResult:
        data = {"level": 60, "auto": True, "pre_state": {"level": 50, "auto": True}}

    await brightness.rollback({"action": "system.brightness.increase"}, FakeResult())
    assert bridge._brightness_level == 50


@pytest.mark.anyio
async def test_rollback_decrease_with_pre_state(brightness, bridge):
    """Rollback of brightness.decrease must restore the exact previous level."""
    bridge._brightness_level = 40

    class FakeResult:
        data = {"level": 40, "auto": True, "pre_state": {"level": 50, "auto": True}}

    await brightness.rollback({"action": "system.brightness.decrease"}, FakeResult())
    assert bridge._brightness_level == 50


@pytest.mark.anyio
async def test_rollback_auto_on_with_pre_state(brightness, bridge):
    """Rollback of auto_on must turn auto off if pre_state shows auto=False."""
    bridge._brightness_auto = True

    class FakeResult:
        data = {"level": 50, "auto": True, "pre_state": {"level": 50, "auto": False}}

    await brightness.rollback({"action": "system.brightness.auto_on"}, FakeResult())
    assert bridge._brightness_auto is False


@pytest.mark.anyio
async def test_rollback_auto_off_with_pre_state(brightness, bridge):
    """Rollback of auto_off must turn auto on if pre_state shows auto=True."""
    bridge._brightness_auto = False

    class FakeResult:
        data = {"level": 50, "auto": False, "pre_state": {"level": 50, "auto": True}}

    await brightness.rollback({"action": "system.brightness.auto_off"}, FakeResult())
    assert bridge._brightness_auto is True


# ── rollback — approximate (no pre_state / failure path) ──────────────────────

@pytest.mark.anyio
async def test_rollback_increase_without_pre_state(brightness, bridge):
    """Rollback of brightness.increase without pre_state falls back to decrease."""
    bridge._brightness_level = 60
    await brightness.rollback({"action": "system.brightness.increase", "step": 10}, None)
    assert bridge._brightness_level == 50


@pytest.mark.anyio
async def test_rollback_decrease_without_pre_state(brightness, bridge):
    """Rollback of brightness.decrease without pre_state falls back to increase."""
    bridge._brightness_level = 40
    await brightness.rollback({"action": "system.brightness.decrease", "step": 10}, None)
    assert bridge._brightness_level == 50


@pytest.mark.anyio
async def test_rollback_set_without_pre_state_is_noop(brightness, bridge):
    """brightness.set rollback without pre_state is a safe no-op (no prior level known)."""
    bridge._brightness_level = 80
    await brightness.rollback({"action": "system.brightness.set", "value": 80}, None)
    # level must be unchanged — no operation should have been performed
    assert bridge._brightness_level == 80


@pytest.mark.anyio
async def test_rollback_auto_on_without_pre_state(brightness, bridge):
    """Rollback of auto_on without pre_state always turns auto off."""
    bridge._brightness_auto = True
    await brightness.rollback({"action": "system.brightness.auto_on"}, None)
    assert bridge._brightness_auto is False


@pytest.mark.anyio
async def test_rollback_auto_off_without_pre_state(brightness, bridge):
    """Rollback of auto_off without pre_state always turns auto on."""
    bridge._brightness_auto = False
    await brightness.rollback({"action": "system.brightness.auto_off"}, None)
    assert bridge._brightness_auto is True


# ── Pre-state embedded in mutating results ─────────────────────────────────────

@pytest.mark.anyio
async def test_set_embeds_pre_state(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.set", "value": 80})
    assert res.success is True
    assert "pre_state" in res.data
    assert res.data["pre_state"]["level"] == 50


@pytest.mark.anyio
async def test_increase_embeds_pre_state(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.increase"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["level"] == 50


@pytest.mark.anyio
async def test_decrease_embeds_pre_state(brightness, bridge):
    bridge._brightness_level = 50
    res = await brightness.execute_action({"action": "system.brightness.decrease"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["level"] == 50


@pytest.mark.anyio
async def test_auto_on_embeds_pre_state(brightness, bridge):
    bridge._brightness_auto = False
    res = await brightness.execute_action({"action": "system.brightness.auto_on"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["auto"] is False


@pytest.mark.anyio
async def test_auto_off_embeds_pre_state(brightness, bridge):
    bridge._brightness_auto = True
    res = await brightness.execute_action({"action": "system.brightness.auto_off"})
    assert "pre_state" in res.data
    assert res.data["pre_state"]["auto"] is True


@pytest.mark.anyio
async def test_get_does_not_embed_pre_state(brightness, bridge):
    """brightness.get is read-only and must not embed pre_state."""
    res = await brightness.execute_action({"action": "system.brightness.get"})
    assert res.success is True
    assert "pre_state" not in res.data


# ── Bridge isolation ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_capability_does_not_mutate_bridge_directly(brightness, bridge):
    """BrightnessCapability must never access bridge internals — only bridge.execute()."""
    import core.android.capabilities.brightness as mod
    src = inspect.getsource(mod)
    # Capability source must not reference bridge state variables directly
    assert "_brightness_level" not in src
    assert "_brightness_auto" not in src
