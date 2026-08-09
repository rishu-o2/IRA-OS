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
    Sub-domains: battery, clipboard, device info, storage, time, flashlight,
    volume, brightness, vibrate, dnd, rotation, screen_timeout.

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

    Brightness Actions:
    - system.brightness.get
    - system.brightness.set       (args: {"value": int 0-100})
    - system.brightness.increase  (args: {"step": int, default 10})
    - system.brightness.decrease  (args: {"step": int, default 10})
    - system.brightness.auto_on
    - system.brightness.auto_off

    Vibrate Actions:
    - system.vibrate.start        (args: {"duration_ms": int})
    - system.vibrate.cancel

    Do Not Disturb Actions:
    - system.dnd.get
    - system.dnd.set              (args: {"mode": str})

    Rotation Actions:
    - system.rotation.get
    - system.rotation.lock        (args: {"orientation": str})
    - system.rotation.unlock

    Screen Timeout Actions:
    - system.screen_timeout.get
    - system.screen_timeout.set             (args: {"duration_ms": int})
    - system.screen_timeout.get_supported
    """
    pass



class NetworkBridge(BaseBridge):
    """
    Bridge for networking radios.
    Sub-domains: wifi, bluetooth, hotspot, mobile_data, airplane_mode.

    Action Namespace: network.*

    WiFi Actions:
    - network.wifi.status
    - network.wifi.enable
    - network.wifi.disable
    - network.wifi.connect    (args: {"ssid": str, "password": str})
    - network.wifi.disconnect

    Bluetooth Actions:
    - network.bluetooth.status
    - network.bluetooth.enable
    - network.bluetooth.disable
    - network.bluetooth.pair   (args: {"device_id": str})
    - network.bluetooth.unpair (args: {"device_id": str})

    Mobile Data Actions:
    - network.mobile_data.status
    - network.mobile_data.enable
    - network.mobile_data.disable

    Hotspot Actions:
    - network.hotspot.status
    - network.hotspot.enable
    - network.hotspot.disable

    Airplane Mode Actions:
    - network.airplane.status
    - network.airplane.enable
    - network.airplane.disable
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


# ── Pack C: Communication Bridges ─────────────────────────────────────────────

class CallBridge(BaseBridge):
    """
    Bridge for telephony call control.
    Sub-domain: phone calls.

    Action Namespace: telephony.phone.*

    Actions:
    - telephony.phone.status               — current call state
    - telephony.phone.call   (args: {"number": str})
    - telephony.phone.end
    - telephony.phone.reject
    """
    pass


class SMSBridge(BaseBridge):
    """
    Bridge for SMS messaging.
    Sub-domain: sms.

    Action Namespace: telephony.sms.*

    Actions:
    - telephony.sms.read     (args: {"message_id": str})
    - telephony.sms.search   (args: {"query": str})
    - telephony.sms.send     (args: {"number": str, "body": str})
    - telephony.sms.delete   (args: {"message_id": str})
    """
    pass


class ContactsBridge(BaseBridge):
    """
    Bridge for contact book management.
    Sub-domain: contacts.

    Action Namespace: telephony.contacts.*

    Actions:
    - telephony.contacts.read    (args: {"contact_id": str})
    - telephony.contacts.search  (args: {"query": str})
    - telephony.contacts.create  (args: {"name": str, "number": str})
    - telephony.contacts.update  (args: {"contact_id": str, "name": str, "number": str})
    - telephony.contacts.delete  (args: {"contact_id": str})
    """
    pass


class NotificationBridge(BaseBridge):
    """
    Bridge for notification management.
    Sub-domain: notifications.

    Action Namespace: notification.*

    Actions:
    - notification.read
    - notification.dismiss  (args: {"notification_id": str})
    - notification.clear
    - notification.reply    (args: {"notification_id": str, "text": str})
    """
    pass
