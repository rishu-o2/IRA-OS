"""
VolumeCapability — android.device.volume

Reference implementation for all future mutable device controls.

Design principles:
  - Stateless: no instance variables store device state.
  - Bridge-only: all hardware interaction flows through SystemBridge.execute().
  - Pre-state capture: every mutating action queries current state first and
    embeds it in the result dict under "pre_state". This gives rollback()
    the exact prior values to restore without needing instance state.
  - Self-describing: CapabilityDescriptor carries all mutation metadata so
    the MutationManager and DefaultAndroidAdapter need no capability-specific
    logic.
"""
from typing import Any, Mapping, Optional

from core.android.bridge.contracts import SystemBridge
from core.android.capabilities.base import BaseAndroidCapability
from core.android.capabilities.exceptions import InvalidArgumentError
from core.android.models import CapabilityDescriptor, ConfirmationLevel, SecurityLevel, CapabilityCategory


# ── Action constants ───────────────────────────────────────────────────────────
_VOLUME_GET = "system.volume.get"
_VOLUME_SET = "system.volume.set"
_VOLUME_UP = "system.volume.up"
_VOLUME_DOWN = "system.volume.down"
_VOLUME_MUTE = "system.volume.mute"
_VOLUME_UNMUTE = "system.volume.unmute"

# Actions that mutate state and therefore support rollback
_MUTATING_ACTIONS = frozenset({_VOLUME_SET, _VOLUME_UP, _VOLUME_DOWN, _VOLUME_MUTE, _VOLUME_UNMUTE})


class VolumeCapability(BaseAndroidCapability):
    """
    Android Volume Control capability.

    Provides full volume management through the system.volume.* bridge namespace.
    Every mutating action embeds a "pre_state" snapshot in its result so that
    rollback() can restore the exact previous volume without holding any state.

    Capability ID: android.device.volume

    Actions:
        system.volume.get     — read current level + mute state (read-only)
        system.volume.set     — set absolute volume (0-100)
        system.volume.up      — raise volume by step (default 10)
        system.volume.down    — lower volume by step (default 10)
        system.volume.mute    — mute audio output
        system.volume.unmute  — unmute audio output

    Rollback:
        set   → restore level from pre_state.level
        up    → restore level from pre_state.level
        down  → restore level from pre_state.level
        mute  → restore mute state from pre_state.muted (unmute)
        unmute→ restore mute state from pre_state.muted (mute)
    """

    def __init__(self, bridge: SystemBridge) -> None:
        self._bridge = bridge

    # ── Descriptor ────────────────────────────────────────────────────────────

    @property
    def descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            id="android.device.volume",
            name="Volume Control",
            description=(
                "Controls device media volume including absolute set, step up/down, "
                "and mute/unmute. Supports precise rollback using pre-state capture."
            ),
            version="1.0.0",
            category=CapabilityCategory.AUDIO,
            security_level=SecurityLevel.NORMAL,
            required_permissions=(),
            supported_actions=(
                _VOLUME_GET,
                _VOLUME_SET,
                _VOLUME_UP,
                _VOLUME_DOWN,
                _VOLUME_MUTE,
                _VOLUME_UNMUTE,
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

        For mutating actions (set/up/down/mute/unmute) the bridge returns a
        "pre_state" dict inside its response. This is forwarded transparently
        so rollback() can use it.

        For volume.set, the "value" argument is required; raises
        InvalidArgumentError if absent.
        """
        if action == _VOLUME_SET:
            if "value" not in arguments:
                raise InvalidArgumentError(
                    "system.volume.set requires a 'value' argument (int 0-100)."
                )
            value = int(arguments["value"])
            if not (0 <= value <= 100):
                raise InvalidArgumentError(
                    f"system.volume.set 'value' must be 0-100, got {value}."
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
        Restores the device to its pre-mutation state.

        Rollback uses pre_state from the original result when available
        (success-then-undo scenario). When original_result is None or
        lacks pre_state (failure before bridge reached hardware), rollback
        uses logical inversion of the action.

        Args:
            arguments:      The original command arguments (contains "action").
            original_result: The CapabilityResult from the original execution
                             (may be None if execution failed before completion).
        """
        action = arguments.get("action")

        # Extract pre_state from result if available (precise rollback)
        pre_state: Optional[Mapping[str, Any]] = None
        if original_result is not None and hasattr(original_result, "data"):
            pre_state = original_result.data.get("pre_state")

        if action in (_VOLUME_SET, _VOLUME_UP, _VOLUME_DOWN):
            if pre_state is not None:
                # Precise: restore exact previous volume level
                await self._bridge.execute(
                    _VOLUME_SET, {"value": pre_state["level"]}
                )
            else:
                # Approximate: invert the direction
                inverse = {
                    _VOLUME_SET: None,       # can't invert without pre-state; no-op
                    _VOLUME_UP: _VOLUME_DOWN,
                    _VOLUME_DOWN: _VOLUME_UP,
                }
                inv_action = inverse.get(action)
                if inv_action:
                    await self._bridge.execute(
                        inv_action, {"step": arguments.get("step", 10)}
                    )
        elif action == _VOLUME_MUTE:
            if pre_state is not None and not pre_state.get("muted", False):
                await self._bridge.execute(_VOLUME_UNMUTE)
            else:
                # Logical inversion
                await self._bridge.execute(_VOLUME_UNMUTE)
        elif action == _VOLUME_UNMUTE:
            if pre_state is not None and pre_state.get("muted", True):
                await self._bridge.execute(_VOLUME_MUTE)
            else:
                await self._bridge.execute(_VOLUME_MUTE)
