from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional


class PluginState(Enum):
    """Lifecycle state of a plugin."""
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    REGISTERED = "REGISTERED"
    LOADED = "LOADED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class PluginType(Enum):
    """Type/category of the plugin."""
    BUILTIN = "BUILTIN"
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


class PluginStatus(Enum):
    """Current health/operational status of the plugin."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


@dataclass(frozen=True)
class PluginDependency:
    """A declared dependency on another plugin or core module."""
    dependency_id: str
    min_version: str
    optional: bool = False


@dataclass(frozen=True)
class PluginCapability:
    """A capability advertised by the plugin."""
    capability_id: str
    description: str


@dataclass(frozen=True)
class PluginManifest:
    """The static metadata definition of a plugin."""
    id: str
    name: str
    version: str
    author: str
    description: str
    type: PluginType
    dependencies: List[PluginDependency] = field(default_factory=list)
    capabilities: List[PluginCapability] = field(default_factory=list)
    minimum_os_version: str = "1.0.0"
    api_version: str = "1.0"


@dataclass(frozen=True)
class PluginMetadata:
    """Runtime metadata combining the manifest and discovery info."""
    manifest: PluginManifest
    source_path: str
    checksum: str


@dataclass(frozen=True)
class PluginDescriptor:
    """Internal registry representation of a plugin."""
    plugin_id: str
    metadata: PluginMetadata
    state: PluginState
    status: PluginStatus


@dataclass(frozen=True)
class PluginRequest:
    """A request to load or enable a specific plugin."""
    plugin_id: str
    configuration: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginResult:
    """Result of a plugin lifecycle transition."""
    plugin_id: str
    success: bool
    state: PluginState
    error_message: Optional[str] = None


@dataclass(frozen=True)
class PluginContext:
    """Context provided to plugins during their lifecycle transitions."""
    plugin_id: str
    config: Mapping[str, Any] = field(default_factory=dict)
