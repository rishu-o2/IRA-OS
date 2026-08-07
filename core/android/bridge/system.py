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

        raise UnsupportedPlatformError(
            f"MockSystemBridge does not support action: {action}"
        )

