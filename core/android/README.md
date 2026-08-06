# Android Runtime Subsystem

## Overview

The Android Runtime is the platform adapter layer for IRA OS on Android.

Its single responsibility is to expose Android device capabilities to the Tool Runtime as abstract `Capability` objects.

**Android Runtime does not know what the user wants. It only knows how Android can fulfill a capability request.**

## Architecture Position

```
Brain
  ↓
Tool Runtime
  ↓
Android Runtime
  ↓
Android Capabilities (Call, SMS, Camera, ...)
```

## Components

| Component | File | Responsibility |
|---|---|---|
| `AndroidCapability` | `contracts.py` | Abstract interface for all Android capabilities |
| `AndroidAdapter` | `contracts.py` + `adapter.py` | Translates Tool Runtime requests into Android calls |
| `AndroidRegistry` | `contracts.py` + `registry.py` | Registers, discovers, and queries capabilities |
| `AndroidHealthTracker` | `health.py` | Independently tracks runtime health state |
| `AndroidRuntimeManager` | `manager.py` | Lifecycle orchestrator |
| `AndroidModule` | `android_module.py` | DI container wiring |

## Capabilities

All capabilities live in `core/android/capabilities/` and are fully abstract. Implementations are provided in later milestones.

## Non-Responsibilities

The Android Runtime must **never**:
- Call Brain directly
- Perform planning
- Store memory
- Know conversation state
- Contain business logic

## Extension

Future platform capabilities (Call, SMS, Camera etc.) implement `AndroidCapability` and register themselves into the `AndroidRegistry`. The bridging layer (`DefaultAndroidAdapter`) automatically makes them available to the Tool Runtime.
