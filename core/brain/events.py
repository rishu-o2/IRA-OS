from dataclasses import dataclass

from core.events.models import Event


@dataclass(frozen=True, kw_only=True)
class BrainRequestStarted(Event):
    request_id: str
    user_id: str

    @property
    def name(self) -> str:
        return "BrainRequestStarted"


@dataclass(frozen=True, kw_only=True)
class BrainRequestCompleted(Event):
    request_id: str
    success: bool

    @property
    def name(self) -> str:
        return "BrainRequestCompleted"


@dataclass(frozen=True, kw_only=True)
class BrainRequestFailed(Event):
    request_id: str
    error: str

    @property
    def name(self) -> str:
        return "BrainRequestFailed"
