from dataclasses import dataclass
from typing import Any, Mapping

from core.events import Event


@dataclass(frozen=True, kw_only=True)
class ExecutionStarted(Event):
    execution_id: str
    capability_id: str


@dataclass(frozen=True, kw_only=True)
class ExecutionCompleted(Event):
    execution_id: str
    success: bool
    result_data: Any


@dataclass(frozen=True, kw_only=True)
class ExecutionFailed(Event):
    execution_id: str
    error: str


@dataclass(frozen=True, kw_only=True)
class CapabilityRegistered(Event):
    capability_id: str
    capability_name: str


@dataclass(frozen=True, kw_only=True)
class CapabilityUnregistered(Event):
    capability_id: str
