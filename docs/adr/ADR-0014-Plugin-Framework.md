# Architecture Decision Record 0014: Plugin & Capability Framework

## Title
ADR-0014: Plugin & Capability Framework

## Status
Accepted

## Date
2026-08-06

## Context
IRA OS is designed to be an extensible operating system, but hardcoding capabilities directly into the Tool Runtime breaks the open-closed principle. To support an ecosystem of first-party and third-party tools, we need a standard subsystem for discovering and managing plugins.

## Decision
Introduce the Plugin & Capability Framework, positioned between the Permission Kernel and the Tool Runtime.

### Structural Decisions Made

1. **State Machine Lifecycle:** Plugins move through a strict lifecycle: `DISCOVERED` -> `LOADED` -> `ENABLED`. They can also be `DISABLED` or `UNLOADED`.
2. **Stateless Execution Boundary:** The Plugin Framework does not execute plugin code. It simply tracks metadata and state. The `Tool Runtime` is responsible for querying enabled capabilities and executing them.
3. **Expanded Manifests:** `PluginManifest` includes robust metadata (version, author, type, dependencies, capabilities, API version) to support future marketplace features.
4. **Dedicated Health Tracker:** The `PluginHealthTracker` decouples health monitoring from the manager pipeline logic.
5. **Deferred Dynamic Loading:** True dynamic discovery (filesystem scanning, importlib, remote fetches) is explicitly deferred. For API freeze, the loader provides a scaffolding `builtin` plugin list.

## Consequences
- Positive: Clear separation between plugin lifecycle management and plugin execution.
- Positive: Capabilities can be added without modifying the core IRA OS source code.
- Negative: True marketplace and dynamic installation logic remains as technical debt.
