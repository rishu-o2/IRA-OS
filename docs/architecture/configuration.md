# Configuration Subsystem Architecture

## Overview
The Configuration System is the single source of truth for all of IRA OS. It is a strictly typed, immutable, and hierarchical subsystem built exclusively on the Python standard library. It sits at the kernel level alongside the DI Container and Event Bus, providing safe environment-aware settings for all other modules.

## Architecture

The system is separated into clear domains:
1. **Providers (`providers.py`)**: Responsible for sourcing configuration dictionaries from Defaults, JSON files, Environment Variables, and Runtime Overrides.
2. **Loader (`loader.py`)**: Fetches configurations from Providers and deeply merges them in priority order.
3. **Validator (`validator.py`)**: Receives the raw deeply merged dictionary and maps it onto the strongly typed dataclass schema (`schema.py`). Validates types, coerces environment strings to target types, enforces missing field constraints, and applies rules.
4. **Secrets (`secrets.py`)**: Sensitive variables are wrapped in `SecretValue`. This class overrides `__str__` and `__repr__` to emit `******`, ensuring secrets never leak into logs. The real value is exclusively accessible via `.get_secret_value()`.
5. **Manager (`config.py`)**: The `ConfigurationManager` facade controls loading, provides targeted `.section(Class)` access, and can be integrated into the DI Container via `ConfigModule`.

## Provider Priority
The Loader applies a strict merge priority (lowest to highest). Later providers override earlier ones:
1. **Defaults**: Sourced from `defaults.py`.
2. **JSON File**: Sourced from `config.json` via `JsonFileProvider`.
3. **Environment Variables**: Sourced from `os.environ` prefixed with `IRA_` via `EnvVarProvider` (e.g., `IRA_SERVER_PORT`).
4. **Runtime Overrides**: Passed dynamically via `manager.override()`.

## Deep Merge Strategy
The `ConfigLoader._deep_merge` algorithm recursively walks dictionaries. It ensures that overriding a single key in a nested structure (e.g., `server.port`) does not obliterate the sibling keys (e.g., `server.host`).

## Validation Before Boot
If the system detects type mismatches (e.g., expected `int`, got `"abc"`), domain rule violations (e.g., `port = 70000`), or missing required sections without defaults, it raises a `ValidationError` immediately during `manager.load()`. This guarantees the application refuses to start with invalid configurations.

## Dependency Injection (DI) Integration
Configuration should rarely be accessed globally. Instead, the `ConfigModule` registers specific, isolated config slices into the DI Container. 
Components declare dependencies only on the segment they need (e.g., `def __init__(self, config: LLMConfig):`). This prevents broad coupling to the entire `IRAConfig` tree.

## Future Extension Points
The `ConfigProvider` protocol is designed to be easily extensible. Future implementations could include:
- `HashicorpVaultProvider` for fetching dynamic secrets.
- `ConsulProvider` for distributed configuration.
- `S3Provider` for remote initial configurations.
