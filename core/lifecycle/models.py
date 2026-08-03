from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Dict
from .states import ComponentState


@dataclass(frozen=True)
class ComponentHealth:
    """Immutable snapshot of a component's health."""
    state: ComponentState
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ComponentRegistration:
    """Immutable registration details for a component."""
    name: str
    instance: Any
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    critical: bool = True
    startup_timeout: Optional[float] = None
    shutdown_timeout: Optional[float] = None


@dataclass(frozen=True)
class LifecycleResult:
    """Result of a lifecycle operation on a component."""
    success: bool
    error_details: Optional[str] = None


@dataclass(frozen=True)
class StartupReport:
    """Summary of the system startup execution."""
    success: bool
    started_components: List[str]
    failed_component: Optional[str] = None
    error_details: Optional[str] = None


@dataclass(frozen=True)
class ShutdownReport:
    """Summary of the system shutdown execution."""
    success: bool
    stopped_components: List[str]
    errors: Dict[str, str] = field(default_factory=dict)
