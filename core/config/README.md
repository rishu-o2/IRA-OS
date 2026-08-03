# IRA OS Configuration Subsystem

The Configuration Subsystem acts as the strictly-typed, unified source of truth for the IRA OS environment.

## Overview
It aggregates configuration variables from multiple sources and applies strict validation before exposing them as immutable Dataclasses.

## Features
- **Hierarchical Priority**: Merges configurations strictly via Defaults → JSON → Environment Variables → Runtime Overrides.
- **Strict Typing**: Fails fast if types cannot be coerced (e.g., providing a string for an integer port).
- **Environment Aware**: Supports `DEVELOPMENT`, `TESTING`, and `PRODUCTION` contexts natively.
- **Secret Masking**: Sensitive variables use `SecretValue` to actively prevent leakage into logs via `print()` or string formatting.
- **DI Integration**: Tightly coupled with the IRA OS Dependency Injection Container to serve specific sub-configurations to modular components.

## Usage

```python
from core.config import ConfigurationManager

manager = ConfigurationManager()

# Load and validate configs from config.json and os.environ
manager.load("config.json")

# Retrieve typed subsets
server_config = manager.section(ServerConfig)
print(server_config.port) 

# Secrets require explicit unwrapping
api_key = manager.section(SecurityConfig).api_key
print(api_key.get_secret_value()) # Prints real value
print(api_key) # Prints SecretValue(******)
```
