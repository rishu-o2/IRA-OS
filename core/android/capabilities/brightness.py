"""
BrightnessCapability — android.device.brightness

Production-grade kernel capability for Android screen brightness control.

Design principles:
  - Stateless: no instance variables store device state.
  - Bridge-only: all hardware interaction flows through SystemBridge.execute().
  - Pre-state capture: every mutating action embeds a "pre_state" snapshot
    in the bridge response. rollback() reads this to restore the exact prior
    level and auto-mode without holding any instance state.
  - Self-describing: CapabilityDescriptor carries all mutation metadata so
    MutationManager and DefaultAndroidAdapter need zero capability-specific
    logic.
  - Input validation: invalid values (out-of-range, non-numeric) are rejected
    at the capability layer before they ever reach the bridge.
"""
from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory


# ── Action constants ───────────────────────────────────────────────────────────
_BRIGHTNESS_GET = "system.brightness.get"
_BRIGHTNESS_SET = "system.brightness.set"
_BRIGHTNESS_INCREASE = "system.brightness.increase"
_BRIGHTNESS_DECREASE = "system.brightness.decrease"
_BRIGHTNESS_AUTO_ON = "system.brightness.auto_on"
_BRIGHTNESS_AUTO_OFF = "system.brightness.auto_off"

# Actions that mutate device state and therefore support rollback
_MUTATING_ACTIONS = frozenset({
    _BRIGHTNESS_SET,
    _BRIGHTNESS_INCREASE,
    _BRIGHTNESS_DECREASE,
    _BRIGHTNESS_AUTO_ON,
    _BRIGHTNESS_AUTO_OFF,
})


class BrightnessCapability(BaseAndroidCapability):
    """
    Android Screen Brightness Control capability.

    Provides complete brightness management through the system.brightness.*
    bridge namespace. Every mutating action embeds a "pre_state" snapshot in
    its result so that rollback() can restore the exact previous brightness
    level and auto-mode state without holding any instance state.

    Capability ID: android.device.brightness

    Actions:
        system.brightness.get       — read current level + auto mode (read-only)
        system.brightness.set       — set absolute brightness (0-100)
        system.brightness.increase  — raise brightness by step (default 10)
        system.brightness.decrease  — lower brightness by step (default 10)
        system.brightness.auto_on   — enable auto-brightness
        system.brightness.auto_off  — disable auto-brightness

    Rollback:
        set      → restore level from pre_state.level
        increase → restore level from pre_state.level
        decrease → restore level from pre_state.level
        auto_on  → restore auto mode from pre_state.auto (auto_off)
        auto_off → restore auto mode from pre_state.auto (auto_on)
    """

    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    # ── Descriptor ────────────────────────────────────────────────────────────

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.brightness",
            name="Brightness Control",
            description=(
                "Controls device screen brightness including absolute set, "
                "step increase/decrease, and auto-brightness toggle. "
                "Supports precise rollback using pre-state capture."
            ),
            version="1.0.0",
            category=CapabilityCategory.DISPLAY,
            security_level=SecurityLevel.LOW,
            required_permissions=(),
            supported_actions=(
                _BRIGHTNESS_GET,
                _BRIGHTNESS_SET,
                _BRIGHTNESS_INCREASE,
                _BRIGHTNESS_DECREASE,
                _BRIGHTNESS_AUTO_ON,
                _BRIGHTNESS_AUTO_OFF,
            ),
            is_mutation=True,
            supports_rollback=True,
            audit_required=True,
            confirmation_level=ConfirmationLevel.NONE,
            idempotent=False,
        )

    # ── Core execution ─────────────────────────────────────────────────────────

    async def _execute_internal(
        self, action: str, arguments: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """
        Dispatches the action to SystemBridge.

        For mutating actions (set/increase/decrease/auto_on/auto_off) the bridge
        returns a "pre_state" dict inside its response. This is forwarded
        transparently so rollback() can use it.

        For brightness.set, the "value" argument is required and must be an
        integer in the range 0–100; raises InvalidArgumentError otherwise.
        Non-numeric types (e.g. "high") are rejected before reaching the bridge.
        """
        if action == _BRIGHTNESS_SET:
            if "value" not in arguments:
                raise InvalidArgumentError(
                    "system.brightness.set requires a 'value' argument (int 0-100)."
                )
            raw = arguments["value"]
            if not isinstance(raw, (int, float)):
                raise InvalidArgumentError(
                    f"system.brightness.set 'value' must be a number, "
                    f"got {type(raw).__name__}."
                )
            value = int(raw)
            if not (0 <= value <= 100):
                raise InvalidArgumentError(
                    f"system.brightness.set 'value' must be 0-100, got {value}."
                )

        return await self._bridge.execute(action, arguments)

    # ── Rollback ───────────────────────────────────────────────────────────────

    def supports_rollback(self, arguments: Mapping[str, Any]) -> bool:
        """Returns True for all mutating actions."""
        return arguments.get("action") in _MUTATING_ACTIONS

    async def rollback(
        self,
        arguments: Mapping[str, Any],
        original_result: Any,
    ) -> None:
        """
        Restores the device to its pre-mutation brightness state.

        Rollback strategy:
        - If original_result carries pre_state → precise restoration of the
          exact level and auto-mode that existed before the mutation.
        - If original_result is None or lacks pre_state (execution failed
          before the bridge was reached) → logical inversion of the action.

        Args:
            arguments:       The original command arguments (contains "action").
            original_result: The CapabilityResult from the original execution
                             (may be None if execution failed before completion).
        """
        action = arguments.get("action")

        # Extract pre_state from result if available (precise rollback path)
        pre_state: Optional[Mapping[str, Any]] = None
        if original_result is not None and hasattr(original_result, "data"):
            pre_state = original_result.data.get("pre_state")

        if action in (_BRIGHTNESS_SET, _BRIGHTNESS_INCREASE, _BRIGHTNESS_DECREASE):
            if pre_state is not None:
                # Precise: restore the exact previous brightness level
                await self._bridge.execute(
                    _BRIGHTNESS_SET, {"value": pre_state["level"]}
                )
            else:
                # Approximate: invert the step direction
                # brightness.set has no safe inverse without knowing the prior level
                inverse = {
                    _BRIGHTNESS_SET: None,
                    _BRIGHTNESS_INCREASE: _BRIGHTNESS_DECREASE,
                    _BRIGHTNESS_DECREASE: _BRIGHTNESS_INCREASE,
                }
                inv_action = inverse.get(action)
                if inv_action:
                    await self._bridge.execute(
                        inv_action, {"step": arguments.get("step", 10)}
                    )

        elif action == _BRIGHTNESS_AUTO_ON:
            if pre_state is not None and not pre_state.get("auto", True):
                # Was manual before — restore manual mode
                await self._bridge.execute(_BRIGHTNESS_AUTO_OFF, {})
            else:
                # Logical inversion fallback
                await self._bridge.execute(_BRIGHTNESS_AUTO_OFF, {})

        elif action == _BRIGHTNESS_AUTO_OFF:
            if pre_state is not None and pre_state.get("auto", False):
                # Was auto before — restore auto mode
                await self._bridge.execute(_BRIGHTNESS_AUTO_ON, {})
            else:
                # Logical inversion fallback
                await self._bridge.execute(_BRIGHTNESS_AUTO_ON, {})
