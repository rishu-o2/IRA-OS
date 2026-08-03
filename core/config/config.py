from typing import Any, Dict, Type, TypeVar, Optional
from .schema import IRAConfig, KernelConfig, ServerConfig, LoggingConfig, SecurityConfig, LLMConfig, DatabaseConfig, PluginConfig, AndroidConfig, DesktopConfig, IdentityConfig
from .loader import ConfigLoader
from .providers import DictProvider, JsonFileProvider, EnvVarProvider
from .defaults import (
    DEFAULT_PORT, DEFAULT_HOST, DEFAULT_TIMEOUT, DEFAULT_MAX_HISTORY, 
    DEFAULT_EVENT_LIMIT, DEFAULT_MODEL, DEFAULT_TEMPERATURE, 
    DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT, DEFAULT_SESSION_TIMEOUT
)
from .validator import Validator
from .environment import Environment
from core.container import ContainerProtocol, Module

T = TypeVar('T')

class ConfigurationManager:
    """
    The Single Source of Truth for IRA OS configuration.
    Loads, validates, and provides strictly typed configuration sections.
    """
    def __init__(self):
        self._config: Optional[IRAConfig] = None
        self._runtime_overrides: Dict[str, Any] = {}
        
    def get_default_dict(self) -> Dict[str, Any]:
        """Constructs the default hierarchy matching the schema."""
        return {
            "kernel": {"event_limit": DEFAULT_EVENT_LIMIT},
            "server": {"host": DEFAULT_HOST, "port": DEFAULT_PORT, "timeout": DEFAULT_TIMEOUT},
            "logging": {"level": DEFAULT_LOG_LEVEL, "format": DEFAULT_LOG_FORMAT},
            "security": {"api_key": None, "allowed_origins": []},
            "llm": {"model": DEFAULT_MODEL, "temperature": DEFAULT_TEMPERATURE, "max_history": DEFAULT_MAX_HISTORY, "provider_key": None},
            "database": {"connection_string": "sqlite:///:memory:", "max_connections": 10},
            "plugin": {"enabled": True, "plugin_dir": "plugins"},
            "android": {"enabled": False, "sync_interval": 60},
            "desktop": {"enabled": True, "theme": "dark"},
            "identity": {"session_timeout": DEFAULT_SESSION_TIMEOUT}
        }

    def load(self, json_path: str = "config.json") -> IRAConfig:
        """
        Loads configuration applying merge priorities:
        Defaults -> JSON -> Env Vars -> Runtime Overrides
        Validates before boot.
        """
        loader = ConfigLoader()
        
        # Priority 1: Defaults
        loader.add_provider(DictProvider(self.get_default_dict()))
        
        # Priority 2: JSON File
        loader.add_provider(JsonFileProvider(json_path))
        
        # Priority 3: Environment Variables
        loader.add_provider(EnvVarProvider(prefix="IRA_"))
        
        # Priority 4: Runtime Overrides
        loader.add_provider(DictProvider(self._runtime_overrides))
        
        raw_data = loader.load_raw()
        
        # Validate and Build
        self._config = Validator.validate_and_build(IRAConfig, raw_data)
        return self._config

    def reload(self, json_path: str = "config.json") -> IRAConfig:
        """Reload configuration from disk and environment."""
        return self.load(json_path)

    def validate(self, json_path: str = "config.json") -> None:
        """Dry-run validation without setting active config."""
        manager = ConfigurationManager()
        manager._runtime_overrides = self._runtime_overrides
        manager.load(json_path)

    def override(self, overrides: Dict[str, Any]) -> None:
        """Apply a runtime override map (nested dict). Must call load() to apply."""
        # Simple deep merge into runtime overrides
        loader = ConfigLoader()
        self._runtime_overrides = loader._deep_merge(self._runtime_overrides, overrides)

    def section(self, section_type: Type[T]) -> T:
        """Retrieves a strongly typed section. E.g., .section(ServerConfig)."""
        if not self._config:
            raise RuntimeError("Configuration has not been loaded.")
            
        # Match type
        for field in self._config.__dataclass_fields__:
            val = getattr(self._config, field)
            if isinstance(val, section_type):
                return val
                
        raise ValueError(f"No configuration section of type {section_type.__name__}")

    def get(self) -> IRAConfig:
        """Get the full IRAConfig root."""
        if not self._config:
            raise RuntimeError("Configuration has not been loaded.")
        return self._config


class ConfigModule(Module):
    """
    DI Container integration module for configuration.
    Registers individual configuration sections (ServerConfig, KernelConfig, etc.)
    as singletons, preventing global access to the root manager.
    """
    def __init__(self, manager: ConfigurationManager):
        self.manager = manager
        if not self.manager._config:
            self.manager.load()

    def configure(self, container: ContainerProtocol) -> None:
        config = self.manager.get()
        # Register the whole config
        container.register_instance(IRAConfig, config)
        
        # Register sections individually to encourage component isolation
        container.register_instance(KernelConfig, config.kernel)
        container.register_instance(ServerConfig, config.server)
        container.register_instance(LoggingConfig, config.logging)
        container.register_instance(SecurityConfig, config.security)
        container.register_instance(LLMConfig, config.llm)
        container.register_instance(DatabaseConfig, config.database)
        container.register_instance(PluginConfig, config.plugin)
        container.register_instance(AndroidConfig, config.android)
        container.register_instance(DesktopConfig, config.desktop)
        container.register_instance(IdentityConfig, config.identity)
