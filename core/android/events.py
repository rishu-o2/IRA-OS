from dataclasses import dataclass
from core.events import Event
from .models import AndroidRuntimeStatus

@dataclass(frozen=True, kw_only=True)
class AndroidRuntimeStarted(Event):
    """Published when the Android Runtime successfully starts."""
    pass

@dataclass(frozen=True, kw_only=True)
class AndroidRuntimeStopped(Event):
    """Published when the Android Runtime stops."""
    pass

@dataclass(frozen=True, kw_only=True)
class AndroidCapabilityRegistered(Event):
    capability_id: str
    capability_name: str

@dataclass(frozen=True, kw_only=True)
class AndroidCapabilityRemoved(Event):
    capability_id: str

@dataclass(frozen=True, kw_only=True)
class AndroidHealthChanged(Event):
    previous_status: AndroidRuntimeStatus
    current_status: AndroidRuntimeStatus
    details: str
