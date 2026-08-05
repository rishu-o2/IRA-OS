from dataclasses import dataclass, field
from typing import Any
from core.events.models import Event


@dataclass(frozen=True, kw_only=True)
class MemoryStored(Event):
    memory_id: str
    owner_id: str
    namespace: str

    @property
    def name(self) -> str:
        return "MemoryStored"


@dataclass(frozen=True, kw_only=True)
class MemoryUpdated(Event):
    memory_id: str
    owner_id: str
    namespace: str

    @property
    def name(self) -> str:
        return "MemoryUpdated"


@dataclass(frozen=True, kw_only=True)
class MemoryDeleted(Event):
    memory_id: str
    owner_id: str
    namespace: str

    @property
    def name(self) -> str:
        return "MemoryDeleted"


@dataclass(frozen=True, kw_only=True)
class MemoryAccessed(Event):
    memory_id: str
    owner_id: str
    namespace: str

    @property
    def name(self) -> str:
        return "MemoryAccessed"


@dataclass(frozen=True, kw_only=True)
class MemoryForgotten(Event):
    memory_id: str
    owner_id: str
    namespace: str

    @property
    def name(self) -> str:
        return "MemoryForgotten"
