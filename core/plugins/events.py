from dataclasses import dataclass
from typing import Any, Mapping

from core.events import Event


@dataclass(frozen=True, kw_only=True)
class PluginDiscovered(Event):
    plugin_id: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class PluginLoaded(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginEnabled(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginDisabled(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginUnloaded(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginRegistered(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginRemoved(Event):
    plugin_id: str


@dataclass(frozen=True, kw_only=True)
class PluginValidationFailed(Event):
    plugin_id: str
    error: str
