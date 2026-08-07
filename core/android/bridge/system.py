from typing import Any, Mapping, Optional

from core.android.capabilities.exceptions import UnsupportedPlatformError
from .contracts import SystemBridge


class MockSystemBridge(SystemBridge):
    """
    Mock implementation of the SystemBridge.

    Simulates device hardware services deterministically for testing.
    Maintains independent state for each sub-domain (flashlight, volume).
    """

    # ── Defaults ──────────────────────────────────────────────────────────────
    _DEFAULT_VOLUME: int = 50
    _VOLUME_STEP: int = 10
    _MIN_VOLUME: int = 0
    _MAX_VOLUME: int = 100

    def __init__(self) -> None:
        super().__init__()
        # Flashlight state
        self._flashlight_on: bool = False
        # Volume state
        self._volume_level: int = self._DEFAULT_VOLUME
        self._volume_muted: bool = False
        # Brightness state
        self._brightness_level: int = 50
        self._brightness_auto: bool = True
        # Vibrate state
        self._is_vibrating: bool = False
        # DND state
        self._dnd_mode: str = "OFF"
        # Rotation state
        self._rotation_locked: bool = False
        self._rotation_orientation: str = "PORTRAIT"
        # Screen timeout state
        self._screen_timeout_ms: int = 60000
        self._supported_timeouts = [15000, 30000, 60000, 120000, 300000, 600000, 1800000]

    # ── Execute dispatcher ─────────────────────────────────────────────────────

    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        args = arguments or {}

        # ── Legacy actions (kept for backward-compat) ─────────────────────────
        if action == "battery.read":
            return {"level": 85, "is_charging": False}
        if action == "clipboard.read":
            return {"text": "mocked clipboard content"}

        # ── Flashlight ────────────────────────────────────────────────────────
        if action == "system.flashlight.status":
            return {"enabled": self._flashlight_on}
        if action == "system.flashlight.on":
            self._flashlight_on = True
            return {"enabled": True}
        if action == "system.flashlight.off":
            self._flashlight_on = False
            return {"enabled": False}
        if action == "system.flashlight.toggle":
            self._flashlight_on = not self._flashlight_on
            return {"enabled": self._flashlight_on}

        # ── Volume ────────────────────────────────────────────────────────────
        if action == "system.volume.get":
            return {
                "level": self._volume_level,
                "muted": self._volume_muted,
            }
        if action == "system.volume.set":
            value = int(args.get("value", self._volume_level))
            pre_level, pre_muted = self._volume_level, self._volume_muted
            self._volume_level = max(self._MIN_VOLUME, min(self._MAX_VOLUME, value))
            return {
                "level": self._volume_level,
                "muted": self._volume_muted,
                "pre_state": {"level": pre_level, "muted": pre_muted},
            }
        if action == "system.volume.up":
            step = int(args.get("step", self._VOLUME_STEP))
            pre_level, pre_muted = self._volume_level, self._volume_muted
            self._volume_level = min(self._MAX_VOLUME, self._volume_level + step)
            return {
                "level": self._volume_level,
                "muted": self._volume_muted,
                "pre_state": {"level": pre_level, "muted": pre_muted},
            }
        if action == "system.volume.down":
            step = int(args.get("step", self._VOLUME_STEP))
            pre_level, pre_muted = self._volume_level, self._volume_muted
            self._volume_level = max(self._MIN_VOLUME, self._volume_level - step)
            return {
                "level": self._volume_level,
                "muted": self._volume_muted,
                "pre_state": {"level": pre_level, "muted": pre_muted},
            }
        if action == "system.volume.mute":
            pre_level, pre_muted = self._volume_level, self._volume_muted
            self._volume_muted = True
            return {
                "level": self._volume_level,
                "muted": True,
                "pre_state": {"level": pre_level, "muted": pre_muted},
            }
        if action == "system.volume.unmute":
            pre_level, pre_muted = self._volume_level, self._volume_muted
            self._volume_muted = False
            return {
                "level": self._volume_level,
                "muted": False,
                "pre_state": {"level": pre_level, "muted": pre_muted},
            }

        # ── Brightness ────────────────────────────────────────────────────────
        if action == "system.brightness.get":
            return {
                "level": self._brightness_level,
                "auto": self._brightness_auto,
            }
        if action == "system.brightness.set":
            value = int(args.get("value", self._brightness_level))
            pre_level, pre_auto = self._brightness_level, self._brightness_auto
            self._brightness_level = max(0, min(100, value))
            return {
                "level": self._brightness_level,
                "auto": self._brightness_auto,
                "pre_state": {"level": pre_level, "auto": pre_auto},
            }
        if action == "system.brightness.increase":
            step = int(args.get("step", 10))
            pre_level, pre_auto = self._brightness_level, self._brightness_auto
            self._brightness_level = min(100, self._brightness_level + step)
            return {
                "level": self._brightness_level,
                "auto": self._brightness_auto,
                "pre_state": {"level": pre_level, "auto": pre_auto},
            }
        if action == "system.brightness.decrease":
            step = int(args.get("step", 10))
            pre_level, pre_auto = self._brightness_level, self._brightness_auto
            self._brightness_level = max(0, self._brightness_level - step)
            return {
                "level": self._brightness_level,
                "auto": self._brightness_auto,
                "pre_state": {"level": pre_level, "auto": pre_auto},
            }
        if action == "system.brightness.auto_on":
            pre_level, pre_auto = self._brightness_level, self._brightness_auto
            self._brightness_auto = True
            return {
                "level": self._brightness_level,
                "auto": True,
                "pre_state": {"level": pre_level, "auto": pre_auto},
            }
        if action == "system.brightness.auto_off":
            pre_level, pre_auto = self._brightness_level, self._brightness_auto
            self._brightness_auto = False
            return {
                "level": self._brightness_level,
                "auto": False,
                "pre_state": {"level": pre_level, "auto": pre_auto},
            }

        # ── Vibrate ──────────────────────────────────────────────────────────
        if action == "system.vibrate.start":
            self._is_vibrating = True
            return {"success": True}
        if action == "system.vibrate.cancel":
            self._is_vibrating = False
            return {"success": True}

        # ── Do Not Disturb ───────────────────────────────────────────────────
        if action == "system.dnd.get":
            return {"mode": self._dnd_mode}
        if action == "system.dnd.set":
            mode = args.get("mode", "OFF")
            pre_mode = self._dnd_mode
            self._dnd_mode = mode
            return {
                "mode": self._dnd_mode,
                "pre_state": {"mode": pre_mode}
            }

        # ── Rotation ─────────────────────────────────────────────────────────
        if action == "system.rotation.get":
            return {
                "locked": self._rotation_locked,
                "orientation": self._rotation_orientation
            }
        if action == "system.rotation.lock":
            orientation = args.get("orientation", self._rotation_orientation)
            pre_locked = self._rotation_locked
            pre_orientation = self._rotation_orientation
            self._rotation_locked = True
            self._rotation_orientation = orientation
            return {
                "locked": True,
                "orientation": self._rotation_orientation,
                "pre_state": {"locked": pre_locked, "orientation": pre_orientation}
            }
        if action == "system.rotation.unlock":
            pre_locked = self._rotation_locked
            pre_orientation = self._rotation_orientation
            self._rotation_locked = False
            return {
                "locked": False,
                "orientation": self._rotation_orientation,
                "pre_state": {"locked": pre_locked, "orientation": pre_orientation}
            }

        # ── Screen Timeout ───────────────────────────────────────────────────
        if action == "system.screen_timeout.get":
            return {"duration_ms": self._screen_timeout_ms}
        if action == "system.screen_timeout.get_supported":
            return {"supported": self._supported_timeouts}
        if action == "system.screen_timeout.set":
            duration_ms = args.get("duration_ms", self._screen_timeout_ms)
            pre_duration = self._screen_timeout_ms
            self._screen_timeout_ms = duration_ms
            return {
                "duration_ms": self._screen_timeout_ms,
                "pre_state": {"duration_ms": pre_duration}
            }

        raise UnsupportedPlatformError(
            f"MockSystemBridge does not support action: {action}"
        )

