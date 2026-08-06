# Plugin Framework Architecture

## Overview
The Plugin Framework handles the discovery, validation, registration, and lifecycle management of plugins in IRA OS.

## Architecture Position

```
Kernel
├── Identity
├── Memory
├── Planner
├── Brain
├── Workflow Engine
├── Security Layer
└── Plugin Framework     ← This subsystem
        ↓
    Tool Runtime
        ↓
    Platform Layer
```

## Dependency Direction
The Plugin Framework sits above the Tool Runtime. It never calls the Brain, Identity, or Android runtimes directly.

## Canonical Pipeline
1. **Plugin Request** - Instruction to discover, load, or transition state.
2. **Validation** - Input sanity checks.
3. **Plugin Discovery** - Loader identifies available plugins.
4. **Metadata Validation** - Validator ensures manifests are well-formed.
5. **Registry Update** - In-memory registry is mutated.
6. **Lifecycle Transition** - State changes from DISCOVERED -> LOADED -> ENABLED.
7. **Publish Events** - Event bus notification of state changes.
8. **Plugin Result** - Returned outcome.

## Components

| Component | Responsibility |
|---|---|
| `PluginManager` | Pipeline orchestration and lifecycle |
| `PluginLoader` | Discovers available plugins |
| `PluginRegistry` | Manages in-memory descriptors and states |
| `PluginValidator` | Ensures metadata is correct |
| `PluginHealthTracker`| Evaluates subsystem health separate from execution logic |

## Public API

Consumers interact with contracts and models only:
```python
manager = await container.resolve(PluginManager)
await manager.start()

await manager.discover()
await manager.load(PluginRequest(plugin_id="core.example.plugin"))
await manager.enable("core.example.plugin")
```
