from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


@dataclass(frozen=True)
class CapabilityResult:
    """Immutable result structure for all capabilities."""
    capability_id: str
    success: bool
    data: Mapping[str, Any] = field(default_factory=dict)
    error_code: str = ""
    error_message: str = ""
