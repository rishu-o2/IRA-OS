from dataclasses import dataclass
from enum import Enum


class AndroidRuntimeStatus(Enum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"


class CapabilityState(Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass(frozen=True)
class CapabilityDescriptor:
    id: str
    name: str
    description: str
    version: str
    required_permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AndroidDeviceInfo:
    sdk_version: int
    model: str
    manufacturer: str
