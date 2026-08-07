from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional


class BaseBridge(ABC):
    """
    Base contract for all domain-specific Android bridges.
    Capabilities MUST NOT call specific native API methods.
    They must only call `execute()` with an action and arguments.
    """

    @abstractmethod
    async def execute(self, action: str, arguments: Optional[Mapping[str, Any]] = None) -> Any:
        """
        Executes an action through the bridge.
        """
        pass


class SystemBridge(BaseBridge):
    """
    Bridge for device state and core system data.
    Sub-domains: battery, clipboard, device info, storage, time, flashlight, volume.

    Action Namespace: system.*

    Flashlight Actions:
    - system.flashlight.on
    - system.flashlight.off
    - system.flashlight.toggle
    - system.flashlight.status

    Volume Actions:
    - system.volume.get
    - system.volume.set       (args: {"value": int 0-100})
    - system.volume.up        (args: {"step": int, default 10})
    - system.volume.down      (args: {"step": int, default 10})
    - system.volume.mute
    - system.volume.unmute
    """
    pass



class NetworkBridge(BaseBridge):
    """
    Bridge for networking radios.
    Sub-domains: wifi, bluetooth, hotspot, mobile network.
    """
    pass


class LocationBridge(BaseBridge):
    """
    Bridge for positioning and geocoding.
    Sub-domains: coarse, fine, geocoder.
    """
    pass


class TelephonyBridge(BaseBridge):
    """
    Bridge for telephony features.
    Sub-domains: calls, sms, contacts.
    """
    pass


class MediaBridge(BaseBridge):
    """
    Bridge for media capture and playback.
    Sub-domains: camera, gallery, microphone.
    """
    pass


class NotificationBridge(BaseBridge):
    """Bridge for reading and managing notifications."""
    pass


class SettingsBridge(BaseBridge):
    """Bridge for modifying device settings."""
    pass


class FilesBridge(BaseBridge):
    """Bridge for local and external file management."""
    pass


class SensorsBridge(BaseBridge):
    """Bridge for reading raw sensors (accelerometer, gyroscope)."""
    pass
