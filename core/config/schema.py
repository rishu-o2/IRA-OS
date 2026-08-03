from dataclasses import dataclass, field
from .secrets import SecretValue

@dataclass(frozen=True)
class IdentityConfig:
    session_timeout: int
    
@dataclass(frozen=True)
class KernelConfig:
    event_limit: int

@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    timeout: float

@dataclass(frozen=True)
class LoggingConfig:
    level: str
    format: str

@dataclass(frozen=True)
class SecurityConfig:
    api_key: SecretValue | None = None
    allowed_origins: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class LLMConfig:
    model: str
    temperature: float
    max_history: int
    provider_key: SecretValue | None = None

@dataclass(frozen=True)
class DatabaseConfig:
    connection_string: SecretValue | str
    max_connections: int = 10

@dataclass(frozen=True)
class PluginConfig:
    enabled: bool = True
    plugin_dir: str = "plugins"

@dataclass(frozen=True)
class AndroidConfig:
    enabled: bool = False
    sync_interval: int = 60

@dataclass(frozen=True)
class DesktopConfig:
    enabled: bool = True
    theme: str = "dark"

@dataclass(frozen=True)
class IRAConfig:
    kernel: KernelConfig
    server: ServerConfig
    logging: LoggingConfig
    security: SecurityConfig
    llm: LLMConfig
    database: DatabaseConfig
    plugin: PluginConfig
    android: AndroidConfig
    desktop: DesktopConfig
    identity: IdentityConfig
