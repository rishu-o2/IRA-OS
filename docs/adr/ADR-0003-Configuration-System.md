# Architecture Decision Record 0003: Configuration System

## Title
ADR-0003: Configuration System Architecture

## Status
Accepted

## Date
2026-08-03

## Context
IRA OS is modularizing its architecture. All system components require configuration variables, feature flags, environment awareness, and secrets. Having components source their configuration independently (e.g., by reading `os.environ` randomly throughout the code) creates scattered security risks, lack of discoverability, untestable states, and impossible validation. A robust, strictly typed Configuration subsystem must be introduced as a kernel module to act as the single source of truth.

## Decision
We implemented a hierarchical, immutable, and strictly typed Configuration System.

Key design choices:
1. **Schema Definition**: Utilizes `dataclasses` (frozen) to provide explicit typings and immutability.
2. **Standard Library Only**: Relies on `json` and `os.environ`. We explicitly rejected YAML and INI formats to keep the kernel lightweight and free of external dependencies.
3. **Deep Merge Priority**: Defaults → JSON File → Environment Variables → Runtime Overrides.
4. **Secret Wrapper**: The `SecretValue` wrapper replaces native strings for sensitive variables, explicitly overriding `__repr__` and `__str__` to output `******`.
5. **Component Isolation**: The configuration is split into domains (e.g., `ServerConfig`, `DatabaseConfig`). Components inject only the specific dataclass they require via the DI container, avoiding a global monolithic `Config` object dependency.
6. **Pre-Boot Validation**: A validation layer coerces environment string inputs, checks for missing requirements, and applies domain rules (e.g., Port limits) before the application is permitted to start.

## Alternatives Considered
- **Pydantic**: Rejected. While it offers excellent validation, it introduces a significant external dependency, violating the requirement to use the Python standard library for kernel modules.
- **Dynaconf / OmegaConf**: Rejected. They are overly complex and introduce third-party dependencies.
- **Global Config Singleton**: Rejected. A globally accessed configuration object tight-couples components. We opted for targeted Dependency Injection.

## Consequences
- **Positive**: Configurations are safe, typed, and predictable. Secrets cannot be accidentally logged. The system will fail fast on misconfiguration.
- **Negative**: Adds initial overhead when defining new configuration variables as they must be declared in `schema.py`, defaults updated, and properly nested.

## Version
v1.2.0
