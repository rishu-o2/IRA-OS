from dataclasses import dataclass
from typing import Any, Mapping

from core.events import Event


@dataclass(frozen=True, kw_only=True)
class ExecutionRequested(Event):
    """Published when an ExecutionCommand enters the pipeline."""
    command_id: str
    capability_id: str


@dataclass(frozen=True, kw_only=True)
class ExecutionAuthorized(Event):
    """Published when the Security Kernel has granted permission."""
    command_id: str
    capability_id: str


@dataclass(frozen=True, kw_only=True)
class ExecutionDispatched(Event):
    """Published when the command has been forwarded to the Runtime."""
    command_id: str
    capability_id: str


@dataclass(frozen=True, kw_only=True)
class ExecutionSucceeded(Event):
    """Published on successful capability execution."""
    command_id: str
    capability_id: str
    result_data: Any = None


@dataclass(frozen=True, kw_only=True)
class ExecutionDenied(Event):
    """Published when the Security Kernel denies a command."""
    command_id: str
    capability_id: str
    denial_reason: str


@dataclass(frozen=True, kw_only=True)
class ExecutionFailed(Event):
    """Published when the Runtime raises an error during execution."""
    command_id: str
    capability_id: str
    error: str
