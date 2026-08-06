# Plugin & Capability Framework

## Overview
The Plugin Framework makes IRA OS extensible. It allows new capabilities to be registered dynamically without hardcoding them into the OS.

> **The Plugin Framework handles discovery, validation, and lifecycle management. It never executes the plugins.**

## Architecture Position

```
Workflow Engine
  ↓
Permission Kernel
  ↓
Plugin Framework      ← Discovery & Lifecycle
  ↓
Tool Runtime          ← Actual Execution
```

## Canonical Pipeline

1. **Plugin Request**
2. **Validation**
3. **Plugin Discovery**
4. **Metadata Validation**
5. **Registry Update**
6. **Lifecycle Transition**
7. **Publish Events**
8. **Plugin Result**

## Responsibilities
- Discover plugins (built-in, local, remote).
- Validate plugin manifests and metadata.
- Maintain a registry of available and active plugins.
- Manage state transitions (load, unload, enable, disable).

## Non-Responsibilities
- Does NOT execute tools or capabilities.
- Does NOT interact with Android/Windows platforms directly.
- Does NOT perform planning or workflow orchestration.

## Components
| Component | Contract | Scaffolding Implementation |
|---|---|---|
| Manager | `PluginManager` | `PluginManagerImpl` |
| Loader | `PluginLoader` | `DefaultPluginLoader` |
| Registry | `PluginRegistry` | `InMemoryPluginRegistry` |
| Validator | `PluginValidator` | `DefaultPluginValidator` |
| Health | `PluginHealthTracker`| `DefaultPluginHealthTracker` |
