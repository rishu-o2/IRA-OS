from contextvars import ContextVar
from typing import Optional
from dataclasses import dataclass, field
import uuid

@dataclass
class LogContext:
    """Represents the active logging context for the current execution scope."""
    correlation_id: str | None = None
    event_id: str | None = None
    scope: str | None = None

_log_context: ContextVar[LogContext] = ContextVar('log_context', default=LogContext())


def get_context() -> LogContext:
    """Get the current log context for this task/coroutine."""
    return _log_context.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation_id for the current execution context."""
    ctx = _log_context.get()
    new_ctx = LogContext(
        correlation_id=correlation_id,
        event_id=ctx.event_id,
        scope=ctx.scope
    )
    _log_context.set(new_ctx)


def set_event_id(event_id: str) -> None:
    """Set the event_id for the current execution context."""
    ctx = _log_context.get()
    new_ctx = LogContext(
        correlation_id=ctx.correlation_id,
        event_id=event_id,
        scope=ctx.scope
    )
    _log_context.set(new_ctx)


def new_correlation_id() -> str:
    """Generate and set a new UUID correlation_id."""
    cid = str(uuid.uuid4())
    set_correlation_id(cid)
    return cid


class LogScope:
    """
    Context manager for scoped log contexts.
    Restores the previous context on exit.
    """
    def __init__(self, scope: str, correlation_id: str | None = None):
        self._scope = scope
        self._correlation_id = correlation_id
        self._token = None

    def __enter__(self) -> 'LogScope':
        ctx = _log_context.get()
        new_ctx = LogContext(
            correlation_id=self._correlation_id or ctx.correlation_id,
            event_id=ctx.event_id,
            scope=self._scope
        )
        self._token = _log_context.set(new_ctx)
        return self

    def __exit__(self, *args) -> None:
        if self._token is not None:
            _log_context.reset(self._token)
