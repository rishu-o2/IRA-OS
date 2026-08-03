from typing import Any, Dict
from .providers import ConfigProvider
import copy

class ConfigLoader:
    """
    Loads configuration from multiple providers and performs a deep merge
    in priority order.
    """
    def __init__(self):
        self.providers: list[ConfigProvider] = []
        
    def add_provider(self, provider: ConfigProvider) -> None:
        """Add a provider. Order added determines merge priority (lowest to highest)."""
        self.providers.append(provider)
        
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively deep merge two dictionaries."""
        merged = copy.deepcopy(base)
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    def load_raw(self) -> Dict[str, Any]:
        """Loads and merges raw dictionaries from all providers in order."""
        merged_config: Dict[str, Any] = {}
        for provider in self.providers:
            provider_data = provider.load()
            merged_config = self._deep_merge(merged_config, provider_data)
        return merged_config
