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


class SecurityLevel(Enum):
    """Security classification for Android Capabilities."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class CapabilityDescriptor:
    id: str
    name: str
    description: str
    version: str
    security_level: SecurityLevel
    required_permissions: tuple[str, ...] = ()
    requires_confirmation: bool = False
    supported_actions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class AndroidDeviceInfo:
    sdk_version: int
    model: str
    manufacturer: str
