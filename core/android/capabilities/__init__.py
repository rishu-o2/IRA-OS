from .alarm import AlarmCapability
from .application import ApplicationCapability
from .battery import BatteryCapability
from .bluetooth import BluetoothCapability
from .brightness import BrightnessCapability
from .calendar import CalendarCapability
from .call import CallCapability, PhoneReadCapability, PhoneWriteCapability
from .camera import CameraCapability
from .clipboard import ClipboardCapability
from .contacts import ContactsCapability, ContactsReadCapability, ContactsWriteCapability
from .device import DeviceCapability
from .do_not_disturb import DoNotDisturbCapability
from .files import FilesCapability
from .flashlight import FlashlightCapability
from .location import LocationCapability
from .media import MediaCapability
from .notification import NotificationCapability, NotificationReadCapability, NotificationWriteCapability
from .rotation import RotationCapability
from .screen_timeout import ScreenTimeoutCapability
from .sms import SmsCapability, SmsReadCapability, SmsWriteCapability
from .vibrate import VibrateCapability
from .volume import VolumeCapability
from .wifi import WifiCapability
from .mobile_data import MobileDataCapability
from .hotspot import HotspotCapability
from .airplane_mode import AirplaneModeCapability

__all__ = [
    # ── Pre-Pack ──
    "BrightnessCapability",
    "FlashlightCapability",
    "VolumeCapability",
    "VibrateCapability",
    "RotationCapability",
    "ScreenTimeoutCapability",
    "DoNotDisturbCapability",
    # ── Pack A ──
    "WifiCapability",
    "BluetoothCapability",
    "MobileDataCapability",
    "HotspotCapability",
    "AirplaneModeCapability",
    # ── Pack C: Communication ──
    "PhoneReadCapability",
    "PhoneWriteCapability",
    "SmsReadCapability",
    "SmsWriteCapability",
    "ContactsReadCapability",
    "ContactsWriteCapability",
    "NotificationReadCapability",
    "NotificationWriteCapability",
    # ── Legacy aliases ──
    "CallCapability",
    "SmsCapability",
    "ContactsCapability",
    "NotificationCapability",
    # ── Other ──
    "AlarmCapability",
    "CalendarCapability",
    "CameraCapability",
    "FilesCapability",
    "MediaCapability",
    "LocationCapability",
    "ApplicationCapability",
    "ClipboardCapability",
    "BatteryCapability",
    "DeviceCapability",
]

