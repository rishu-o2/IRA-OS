from .alarm import AlarmCapability
from .application import ApplicationCapability
from .battery import BatteryCapability
from .bluetooth import BluetoothCapability
from .calendar import CalendarCapability
from .call import CallCapability
from .camera import CameraCapability
from .clipboard import ClipboardCapability
from .contacts import ContactsCapability
from .device import DeviceCapability
from .files import FilesCapability
from .location import LocationCapability
from .media import MediaCapability
from .notification import NotificationCapability
from .sms import SmsCapability
from .wifi import WifiCapability

__all__ = [
    "CallCapability",
    "SmsCapability",
    "AlarmCapability",
    "CalendarCapability",
    "NotificationCapability",
    "CameraCapability",
    "ContactsCapability",
    "FilesCapability",
    "MediaCapability",
    "LocationCapability",
    "BluetoothCapability",
    "WifiCapability",
    "ApplicationCapability",
    "ClipboardCapability",
    "BatteryCapability",
    "DeviceCapability",
]
